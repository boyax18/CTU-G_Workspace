"""AR-6C7D.9 P3C: exact-scope read-only gate in disposable local MySQL."""

from io import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
    exercise_registration_review_activation_recovery_test_only as p3b,
)
from apps.access_control.models import (
    AccountRole, AccessAuditLog, Role, RolePermission, Service,
)

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3C gate tests require --settings=config.test_settings.")


class OperationalScopeGateTests(TransactionTestCase):
    def setUp(self):
        self.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        self.student_role = Role.objects.create(role_name="Student", is_active=True)
        self.actor = self.account("P3C-GATE-ADMIN")
        AccountRole.objects.create(account=self.actor, role=self.admin_role)
        self.student = self.account("P3C-GATE-STUDENT")
        AccountRole.objects.create(account=self.student, role=self.student_role)

    def account(self, school_id, **kwargs):
        account = Account(school_id=school_id, request_status="Approved", is_active=True, **kwargs)
        account.set_unusable_password()
        account.save()
        return account

    def prepare(self):
        call_command(
            "init_registration_review_metadata_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO(),
        )
        call_command(
            "init_registration_review_inactive_bindings_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase2=p2.TEST_CONFIRM, stdout=StringIO(),
        )

    def report(self, *, actor=None, scope=None):
        output = StringIO()
        call_command(
            "report_registration_review_operational_gate_p3c",
            actor_account_id=self.actor.pk if actor is None else actor,
            expected_admin_account_ids=str(self.actor.pk) if scope is None else scope,
            stdout=output,
        )
        return output.getvalue()

    def assert_inactive(self):
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertFalse(RolePermission.objects.filter(is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_exact_scope_reports_blocked_and_performs_no_writes(self):
        self.prepare()
        output = self.report()
        self.assertIn("OPERATIONAL SCOPE VERIFIED", output)
        self.assertIn("ACTIVATION: BLOCKED", output)
        self.assertIn("NO WRITES EXECUTED", output)
        self.assert_inactive()

    def test_repeated_read_only_report_changes_nothing(self):
        self.prepare()
        first = self.report()
        second = self.report()
        self.assertEqual(first, second)
        self.assert_inactive()

    def test_actor_cannot_be_omitted_from_expected_scope(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.report(scope=str(self.student.pk))
        self.assert_inactive()

    def test_wrong_actor_is_refused(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.report(actor=self.student.pk)
        self.assert_inactive()

    def test_duplicate_or_malformed_scope_is_refused(self):
        self.prepare()
        for scope in (f"{self.actor.pk},{self.actor.pk}", "abc", "", "0"):
            with self.subTest(scope=scope), self.assertRaises(CommandError):
                self.report(scope=scope)
        self.assert_inactive()

    def test_unexpected_second_admin_is_refused(self):
        self.prepare()
        additional = self.account("P3C-GATE-EXTRA-ADMIN")
        AccountRole.objects.create(account=additional, role=self.admin_role)
        with self.assertRaises(CommandError):
            self.report()
        self.assert_inactive()

    def test_explicit_two_admin_scope_is_reportable_but_blocked(self):
        self.prepare()
        additional = self.account("P3C-GATE-SECOND-ADMIN")
        AccountRole.objects.create(account=additional, role=self.admin_role)
        output = self.report(scope=f"{self.actor.pk},{additional.pk}")
        self.assertIn("Eligible Admin count: 2", output)
        self.assertIn("ACTIVATION: BLOCKED", output)
        self.assert_inactive()

    def test_framework_privileged_admin_assignment_is_refused(self):
        self.prepare()
        privileged = self.account("P3C-GATE-FRAMEWORK-ADMIN", is_staff=True, is_superuser=True)
        AccountRole.objects.create(account=privileged, role=self.admin_role)
        with self.assertRaises(CommandError):
            self.report(scope=f"{self.actor.pk},{privileged.pk}")
        self.assert_inactive()

    def test_active_service_is_refused(self):
        self.prepare()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(CommandError):
            self.report()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_existing_activation_receipt_is_refused(self):
        self.prepare()
        AccessAuditLog.objects.create(
            actor_account=self.actor, action=p3b.SERVICE_ACTIVATE,
            reason="permission_change",
        )
        with self.assertRaises(CommandError):
            self.report()
        self.assertFalse(Service.objects.filter(is_active=True).exists())

    def test_enabled_api_gate_is_refused(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True):
            with self.assertRaises(CommandError):
                self.report()
        self.assert_inactive()

    def test_missing_phase_two_receipts_is_refused(self):
        self.prepare()
        AccessAuditLog.objects.filter(action=p2.EVENT).delete()
        with self.assertRaises(CommandError):
            self.report()
        self.assertFalse(Service.objects.filter(is_active=True).exists())
