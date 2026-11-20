"""WF-02.04 Reject applicant, notify by email, and delete rejected registration data.

Run: python manage.py test apps.accounts.test_wf0204_rejection --settings=config.test_settings --noinput
Owner decisions 18 Nov 2026: D-54 durable outbox mandatory; D-55 (revised) a verified recipient is
required; D-56 four fixed reasons; D-58 privacy-safe 404 plus fixed 409 conflicts; D-62 local review
and sandbox only. Disposable MySQL only; locmem email only; isolated synthetic applicants.
"""

import base64
import json
import os
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.models import ADDITION, LogEntry
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Role, RolePermission

from . import registration_review
from .models import Account, UserProfile
from .outbox_crypto import decrypt_recipient
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import process_one
from .registration_review import (
    RegistrationRejectionNotAllowed, RegistrationReviewDenied, RegistrationReviewUnavailable,
    approve_registration, reject_registration,
)
from .registration_staging import _identity_conflicts
from .test_wf0203_approval import APPLICANT_EMAIL, BASE, PASSWORD, STUDENT, applicant, build_world, verify_database

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.04 tests require --settings=config.test_settings.")

CODES = ("incomplete_submission", "ineligible_registration", "identity_mismatch", "duplicate_request")
REJECT = {"rejection_code": "identity_mismatch"}
READY = dict(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


class KeyMixin:
    def start_keys(self):
        self.env = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
            "WORKSPACE_OUTBOX_WORKER_ENABLED": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        mail.outbox = []


def recipient(row):
    return decrypt_recipient(
        encrypted_recipient=row.encrypted_recipient, recipient_nonce=row.recipient_nonce,
        wrapped_data_key=row.wrapped_data_key, encryption_key_version=row.encryption_key_version,
        audit_log_id=row.decision_audit_log_id, template_code=row.template_code,
        template_version=row.template_version,
    )


@override_settings(**READY)
class RejectionServiceTests(KeyMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = build_world()

    def setUp(self):
        self.start_keys()
        self.target = applicant("WF0204-STUDENT", self.w.roles["Student"])

    def reject(self, code="identity_mismatch", target=None):
        return reject_registration(actor=self.w.reviewer, target_id=(target or self.target).pk, rejection_code=code)

    def assert_untouched(self, target=None):
        target = target or self.target
        target.refresh_from_db()
        self.assertEqual((target.request_status, target.is_active), ("Pending", False))
        self.assertIsNone(target.reviewed_by_id)
        self.assertTrue(UserProfile.objects.filter(account=target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_rejection_audits_queues_one_encrypted_email_and_deletes_only_the_applicant(self):
        target_id, school_id = self.target.pk, self.target.school_id
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.reject(), target_id)
        self.assertFalse(Account.objects.filter(pk=target_id).exists())
        self.assertFalse(UserProfile.objects.filter(account_id=target_id).exists())
        deletes = [q["sql"] for q in queries if q["sql"].upper().startswith("DELETE")]
        self.assertEqual(len(deletes), 2)
        self.assertTrue(deletes[0].startswith("DELETE FROM users WHERE account_id="))
        self.assertTrue(deletes[1].startswith("DELETE FROM accounts WHERE account_id="))
        audit = AccessAuditLog.objects.get()
        self.assertEqual((audit.action, audit.reason), ("account.registration.reject", "account_status_change"))
        self.assertEqual(audit.actor_account_id, self.w.reviewer.pk)
        self.assertIsNone(audit.target_account_id)
        self.assertIsNone(audit.role_id)
        self.assertEqual(audit.old_value, {"account_id": target_id, "request_status": "Pending", "is_active": False})
        self.assertEqual(audit.new_value, {"account_id": target_id, "request_status": "Rejected", "is_active": False,
                                           "rejection_code": "identity_mismatch", "account_deleted": True})
        text = json.dumps([audit.old_value, audit.new_value])
        for private in (APPLICANT_EMAIL, school_id, "Ada", "Reyes"):
            self.assertNotIn(private, text)
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual((row.decision_audit_log_id, row.template_code, row.template_version, row.delivery_status),
                         (audit.pk, "registration.rejected", 2, "Pending"))
        self.assertEqual(recipient(row), APPLICANT_EMAIL)
        self.assertNotIn(APPLICANT_EMAIL.encode(), bytes(row.encrypted_recipient))
        self.assertEqual(len(mail.outbox), 0)  # queued, not sent, by the decision
        # The reviewer and unrelated accounts are untouched.
        self.assertTrue(Account.objects.filter(pk=self.w.reviewer.pk, is_active=True).exists())

    def test_each_fixed_reason_is_recorded_and_others_are_refused(self):
        for index, code in enumerate(CODES):
            with self.subTest(code=code):
                target = applicant(f"WF0204-R{index}", self.w.roles["Student"], email=f"r{index}.wf0204@example.edu")
                self.reject(code, target)
                self.assertEqual(AccessAuditLog.objects.get(new_value__account_id=target.pk).new_value["rejection_code"], code)
        before = AccessAuditLog.objects.count()
        for bad in ("", "other", "Identity_Mismatch", "identity mismatch", None, 1, ["identity_mismatch"]):
            with self.subTest(bad=bad), self.assertRaises(RegistrationReviewDenied):
                self.reject(bad)
        self.assertEqual(AccessAuditLog.objects.count(), before)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")

    def test_instructor_rejection(self):
        instructor = applicant("WF0204-INSTRUCTOR", self.w.roles["Instructor"], email="staff.wf0204@example.edu")
        self.reject("ineligible_registration", instructor)
        self.assertFalse(Account.objects.filter(pk=instructor.pk).exists())
        self.assertEqual(recipient(RegistrationNotificationOutbox.objects.get()), "staff.wf0204@example.edu")

    def test_unverified_recipients_are_refused_and_nothing_changes(self):
        states = {
            "no_email": dict(email=None),
            "blank_email": dict(email="   "),
            "no_proof_time": dict(email_verified_at=None),
            "no_proof_address": dict(email_verified_address=None),
            "address_changed": dict(email="changed.wf0204@example.edu"),
        }
        for label, change in states.items():
            with self.subTest(state=label):
                Account.objects.filter(pk=self.target.pk).update(
                    email=APPLICANT_EMAIL, email_verified_at=timezone.now(), email_verified_address=APPLICANT_EMAIL)
                Account.objects.filter(pk=self.target.pk).update(**change)
                with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
                    self.reject()
                self.assertEqual(caught.exception.reason, "recipient_unverified")
                self.assertNotIn(APPLICANT_EMAIL, str(caught.exception))
                self.assert_untouched()

    def test_case_only_proof_difference_is_verified(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_address=APPLICANT_EMAIL.upper())
        self.reject()
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())

    def test_outbox_or_v2_template_disabled_refuses_before_any_read_or_write(self):
        for flags in ({"WORKSPACE_REGISTRATION_OUTBOX_ENABLED": False},
                      {"WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED": False},
                      {"WORKSPACE_REGISTRATION_OUTBOX_ENABLED": False,
                       "WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED": True}):
            with self.subTest(flags=flags), override_settings(**flags):
                with CaptureQueriesContext(connection) as queries, self.captureOnCommitCallbacks() as callbacks:
                    with self.assertRaises(RegistrationReviewUnavailable):
                        self.reject()
                self.assertEqual(len(queries), 0)
                self.assertEqual(callbacks, [])  # never the best-effort path
                self.assert_untouched()

    def test_missing_key_outbox_error_delete_error_and_audit_error_roll_back_everything(self):
        failures = [
            patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": ""}),
            patch("apps.accounts.registration_review.record_registration_decision_outbox", side_effect=RuntimeError("outbox down")),
            patch("apps.accounts.registration_review._delete_rejected_registration", side_effect=RuntimeError("delete down")),
            patch("apps.accounts.registration_review.record_access_audit_receipt", side_effect=RuntimeError("audit down")),
        ]
        for failure in failures:
            with self.subTest(failure=str(failure)), failure:
                with self.assertRaises(Exception):
                    self.reject()
                self.assert_untouched()

    def test_a_non_pending_outbox_row_never_completes_a_rejection(self):
        real = registration_review.record_registration_decision_outbox

        def dead(**kwargs):
            pk = real(**kwargs)
            RegistrationNotificationOutbox.objects.filter(pk=pk).update(delivery_status="Dead")
            return pk
        with patch("apps.accounts.registration_review.record_registration_decision_outbox", side_effect=dead):
            with self.assertRaises(RegistrationReviewUnavailable):
                self.reject()
        self.assert_untouched()

    def test_direct_permissions_and_protected_history_are_fixed_conflicts(self):
        AccountPermission.objects.create(account=self.target, permission=self.w.perms["read"], effect="Grant")
        with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
            self.reject()
        self.assertEqual(caught.exception.reason, "direct_permissions")
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        AccountPermission.objects.filter(account=self.target).delete()
        LogEntry.objects.create(user=self.target, action_flag=ADDITION, object_repr="Synthetic fixture")
        with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
            self.reject()
        self.assertEqual(caught.exception.reason, "protected_history")
        self.assert_untouched()
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_authorization_denials_before_policy(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_at=None)
        RolePermission.objects.filter(permission=self.w.perms["reject"]).update(is_active=False)
        with self.assertRaises(RegistrationReviewDenied) as caught:
            self.reject()
        self.assertNotIsInstance(caught.exception, RegistrationRejectionNotAllowed)
        RolePermission.objects.filter(permission=self.w.perms["reject"]).update(is_active=True)
        AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["reject"], effect="Deny")
        with self.assertRaises(RegistrationReviewDenied) as caught:
            self.reject()
        self.assertNotIsInstance(caught.exception, RegistrationRejectionNotAllowed)
        self.assert_untouched()

    def test_self_and_framework_superuser_rejection_are_denied(self):
        with self.assertRaises(RegistrationReviewDenied):
            reject_registration(actor=self.w.reviewer, target_id=self.w.reviewer.pk, rejection_code="duplicate_request")
        Account.objects.filter(pk=self.w.reviewer.pk).update(is_superuser=True, is_staff=True)
        with self.assertRaises(RegistrationReviewDenied):
            reject_registration(actor=Account.objects.get(pk=self.w.reviewer.pk), target_id=self.target.pk,
                                rejection_code="duplicate_request")
        self.assert_untouched()

    def test_stale_targets_and_repeat_rejection_are_denied_without_new_records(self):
        approved = applicant("WF0204-APPROVED", self.w.roles["Student"], email="approved.wf0204@example.edu")
        approve_registration(actor=self.w.reviewer, target_id=approved.pk, attestation=STUDENT)
        with self.assertRaises(RegistrationReviewDenied) as caught:
            self.reject(target=approved)
        self.assertNotIsInstance(caught.exception, RegistrationRejectionNotAllowed)
        self.reject()
        audits, rows = AccessAuditLog.objects.count(), RegistrationNotificationOutbox.objects.count()
        with self.assertRaises(RegistrationReviewDenied):
            self.reject()
        self.assertEqual((AccessAuditLog.objects.count(), RegistrationNotificationOutbox.objects.count()), (audits, rows))

    def test_fresh_registration_with_the_same_school_id_and_email_is_a_new_pending_application(self):
        old_id, school_id = self.target.pk, self.target.school_id
        payload = {"school_id": school_id, "email": APPLICANT_EMAIL}
        self.assertTrue(_identity_conflicts(payload))
        self.reject()
        self.assertFalse(_identity_conflicts(payload))  # the ordinary registration check now passes
        fresh = Account.objects.create_user(school_id=school_id, email=APPLICANT_EMAIL,
                                            password="Other!Harbor4821", requested_role=self.w.roles["Student"])
        self.assertNotEqual(fresh.pk, old_id)
        self.assertEqual((fresh.request_status, fresh.is_active), ("Pending", False))
        self.assertIsNone(fresh.email_verified_at)  # proof must be earned again through OTP
        self.assertIsNone(fresh.reviewed_by_id)
        self.assertFalse(AccountRole.objects.filter(account=fresh).exists())
        self.assertTrue(fresh.check_password("Other!Harbor4821"))
        self.assertFalse(fresh.check_password(PASSWORD))
        # The old decision is not linked to the new account.
        self.assertFalse(AccessAuditLog.objects.filter(target_account=fresh).exists())

    def test_queued_email_is_delivered_after_deletion_to_the_right_recipient_with_the_public_reason(self):
        self.reject("incomplete_submission")
        self.assertEqual(process_one(), "delivered")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [APPLICANT_EMAIL])
        self.assertIn("Registration Rejected", message.subject)
        self.assertIn("Incomplete registration information", message.body)
        self.assertNotIn(self.w.reviewer.school_id, message.body)
        self.assertEqual(RegistrationNotificationOutbox.objects.get().delivery_status, "Delivered")
        self.assertEqual(process_one(), "empty")  # nothing left: no duplicate

    def test_delivery_failure_retries_and_the_rejection_stands(self):
        self.reject()
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("smtp down")):
            self.assertEqual(process_one(), "retry")
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual((row.delivery_status, row.attempt_count), ("Retry", 1))
        self.assertEqual(len(mail.outbox), 0)

    def test_bulk_rejection_enforces_the_same_recipient_policy(self):
        from .registration_bulk import process_bulk_registration
        unverified = applicant("WF0204-BULK-U", self.w.roles["Student"], email="u.wf0204@example.edu", proof=None)
        result = process_bulk_registration(actor=self.w.reviewer, action="reject",
                                           account_ids=[self.target.pk, unverified.pk], rejection_code="duplicate_request")
        self.assertEqual((result["counts"]["Rejected"], result["counts"]["Skipped"]), (1, 1))
        self.assertTrue(Account.objects.filter(pk=unverified.pk, request_status="Pending").exists())
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 1)


