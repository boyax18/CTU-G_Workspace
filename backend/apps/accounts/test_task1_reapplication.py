"""Task 1 acceptance tests: run ONLY with --settings=config.test_settings."""

import base64
import os
import secrets
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.conf import settings
from django.core import mail, signing
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service,
)
from .models import Account, UserProfile
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import _message_for
from .reapplication import (
    ReapplicationDenied, complete_reapplication, issue_reapplication_email_if_eligible,
)
from .registration_bulk import process_bulk_registration
from .registration_email_templates import render_decision_email
from .registration_review import reject_registration

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Task 1 tests require --settings=config.test_settings.")


@override_settings(
    WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED=True,
    WORKSPACE_REGISTRATION_REAPPLICATION_EMAIL_ENABLED=True,
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ReapplicationWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            if cur.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected test database.")
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.reviewer = Account.objects.create(school_id="9000001", request_status="Approved", is_active=True)

    def setUp(self):
        self.account = Account.objects.create_user(
            school_id="1000001", email="old@example.edu", password="Good!Password1234",
            requested_role=self.student,
        )
        UserProfile.objects.create(account=self.account, first_name="Original", last_name="Student")
        Account.objects.filter(pk=self.account.pk).update(
            request_status="Rejected", is_active=False, rejection_reason="incomplete_submission",
        )
        self.account.refresh_from_db()
        self.rejection = AccessAuditLog.objects.create(
            actor_account=self.reviewer, target_account=self.account,
            action="account.registration.reject",
            old_value={"request_status": "Pending"},
            new_value={"request_status": "Rejected", "rejection_code": "incomplete_submission"},
        )
        self.data = {
            "school_id": "1000001", "email": "new@example.edu", "first_name": "Updated",
            "middle_name": "C", "last_name": "Person", "suffix": "", "requested_role": "Instructor",
            "password": "Better!Password4567", "password_confirmation": "Better!Password4567",
        }

    def _token(self):
        issue_reapplication_email_if_eligible(school_id="1000001", email="old@example.edu")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["old@example.edu"])
        link = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        return parse_qs(urlsplit(link).fragment)["reapply"][0]

    def test_complete_reapplication_reuses_id_with_full_fields_and_preserves_audit(self):
        token = self._token()
        original_id = self.account.pk
        complete_reapplication(token=token, data=self.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.pk, original_id)
        self.assertEqual(self.account.request_status, "Pending")
        self.assertFalse(self.account.is_active)
        self.assertEqual(self.account.email, "new@example.edu")
        self.assertEqual(self.account.requested_role.role_name, "Instructor")
        self.assertTrue(self.account.check_password("Better!Password4567"))
        self.assertFalse(self.account.check_password("Good!Password1234"))
        self.assertIsNone(self.account.reviewed_by_id)
        self.assertIsNone(self.account.rejection_reason)
        self.assertFalse(AccountRole.objects.filter(account=self.account).exists())
        profile = UserProfile.objects.get(account=self.account)
        self.assertEqual(profile.first_name, "Updated")
        self.assertEqual(profile.last_name, "Person")
        self.assertTrue(AccessAuditLog.objects.filter(pk=self.rejection.pk).exists())
        self.assertTrue(AccessAuditLog.objects.filter(
            target_account=self.account, actor_account=self.account,
            action="account.registration.reapply",
        ).exists())
        self.assertEqual(Account.objects.filter(school_id="1000001").count(), 1)
        with self.assertRaises(ReapplicationDenied):
            complete_reapplication(token=token, data=self.data)

    def test_wrong_email_does_not_send_and_correct_request_has_generic_shape(self):
        issue_reapplication_email_if_eligible(school_id="1000001", email="attacker@example.edu")
        issue_reapplication_email_if_eligible(school_id="9999999", email="old@example.edu")
        self.assertEqual(len(mail.outbox), 0)
        token = self._token()
        with self.assertRaises(ReapplicationDenied):
            complete_reapplication(token=token, data={**self.data, "school_id": "1000002"})
        self.account.refresh_from_db()
        self.assertEqual(self.account.request_status, "Rejected")

    def test_expired_or_tampered_tokens_cannot_change_account(self):
        token = self._token()
        with patch("apps.accounts.reapplication.signing.loads", side_effect=signing.SignatureExpired("expired")):
            with self.assertRaises(ReapplicationDenied):
                complete_reapplication(token=token, data=self.data)
        with self.assertRaises(ReapplicationDenied):
            complete_reapplication(token=token + "tampered", data=self.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.request_status, "Rejected")

    def test_assigned_role_blocks_resubmission(self):
        token = self._token()
        AccountRole.objects.create(account=self.account, role=self.student)
        with self.assertRaises(ReapplicationDenied):
            complete_reapplication(token=token, data=self.data)
        self.account.refresh_from_db()
        self.assertEqual(self.account.request_status, "Rejected")

    def test_changed_rejection_cycle_invalidates_link(self):
        token = self._token()
        AccessAuditLog.objects.create(
            actor_account=self.reviewer, target_account=self.account,
            action="account.registration.reject",
            old_value={"request_status": "Pending"},
            new_value={"request_status": "Rejected", "rejection_code": "incomplete_submission"},
        )
        with self.assertRaises(ReapplicationDenied):
            complete_reapplication(token=token, data=self.data)

    def test_email_reasons_are_fixed_labels_and_links_are_local_test_only(self):
        subject, plain, html = render_decision_email(
            approved=False, rejection_code="identity_mismatch",
        )
        self.assertIn("Registration Rejected", subject)
        self.assertIn("Registration identity could not be verified", plain)
        self.assertIn("/register", html)
        self.assertNotIn("1000001", plain)
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"):
            with self.assertRaises(ValueError):
                render_decision_email(approved=False, rejection_code="identity_mismatch")


