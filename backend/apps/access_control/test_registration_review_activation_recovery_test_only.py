"""P3B test-only activation/compensation; fresh disposable MySQL required."""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import Account
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
    exercise_registration_review_activation_recovery_test_only as p3b,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions, has_permission

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3B tests require --settings=config.test_settings.")


class ActivationRecoveryExerciseTests(TransactionTestCase):
    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.student_role = Role.objects.create(role_name="Student", is_active=True)
        self.instructor_role = Role.objects.create(role_name="Instructor", is_active=True)
        self.actor = self.account("TEST-P3B-ADMIN")
        AccountRole.objects.create(account=self.actor, role=self.admin)
        self.student = self.account("TEST-P3B-STUDENT")
        AccountRole.objects.create(account=self.student, role=self.student_role)
        self.instructor = self.account("TEST-P3B-INSTRUCTOR")
        AccountRole.objects.create(account=self.instructor, role=self.instructor_role)

    def account(self, school_id, **kwargs):
        account = Account(
            school_id=school_id, request_status="Approved", is_active=True,
            **kwargs,
        )
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

    def run_exercise(self, mode="activate", *, actor=None, scope=None,
                     confirmation=p3b.TEST_CONFIRM, run=True):
        output = StringIO()
        call_command(
            "exercise_registration_review_activation_recovery_test_only",
            run_disposable_test=run,
            mode=mode,
            actor_account_id=self.actor.pk if actor is None else actor,
            expected_admin_account_ids=str(self.actor.pk) if scope is None else scope,
            confirm_disposable_test=confirmation,
            stdout=output,
        )
        return output.getvalue()

    def assert_inactive(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)
        for account in (self.actor, self.student, self.instructor):
            self.assertFalse(get_effective_permissions(account) & set(p1.PERMISSION_CODES))

    def assert_active_only_for_admin(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 3)
        self.assertEqual(set(p1.PERMISSION_CODES), get_effective_permissions(self.actor))
        for account in (self.student, self.instructor):
            self.assertFalse(get_effective_permissions(account) & set(p1.PERMISSION_CODES))

    def test_activation_exact_5_receipts_and_admin_effect(self):
        self.prepare()
        output = self.run_exercise()
        self.assertIn("EXERCISED_ACTIVATION", output)
        self.assertIn("development_database_writes=NO", output)
        self.assertEqual(AccountPermission.objects.count(), 0)
        self.assert_active_only_for_admin()
        self.assertEqual(AccessAuditLog.objects.filter(action__in=p3b.TRANSITION_EVENTS).count(), 5)
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_compensation_reverses_grants_and_keeps_all_receipts(self):
        self.prepare()
        self.run_exercise()
        self.assertIn("EXERCISED_COMPENSATION", self.run_exercise("compensate"))
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.SERVICE_DEACTIVATE).count(), 2)
        self.assertEqual(AccessAuditLog.objects.filter(action=p3b.BINDING_DEACTIVATE).count(), 3)

    def test_disabled_flags_and_url_remain_unmodified(self):
        self.prepare()
        self.run_exercise()
        self.assertIs(getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False), False)
        self.assertIs(getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False), False)
        with self.assertRaises(NoReverseMatch):
            reverse("registration-review-pending")
        self.run_exercise("compensate")
        with self.assertRaises(NoReverseMatch):
            reverse("registration-review-pending")

    def test_no_implicit_run(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise(run=False)
        self.assert_inactive()

    def test_wrong_confirmation_is_refused(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise(confirmation="wrong")
        self.assert_inactive()

    def test_local_development_settings_are_always_refused(self):
        self.prepare()
        with override_settings(SETTINGS_MODULE="config.settings"):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()

    def test_wrong_actor_is_refused(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise(actor=self.student.pk)
        self.assert_inactive()

    def test_expected_admin_scope_must_include_actor(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise(scope=str(self.student.pk))
        self.assert_inactive()

    def test_duplicate_scope_id_is_refused(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise(scope=f"{self.actor.pk},{self.actor.pk}")
        self.assert_inactive()

    def test_added_admin_cannot_be_silently_excluded(self):
        self.prepare()
        additional = self.account("TEST-P3B-SECOND-ADMIN")
        AccountRole.objects.create(account=additional, role=self.admin)
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_explicit_second_admin_scope_is_supported(self):
        self.prepare()
        additional = self.account("TEST-P3B-SECOND-ADMIN")
        AccountRole.objects.create(account=additional, role=self.admin)
        self.run_exercise(scope=f"{self.actor.pk},{additional.pk}")
        self.assertEqual(set(p1.PERMISSION_CODES), get_effective_permissions(additional))
        self.run_exercise("compensate", scope=f"{self.actor.pk},{additional.pk}")
        self.assertFalse(get_effective_permissions(additional))

    def test_requested_role_without_assignment_cannot_gain_grant(self):
        self.prepare()
        applicant = Account(school_id="TEST-P3B-APPLICANT", requested_role=self.admin,
                            request_status="Pending", is_active=False)
        applicant.set_unusable_password()
        applicant.save()
        self.run_exercise()
        self.assertFalse(has_permission(applicant, p1.PERMISSION_CODES[0]))

    def test_staff_superuser_admin_assignment_is_refused(self):
        self.prepare()
        staff = self.account("TEST-P3B-FRAMEWORK-ADMIN", is_staff=True, is_superuser=True)
        AccountRole.objects.create(account=staff, role=self.admin)
        with self.assertRaises(CommandError):
            self.run_exercise(scope=f"{self.actor.pk},{staff.pk}")
        self.assert_inactive()

    def test_superuser_without_admin_role_gets_no_permissions(self):
        self.prepare()
        staff = self.account("TEST-P3B-FRAMEWORK-ONLY", is_staff=True, is_superuser=True)
        self.run_exercise()
        self.assertFalse(get_effective_permissions(staff))

    def test_account_override_is_refused(self):
        self.prepare()
        permission = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(account=self.actor, permission=permission,
                                         effect="Deny", is_active=True)
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_extra_service_refuses_activation(self):
        self.prepare()
        Service.objects.create(service_code="unrelated", service_name="Unrelated", is_active=False)
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_partial_service_activation_is_refused(self):
        self.prepare()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_tampered_phase_one_receipt_refuses_activation(self):
        self.prepare()
        AccessAuditLog.objects.filter(action=p1.SERVICE_EVENT).update(reason="correction")
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_tampered_phase_two_receipt_refuses_activation(self):
        self.prepare()
        AccessAuditLog.objects.filter(action=p2.EVENT).update(reason="correction")
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_disabled_backend_gate_refuses_activation_if_enabled(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()

    def test_active_approval_gate_refuses_activation(self):
        self.prepare()
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()

    def test_failed_first_audit_rolls_back_activation(self):
        self.prepare()
        with patch.object(p3b, "record_access_audit_receipt", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_failed_midway_audit_rolls_back_entire_activation(self):
        self.prepare()
        original = p3b.record_access_audit_receipt
        calls = 0

        def fail_on_fourth(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise RuntimeError("audit unavailable")
            return original(**kwargs)

        with patch.object(p3b, "record_access_audit_receipt", side_effect=fail_on_fourth):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_concurrent_lock_refusal_does_not_write(self):
        self.prepare()
        with patch.object(p3b, "_acquire_lock", side_effect=p3b.ActivationExerciseRefused("busy")):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_repeated_activation_is_refused(self):
        self.prepare()
        self.run_exercise()
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_active_only_for_admin()
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_compensation_without_activation_is_refused(self):
        self.prepare()
        with self.assertRaises(CommandError):
            self.run_exercise("compensate")
        self.assert_inactive()

    def test_compensation_requires_untampered_activation_receipt(self):
        self.prepare()
        self.run_exercise()
        AccessAuditLog.objects.filter(action=p3b.SERVICE_ACTIVATE).update(reason="correction")
        with self.assertRaises(CommandError):
            self.run_exercise("compensate")
        self.assert_active_only_for_admin()

    def test_compensation_rolls_back_if_audit_write_fails(self):
        self.prepare()
        self.run_exercise()
        with patch.object(p3b, "record_access_audit_receipt", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(CommandError):
                self.run_exercise("compensate")
        self.assert_active_only_for_admin()
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_second_compensation_is_refused(self):
        self.prepare()
        self.run_exercise()
        self.run_exercise("compensate")
        with self.assertRaises(CommandError):
            self.run_exercise("compensate")
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)

    def test_reactivation_after_compensation_is_refused(self):
        self.prepare()
        self.run_exercise()
        self.run_exercise("compensate")
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)

    def test_no_activation_route_or_account_decisions(self):
        self.prepare()
        self.run_exercise()
        self.assertEqual(Account.objects.filter(request_status="Pending").count(), 0)
        with self.assertRaises(NoReverseMatch):
            reverse("registration-review-pending")
        self.assertEqual(AccountRole.objects.filter(role=self.student_role).count(), 1)
        self.assertEqual(AccountRole.objects.filter(role=self.instructor_role).count(), 1)

    def test_compensation_refuses_enabled_approval_flag(self):
        self.prepare()
        self.run_exercise()
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(CommandError):
                self.run_exercise("compensate")
        self.assert_active_only_for_admin()

    def test_missing_phase_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_missing_phase_two_is_refused(self):
        call_command(
            "init_registration_review_metadata_local_dev",
            apply=True, actor_account_id=self.actor.pk,
            confirm_local_dev_phase1=p1.TEST_CONFIRM, stdout=StringIO(),
        )
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assertEqual(AccessAuditLog.objects.count(), 5)

    def test_frozen_catalogue_drift_refuses_activation(self):
        self.prepare()
        with patch.object(p1, "load_local", side_effect=ValueError("drift")):
            with self.assertRaises(CommandError):
                self.run_exercise()
        self.assert_inactive()

    def test_disabled_admin_actor_refuses_activation(self):
        self.prepare()
        Account.objects.filter(pk=self.actor.pk).update(is_active=False)
        with self.assertRaises(CommandError):
            self.run_exercise()
        self.assert_inactive()

    def test_compensation_midway_audit_failure_rolls_back_all_changes(self):
        self.prepare()
        self.run_exercise()
        original = p3b.record_access_audit_receipt
        calls = 0

        def fail_on_fourth(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise RuntimeError("audit unavailable")
            return original(**kwargs)

        with patch.object(p3b, "record_access_audit_receipt", side_effect=fail_on_fourth):
            with self.assertRaises(CommandError):
                self.run_exercise("compensate")
        self.assert_active_only_for_admin()
        self.assertEqual(AccessAuditLog.objects.count(), 13)
