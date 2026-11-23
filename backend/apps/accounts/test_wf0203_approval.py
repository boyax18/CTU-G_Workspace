"""WF-02.03 Approve applicant account: D-44 to D-51 (owner-approved 17 Nov 2026).

Run: python manage.py test apps.accounts.test_wf0203_approval --settings=config.test_settings --noinput
Disposable MySQL only. Approval stays unmounted in config.urls (D-46); these tests reach the HTTP
view through the loopback local-review URLconf (config.review_local_urls), never config.urls.
"""

import base64
import json
import os
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import Resolver404, resolve
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions
from apps.access_control.writer_boundary import WriterBoundaryUnavailable

from . import registration_review
from .models import Account, UserProfile
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import process_one
from .registration_review import (
    RegistrationApprovalNotAllowed, RegistrationReviewDenied, approve_registration, reject_registration,
)

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.03 tests require --settings=config.test_settings.")

STUDENT = {"confirmed": True, "source": "ctu_main_system_records"}
INSTRUCTOR = {"confirmed": True, "source": "institutional_employment_records"}
BODY = {"eligibility_confirmed": True, "eligibility_source": "ctu_main_system_records"}
PASSWORD = "Copper!River7799"
BASE = "/api/v1/admin/registration-requests/"
APPLICANT_EMAIL = "applicant.wf0203@example.edu"


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing WF-02.03 fixtures on an unexpected database.")


def build_world():
    verify_database()
    accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
    Service.objects.create(service_code="access_control", service_name="Access Control")
    roles = {name: Role.objects.create(role_name=name) for name in ("Student", "Instructor", "Admin")}
    reviewer = Account.objects.create_user(school_id="WF0203-REVIEWER", password=PASSWORD)
    Account.objects.filter(pk=reviewer.pk).update(is_active=True, request_status="Approved")
    reviewer.refresh_from_db()
    AccountRole.objects.create(account=reviewer, role=roles["Admin"])
    perms = {}
    for action in ("read", "approve", "reject"):
        perms[action] = Permission.objects.create(
            service=accounts, permission_code=f"accounts.registration_requests.{action}",
            permission_name=f"Registration requests {action}", module_name="registration_requests",
            action_name=action,
        )
        RolePermission.objects.create(role=roles["Admin"], permission=perms[action])
    return SimpleNamespace(roles=roles, reviewer=reviewer, perms=perms)


def applicant(school_id, role, *, email=APPLICANT_EMAIL, proof="same", profile=True):
    """A Pending applicant. proof: "same" (verified), None (no proof) or another address."""
    account = Account.objects.create_user(school_id=school_id, password=PASSWORD, requested_role=role)
    proof_address = email if proof == "same" else proof
    Account.objects.filter(pk=account.pk).update(
        email=email,
        email_verified_at=timezone.now() if proof_address else None,
        email_verified_address=proof_address,
    )
    if profile:
        UserProfile.objects.create(account=account, first_name="Ada", last_name="Reyes")
    account.refresh_from_db()
    return account


GATES = dict(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False,
)