@override_settings(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True,
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
)
class Task1BulkNotificationCompatibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            if cur.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected test database.")
        accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        approve = Permission.objects.create(
            service=accounts, permission_code="accounts.registration_requests.approve",
            permission_name="Approve", module_name="registration_requests", action_name="approve",
        )
        reject = Permission.objects.create(
            service=accounts, permission_code="accounts.registration_requests.reject",
            permission_name="Reject", module_name="registration_requests", action_name="reject",
        )
        cls.student = Role.objects.create(role_name="Student")
        admin_role = Role.objects.create(role_name="Admin")
        cls.admin = Account.objects.create(school_id="9000002", request_status="Approved", is_active=True)
        AccountRole.objects.create(account=cls.admin, role=admin_role)
        RolePermission.objects.create(role=admin_role, permission=approve)
        RolePermission.objects.create(role=admin_role, permission=reject)

    def setUp(self):
        self.key_env = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.key_env.start()
        self.addCleanup(self.key_env.stop)
        self.targets = []
        for n in (1, 2):
            self.targets.append(Account.objects.create_user(
                school_id=f"200000{n}", email=f"person{n}@example.edu",
                password="Strong!Password1234", requested_role=self.student,
            ))

    def test_bulk_rejection_creates_one_v2_reason_snapshot_per_decision(self):
        result = process_bulk_registration(
            actor=self.admin, action="reject",
            account_ids=[target.pk for target in self.targets],
            rejection_code="identity_mismatch",
        )
        self.assertEqual(result["counts"]["Rejected"], 2)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 2)
        for row in RegistrationNotificationOutbox.objects.select_related("decision_audit_log"):
            self.assertEqual(row.template_version, 2)
            self.assertEqual(row.decision_audit_log.new_value["rejection_code"], "identity_mismatch")
            subject, plain, html = _message_for(row)
            self.assertIn("Registration Rejected", subject)
            self.assertIn("Registration identity could not be verified", plain)
            self.assertIn("Reapply for Registration", html)
        # Source current reason may change; historic v2 messages do not.
        Account.objects.filter(pk=self.targets[0].pk).update(rejection_reason="duplicate_request")
        for row in RegistrationNotificationOutbox.objects.select_related("decision_audit_log"):
            self.assertIn("Registration identity could not be verified", _message_for(row)[1])

    def test_bulk_approval_creates_one_v2_approval_per_account(self):
        result = process_bulk_registration(
            actor=self.admin, action="approve", account_ids=[t.pk for t in self.targets],
        )
        self.assertEqual(result["counts"]["Approved"], 2)
        for row in RegistrationNotificationOutbox.objects.select_related("decision_audit_log"):
            self.assertEqual(row.template_version, 2)
            self.assertIn("Registration Approved", _message_for(row)[0])
