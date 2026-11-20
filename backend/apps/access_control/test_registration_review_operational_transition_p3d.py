"""AR-6C7D.9 P3D: preview and disposable-MySQL-only operational candidate tests."""

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
    transition_registration_review_p3d as p3d,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3D tests require isolated --settings=config.test_settings.")


class OperationalTransitionCandidateTests(TransactionTestCase):
    def setUp(self):
        self.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        self.student_role = Role.objects.create(role_name="Student", is_active=True)
        self.actor = self.account("TEST-P3D-ADMIN")
        AccountRole.objects.create(account=self.actor, role=self.admin_role)
        self.student = self.account("TEST-P3D-STUDENT")
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
            confirm_local_dev_phase1=p1.TEST_CONFIRM,
            stdout=StringIO(),
        )
        call_command(
            "init_registration_review_inactive_bindings_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase2=p2.TEST_CONFIRM,
            stdout=StringIO(),
        )

    def operation(self, mode="activate", *, apply=False, actor=None, scope=None,
                  confirmation=p3d.TEST_CONFIRM):
        output = StringIO()
        call_command(
            "transition_registration_review_p3d",
            mode=mode,
            actor_account_id=self.actor.pk if actor is None else actor,
            expected_admin_account_ids=str(self.actor.pk) if scope is None else scope,
            apply=apply,
            confirm_disposable_test=confirmation,
            stdout=output,
        )
        return output.getvalue()

    def assert_inactive(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)
        self.assertFalse(get_effective_permissions(self.actor))
        self.assertFalse(get_effective_permissions(self.student))

    def assert_active(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 3)
        self.assertEqual(set(get_effective_permissions(self.actor)), set(p1.PERMISSION_CODES))
        self.assertFalse(get_effective_permissions(self.student))

    def test_local_style_preview_is_read_only_and_blocked(self):
        self.prepare()
        out = self.operation()
        self.assertIn("PREVIEW PASSED", out)
        self.assertIn("ACTUAL WRITES BLOCKED", out)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_preview_rejects_unknown_admin_in_scope(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.operation(scope=str(self.student.pk))
        self.assert_inactive()

    def test_preview_rejects_unexpected_additional_admin(self):
        self.prepare()
        another = self.account("TEST-P3D-OTHER-ADMIN")
        AccountRole.objects.create(account=another, role=self.admin_role)
        with self.assertRaises(CommandError):
            self.operation()
        self.assert_inactive()

    def test_preview_rejects_an_active_service(self):
        self.prepare()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(CommandError):
            self.operation()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_preview_rejects_tampered_p2_receipt(self):
        self.prepare()
        AccessAuditLog.objects.filter(action=p2.EVENT).update(reason="other_reason")
        with self.assertRaises(CommandError):
            self.operation()
        self.assert_inactive()

    def test_preview_rejects_unexpected_override(self):
        self.prepare()
        permission = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(account=self.actor, permission=permission,
                                         effect="Deny", is_active=True)
        with self.assertRaises(CommandError):
            self.operation()
        self.assert_inactive()

    def test_no_apply_never_writes_even_with_confirmation(self):
        self.prepare()
        self.assertIn("NO WRITES EXECUTED", self.operation(apply=False))
        self.assertEqual(AccessAuditLog.objects.count(), 8)
        self.assert_inactive()

    def test_apply_refuses_wrong_disposable_confirmation(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.operation(apply=True, confirmation="wrong")
        self.assertEqual(AccessAuditLog.objects.count(), 8)
        self.assert_inactive()

    def test_apply_refuses_local_settings_even_in_disposable_database(self):
        self.prepare()
        with override_settings(SETTINGS_MODULE="config.settings"):
            with self.assertRaises(CommandError):
                self.operation(apply=True)
        self.assert_inactive()

    def test_apply_rejects_wrong_actor(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.operation(apply=True, actor=self.student.pk)
        self.assert_inactive()

    def test_apply_activation_creates_five_audits_and_only_admin_effect(self):
        self.prepare()
        out = self.operation(apply=True)
        self.assertIn("TEST_ACTIVATED", out)
        self.assertIn("development_database_writes=NO", out)
        self.assert_active()
        self.assertEqual(AccessAuditLog.objects.count(), 13)
        self.assertEqual(AccessAuditLog.objects.filter(
            action__in=("workspace.review.service.activate", "workspace.review.role_binding.activate")
        ).count(), 5)

    def test_compensation_reverts_and_preserves_eighteen_audits(self):
        self.prepare()
        self.operation(apply=True)
        self.assert_active()
        self.assertIn("TEST_COMPENSATED", self.operation(mode="compensate", apply=True))
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)
        self.assertEqual(AccessAuditLog.objects.filter(
            action__in=("workspace.review.service.deactivate", "workspace.review.role_binding.deactivate")
        ).count(), 5)

    def test_compensation_preview_rejects_inactive_start_state(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.operation(mode="compensate")
        self.assert_inactive()

    def test_compensation_preview_reads_only_active_state(self):
        self.prepare()
        self.operation(apply=True)
        out = self.operation(mode="compensate")
        self.assertIn("PREVIEW PASSED", out)
        self.assertIn("ACTUAL WRITES BLOCKED", out)
        self.assert_active()
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_repeated_activation_refuses(self):
        self.prepare()
        self.operation(apply=True)
        with self.assertRaises(CommandError):
            self.operation(apply=True)
        self.assert_active()
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_compensation_without_activation_refuses(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.operation(mode="compensate", apply=True)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_repeated_compensation_refuses(self):
        self.prepare()
        self.operation(apply=True)
        self.operation(mode="compensate", apply=True)
        with self.assertRaises(CommandError):
            self.operation(mode="compensate", apply=True)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)

    def test_mid_transaction_audit_failure_rolls_back(self):
        self.prepare()
        original = p3d.record_access_audit_receipt
        attempts = 0

        def broken_receipt(**kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 4:
                raise RuntimeError("audit storage failure")
            return original(**kwargs)

        with patch.object(p3d, "record_access_audit_receipt", side_effect=broken_receipt):
            with self.assertRaises(CommandError):
                self.operation(apply=True)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_approved_superuser_with_admin_assignment_is_refused(self):
        self.prepare()
        framework = self.account("TEST-P3D-FRAMEWORK", is_staff=True, is_superuser=True)
        AccountRole.objects.create(account=framework, role=self.admin_role)
        with self.assertRaises(CommandError):
            self.operation(apply=True, scope=f"{self.actor.pk},{framework.pk}")
        self.assert_inactive()

    def test_requested_admin_without_assigned_role_stays_unprivileged(self):
        self.prepare()
        applicant = Account(school_id="TEST-P3D-REQUEST", requested_role=self.admin_role,
                            request_status="Pending", is_active=False)
        applicant.set_unusable_password()
        applicant.save()
        self.operation(apply=True)
        self.assertFalse(get_effective_permissions(applicant))

    def test_disabled_feature_flags_remain_disabled_after_test_activation(self):
        self.prepare()
        self.operation(apply=True)
        self.assertIs(getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False), False)
        self.assertIs(getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False), False)

    def test_enabled_approval_flag_refuses_test_activation(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(CommandError):
                self.operation(apply=True)
        self.assert_inactive()