@override_settings(ROOT_URLCONF="config.review_local_urls", WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True, **READY)
class RejectionHTTPContractTests(KeyMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = build_world()
        cls.tsa = Role.objects.create(role_name="Technical Super Admin")

    def setUp(self):
        self.start_keys()
        cache.clear()
        self.client = self.signed_in(self.w.reviewer)
        self.target = applicant("WF0204-HTTP", self.w.roles["Student"])

    def signed_in(self, account):
        client = Client(enforce_csrf_checks=True)
        client.force_login(account)
        client.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32
        return client

    def post(self, body, target_id=None, *, client=None, csrf=True, raw=None):
        return (client or self.client).post(
            f"{BASE}{target_id or self.target.pk}/reject/",
            data=raw if raw is not None else json.dumps(body), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": "d" * 32} if csrf else {}),
        )

    def assert_pending(self):
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def assert_no_leak(self, response):
        text = response.content.decode()
        for private in (APPLICANT_EMAIL, self.target.school_id, "Ada", "Reyes", "Traceback"):
            self.assertNotIn(private, text)

    def test_success_reports_queued_never_delivered(self):
        response = self.post(REJECT)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"account_id": self.target.pk, "status": "Rejected", "notification": "queued"})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(RegistrationNotificationOutbox.objects.get().delivery_status, "Pending")

    def test_recipient_conflict_is_a_fixed_409_without_applicant_data(self):
        Account.objects.filter(pk=self.target.pk).update(email_verified_at=None)
        response = self.post(REJECT)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"error": {"code": "rejection_not_allowed", "reason": "recipient_unverified",
                                                     "message": "Rejection is not allowed for this application."}})
        self.assert_no_leak(response)
        self.assert_pending()

    def test_direct_permission_conflict_is_409(self):
        AccountPermission.objects.create(account=self.target, permission=self.w.perms["read"], effect="Grant")
        response = self.post(REJECT)
        self.assertEqual((response.status_code, response.json()["error"]["reason"]), (409, "direct_permissions"))

    def test_malformed_bodies_are_400(self):
        for body in ({}, {"rejection_code": "other"}, {"rejection_code": None}, {"rejection_code": ["identity_mismatch"]},
                     {**REJECT, "reason_text": "free text"}, {**REJECT, "no_email_acknowledged": True},
                     {**REJECT, "account_id": 1}, [REJECT]):
            with self.subTest(body=body):
                cache.clear()
                response = self.post(body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_request")
        cache.clear()
        self.assertEqual(self.post(None, raw="{bad").status_code, 400)
        self.assert_pending()

    def test_stale_and_unknown_share_one_404_and_duplicates_do_not_repeat(self):
        self.assertEqual(self.post(REJECT).status_code, 200)
        repeat = self.post(REJECT)
        unknown = self.post(REJECT, target_id=2_000_000_000)
        self.assertEqual((repeat.status_code, unknown.status_code), (404, 404))
        self.assertEqual(repeat.json(), unknown.json())
        self.assertEqual((AccessAuditLog.objects.count(), RegistrationNotificationOutbox.objects.count()), (1, 1))

    def test_authentication_csrf_permission_deny_and_gates(self):
        self.assertEqual(self.post(REJECT, csrf=False).status_code, 403)
        anonymous = Client(enforce_csrf_checks=True)
        anonymous.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32
        self.assertEqual(self.post(REJECT, client=anonymous).status_code, 401)
        AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["reject"], effect="Deny")
        response = self.post(REJECT)
        self.assertEqual(response.status_code, 403)
        self.assert_no_leak(response)
        AccountPermission.objects.filter(account=self.w.reviewer).delete()
        self.assertEqual(self.post({}).status_code, 400)  # permission restored: body now checked
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False):
            response = self.post(REJECT)
            self.assertEqual((response.status_code, response.json()["error"]["code"]), (503, "review_unavailable"))
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            self.assertEqual(self.post(REJECT).status_code, 503)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            self.assertEqual(self.post(REJECT).status_code, 503)  # executor unavailable in tests
        self.assert_pending()

    def test_permission_is_checked_before_the_body(self):
        RolePermission.objects.filter(permission=self.w.perms["reject"]).update(is_active=False)
        self.assertEqual(self.post({}).status_code, 403)

    def test_student_instructor_and_technical_super_admin_roles(self):
        def approved(school_id, *roles):
            account = Account.objects.create_user(school_id=school_id, password=PASSWORD)
            Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved")
            for role in roles:
                AccountRole.objects.create(account=account, role=role)
            return Account.objects.get(pk=account.pk)
        for school_id, role in (("WF0204-S", self.w.roles["Student"]), ("WF0204-I", self.w.roles["Instructor"]),
                                ("WF0204-TSA-ONLY", self.tsa)):
            with self.subTest(role=role.role_name):
                cache.clear()
                self.assertEqual(self.post(REJECT, client=self.signed_in(approved(school_id, role))).status_code, 403)
        self.assert_pending()
        cache.clear()
        both = self.signed_in(approved("WF0204-TSA-ADMIN", self.w.roles["Admin"], self.tsa))
        self.assertEqual(self.post(REJECT, client=both).status_code, 200)

    def test_rate_limit(self):
        statuses = [self.post({}).status_code for _ in range(21)]
        self.assertEqual(statuses[:20], [400] * 20)
        self.assertEqual(statuses[20], 429)

    def test_rejected_application_leaves_list_and_detail(self):
        self.assertIn(self.target.pk, [r["account_id"] for r in self.client.get(BASE).json()["results"]])
        self.assertEqual(self.post(REJECT).status_code, 200)
        self.assertNotIn(self.target.pk, [r["account_id"] for r in self.client.get(BASE).json()["results"]])
        self.assertEqual(self.client.get(f"{BASE}{self.target.pk}/").status_code, 404)

    def test_reject_is_not_mounted_in_config_urls(self):
        from django.urls import Resolver404, resolve
        with self.assertRaises(Resolver404):
            resolve(f"{BASE}{self.target.pk}/reject/", urlconf="config.urls")


