"""AR-6C5C isolated MySQL API tests; do not run without config.test_settings."""

import json
import os
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)
from .models import Account
from .outbox_models import RegistrationNotificationOutbox
from .rejection_test_support import REJECTION_READY, fresh_test_key, verified_email

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Bulk review tests require config.test_settings.")


@override_settings(
    ROOT_URLCONF="apps.accounts.registration_bulk_urls",
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
    # WF-02.04 D-54/D-55 (owner-approved test correction): bulk rejection uses the same
    # single-account service, which now needs the durable outbox and a verified recipient.
    **REJECTION_READY,
)
class BulkRegistrationReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        cls.access_service = Service.objects.create(service_code="access_control", service_name="Access Control")
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.admin = Role.objects.create(role_name="Admin")
        cls.reviewer = Account.objects.create_user(
            school_id="BULK-ADMIN", password="Copper!River7293",
        )
        cls.reviewer.is_active = True
        cls.reviewer.request_status = "Approved"
        cls.reviewer.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin)
        cls.permissions = {}
        for action in ("read", "approve", "reject"):
            perm = Permission.objects.create(
                service=cls.accounts_service,
                permission_code=f"accounts.registration_requests.{action}",
                permission_name=f"Registration requests {action}",
                module_name="registration_requests", action_name=action,
            )
            RolePermission.objects.create(role=cls.admin, permission=perm)
            cls.permissions[action] = perm

    def setUp(self):
        import os
        key = patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()})
        key.start()
        self.addCleanup(key.stop)
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.reviewer)
        self.csrf = "b" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.one = self.new_target("BULK-STUDENT-1")
        self.two = self.new_target("BULK-STUDENT-2")

    def new_target(self, school_id, role=None):
        return verified_email(Account.objects.create_user(
            school_id=school_id, password="Copper!River7293",
            requested_role=role or self.student,
        ), f"{school_id.lower()}@example.edu")

    def post(self, payload, *, csrf=True):
        return self.client.post(
            "/bulk/", data=json.dumps(payload), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": self.csrf} if csrf else {}),
        )

    def request_for(self, action="approve", ids=None, reason="duplicate_request", eligibility_confirmed=True):
        request = {"action": action, "account_ids": ids if ids is not None else [self.one.pk, self.two.pk]}
        if action == "reject":
            request["rejection_code"] = reason
        else:
            request["eligibility_confirmed"] = eligibility_confirmed
        return request

    def test_bulk_approval_confirms_each_applicant_and_queues_individual_notifications(self):
        instructor = self.new_target("BULK-INSTRUCTOR-1", self.instructor)
        response = self.post(self.request_for(ids=[self.one.pk, self.two.pk, instructor.pk]))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["action"], "approve")
        self.assertEqual(data["counts"]["Approved"], 3)
        self.assertEqual(data["counts"]["Skipped"], 0)
        self.assertEqual(data["counts"]["Unconfirmed"], 0)
        self.assertEqual(AccessAuditLog.objects.count(), 3)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 3)
        self.assertEqual(
            set(AccountRole.objects.filter(account_id__in=[self.one.pk, self.two.pk]).values_list("role_id", flat=True)),
            {self.student.pk},
        )
        self.assertEqual(
            AccountRole.objects.get(account=instructor).role_id,
            self.instructor.pk,
        )
        for target in (self.one, self.two, instructor):
            target.refresh_from_db()
            self.assertEqual(target.request_status, "Approved")
            self.assertTrue(target.is_active)
        approved_audits = AccessAuditLog.objects.filter(action="account.registration.approve")
        self.assertEqual(approved_audits.count(), 3)
        self.assertEqual(
            {row.new_value["eligibility_source"] for row in approved_audits},
            {"ctu_main_system_records", "institutional_employment_records"},
        )
        for row in RegistrationNotificationOutbox.objects.select_related("decision_audit_log"):
            self.assertEqual(row.delivery_status, "Pending")
            self.assertEqual(row.decision_audit_log.action, "account.registration.approve")

    def test_bulk_approval_requires_explicit_eligibility_confirmation(self):
        request = self.request_for()
        del request["eligibility_confirmed"]
        response = self.post(request)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.one.refresh_from_db()
        self.assertEqual(self.one.request_status, "Pending")

    def test_mixed_eligible_and_ineligible_approval_reports_each_independently(self):
        self.two.email_verified_address = "different@example.edu"
        self.two.save(update_fields=["email_verified_address"])
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["counts"]["Approved"], 1)
        self.assertEqual(data["counts"]["Skipped"], 1)
        self.assertEqual(
            [result["outcome"] for result in data["results"]],
            ["Approved", "Skipped"],
        )
        self.assertEqual(AccessAuditLog.objects.filter(action="account.registration.approve").count(), 1)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 1)

    def test_rejection_deletes_accounts_and_preserves_audit(self):
        response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Rejected"], 2)
        self.assertFalse(Account.objects.filter(pk__in=[self.one.pk, self.two.pk]).exists())
        self.assertFalse(AccountRole.objects.filter(account=self.one).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 2)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 2)
        for row in RegistrationNotificationOutbox.objects.select_related("decision_audit_log"):
            self.assertEqual(row.delivery_status, "Pending")
            self.assertEqual(row.decision_audit_log.action, "account.registration.reject")

    def test_select_all_on_current_page_uses_explicit_ids(self):
        for i in range(21):
            self.new_target(f"BULK-EXTRA-{i}")
        first_page = self.client.get("/?page=1")
        self.assertEqual(first_page.status_code, 200, first_page.content)
        ids = [row["account_id"] for row in first_page.json()["results"]]
        self.assertEqual(len(ids), 20)
        response = self.post(self.request_for("reject", ids=ids))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Rejected"], 20)
        self.assertEqual(Account.objects.filter(request_status="Pending").count(), 3)

    def test_repeated_target_is_invalid_before_writes(self):
        response = self.post(self.request_for(ids=[self.one.pk, self.one.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_21_targets_require_future_queue(self):
        response = self.post(self.request_for(ids=list(range(1, 22))))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_boolean_and_string_ids_are_invalid(self):
        for ids in ([True], [str(self.one.pk)], [0], [-1]):
            with self.subTest(ids=ids):
                cache.clear()
                self.assertEqual(self.post(self.request_for(ids=ids)).status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_rejection_code_and_extra_fields_are_rejected(self):
        self.assertEqual(self.post(self.request_for("reject", reason="sensitive narrative")).status_code, 400)
        self.assertEqual(self.post({**self.request_for(), "select_all_matching": True}).status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_stale_target_is_skipped_without_extra_audit(self):
        self.one.request_status, self.one.is_active = "Approved", True
        self.one.save(update_fields=["request_status", "is_active"])
        response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Skipped"], 1)
        self.assertEqual(response.json()["counts"]["Rejected"], 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_replay_does_not_redecide_or_reaudit(self):
        self.assertEqual(self.post(self.request_for("reject")).status_code, 200)
        response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Skipped"], 2)
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_independent_decisions_when_middle_target_is_stale(self):
        three = self.new_target("BULK-STUDENT-3")
        self.two.request_status = "Rejected"
        self.two.save(update_fields=["request_status"])
        response = self.post(self.request_for("reject", ids=[self.one.pk, self.two.pk, three.pk]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["outcome"] for row in response.json()["results"]],
                         ["Rejected", "Skipped", "Rejected"])
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_missing_csrf_rejected(self):
        response = self.post(self.request_for(), csrf=False)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_anonymous_session_rejected(self):
        self.client.logout()
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf

        response = self.post(self.request_for())

        self.assertEqual(response.status_code, 401, response.content)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_feature_gate_blocks_review(self):
        with override_settings(WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED=False):
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 503)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_list_advertises_bulk_actions_only_when_route_permission_and_outbox_are_ready(self):
        response = self.client.get("/")
        self.assertEqual(response["X-Workspace-Available-Actions"], "bulk-approve,bulk-reject")
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False):
            response = self.client.get("/")
            self.assertEqual(response["X-Workspace-Available-Actions"], "")
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": ""}):
            response = self.client.get("/")
            self.assertEqual(response["X-Workspace-Available-Actions"], "")
        AccountPermission.objects.create(
            account=self.reviewer, permission=self.permissions["approve"], effect="Deny",
        )
        response = self.client.get("/")
        self.assertEqual(response["X-Workspace-Available-Actions"], "bulk-reject")

    def test_existing_approval_gate_still_blocks(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 503)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_admin_role_without_permission_cannot_bulk_approve(self):
        RolePermission.objects.filter(role=self.admin, permission=self.permissions["approve"]).update(is_active=False)
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_account_deny_overrides_role_grant(self):
        AccountPermission.objects.create(
            account=self.reviewer, permission=self.permissions["approve"], effect="Deny",
        )
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_framework_superuser_never_bulk_approves(self):
        self.reviewer.is_staff, self.reviewer.is_superuser = True, True
        self.reviewer.save(update_fields=["is_staff", "is_superuser"])
        response = self.post(self.request_for())
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_permission_revoked_during_batch_stops_remaining_items(self):
        # Simulate policy change after one committed target; no second decision.
        from . import registration_bulk_api
        real_check = registration_bulk_api.BulkRegistrationReviewView.require_actor
        calls = {"count": 0}

        def check(view, request, permission):
            calls["count"] += 1
            if calls["count"] == 3:  # initial, first item, second item
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Policy changed")
            return real_check(view, request, permission)

        with patch.object(registration_bulk_api.BulkRegistrationReviewView, "require_actor", check):
            response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["interrupted"])
        self.assertEqual(data["counts"]["Rejected"], 1)
        self.assertEqual(data["remaining"], 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_single_account_unavailability_interrupts_with_true_counts(self):
        from . import registration_bulk
        real = registration_bulk.reject_registration
        attempts = {"count": 0}

        def decide(*, actor, target_id, rejection_code):
            attempts["count"] += 1
            if attempts["count"] == 2:
                from .registration_review import RegistrationReviewUnavailable
                raise RegistrationReviewUnavailable()
            return real(actor=actor, target_id=target_id, rejection_code=rejection_code)

        with patch.object(registration_bulk, "reject_registration", side_effect=decide):
            response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["counts"]["Rejected"], 1)
        self.assertEqual(data["counts"]["Failed"], 1)
        self.assertTrue(data["interrupted"])
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_existing_review_api_gate_still_blocks(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False):
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 503)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_cross_origin_request_is_denied(self):
        response = self.client.post(
            "/bulk/", data=json.dumps(self.request_for()),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
            HTTP_ORIGIN="https://malicious.example",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_unexpected_second_decision_failure_stops_truthfully(self):
        from . import registration_bulk
        real = registration_bulk.reject_registration
        count = {"n": 0}

        def decide(*, actor, target_id, rejection_code):
            count["n"] += 1
            if count["n"] == 2:
                raise RuntimeError("private diagnostic")
            return real(actor=actor, target_id=target_id, rejection_code=rejection_code)

        with patch.object(registration_bulk, "reject_registration", side_effect=decide):
            response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["interrupted"])
        self.assertEqual(data["counts"]["Rejected"], 1)
        self.assertEqual(data["counts"]["Unconfirmed"], 1)
        self.assertNotIn("private diagnostic", response.content.decode())
        self.assertEqual(AccessAuditLog.objects.count(), 1)
