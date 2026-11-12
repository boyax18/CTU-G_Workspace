"""AR-6C7D.9 P3E release evidence tests; disposable MySQL ONLY."""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
    report_registration_review_release_gates_p3e as p3e,
    transition_registration_review_p3d as p3d,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role, RolePermission, Service,
)

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3E tests MUST run in disposable config.test_settings MySQL.")


class ReadOnlyReleaseGateTests(TransactionTestCase):
    def setUp(self):
        self.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        self.student_role = Role.objects.create(role_name="Student", is_active=True)
        self.actor = self.account("TEST-P3E-ADMIN")
        AccountRole.objects.create(account=self.actor, role=self.admin_role)
        self.student = self.account("TEST-P3E-STUDENT")
        AccountRole.objects.create(account=self.student, role=self.student_role)
        self.prepare()

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

    def inspect(self, scope=None, actor=None, fingerprint=None):
        return p3e.inspect_release_gates(
            actor_account_id=self.actor.pk if actor is None else actor,
            expected_admin_account_ids=str(self.actor.pk) if scope is None else scope,
            expected_fingerprint=fingerprint,
        )

    def report(self, fingerprint=None):
        out = StringIO()
        call_command(
            "report_registration_review_release_gates_p3e",
            actor_account_id=self.actor.pk,
            expected_admin_account_ids=str(self.actor.pk),
            expected_fingerprint=fingerprint,
            stdout=out,
        )
        return out.getvalue()

    def unchanged(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)
        self.assertEqual(AccountPermission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_report_has_fingerprint_but_no_release(self):
        report = self.report()
        self.assertIn("READ-ONLY RELEASE EVIDENCE PASSED", report)
        self.assertIn("Authorization snapshot SHA-256:", report)
        self.assertIn("ACTUAL ACTIVATION: BLOCKED", report)
        self.unchanged()

    def test_fingerprint_stable_on_repeated_read(self):
        first = self.inspect()["fingerprint"]
        second = self.inspect()["fingerprint"]
        self.assertEqual(first, second)
        self.unchanged()

    def test_matching_fingerprint_can_be_rechecked(self):
        fingerprint = self.inspect()["fingerprint"]
        self.assertIn(fingerprint, self.report(fingerprint))
        self.unchanged()

    def test_incorrect_fingerprint_refuses_without_writes(self):
        with self.assertRaises(p3e.ReleaseGateRefused):
            self.inspect(fingerprint="0" * 64)
        self.unchanged()

    def test_non_hex_fingerprint_refuses(self):
        with self.assertRaises(p3e.ReleaseGateRefused):
            self.inspect(fingerprint="not-a-hash")
        self.unchanged()

    def test_unauthorized_student_as_audit_actor_refuses(self):
        with self.assertRaises(Exception):
            self.inspect(actor=self.student.pk)
        self.unchanged()

    def test_changed_expected_admin_set_refuses(self):
        with self.assertRaises(Exception):
            self.inspect(scope=str(self.student.pk))
        self.unchanged()

    def test_extra_eligible_admin_assignment_refuses(self):
        extra = self.account("TEST-P3E-EXTRA-ADMIN")
        AccountRole.objects.create(account=extra, role=self.admin_role)
        with self.assertRaises(Exception):
            self.inspect()
        self.unchanged()

    def test_activated_service_refuses(self):
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(Exception):
            self.inspect()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_activated_binding_refuses(self):
        RolePermission.objects.update(is_active=True)
        with self.assertRaises(Exception):
            self.inspect()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_tampered_phase_one_receipt_refuses(self):
        AccessAuditLog.objects.filter(action=p1.SERVICE_EVENT).update(reason="unexpected")
        with self.assertRaises(Exception):
            self.inspect()
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)

    def test_added_account_override_refuses(self):
        permission = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(
            account=self.student, permission=permission, effect="Grant",
            is_active=False, assigned_by=self.actor,
        )
        with self.assertRaises(Exception):
            self.inspect()
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_enabled_approval_flag_refuses(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(Exception):
                self.inspect()
        self.unchanged()

    def test_modified_local_release_constant_refuses(self):
        with patch.object(p3d, "LOCAL_DEV_WRITES_RELEASED", True):
            with self.assertRaises(p3e.ReleaseGateRefused):
                self.inspect()
        self.unchanged()

    def test_backup_waiver_does_not_unlock_local_write_gate(self):
        self.inspect()
        with override_settings(SETTINGS_MODULE="config.settings"):
            with self.assertRaises(p3d.TransitionRefused):
                p3d._write_target("operator-skipped-backup")
        self.unchanged()

    def test_apply_switch_not_exposed(self):
        parser = p3e.Command().create_parser("manage.py", "report_registration_review_release_gates_p3e")
        option_names = {opt for action in parser._actions for opt in action.option_strings}
        self.assertNotIn("--apply", option_names)
        self.assertNotIn("--release", option_names)
        self.assertNotIn("--backup-complete", option_names)
        self.unchanged()

    def test_unexpected_transition_receipt_refuses_drift_check(self):
        old = self.inspect()["fingerprint"]
        # Added transition evidence is unauthorized and rejected rather than rehashed.
        AccessAuditLog.objects.create(
            actor_account=self.actor, action="workspace.review.service.activate",
            reason="permission_change",
        )
        with self.assertRaises(Exception):
            self.inspect(fingerprint=old)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)

    def test_management_command_surfaces_refusal(self):
        with self.assertRaises(CommandError):
            self.report("f" * 64)
        self.unchanged()
