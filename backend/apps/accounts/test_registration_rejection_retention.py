"""AR-6C5B: non-destructive tests for rejected registrations.

These tests run only against CTU-G Workspace's isolated MySQL test database.
They do NOT perform cleanup, hard deletion, migrations or email sending.

Run:
  python manage.py test apps.accounts.test_registration_rejection_retention \
      --settings=config.test_settings --noinput
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)

from .models import Account, UserProfile
from .registration_review import (
    RegistrationReviewDenied,
    reject_registration,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith(
    "test_ctug_registration_"
):
    raise ImproperlyConfigured(
        "AR-6C5B retention tests require --settings=config.test_settings."
    )


@override_settings(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
)
class RejectedRegistrationRetentionTests(TestCase):
    """Document existing safe behavior while deletion policy is undecided."""

    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]
            if database_name != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected MySQL test database.")

        Service.objects.create(
            service_code="access_control", service_name="Access Control"
        )
        accounts_service = Service.objects.create(
            service_code="accounts", service_name="Accounts"
        )
        reject_permission = Permission.objects.create(
            service=accounts_service,
            permission_code="accounts.registration_requests.reject",
            permission_name="Reject registration requests",
            module_name="registration_requests",
            action_name="reject",
        )
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.student_role = Role.objects.create(role_name="Student")
        cls.reviewer = Account.objects.create(
            school_id="9000001", request_status="Approved", is_active=True
        )
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin_role)
        RolePermission.objects.create(
            role=cls.admin_role, permission=reject_permission
        )

    def setUp(self):
        self.target = Account.objects.create_user(
            school_id="9000002",
            email="test-applicant@example.edu",
            password="Mango!Library7392",
            requested_role=self.student_role,
        )
        self.profile = UserProfile.objects.create(
            account=self.target, first_name="Test", last_name="Applicant"
        )

    def _reject(self):
        return reject_registration(
            actor=self.reviewer,
            target_id=self.target.pk,
            rejection_code="incomplete_submission",
        )

    def test_rejection_leaves_inactive_account_profile_and_audit(self):
        account_id = self._reject()
        self.assertEqual(account_id, self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Rejected")
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.target.rejection_reason, "incomplete_submission")
        self.assertEqual(self.target.reviewed_by_id, self.reviewer.pk)
        self.assertIsNotNone(self.target.reviewed_at)
        self.assertTrue(UserProfile.objects.filter(pk=self.profile.pk).exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        event = AccessAuditLog.objects.get()
        self.assertEqual(event.action, "account.registration.reject")
        self.assertEqual(event.target_account_id, self.target.pk)
        self.assertEqual(event.actor_account_id, self.reviewer.pk)

    def test_direct_target_deletion_is_blocked_by_audit_and_profile_references(self):
        self._reject()
        with self.assertRaises(ProtectedError):
            self.target.delete()
        self.assertTrue(Account.objects.filter(pk=self.target.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.profile.pk).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_direct_reviewer_deletion_is_blocked_by_audit_reference(self):
        self._reject()
        with self.assertRaises(ProtectedError):
            self.reviewer.delete()
        self.assertTrue(Account.objects.filter(pk=self.reviewer.pk).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_second_rejection_is_denied_without_duplicate_audit(self):
        self._reject()
        with self.assertRaises(RegistrationReviewDenied):
            self._reject()
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_rejection_does_not_claim_to_erase_existing_personal_data(self):
        original_password_hash = self.target.password
        original_email = self.target.email
        self._reject()
        self.target.refresh_from_db()
        self.assertEqual(self.target.email, original_email)
        self.assertEqual(self.target.password, original_password_hash)
        self.assertEqual(self.target.profile.first_name, "Test")
        self.assertFalse(self.target.is_active)
