"""AR-6C7D.4 test-only protected initialization candidate; disposable MySQL."""
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions
from apps.access_control.tests_support import (
    registration_review_metadata as metadata,
    registration_review_inactive_grants as inactive,
    registration_review_protected_candidate as subject,
)

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("AR-6C7D.4 tests require --settings=config.test_settings.")


class ProtectedRegistrationCandidateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Role.objects.create(role_name="Admin", is_active=True)
        cls.actor = Account(school_id="TEST-D4-ACTOR", is_active=True,
                            request_status="Approved")
        cls.actor.set_unusable_password()
        cls.actor.save()

    def candidate(self, actor=None):
        return subject.exercise_protected_initialization_candidate_in_disposable_test(
            test_audit_actor=self.actor if actor is None else actor)

    def test_first_pass_exact_inactive_rows_and_eight_receipts(self):
        result = self.candidate()
        self.assertEqual(result, {
            "created_services": 2, "created_permissions": 3,
            "inactive_bindings_created": 3, "audit_receipts_verified": 8,
            "active_grants": 0, "services_activated": 0,
            "api_activated": False, "test_database_only": True,
            "live_execution_authorized": False,
        })
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(Permission.objects.count(), 3)
        self.assertEqual(RolePermission.objects.count(), 3)
        self.assertEqual(AccessAuditLog.objects.count(), 8)
        self.assertFalse(Service.objects.filter(is_active=True).exists())
        self.assertFalse(RolePermission.objects.filter(is_active=True).exists())
        self.assertFalse(AccountPermission.objects.exists())

    def test_repeat_is_idempotent_and_audit_exact(self):
        self.candidate()
        result = self.candidate()
        self.assertEqual((result["created_services"], result["created_permissions"],
                          result["inactive_bindings_created"]), (0, 0, 0))
        self.assertEqual(result["audit_receipts_verified"], 8)
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_failure_during_second_binding_audit_rolls_back_everything(self):
        original = inactive.record_access_audit_receipt
        call_count = [0]
        def fail_second(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("injected stage audit failure")
            return original(*args, **kwargs)
        with patch.object(inactive, "record_access_audit_receipt", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "injected stage audit failure"):
                self.candidate()
        self.assertFalse(Service.objects.exists())
        self.assertFalse(Permission.objects.exists())
        self.assertFalse(RolePermission.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_metadata_audit_failure_rolls_back_everything(self):
        with patch.object(metadata, "record_access_audit_receipt",
                          side_effect=RuntimeError("metadata audit failed")):
            with self.assertRaisesRegex(RuntimeError, "metadata audit failed"):
                self.candidate()
        self.assertFalse(Service.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_final_receipt_check_failure_rolls_back_everything(self):
        with patch.object(subject, "_verify_exact_audit_receipts",
                          side_effect=subject.ProtectedCandidateRefused("receipt mismatch")):
            with self.assertRaises(subject.ProtectedCandidateRefused):
                self.candidate()
        self.assertFalse(Service.objects.exists())
        self.assertFalse(Permission.objects.exists())
        self.assertFalse(RolePermission.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_removed_receipt_detected_on_repeat_without_new_writes(self):
        self.candidate()
        AccessAuditLog.objects.filter(action="test.role_permission.stage_inactive").first().delete()
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate()
        self.assertEqual(AccessAuditLog.objects.count(), 7)
        self.assertEqual(RolePermission.objects.count(), 3)

    def test_modified_receipt_detected_on_repeat(self):
        self.candidate()
        AccessAuditLog.objects.filter(action="test.catalogue.permission.create").update(
            reason="role_assignment")
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate()
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_foreign_actor_receipt_detected(self):
        self.candidate()
        other = Account(school_id="TEST-D4-OTHER", is_active=True, request_status="Approved")
        other.set_unusable_password()
        other.save()
        AccessAuditLog.objects.filter(action="test.catalogue.service.create").update(
            actor_account=other)
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate()

    def test_existing_metadata_with_no_grants_can_be_completed(self):
        metadata.exercise_metadata_transaction_in_disposable_test(test_audit_actor=self.actor)
        result = self.candidate()
        self.assertEqual((result["created_services"], result["created_permissions"],
                          result["inactive_bindings_created"]), (0, 0, 3))
        self.assertEqual(AccessAuditLog.objects.count(), 8)

    def test_partial_preexisting_grants_are_refused(self):
        metadata.exercise_metadata_transaction_in_disposable_test(test_audit_actor=self.actor)
        RolePermission.objects.create(role=self.admin,
            permission=Permission.objects.get(permission_code="accounts.registration_requests.read"),
            is_active=False, granted_by=self.actor)
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate()
        self.assertEqual(RolePermission.objects.count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 5)

    def test_unaudited_complete_preexisting_grants_are_refused(self):
        metadata.exercise_metadata_transaction_in_disposable_test(test_audit_actor=self.actor)
        for permission in Permission.objects.all():
            RolePermission.objects.create(role=self.admin, permission=permission,
                                          is_active=False, granted_by=self.actor)
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate()
        self.assertEqual(AccessAuditLog.objects.count(), 5)

    def test_live_database_name_refused(self):
        with override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace"):
            with self.assertRaises(subject.ProtectedCandidateRefused):
                self.candidate()
        self.assertFalse(Service.objects.exists())

    def test_registration_review_gates_must_remain_off(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True):
            with self.assertRaises(subject.ProtectedCandidateRefused):
                self.candidate()
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True):
            with self.assertRaises(subject.ProtectedCandidateRefused):
                self.candidate()
        self.assertFalse(Service.objects.exists())

    def test_frozen_draft_mutation_refused(self):
        with patch.object(metadata, "_metadata_from_frozen_draft",
                          side_effect=RuntimeError("unapproved profile")):
            with self.assertRaises(subject.ProtectedCandidateRefused):
                self.candidate()
        self.assertFalse(Service.objects.exists())

    def test_active_service_refused_and_unchanged(self):
        self.candidate()
        Service.objects.filter(service_code="accounts").update(is_active=True)
        with self.assertRaises((subject.ProtectedCandidateRefused, inactive.TestInactiveGrantRefused)):
            self.candidate()
        self.assertTrue(Service.objects.get(service_code="accounts").is_active)

    def test_unpersisted_actor_refused(self):
        with self.assertRaises(subject.ProtectedCandidateRefused):
            self.candidate(actor=Account(school_id="UNSAVED-D4"))
        self.assertFalse(Service.objects.exists())

    def test_no_account_role_assignments_or_effective_access(self):
        AccountRole.objects.create(account=self.actor, role=self.admin)
        self.candidate()
        self.assertEqual(AccountRole.objects.count(), 1)
        self.assertFalse(get_effective_permissions(self.actor))
        self.assertFalse(Service.objects.filter(is_active=True).exists())
