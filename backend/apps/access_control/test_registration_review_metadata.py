"""AR-6C7C.6 isolated MySQL tests; NEVER run with regular settings."""

from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import TestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission,
    Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions
from apps.access_control.tests_support import registration_review_metadata as subject


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("AR-6C7C.6 tests require --settings=config.test_settings.")


class RegistrationReviewMetadataTransactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Role.objects.create(role_name="Admin", is_active=True)
        cls.actor = Account(school_id="TEST-C7C6-AUDIT-ACTOR", request_status="Approved", is_active=True)
        cls.actor.set_unusable_password()
        cls.actor.save()

    def exercise(self, **kwargs):
        return subject.exercise_metadata_transaction_in_disposable_test(
            test_audit_actor=kwargs.pop("actor", self.actor)
        )

    def test_creates_exact_inactive_metadata_and_five_bounded_audits(self):
        report = self.exercise()
        self.assertEqual(report, {"created_services": 2, "created_permissions": 3,
                                  "grants_created": 0, "services_activated": 0, "test_database_only": True})
        self.assertEqual(set(Service.objects.values_list("service_code", flat=True)), set(subject.SERVICE_CODES))
        self.assertEqual(set(Permission.objects.values_list("permission_code", flat=True)), set(subject.PERMISSION_CODES))
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertEqual(AccessAuditLog.objects.count(), 5)
        self.assertFalse(RolePermission.objects.exists())
        self.assertFalse(AccountPermission.objects.exists())
        self.assertEqual(Role.objects.count(), 1)
        self.assertEqual(AccountRole.objects.count(), 0)
        self.assertEqual(set(AccessAuditLog.objects.values_list("reason", flat=True)), {"permission_change"})
        self.assertTrue(all(row.actor_account_id == self.actor.pk for row in AccessAuditLog.objects.all()))

    def test_second_run_is_idempotent_without_duplicate_audits(self):
        self.exercise()
        second = self.exercise()
        self.assertEqual(second["created_services"], 0)
        self.assertEqual(second["created_permissions"], 0)
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(Permission.objects.count(), 3)
        self.assertEqual(AccessAuditLog.objects.count(), 5)

    def test_audit_failure_mid_transaction_rolls_back_all_metadata_and_audits(self):
        original = subject.record_access_audit_receipt
        calls = [0]
        def fail_on_third(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 3:
                raise RuntimeError("injected audit failure")
            return original(*args, **kwargs)
        with patch.object(subject, "record_access_audit_receipt", side_effect=fail_on_third):
            with self.assertRaisesRegex(RuntimeError, "injected audit failure"):
                self.exercise()
        self.assertEqual(Service.objects.count(), 0)
        self.assertEqual(Permission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_mismatched_service_refuses_without_writes(self):
        Service.objects.create(service_code="accounts", service_name="Wrong name", is_active=False)
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(Permission.objects.count(), 0)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_active_service_refuses_without_writes(self):
        Service.objects.create(service_code="accounts", service_name="Accounts and Profiles", is_active=True)
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(Permission.objects.count(), 0)

    def test_unexpected_service_refuses(self):
        Service.objects.create(service_code="surprise", service_name="Unexpected", is_active=False)
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(Service.objects.count(), 1)

    def test_existing_role_grant_refuses_without_other_metadata(self):
        other = Service.objects.create(service_code="accounts", service_name="Accounts and Profiles", is_active=False)
        permission = Permission.objects.create(service=other, permission_code="accounts.registration_requests.read",
                                               permission_name="stub", module_name="registration_requests", action_name="read")
        RolePermission.objects.create(role=self.role, permission=permission, is_active=False)
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_existing_account_override_refuses(self):
        service = Service.objects.create(service_code="accounts", service_name="Accounts and Profiles", is_active=False)
        permission = Permission.objects.create(service=service, permission_code="accounts.registration_requests.read",
                                               permission_name="stub", module_name="registration_requests", action_name="read")
        AccountPermission.objects.create(account=self.actor, permission=permission, effect="Deny", is_active=True)
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_missing_admin_role_refuses(self):
        self.role.delete()
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise()
        self.assertEqual(Service.objects.count(), 0)

    def test_nonpersisted_actor_refuses(self):
        with self.assertRaises(subject.TestMetadataRefused):
            self.exercise(actor=Account(school_id="UNSAVED"))
        self.assertFalse(Service.objects.exists())

    def test_non_disposable_configuration_is_refused(self):
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"):
            with self.assertRaises(subject.TestMetadataRefused):
                self.exercise()
        self.assertFalse(Service.objects.exists())

    def test_changed_frozen_profile_is_refused(self):
        with patch.object(subject, "verify_contract", side_effect=ValueError("changed profile")):
            with self.assertRaises(subject.TestMetadataRefused):
                self.exercise()
        self.assertFalse(Service.objects.exists())

    def test_inactive_services_dont_unlock_module_even_with_admin_assignment(self):
        AccountRole.objects.create(account=self.actor, role=self.role)
        self.exercise()
        self.assertEqual(len(get_effective_permissions(self.actor)), 0)
        self.assertEqual(RolePermission.objects.count(), 0)
