"""AR-6C7E.4 local-dev release candidate, exercised in disposable MySQL ONLY."""

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.test import TransactionTestCase

from apps.accounts.models import Account
from apps.access_control.management.commands import (
    init_registration_review_metadata_local_dev as p1,
    init_registration_review_inactive_bindings_local_dev as p2,
    report_registration_review_release_gates_p3e as p3e,
    transition_registration_review_p3d as p3d,
    release_registration_review_local_dev_p4 as p4,
)
from apps.access_control.models import (
    AccountPermission, AccountRole, AccessAuditLog, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P4 tests require the disposable MySQL test settings.")


class LocalReleaseCandidateTests(TransactionTestCase):
    def setUp(self):
        self.admin = Role.objects.create(role_name="Admin", is_active=True)
        self.student_role = Role.objects.create(role_name="Student", is_active=True)
        self.actor = self.account("TEST-P4-ADMIN")
        AccountRole.objects.create(account=self.actor, role=self.admin)
        self.student = self.account("TEST-P4-STUDENT")
        AccountRole.objects.create(account=self.student, role=self.student_role)

    def account(self, school_id, **kwargs):
        account = Account(school_id=school_id, request_status="Approved", is_active=True, **kwargs)
        account.set_unusable_password()
        account.save()
        return account

    def prepare(self):
        call_command("init_registration_review_metadata_local_dev", apply=True,
                     actor_account_id=self.actor.pk, confirm_local_dev_phase1=p1.TEST_CONFIRM,
                     stdout=StringIO())
        call_command("init_registration_review_inactive_bindings_local_dev", apply=True,
                     actor_account_id=self.actor.pk, confirm_local_dev_phase2=p2.TEST_CONFIRM,
                     stdout=StringIO())
        return p3e.inspect_release_gates(
            actor_account_id=self.actor.pk,
            expected_admin_account_ids=str(self.actor.pk),
        )["fingerprint"]

    def perform(self, mode, fingerprint=None, scope=None, confirmation=p4.LOCAL_CONFIRM):
        # Inject ONLY the disposable DB into this internal operation; normal CLI
        # has no such override and rejects test_settings before any write.
        with patch.object(p4, "_local_target", return_value=connections["default"]):
            return p4._perform(
                mode=mode, actor_id=self.actor.pk,
                expected_ids=scope or str(self.actor.pk),
                fingerprint=fingerprint,
                confirmation=confirmation,
            )

    def assert_inactive(self):
        self.assertEqual(Service.objects.filter(is_active=True).count(), 0)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 0)
        self.assertFalse(get_effective_permissions(self.actor))
        self.assertFalse(get_effective_permissions(self.student))

    def test_local_target_blocks_disposable_test_settings(self):
        self.prepare()
        with self.assertRaises(p4.LocalReleaseRefused):
            p4._local_target()
        self.assert_inactive()

    def test_preview_command_cannot_be_run_in_disposable_test_settings(self):
        fingerprint = self.prepare()
        with self.assertRaises(CommandError):
            call_command(
                "release_registration_review_local_dev_p4", mode="activate",
                actor_account_id=self.actor.pk,
                expected_admin_account_ids=str(self.actor.pk),
                expected_fingerprint=fingerprint, stdout=StringIO(),
            )
        self.assert_inactive()

    def test_requires_exact_confirmation(self):
        fingerprint = self.prepare()
        with self.assertRaises(p4.LocalReleaseRefused):
            self.perform("activate", fingerprint, confirmation="incorrect")
        self.assert_inactive()

    def test_fingerprint_is_required_and_checked(self):
        self.prepare()
        for invalid in (None, "0" * 64, "X" * 64):
            with self.assertRaises(p4.LocalReleaseRefused):
                self.perform("activate", invalid)
        self.assert_inactive()

    def test_activation_changes_five_records_and_grants_only_admin(self):
        fingerprint = self.prepare()
        self.assertEqual(self.perform("activate", fingerprint), "LOCAL_ACTIVATED")
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertEqual(RolePermission.objects.filter(is_active=True).count(), 3)
        self.assertEqual(set(get_effective_permissions(self.actor)), set(p1.PERMISSION_CODES))
        self.assertFalse(get_effective_permissions(self.student))
        self.assertEqual(AccessAuditLog.objects.count(), 13)
        self.assertIs(p3d.LOCAL_DEV_WRITES_RELEASED, False)

    def test_compensation_reverses_grants_and_preserves_audit(self):
        fingerprint = self.prepare()
        self.perform("activate", fingerprint)
        self.assertEqual(self.perform("compensate"), "LOCAL_COMPENSATED")
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)
        self.assertEqual(AccessAuditLog.objects.filter(action__in=(
            "workspace.review.service.deactivate",
            "workspace.review.role_binding.deactivate",
        )).count(), 5)

    def test_second_activation_is_refused(self):
        fingerprint = self.prepare()
        self.perform("activate", fingerprint)
        with self.assertRaises(Exception):
            self.perform("activate", fingerprint)
        self.assertEqual(AccessAuditLog.objects.count(), 13)

    def test_second_compensation_is_refused(self):
        fingerprint = self.prepare()
        self.perform("activate", fingerprint)
        self.perform("compensate")
        with self.assertRaises(Exception):
            self.perform("compensate")
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 18)

    def test_unexpected_additional_admin_blocks_activation(self):
        fingerprint = self.prepare()
        another = self.account("TEST-P4-OTHER-ADMIN")
        AccountRole.objects.create(account=another, role=self.admin)
        with self.assertRaises(Exception):
            self.perform("activate", fingerprint)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_account_override_blocks_activation(self):
        fingerprint = self.prepare()
        permission = Permission.objects.get(permission_code=p1.PERMISSION_CODES[0])
        AccountPermission.objects.create(account=self.student, permission=permission,
                                         effect="Deny", is_active=True)
        with self.assertRaises(Exception):
            self.perform("activate", fingerprint)
        self.assert_inactive()

    def test_mid_transaction_audit_failure_rolls_back(self):
        fingerprint = self.prepare()
        original = p3d.record_access_audit_receipt
        number = 0

        def fail(**kwargs):
            nonlocal number
            number += 1
            if number == 3:
                raise RuntimeError("Simulated audit failure")
            return original(**kwargs)

        with patch.object(p3d, "record_access_audit_receipt", side_effect=fail):
            with self.assertRaises(RuntimeError):
                self.perform("activate", fingerprint)
        self.assert_inactive()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_compensation_without_prior_activation_is_refused(self):
        self.prepare()
        with self.assertRaises(Exception):
            self.perform("compensate")
        self.assert_inactive()