@override_settings(**GATES)
class ApprovalServicePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = build_world()

    def setUp(self):
        self.outbox_key = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.outbox_key.start()
        self.addCleanup(self.outbox_key.stop)
        self.target = applicant("WF0203-STUDENT", self.w.roles["Student"])

    def assert_untouched(self, target=None):
        target = target or self.target
        target.refresh_from_db()
        self.assertEqual(target.request_status, "Pending")
        self.assertFalse(target.is_active)
        self.assertIsNone(target.reviewed_by_id)
        self.assertIsNone(target.reviewed_at)
        self.assertFalse(AccountRole.objects.filter(account=target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def refuse(self, reason, **kwargs):
        with self.assertRaises(RegistrationApprovalNotAllowed) as caught:
            approve_registration(actor=self.w.reviewer, target_id=self.target.pk, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertNotIn(APPLICANT_EMAIL, str(caught.exception))
        self.assert_untouched()

    def test_student_approval_records_state_role_and_attestation_audit(self):
        self.assertEqual(approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT),
                         self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual((self.target.request_status, self.target.is_active), ("Approved", True))
        self.assertEqual(self.target.reviewed_by_id, self.w.reviewer.pk)
        self.assertIsNotNone(self.target.reviewed_at)
        self.assertIsNone(self.target.rejection_reason)
        self.assertEqual(list(AccountRole.objects.filter(account=self.target).values_list("role__role_name", flat=True)),
                         ["Student"])
        self.assertEqual(AccountRole.objects.get(account=self.target).assigned_by_id, self.w.reviewer.pk)
        audit = AccessAuditLog.objects.get()
        self.assertEqual((audit.action, audit.reason), ("account.registration.approve", "account_status_change"))
        self.assertEqual((audit.actor_account_id, audit.target_account_id, audit.role_id),
                         (self.w.reviewer.pk, self.target.pk, self.w.roles["Student"].pk))
        self.assertIsNotNone(audit.created_at)
        self.assertEqual(audit.old_value, {"account_id": self.target.pk, "request_status": "Pending", "is_active": False})
        self.assertEqual(audit.new_value, {
            "account_id": self.target.pk, "request_status": "Approved", "is_active": True,
            "role_id": self.w.roles["Student"].pk, "email_evidence": "verified", "eligibility_confirmed": True,
            "eligibility_subject": "enrollment", "eligibility_source": "ctu_main_system_records",
        })
        self.assertNotIn(APPLICANT_EMAIL, json.dumps([audit.old_value, audit.new_value]))
        self.assertNotIn(self.target.school_id, json.dumps([audit.old_value, audit.new_value]))

    def test_instructor_approval_needs_the_employment_source(self):
        instructor = applicant("WF0203-INSTRUCTOR", self.w.roles["Instructor"], email="staff.wf0203@example.edu")
        with self.assertRaises(RegistrationApprovalNotAllowed):
            approve_registration(actor=self.w.reviewer, target_id=instructor.pk, attestation=STUDENT)
        approve_registration(actor=self.w.reviewer, target_id=instructor.pk, attestation=INSTRUCTOR)
        audit = AccessAuditLog.objects.get()
        self.assertEqual((audit.new_value["eligibility_subject"], audit.new_value["eligibility_source"]),
                         ("employment", "institutional_employment_records"))
        self.assertEqual(list(AccountRole.objects.filter(account=instructor).values_list("role__role_name", flat=True)),
                         ["Instructor"])

    def test_email_proof_matching_ignores_case_only(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_address=APPLICANT_EMAIL.upper())
        approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")

    def test_every_unverified_email_state_is_refused(self):
        states = {
            "no_email": dict(email=None),
            "blank_email": dict(email="   "),
            "no_proof_time": dict(email_verified_at=None),
            "no_proof_address": dict(email_verified_address=None),
            "address_changed": dict(email="changed.wf0203@example.edu"),
        }
        for label, change in states.items():
            with self.subTest(state=label):
                Account.objects.filter(pk=self.target.pk).update(
                    email=APPLICANT_EMAIL, email_verified_at=timezone.now(), email_verified_address=APPLICANT_EMAIL,
                )
                Account.objects.filter(pk=self.target.pk).update(**change)
                self.refuse("email_unverified", attestation=STUDENT)

    def test_invalid_but_self_verified_address_is_refused_for_outbox_delivery(self):
        invalid = "not-an-address"
        Account.objects.filter(pk=self.target.pk).update(
            email=invalid, email_verified_at=timezone.now(), email_verified_address=invalid,
        )
        self.refuse("email_unverified", attestation=STUDENT)

    def test_missing_false_malformed_forged_or_wrong_role_attestations_are_refused(self):
        bad = [
            None, {}, [], "ctu_main_system_records", {"confirmed": True},
            {"source": "ctu_main_system_records"},
            {"confirmed": False, "source": "ctu_main_system_records"},
            {"confirmed": "true", "source": "ctu_main_system_records"},
            {"confirmed": 1, "source": "ctu_main_system_records"},
            {"confirmed": True, "source": "institutional_employment_records"},
            {"confirmed": True, "source": "applicant_upload"},
            {"confirmed": True, "source": ["ctu_main_system_records"]},
            {"confirmed": True, "source": "ctu_main_system_records", "verified_by_workspace": True},
            {"confirmed": True, "source": "ctu_main_system_records", "role": "Admin"},
        ]
        for attestation in bad:
            with self.subTest(attestation=attestation):
                self.refuse("eligibility_unconfirmed", attestation=attestation)
        with self.subTest("omitted"):
            with self.assertRaises(RegistrationApprovalNotAllowed):
                approve_registration(actor=self.w.reviewer, target_id=self.target.pk)
            self.assert_untouched()

    def test_policy_refusal_is_a_denial_for_callers_that_only_know_denials(self):
        self.assertTrue(issubclass(RegistrationApprovalNotAllowed, RegistrationReviewDenied))

    def test_authorization_is_checked_before_policy_and_never_leaks_policy_state(self):
        # Unverified email + reviewer without approve permission: the generic denial wins.
        Account.objects.filter(pk=self.target.pk).update(email_verified_at=None)
        RolePermission.objects.filter(permission=self.w.perms["approve"]).update(is_active=False)
        with self.assertRaises(RegistrationReviewDenied) as caught:
            approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assertNotIsInstance(caught.exception, RegistrationApprovalNotAllowed)
        self.assert_untouched()

    def test_account_deny_overrides_role_grant(self):
        AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["approve"], effect="Deny")
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assert_untouched()

    def test_self_framework_admin_and_stale_targets_are_denied(self):
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.w.reviewer, target_id=self.w.reviewer.pk, attestation=STUDENT)
        approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        with self.assertRaises(RegistrationReviewDenied) as caught:
            approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assertNotIsInstance(caught.exception, RegistrationApprovalNotAllowed)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)
        Account.objects.filter(pk=self.w.reviewer.pk).update(is_superuser=True, is_staff=True)
        other = applicant("WF0203-OTHER", self.w.roles["Student"], email="other.wf0203@example.edu")
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=Account.objects.get(pk=self.w.reviewer.pk), target_id=other.pk,
                                 attestation=STUDENT)
        other.refresh_from_db()
        self.assertEqual(other.request_status, "Pending")

    def test_approval_assigns_only_the_requested_base_role(self):
        approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)
        self.assertFalse(AccountPermission.objects.filter(account=self.target).exists())
        # D-50: Student/Instructor hold no default grants yet (SRS AT-02 unmet, deferred to WF-03).
        self.assertEqual(set(get_effective_permissions(Account.objects.get(pk=self.target.pk))), set())

    def test_audit_failure_rolls_back_the_whole_approval(self):
        with patch("apps.accounts.registration_review.record_access_audit_receipt", side_effect=RuntimeError("audit down")):
            with self.assertRaises(RuntimeError):
                approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assert_untouched()

    def test_d51_writer_enabled_refuses_approval_before_any_transaction(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True), \
                patch("apps.access_control.executor.client.remote_call") as remote:
            with self.assertRaises(WriterBoundaryUnavailable):
                approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
            remote.assert_not_called()
        self.assert_untouched()

    def test_approval_gate_off_refuses(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            with self.assertRaises(registration_review.RegistrationReviewUnavailable):
                approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)
        self.assert_untouched()


