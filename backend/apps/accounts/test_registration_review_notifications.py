"""AR-6C5A draft: isolated registration review notification tests.

Use ONLY --settings=config.test_settings. Never run against development data.
"""

from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)
from .models import Account
from .registration_review import (
    RegistrationReviewDenied,
    approve_registration,
    reject_registration,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Review notification tests require --settings=config.test_settings.")


@override_settings(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RegistrationDecisionEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Refusing to run tests on an unexpected database.")

        accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        approve = Permission.objects.create(
            service=accounts,
            permission_code="accounts.registration_requests.approve",
            permission_name="Approve registrations",
            module_name="registration_requests",
            action_name="approve",
        )
        reject = Permission.objects.create(
            service=accounts,
            permission_code="accounts.registration_requests.reject",
            permission_name="Reject registrations",
            module_name="registration_requests",
            action_name="reject",
        )
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.student_role = Role.objects.create(role_name="Student")
        cls.reviewer = Account.objects.create(
            school_id="EMAIL-REVIEWER-001", request_status="Approved", is_active=True
        )
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin_role)
        RolePermission.objects.create(role=cls.admin_role, permission=approve)
        RolePermission.objects.create(role=cls.admin_role, permission=reject)

    def setUp(self):
        self.target = Account.objects.create(
            school_id="EMAIL-STUDENT-001",
            email="applicant@example.edu",
            requested_role=self.student_role,
            request_status="Pending",
            is_active=False,
        )

    def test_approved_email_only_after_successful_transaction(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            decided_id = approve_registration(actor=self.reviewer, target_id=self.target.pk)
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(decided_id, self.target.pk)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["applicant@example.edu"])
        self.assertIn("approved", mail.outbox[0].subject.lower())
        self.assertNotIn("EMAIL-STUDENT-001", mail.outbox[0].body)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertEqual(self.target.request_status, "Approved")

    def test_rejected_email_and_immutable_rejection_audit(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            reject_registration(
                actor=self.reviewer,
                target_id=self.target.pk,
                rejection_code="incomplete_submission",
            )
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["applicant@example.edu"])
        self.assertIn("rejected", mail.outbox[0].subject.lower())
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Rejected")
        self.assertFalse(self.target.is_active)
        self.assertTrue(Account.objects.filter(pk=self.target.pk).exists())
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.reject")

    def test_disabled_notification_gate_does_not_register_callback(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_email_skips_notification_without_blocking_review(self):
        self.target.email = None
        self.target.save(update_fields=["email"])
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_failed_audit_rolls_back_and_sends_nothing(self):
        with patch("apps.accounts.registration_review.record_access_audit", side_effect=RuntimeError("audit failed")):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(RuntimeError):
                    approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_email_delivery_failure_does_not_reverse_committed_decision(self):
        with patch(
            "apps.accounts.registration_notifications.send_mail",
            side_effect=OSError("private mail-server exception detail"),
        ):
            with self.assertLogs("apps.accounts.registration_notifications", level="ERROR") as captured:
                with self.captureOnCommitCallbacks(execute=True):
                    approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertNotIn("private mail-server exception detail", " ".join(captured.output))
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")
        self.assertTrue(self.target.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_second_decision_denied_without_second_email(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
            with self.assertRaises(RegistrationReviewDenied):
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
