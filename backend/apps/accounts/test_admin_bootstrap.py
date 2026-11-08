"""Isolated MySQL integration tests for the one-time first Workspace Admin bootstrap.

Must run with --settings=config.test_settings. NEVER run against real data.
"""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission,
    Role, RolePermission, Service,
)
from .admin_bootstrap import (
    BOOTSTRAP_ACTION, BootstrapRefused, bootstrap_preflight,
    provision_first_workspace_admin,
)
from .models import Account


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Bootstrap integration tests require isolated MySQL test settings.")


@override_settings(WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED=True)
class FirstAdminBootstrapTests(TransactionTestCase):
    reset_sequences = False
    operator_password = "Framework-Owner!1258"
    admin_password = "New-Workspace-Admin!3481"

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(cursor.fetchone()[0], settings.REGISTRATION_TEST_DATABASE)
        self.admin_role = Role.objects.create(role_name="Admin")
        self.operator = Account.objects.create_user(
            school_id="FRAMEWORK-ROOT", email="operator@example.edu.ph",
            password=self.operator_password,
        )
        self.operator.is_active = True
        self.operator.request_status = "Approved"
        self.operator.is_staff = True
        self.operator.is_superuser = True
        self.operator.save(update_fields=[
            "is_active", "request_status", "is_staff", "is_superuser",
        ])

    def _call(self, **overrides):
        args = {
            "operator_school_id": "FRAMEWORK-ROOT",
            "operator_password": self.operator_password,
            "new_school_id": "WORKSPACE-ADMIN-001",
            "new_email": "admin@example.edu.ph",
            "new_password": self.admin_password,
        }
        args.update(overrides)
        return provision_first_workspace_admin(**args)

    def test_read_only_preflight_does_not_write(self):
        result = bootstrap_preflight()
        self.assertTrue(result["admin_role_exists_and_active"])
        self.assertEqual(result["existing_admin_assignments"], 0)
        self.assertEqual(result["previous_bootstrap_events"], 0)
        self.assertEqual(result["framework_operators"], 1)
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_management_command_defaults_to_read_only(self):
        output = StringIO()
        call_command("bootstrap_workspace_admin", stdout=output)
        self.assertIn("READ-ONLY", output.getvalue())
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_one_time_bootstrap_creates_audited_admin_only(self):
        new_id = self._call()
        account = Account.objects.get(pk=new_id)
        self.assertEqual(account.request_status, "Approved")
        self.assertTrue(account.is_active)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertIsNone(account.requested_role_id)
        self.assertEqual(account.reviewed_by_id, self.operator.pk)
        self.assertTrue(account.check_password(self.admin_password))
        assignment = AccountRole.objects.get(account=account)
        self.assertEqual(assignment.role_id, self.admin_role.pk)
        self.assertEqual(assignment.assigned_by_id, self.operator.pk)
        self.assertFalse(AccountRole.objects.filter(account=self.operator).exists())
        log = AccessAuditLog.objects.get(action=BOOTSTRAP_ACTION)
        self.assertEqual(log.actor_account_id, self.operator.pk)
        self.assertEqual(log.target_account_id, account.pk)
        self.assertEqual(log.role_id, self.admin_role.pk)
        self.assertNotIn("school_id", log.new_value)
        self.assertNotIn("password", log.new_value)
        self.assertEqual(Service.objects.count(), 0)
        self.assertEqual(Permission.objects.count(), 0)
        self.assertEqual(RolePermission.objects.count(), 0)
        self.assertEqual(AccountPermission.objects.count(), 0)

    def test_second_bootstrap_is_rejected_even_with_different_school_id(self):
        self._call()
        with self.assertRaises(BootstrapRefused):
            self._call(new_school_id="WORKSPACE-ADMIN-002")
        self.assertEqual(AccountRole.objects.filter(role=self.admin_role).count(), 1)
        self.assertEqual(AccessAuditLog.objects.filter(action=BOOTSTRAP_ACTION).count(), 1)

    def test_disabled_by_default_rejects_creation(self):
        with override_settings(WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED=False):
            with self.assertRaises(BootstrapRefused):
                self._call()
        self.assertEqual(Account.objects.count(), 1)

    def test_bad_operator_password_is_rejected_without_writes(self):
        with self.assertRaises(BootstrapRefused):
            self._call(operator_password="wrong-password")
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_operator_must_be_active_approved_framework_superuser(self):
        self.operator.is_superuser = False
        self.operator.save(update_fields=["is_superuser"])
        with self.assertRaises(BootstrapRefused):
            self._call()
        self.assertEqual(Account.objects.count(), 1)

    def test_operator_must_not_have_workspace_assignment(self):
        AccountRole.objects.create(account=self.operator, role=self.admin_role)
        with self.assertRaises(BootstrapRefused):
            self._call()
        self.assertEqual(Account.objects.count(), 1)

    def test_pending_registration_is_not_promoted_or_reused(self):
        student_role = Role.objects.create(role_name="Student")
        applicant = Account.objects.create_user(
            school_id="EXISTING-STUDENT", password="Student!12345",
            requested_role=student_role,
        )
        with self.assertRaises(BootstrapRefused):
            self._call(new_school_id="EXISTING-STUDENT")
        applicant.refresh_from_db()
        self.assertEqual(applicant.request_status, "Pending")
        self.assertFalse(applicant.is_active)
        self.assertFalse(AccountRole.objects.filter(account=applicant).exists())

    def test_inactive_admin_role_refuses(self):
        self.admin_role.is_active = False
        self.admin_role.save(update_fields=["is_active"])
        with self.assertRaises(BootstrapRefused):
            self._call()
        self.assertEqual(Account.objects.count(), 1)

    def test_bad_admin_email_refuses(self):
        with self.assertRaises(BootstrapRefused):
            self._call(new_email="not-an-email")
        self.assertEqual(Account.objects.count(), 1)

    def test_bad_admin_password_validation_rolls_back_account(self):
        with self.assertRaises(Exception):
            self._call(new_password="a")
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_audit_failure_rolls_back_everything(self):
        with patch(
            "apps.accounts.admin_bootstrap.record_access_audit",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self._call()
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_previous_event_refuses_even_if_role_assignment_removed(self):
        self._call()
        AccountRole.objects.all().delete()
        with self.assertRaises(BootstrapRefused):
            self._call(new_school_id="WORKSPACE-ADMIN-002")
        self.assertEqual(Account.objects.count(), 2)

    def test_existing_admin_assignment_refuses_even_without_audit(self):
        other = Account.objects.create_user(
            school_id="LEGACY-ADMIN", password="Legacy-Admin!2345"
        )
        AccountRole.objects.create(account=other, role=self.admin_role)
        with self.assertRaises(BootstrapRefused):
            self._call()
        self.assertEqual(Account.objects.count(), 2)