@override_settings(**{**GATES, "WORKSPACE_REGISTRATION_OUTBOX_ENABLED": True,
                      "WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION": "v1",
                      "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend"})
class ApprovalNotificationTests(TestCase):
    """D-49: outbox only when enabled; after commit only; never duplicated; no live email."""

    @classmethod
    def setUpTestData(cls):
        cls.w = build_world()

    def setUp(self):
        self.env = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
            "WORKSPACE_OUTBOX_WORKER_ENABLED": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        mail.outbox = []
        self.target = applicant("WF0203-NOTIFY", self.w.roles["Student"])

    def approve(self):
        return approve_registration(actor=self.w.reviewer, target_id=self.target.pk, attestation=STUDENT)

    def assert_untouched(self):
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_outbox_row_is_written_with_the_approval_and_linked_to_its_audit(self):
        self.approve()
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual(row.decision_audit_log_id, AccessAuditLog.objects.get().pk)
        self.assertEqual((row.template_code, row.delivery_status), ("registration.approved", "Pending"))
        self.assertNotIn(APPLICANT_EMAIL.encode(), bytes(row.encrypted_recipient))
        self.assertEqual(len(mail.outbox), 0)  # queued, not sent, inside the decision

    def test_no_outbox_row_or_email_when_outbox_is_disabled(self):
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(registration_review.RegistrationReviewUnavailable):
                    self.approve()
        self.assertEqual(callbacks, [])
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertEqual(len(mail.outbox), 0)
        self.assert_untouched()

    def test_refused_approval_queues_nothing(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_at=None)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RegistrationApprovalNotAllowed):
                self.approve()
        self.assertEqual(callbacks, [])
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_outbox_failure_rolls_back_the_approval(self):
        with patch("apps.accounts.registration_review.record_registration_decision_outbox",
                   side_effect=RuntimeError("outbox unavailable")):
            with self.assertRaises(RuntimeError):
                self.approve()
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_delivery_failure_keeps_the_approval(self):
        self.approve()
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("mail down")):
            self.assertEqual(process_one(), "retry")
        self.target.refresh_from_db()
        self.assertEqual((self.target.request_status, self.target.is_active), ("Approved", True))
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)
        self.assertEqual(RegistrationNotificationOutbox.objects.get().delivery_status, "Retry")

    def test_repeat_approval_never_duplicates_the_notification(self):
        self.approve()
        with self.assertRaises(RegistrationReviewDenied):
            self.approve()
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_legacy_email_flag_cannot_bypass_the_durable_outbox(self):
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
                               WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=True):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                with self.assertRaises(registration_review.RegistrationReviewUnavailable):
                    self.approve()
            self.assertEqual(len(mail.outbox), 0)
            self.assertEqual(len(callbacks), 0)
        self.assert_untouched()


