"""AR-6C5C isolated MySQL API tests; do not run without config.test_settings."""

import json
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

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Bulk review tests require config.test_settings.")


@override_settings(
    ROOT_URLCONF="apps.accounts.registration_bulk_urls",
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
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
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.reviewer)
        self.csrf = "b" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.one = self.new_target("BULK-STUDENT-1")
        self.two = self.new_target("BULK-STUDENT-2")

    def new_target(self, school_id, role=None):
        return Account.objects.create_user(
            school_id=school_id, password="Copper!River7293",
            requested_role=role or self.student,
        )

    def post(self, payload, *, csrf=True):
        return self.client.post(
            "/bulk/", data=json.dumps(payload), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": self.csrf} if csrf else {}),
        )

    def request_for(self, action="approve", ids=None, reason="duplicate_request"):
        request = {"action": action, "account_ids": ids if ids is not None else [self.one.pk, self.two.pk]}
        if action == "reject":
            request["rejection_code"] = reason
        return request

    def test_two_approvals_are_individually_audited(self):
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["counts"]["Approved"], 2)
        self.assertFalse(data["interrupted"])
        self.assertEqual(AccountRole.objects.filter(account_id__in=[self.one.pk, self.two.pk]).count(), 2)
        self.assertEqual(AccessAuditLog.objects.count(), 2)
        self.one.refresh_from_db()
        self.assertEqual(self.one.request_status, "Approved")

    def test_rejection_leaves_accounts_inactive_and_audited(self):
        response = self.post(self.request_for("reject"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Rejected"], 2)
        self.one.refresh_from_db()
        self.assertEqual(self.one.rejection_reason, "duplicate_request")
        self.assertFalse(self.one.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.one).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_select_all_on_current_page_uses_explicit_ids(self):
        for i in range(21):
            self.new_target(f"BULK-EXTRA-{i}")
        first_page = self.client.get("/?page=1")
        self.assertEqual(first_page.status_code, 200, first_page.content)
        ids = [row["account_id"] for row in first_page.json()["results"]]
        self.assertEqual(len(ids), 20)
        response = self.post(self.request_for(ids=ids))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Approved"], 20)
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
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Skipped"], 1)
        self.assertEqual(response.json()["counts"]["Approved"], 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_replay_does_not_reapprove_or_reaudit(self):
        self.assertEqual(self.post(self.request_for()).status_code, 200)
        response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["counts"]["Skipped"], 2)
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_independent_decisions_when_middle_target_is_stale(self):
        three = self.new_target("BULK-STUDENT-3")
        self.two.request_status = "Rejected"
        self.two.save(update_fields=["request_status"])
        response = self.post(self.request_for(ids=[self.one.pk, self.two.pk, three.pk]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["outcome"] for row in response.json()["results"]],
                         ["Approved", "Skipped", "Approved"])
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
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["interrupted"])
        self.assertEqual(data["counts"]["Approved"], 1)
        self.assertEqual(data["remaining"], 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_single_account_unavailability_interrupts_with_true_counts(self):
        from . import registration_bulk
        real = registration_bulk.approve_registration
        attempts = {"count": 0}

        def decide(*, actor, target_id):
            attempts["count"] += 1
            if attempts["count"] == 2:
                from .registration_review import RegistrationReviewUnavailable
                raise RegistrationReviewUnavailable()
            return real(actor=actor, target_id=target_id)

        with patch.object(registration_bulk, "approve_registration", side_effect=decide):
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["counts"]["Approved"], 1)
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
        real = registration_bulk.approve_registration
        count = {"n": 0}

        def decide(*, actor, target_id):
            count["n"] += 1
            if count["n"] == 2:
                raise RuntimeError("private diagnostic")
            return real(actor=actor, target_id=target_id)

        with patch.object(registration_bulk, "approve_registration", side_effect=decide):
            response = self.post(self.request_for())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["interrupted"])
        self.assertEqual(data["counts"]["Approved"], 1)
        self.assertEqual(data["counts"]["Failed"], 1)
        self.assertNotIn("private diagnostic", response.content.decode())
        self.assertEqual(AccessAuditLog.objects.count(), 1)
