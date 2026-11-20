"""Rejection deletion and audit retention, only in disposable MySQL fixtures.

Run:
  python manage.py test apps.accounts.test_registration_rejection_retention \
      --settings=config.test_settings --noinput
"""

from django.conf import settings
from unittest.mock import patch
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.access_control.models import (
    AccessAuditLog,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)

from .models import Account, UserProfile
from .rejection_test_support import REJECTION_READY, fresh_test_key, verified_email
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
    # WF-02.04 D-54/D-55 (owner-approved test correction): rejection needs the durable outbox.
    **REJECTION_READY,
)
class RejectedRegistrationRetentionTests(TestCase):
    """Remove fresh applicants while retaining immutable rejection evidence."""

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
        import os
        key = patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()})
        key.start()
        self.addCleanup(key.stop)
        self.target = verified_email(Account.objects.create_user(
            school_id="9000002",
            email="test-applicant@example.edu",
            password="Mango!Library7392",
            requested_role=self.student_role,
        ), "test-applicant@example.edu")
        self.profile = UserProfile.objects.create(
            account=self.target, first_name="Test", last_name="Applicant"
        )

    def _reject(self):
        return reject_registration(
            actor=self.reviewer,
            target_id=self.target.pk,
            rejection_code="incomplete_submission",
        )

    def test_rejection_deletes_account_and_profile_but_retains_snapshot_and_reviewer(self):
        account_id = self._reject()
        self.assertEqual(account_id, self.target.pk)
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())
        self.assertFalse(UserProfile.objects.filter(pk=self.profile.pk).exists())
        self.assertTrue(Account.objects.filter(pk=self.reviewer.pk).exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        event = AccessAuditLog.objects.get()
        self.assertEqual(event.action, "account.registration.reject")
        self.assertIsNone(event.target_account_id)
        self.assertEqual(event.actor_account_id, self.reviewer.pk)
        self.assertEqual(event.old_value["account_id"], self.target.pk)
        self.assertEqual(event.new_value, {
            "account_id": self.target.pk, "request_status": "Rejected", "is_active": False,
            "rejection_code": "incomplete_submission", "account_deleted": True,
        })

    def test_existing_audit_history_blocks_deletion_without_altering_history(self):
        event = AccessAuditLog.objects.create(
            actor_account=self.reviewer, target_account=self.target,
            action="account.registration.reject", new_value={"request_status": "Rejected"},
        )
        before = AccessAuditLog.objects.values().get(pk=event.pk)
        with self.assertRaises(RegistrationReviewDenied):
            self._reject()
        self.assertTrue(Account.objects.filter(pk=self.target.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.profile.pk).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertEqual(AccessAuditLog.objects.values().get(pk=event.pk), before)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")

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

    def test_rejected_applicant_can_register_again_with_same_credentials(self):
        old_id = self.target.pk
        self._reject()
        replacement = Account.objects.create_user(
            school_id=self.target.school_id, email=self.target.email,
            password="Other!Library7392", requested_role=self.student_role,
        )
        self.assertNotEqual(replacement.pk, old_id)
        self.assertEqual(replacement.request_status, "Pending")
        self.assertFalse(replacement.is_active)
        self.assertTrue(replacement.check_password("Other!Library7392"))
        self.assertEqual(AccessAuditLog.objects.get().new_value["account_id"], old_id)

    def test_delete_failure_rolls_back_profile_status_and_audit(self):
        with patch("apps.accounts.registration_review._delete_rejected_registration", side_effect=RuntimeError("delete unavailable")):
            with self.assertRaises(RuntimeError):
                self._reject()
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertEqual(self.target.profile.first_name, "Test")
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_rejection_issues_deletes_only_for_the_applicant_tables(self):
        with CaptureQueriesContext(connection) as queries:
            self._reject()
        deletes = [q["sql"] for q in queries if q["sql"].upper().startswith("DELETE")]
        self.assertEqual(len(deletes), 2)
        self.assertTrue(deletes[0].startswith("DELETE FROM users WHERE account_id="))
        self.assertTrue(deletes[1].startswith("DELETE FROM accounts WHERE account_id="))

    def test_framework_history_is_preserved_and_prevents_deletion(self):
        from django.contrib.admin.models import ADDITION, LogEntry

        entry = LogEntry.objects.create(user=self.target, action_flag=ADDITION, object_repr="Synthetic fixture")
        with self.assertRaises(RegistrationReviewDenied):
            self._reject()
        self.assertTrue(LogEntry.objects.filter(pk=entry.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.profile.pk).exists())
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