@override_settings(
    ROOT_URLCONF="config.review_local_urls",
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=True,
    **GATES,
)
class ApprovalHTTPContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = build_world()

    def setUp(self):
        self.outbox_key = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.outbox_key.start()
        self.addCleanup(self.outbox_key.stop)
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.w.reviewer)
        self.csrf = "c" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.target = applicant("WF0203-HTTP", self.w.roles["Student"])

    def post(self, body, target_id=None, *, csrf=True, raw=None):
        return self.client.post(
            f"{BASE}{target_id or self.target.pk}/approve/",
            data=raw if raw is not None else json.dumps(body), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": self.csrf} if csrf else {}),
        )

    def assert_pending(self):
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def assert_no_leak(self, response):
        text = response.content.decode()
        for private in (APPLICANT_EMAIL, self.target.school_id, "Ada", "Reyes", "Traceback"):
            self.assertNotIn(private, text)

    def test_success_returns_only_the_decision_and_no_store(self):
        response = self.post(BODY)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {
            "account_id": self.target.pk, "status": "Approved", "notification": "queued",
        })
        self.assertIn("no-store", response["Cache-Control"])

    def test_policy_refusals_are_409_with_fixed_reasons(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_address="other.wf0203@example.edu")
        response = self.post(BODY)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"error": {
            "code": "approval_not_allowed", "reason": "email_unverified",
            "message": "Approval is not allowed for this application."}})
        self.assert_no_leak(response)
        Account.objects.filter(pk=self.target.pk).update(email_verified_address=APPLICANT_EMAIL)
        for body in ({**BODY, "eligibility_confirmed": False},
                     {**BODY, "eligibility_source": "institutional_employment_records"}):
            with self.subTest(body=body):
                response = self.post(body)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["error"]["reason"], "eligibility_unconfirmed")
                self.assert_no_leak(response)
        self.assert_pending()

    def test_malformed_bodies_are_400_and_cannot_choose_role_or_status(self):
        bodies = [
            {}, {"eligibility_confirmed": True}, {"eligibility_source": "ctu_main_system_records"},
            {**BODY, "role_id": self.w.roles["Admin"].pk}, {**BODY, "request_status": "Approved"},
            {**BODY, "eligibility_confirmed": "true"}, {**BODY, "eligibility_confirmed": 1},
            {**BODY, "eligibility_source": "applicant_upload"}, {**BODY, "eligibility_source": ["x"]},
            {**BODY, "eligibility_source": None}, [BODY],
        ]
        for body in bodies:
            with self.subTest(body=body):
                cache.clear()
                response = self.post(body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_request")
        cache.clear()
        self.assertEqual(self.post(None, raw="{not json").status_code, 400)
        self.assert_pending()

    def test_stale_and_unknown_targets_share_one_404(self):
        self.assertEqual(self.post(BODY).status_code, 200)
        stale = self.post(BODY)
        unknown = self.post(BODY, target_id=2_000_000_000)
        self.assertEqual((stale.status_code, unknown.status_code), (404, 404))
        self.assertEqual(stale.json(), unknown.json())
        self.assertEqual(stale.json()["error"]["code"], "request_unavailable")
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_authentication_permission_csrf_and_gates(self):
        self.assertEqual(self.post(BODY, csrf=False).status_code, 403)
        anonymous = Client(enforce_csrf_checks=True)
        anonymous.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        response = anonymous.post(f"{BASE}{self.target.pk}/approve/", data=json.dumps(BODY),
                                  content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 401)
        RolePermission.objects.filter(permission=self.w.perms["approve"]).update(is_active=False)
        response = self.post(BODY)
        self.assertEqual(response.status_code, 403)
        self.assert_no_leak(response)
        RolePermission.objects.filter(permission=self.w.perms["approve"]).update(is_active=True)
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            self.assertEqual(self.post(BODY).status_code, 503)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):  # D-51
            response = self.post(BODY)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "review_unavailable")
        self.assert_pending()

    def test_permission_is_checked_before_the_body_is_read(self):
        RolePermission.objects.filter(permission=self.w.perms["approve"]).update(is_active=False)
        self.assertEqual(self.post({}).status_code, 403)

    def test_rate_limit_returns_429(self):
        statuses = [self.post({}).status_code for _ in range(21)]
        self.assertEqual(statuses[:20], [400] * 20)
        self.assertEqual(statuses[20], 429)
        self.assert_pending()

    def test_approved_applicant_leaves_list_and_detail_and_can_sign_in(self):
        listed = self.client.get(BASE)
        self.assertIn(self.target.pk, [row["account_id"] for row in listed.json()["results"]])
        self.assertEqual(self.client.get(f"{BASE}{self.target.pk}/").status_code, 200)
        self.assertEqual(self.post(BODY).status_code, 200)
        listed = self.client.get(BASE)
        self.assertNotIn(self.target.pk, [row["account_id"] for row in listed.json()["results"]])
        self.assertEqual(self.client.get(f"{BASE}{self.target.pk}/").status_code, 404)
        api = APIClient(enforce_csrf_checks=True)
        token = api.get("/api/v1/auth/csrf/").json()["csrfToken"]
        login = api.post("/api/v1/auth/login/", {"school_id": self.target.school_id, "password": PASSWORD},
                         format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login.status_code, 200, login.content)
        self.assertEqual(login.json()["account"]["roles"], ["Student"])
        # D-50: no default access yet; SRS AT-02 stays UNMET until WF-03 seeds base-role grants.
        self.assertEqual(login.json()["permissions"], [])


