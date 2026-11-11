"""AR-6C7C.7 isolated staged-binding tests; require config.test_settings."""
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission,
    Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions
from apps.access_control.tests_support.registration_review_metadata import (
    exercise_metadata_transaction_in_disposable_test,
)
from apps.access_control.tests_support import registration_review_inactive_grants as subject

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("AR-6C7C.7 tests require --settings=config.test_settings.")


class RegistrationReviewInactiveGrantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Role.objects.create(role_name="Admin", is_active=True)
        cls.actor = Account(school_id="TEST-C7C7-ACTOR", is_active=True, request_status="Approved")
        cls.actor.set_unusable_password()
        cls.actor.save()

    def prepare_metadata(self):
        exercise_metadata_transaction_in_disposable_test(test_audit_actor=self.actor)

    def stage(self, actor=None):
        return subject.exercise_inactive_admin_bindings_in_disposable_test(
            test_audit_actor=actor if actor is not None else self.actor
        )

    def test_exact_three_bindings_remain_inactive_and_audited(self):
        self.prepare_metadata()
        report = self.stage()
        self.assertEqual(report, {"inactive_bindings_created": 3, "active_grants": 0,
                                  "services_activated": 0, "test_database_only": True})
        self.assertEqual(RolePermission.objects.count(), 3)
        self.assertFalse(RolePermission.objects.filter(is_active=True).exists())
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 8)  # 5 metadata + 3 bindings
        self.assertEqual(AccessAuditLog.objects.filter(action="test.role_permission.stage_inactive").count(), 3)
        self.assertFalse(AccountPermission.objects.exists())

    def test_rerun_does_not_duplicate_bindings_or_audits(self):
        self.prepare_metadata()
        self.stage()
        self.assertEqual(self.stage()["inactive_bindings_created"], 0)
        self.assertEqual(RolePermission.objects.count(), 3)
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_audit_failure_rolls_back_all_staged_bindings(self):
        self.prepare_metadata()
        original = subject.record_access_audit_receipt
        calls = [0]
        def fail_second(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError("injected audit failure")
            return original(*args, **kwargs)
        with patch.object(subject, "record_access_audit_receipt", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "injected audit failure"):
                self.stage()
        self.assertEqual(RolePermission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 5)

    def test_missing_metadata_refused_without_writes(self):
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage()
        self.assertFalse(RolePermission.objects.exists())

    def test_live_database_name_refused(self):
        self.prepare_metadata()
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"):
            with self.assertRaises(subject.TestInactiveGrantRefused):
                self.stage()
        self.assertFalse(RolePermission.objects.exists())

    def test_active_service_refused(self):
        self.prepare_metadata()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage()
        self.assertFalse(RolePermission.objects.exists())

    def test_existing_active_grant_refused(self):
        self.prepare_metadata()
        perm = Permission.objects.get(permission_code="accounts.registration_requests.read")
        RolePermission.objects.create(role=self.admin, permission=perm, is_active=True,
                                      granted_by=self.actor)
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage()
        self.assertEqual(RolePermission.objects.count(), 1)

    def test_account_override_refused(self):
        self.prepare_metadata()
        perm = Permission.objects.get(permission_code="accounts.registration_requests.read")
        AccountPermission.objects.create(account=self.actor, permission=perm, effect="Deny", is_active=True)
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage()
        self.assertFalse(RolePermission.objects.exists())

    def test_foreign_grant_actor_refused(self):
        self.prepare_metadata()
        other = Account(school_id="TEST-C7C7-OTHER", is_active=True, request_status="Approved")
        other.set_unusable_password()
        other.save()
        perm = Permission.objects.get(permission_code="accounts.registration_requests.read")
        RolePermission.objects.create(role=self.admin, permission=perm, is_active=False,
                                      granted_by=other)
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage()
        self.assertEqual(RolePermission.objects.count(), 1)

    def test_no_effective_access_even_with_assigned_admin_role(self):
        self.prepare_metadata()
        AccountRole.objects.create(account=self.actor, role=self.admin)
        self.stage()
        self.assertFalse(get_effective_permissions(self.actor))
        self.assertEqual(AccountRole.objects.count(), 1)

    def test_non_persisted_actor_refused(self):
        self.prepare_metadata()
        with self.assertRaises(subject.TestInactiveGrantRefused):
            self.stage(actor=Account(school_id="UNSAVED-C7C7"))
        self.assertFalse(RolePermission.objects.exists())

    def test_changed_frozen_contract_refused(self):
        self.prepare_metadata()
        with patch.object(subject.metadata, "_metadata_from_frozen_draft", side_effect=RuntimeError("changed")):
            with self.assertRaises(subject.TestInactiveGrantRefused):
                self.stage()
        self.assertFalse(RolePermission.objects.exists())