@override_settings(**READY)
class RejectionConcurrencyTests(KeyMixin, TransactionTestCase):
    """Two real MySQL connections; the second decision waits on the first one's row locks."""

    def setUp(self):
        self.start_keys()
        self.w = build_world()
        self.target = applicant("WF0204-RACE", self.w.roles["Student"])
        self.holding, self.release = threading.Event(), threading.Event()

    def tearDown(self):
        self.release.set()
        connections.close_all()

    def pause_first(self):
        real = registration_review.has_permission
        first = threading.Lock()

        def paused(account, code):
            if first.acquire(blocking=False):
                self.holding.set()
                self.release.wait(timeout=20)
            return real(account, code)
        return patch.object(registration_review, "has_permission", paused)

    @staticmethod
    def in_thread(fn):
        def call():
            try:
                verify_database()
                return ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - asserted by the test
                return ("error", exc)
            finally:
                connections.close_all()
        return call

    def race(self, first, second):
        rid, tid = self.w.reviewer.pk, self.target.pk
        with self.pause_first(), ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(self.in_thread(lambda: first(Account.objects.get(pk=rid), tid)))
            self.assertTrue(self.holding.wait(timeout=20))
            b = pool.submit(self.in_thread(lambda: second(Account.objects.get(pk=rid), tid)))
            self.release.wait(timeout=1.0)
            self.assertFalse(b.done(), "the second decision must wait on the first one's locks")
            self.release.set()
            return a.result(timeout=30), b.result(timeout=60)

    @staticmethod
    def reject(actor, pk):
        return reject_registration(actor=actor, target_id=pk, rejection_code="duplicate_request")

    @staticmethod
    def approve(actor, pk):
        return approve_registration(actor=actor, target_id=pk, attestation=STUDENT)

    def test_two_concurrent_rejections_decide_once(self):
        (a, _), (b, err) = self.race(self.reject, self.reject)
        self.assertEqual((a, b), ("ok", "error"))
        self.assertIsInstance(err, RegistrationReviewDenied)
        self.assertNotIsInstance(err, RegistrationRejectionNotAllowed)
        self.assertEqual((AccessAuditLog.objects.count(), RegistrationNotificationOutbox.objects.count()), (1, 1))
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())

    def test_rejection_first_then_approval_is_refused(self):
        (a, _), (b, err) = self.race(self.reject, self.approve)
        self.assertEqual((a, b), ("ok", "error"))
        self.assertIsInstance(err, RegistrationReviewDenied)
        self.assertEqual(list(AccessAuditLog.objects.values_list("action", flat=True)), ["account.registration.reject"])
        self.assertFalse(AccountRole.objects.filter(account_id=self.target.pk).exists())

    def test_approval_first_then_rejection_is_refused(self):
        (a, _), (b, err) = self.race(self.approve, self.reject)
        self.assertEqual((a, b), ("ok", "error"))
        self.assertIsInstance(err, RegistrationReviewDenied)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")
        self.assertFalse(RegistrationNotificationOutbox.objects.filter(template_code="registration.rejected").exists())

    def test_permission_revoked_while_rejection_waits_is_honoured(self):
        from django.db import transaction
        from apps.access_control.models import Service
        rp = RolePermission.objects.get(permission=self.w.perms["reject"]).pk
        rid, tid = self.w.reviewer.pk, self.target.pk
        revoked, commit = threading.Event(), threading.Event()

        def revoke():
            with transaction.atomic():
                list(Service.objects.select_for_update().filter(
                    service_code__in=["access_control", "accounts"]).order_by("service_id"))
                RolePermission.objects.filter(pk=rp).update(is_active=False)
                revoked.set()
                commit.wait(timeout=20)
        with ThreadPoolExecutor(max_workers=2) as pool:
            r = pool.submit(self.in_thread(revoke))
            self.assertTrue(revoked.wait(timeout=20))
            b = pool.submit(self.in_thread(lambda: self.reject(Account.objects.get(pk=rid), tid)))
            commit.wait(timeout=1.0)
            self.assertFalse(b.done())
            commit.set()
            self.assertEqual(r.result(timeout=30)[0], "ok")
            status, err = b.result(timeout=60)
        self.assertEqual(status, "error")
        self.assertIsInstance(err, RegistrationReviewDenied)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