class ApprovalRouteReleaseTests(TestCase):
    def test_approve_is_not_mounted_in_config_urls(self):
        for url in (f"{BASE}1/approve/", f"{BASE}1/reject/"):
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url, urlconf="config.urls")
        self.assertEqual(resolve(f"{BASE}1/approve/", urlconf="config.review_local_urls").url_name,
                         "registration-review-approve")


@override_settings(**GATES)
class ApprovalConcurrencyTests(TransactionTestCase):
    """Two real MySQL connections: locks serialize decisions; the loser sees committed state."""

    def setUp(self):
        self.outbox_key = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.outbox_key.start()
        self.addCleanup(self.outbox_key.stop)
        self.w = build_world()
        self.target = applicant("WF0203-RACE", self.w.roles["Student"])
        self.holding, self.release = threading.Event(), threading.Event()

    def tearDown(self):
        self.release.set()
        connections.close_all()

    def first_caller_pauses_holding_locks(self):
        """Pause the FIRST decision after it holds every row lock, before it checks permission."""
        real = registration_review.has_permission
        first = threading.Lock()

        def paused(account, code):
            if first.acquire(blocking=False):
                self.holding.set()
                self.release.wait(timeout=20)
            return real(account, code)
        return patch.object(registration_review, "has_permission", paused)

    def run_in_thread(self, fn):
        def call():
            try:
                verify_database()
                return ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - outcome is asserted by the test
                return ("error", exc)
            finally:
                connections.close_all()
        return call

    def race(self, first, second):
        reviewer_id, target_id = self.w.reviewer.pk, self.target.pk
        with self.first_caller_pauses_holding_locks(), ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.run_in_thread(lambda: first(Account.objects.get(pk=reviewer_id), target_id)))
            self.assertTrue(self.holding.wait(timeout=20), "first decision never acquired its locks")
            b = pool.submit(self.run_in_thread(lambda: second(Account.objects.get(pk=reviewer_id), target_id)))
            # The second decision is blocked on the first one's row locks.
            self.release.wait(timeout=1.0)
            self.assertFalse(b.done())
            self.release.set()
            return a.result(timeout=30), b.result(timeout=60)

    def test_two_concurrent_approvals_approve_once(self):
        def approve(actor, pk):
            return approve_registration(actor=actor, target_id=pk, attestation=STUDENT)
        (a_status, _), (b_status, b_value) = self.race(approve, approve)
        self.assertEqual(a_status, "ok")
        self.assertEqual(b_status, "error")
        self.assertIsInstance(b_value, RegistrationReviewDenied)
        self.assertNotIsInstance(b_value, RegistrationApprovalNotAllowed)
        self.assertEqual(AccessAuditLog.objects.filter(action="account.registration.approve").count(), 1)
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)

    def test_concurrent_approve_and_reject_decide_once(self):
        # WF-02.04 D-54 (owner-approved test correction): rejection needs the outbox to reach the locks.
        from .rejection_test_support import rejection_outbox
        ready = rejection_outbox()
        ready.__enter__()
        self.addCleanup(ready.__exit__, None, None, None)
        def approve(actor, pk):
            return approve_registration(actor=actor, target_id=pk, attestation=STUDENT)

        def reject(actor, pk):
            return reject_registration(actor=actor, target_id=pk, rejection_code="incomplete_submission")
        (a_status, _), (b_status, b_value) = self.race(approve, reject)
        self.assertEqual((a_status, b_status), ("ok", "error"))
        self.assertIsInstance(b_value, RegistrationReviewDenied)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")
        self.assertEqual(list(AccessAuditLog.objects.values_list("action", flat=True)),
                         ["account.registration.approve"])

    def test_permission_revoked_while_approval_waits_is_honored(self):
        role_permission_id = RolePermission.objects.get(permission=self.w.perms["approve"]).pk
        reviewer_id, target_id = self.w.reviewer.pk, self.target.pk
        revoked, commit = threading.Event(), threading.Event()

        def revoke():
            from django.db import transaction
            with transaction.atomic():
                list(Service.objects.select_for_update().filter(
                    service_code__in=["access_control", "accounts"]).order_by("service_id"))
                RolePermission.objects.filter(pk=role_permission_id).update(is_active=False)
                revoked.set()
                commit.wait(timeout=20)

        with ThreadPoolExecutor(max_workers=2) as pool:
            r = pool.submit(self.run_in_thread(revoke))
            self.assertTrue(revoked.wait(timeout=20))
            b = pool.submit(self.run_in_thread(lambda: approve_registration(
                actor=Account.objects.get(pk=reviewer_id), target_id=target_id, attestation=STUDENT)))
            commit.wait(timeout=1.0)
            self.assertFalse(b.done())
            commit.set()
            self.assertEqual(r.result(timeout=30)[0], "ok")
            status, value = b.result(timeout=60)
        self.assertEqual(status, "error")
        self.assertIsInstance(value, RegistrationReviewDenied)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
