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
from .outbox_models import RegistrationNotificationOutbox
from .rejection_test_support import rejection_outbox
from .registration_review import (
    RegistrationRejectionNotAllowed,
    RegistrationReviewDenied,
    RegistrationReviewUnavailable,
    approve_registration,
    reject_registration,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Review notification tests require --settings=config.test_settings.")

# WF-02.03 (D-44/D-45): approval needs verified email ownership and the reviewer's attestation.
STUDENT_ATTESTATION = {"confirmed": True, "source": "ctu_main_system_records"}
INSTRUCTOR_ATTESTATION = {"confirmed": True, "source": "institutional_employment_records"}
APPROVAL_BODY = {"eligibility_confirmed": True, "eligibility_source": "ctu_main_system_records"}


def with_email_proof(account, email):
    """Record OTP proof for the account's current address, as WF-01.01/01.02 registration does."""
    from django.utils import timezone
    type(account).objects.filter(pk=account.pk).update(
        email=email, email_verified_at=timezone.now(), email_verified_address=email,
    )
    account.refresh_from_db()
    return account


@override_settings(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # Deterministic, local-only email context so a developer's backend/.env (for
    # example a LAN WORKSPACE_PUBLIC_BASE_URL or an enabled outbox) cannot change
    # the result. Production email rules are unchanged: http is accepted only for
    # localhost with the locmem test backend.
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    WORKSPACE_EMAIL_PUBLIC_HOSTS=frozenset(),
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
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
        self.target = with_email_proof(Account.objects.create(
            school_id="EMAIL-STUDENT-001",
            email="applicant@example.edu",
            requested_role=self.student_role,
            request_status="Pending",
            is_active=False,
        ), "applicant@example.edu")

    def test_approved_email_only_after_successful_transaction(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            decided_id = approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
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
        # WF-02.04 D-54 (owner-approved rewrite): rejection never uses this best-effort email path.
        # With the best-effort gate ON but no durable outbox, it is refused before any write.
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RegistrationReviewUnavailable):
                reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.assertEqual((len(callbacks), len(mail.outbox)), (0, 0))
        self.assertTrue(Account.objects.filter(pk=self.target.pk, request_status="Pending").exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        # With the outbox ready, an authorized rejection queues exactly one encrypted row bound to its
        # immutable audit inside the decision, schedules no best-effort email and sends nothing itself.
        with rejection_outbox(), self.captureOnCommitCallbacks(execute=True) as callbacks:
            reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.assertEqual((len(callbacks), len(mail.outbox)), (0, 0))
        audit = AccessAuditLog.objects.get()
        self.assertEqual(audit.action, "account.registration.reject")
        self.assertEqual(audit.new_value["rejection_code"], "incomplete_submission")
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual((row.decision_audit_log_id, row.template_code, row.template_version, row.delivery_status),
                         (audit.pk, "registration.rejected", 2, "Pending"))
        self.assertNotIn(b"applicant@example.edu", bytes(row.encrypted_recipient))
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())

    def test_disabled_notification_gate_does_not_register_callback(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.assertEqual(len(callbacks), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_email_skips_notification_without_blocking_review(self):
        # WF-02.04 D-55 (revised, owner-approved rewrite): without a recipient the rejection is now
        # REFUSED, even with the outbox ready: no deletion, role change, audit, row or email.
        self.target.email = None
        self.target.save(update_fields=["email"])
        with rejection_outbox(), self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
                reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.assertEqual(caught.exception.reason, "recipient_unverified")
        self.assertEqual((len(callbacks), len(mail.outbox)), (0, 0))
        self.target.refresh_from_db()
        self.assertEqual((self.target.request_status, self.target.is_active), ("Pending", False))
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_failed_audit_rolls_back_and_sends_nothing(self):
        with patch("apps.accounts.registration_review.record_access_audit", side_effect=RuntimeError("audit failed")):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(RuntimeError):
                    approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
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
                    approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.assertNotIn("private mail-server exception detail", " ".join(captured.output))
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")
        self.assertTrue(self.target.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_second_decision_denied_without_second_email(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
            with self.assertRaises(RegistrationReviewDenied):
                approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
