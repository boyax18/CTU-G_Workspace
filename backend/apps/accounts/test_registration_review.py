"""Isolated MySQL tests for the disabled-by-default registration review service.

Run ONLY with --settings=config.test_settings; the runner creates and removes a
fresh random test database and never uses the development database.
"""

from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog,
    AccountPermission,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)
from apps.access_control.services import has_permission

from .models import Account
from .registration_review import (
    RegistrationReviewDenied,
    RegistrationReviewUnavailable,
    approve_registration,
    reject_registration,
)

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith(
    "test_ctug_registration_"
):
    raise ImproperlyConfigured(
        "Registration-review integration tests require --settings=config.test_settings."
    )


@override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True)
class RegistrationReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected test database.")

        cls.accounts_service = Service.objects.create(
            service_code="accounts", service_name="Accounts"
        )
        cls.governance_service = Service.objects.create(
            service_code="access_control", service_name="Access Control"
        )
        cls.approve_permission = Permission.objects.create(
            service=cls.accounts_service,
            permission_code="accounts.registration_requests.approve",
            permission_name="Approve registration requests",
            module_name="registration_requests",
            action_name="approve",
        )
        cls.reject_permission = Permission.objects.create(
            service=cls.accounts_service,
            permission_code="accounts.registration_requests.reject",
            permission_name="Reject registration requests",
            module_name="registration_requests",
            action_name="reject",
        )
        cls.student_role = Role.objects.create(role_name="Student")
        cls.instructor_role = Role.objects.create(role_name="Instructor")
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.reviewer = Account.objects.create(
            school_id="REVIEWER-001",
            request_status="Approved",
            is_active=True,
        )
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin_role)
        RolePermission.objects.create(
            role=cls.admin_role, permission=cls.approve_permission
        )
        RolePermission.objects.create(
            role=cls.admin_role, permission=cls.reject_permission
        )

    def setUp(self):
        self.target = Account.objects.create_user(
            school_id="STUDENT-001",
            password="Strong!Curriculum9682",
            requested_role=self.student_role,
        )

    def test_approval_assigns_only_base_role_and_audits(self):
        decided = approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(decided, self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Approved")
        self.assertTrue(self.target.is_active)
        self.assertEqual(self.target.reviewed_by_id, self.reviewer.pk)
        self.assertIsNotNone(self.target.reviewed_at)
        self.assertEqual(
            list(AccountRole.objects.filter(account=self.target).values_list(
                "role__role_name", flat=True
            )),
            ["Student"],
        )
        self.assertEqual(AccountPermission.objects.filter(account=self.target).count(), 0)
        event = AccessAuditLog.objects.get()
        self.assertEqual(event.action, "account.registration.approve")
        self.assertEqual(event.actor_account_id, self.reviewer.pk)
        self.assertEqual(event.target_account_id, self.target.pk)
        self.assertEqual(event.new_value["role_id"], self.student_role.pk)
        self.assertNotIn("school_id", event.old_value)
        self.assertNotIn("password", event.new_value)

    def test_role_defaults_remain_dynamic_not_copied_to_account(self):
        catalog_service = Service.objects.create(
            service_code="academic", service_name="Academic"
        )
        catalog_permission = Permission.objects.create(
            service=catalog_service,
            permission_code="academic.catalogue.read",
            permission_name="Read course catalogue",
            module_name="catalogue",
            action_name="read",
        )
        RolePermission.objects.create(
            role=self.student_role, permission=catalog_permission
        )
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertTrue(has_permission(self.target, "academic.catalogue.read"))
        self.assertFalse(has_permission(self.target, "accounts.registration_requests.approve"))
        self.assertFalse(AccountPermission.objects.filter(account=self.target).exists())

    def test_instructor_request_assigns_instructor_not_admin(self):
        self.target.requested_role = self.instructor_role
        self.target.save(update_fields=["requested_role"])
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(
            AccountRole.objects.get(account=self.target).role_id,
            self.instructor_role.pk,
        )

    def test_rejection_keeps_account_inactive_without_assignment(self):
        reject_registration(
            actor=self.reviewer,
            target_id=self.target.pk,
            rejection_code="incomplete_submission",
        )
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Rejected")
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.target.rejection_reason, "incomplete_submission")
        self.assertEqual(self.target.reviewed_by_id, self.reviewer.pk)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.reject")

    def test_default_feature_gate_blocks_any_review(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            with self.assertRaises(RegistrationReviewUnavailable):
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_review_permission_deny_overrides_admin_grant(self):
        AccountPermission.objects.create(
            account=self.reviewer, permission=self.approve_permission, effect="Deny"
        )
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_reviewer_must_be_admin_not_merely_permission_holder(self):
        AccountRole.objects.filter(account=self.reviewer).delete()
        AccountRole.objects.create(account=self.reviewer, role=self.instructor_role)
        AccountPermission.objects.create(
            account=self.reviewer, permission=self.approve_permission, effect="Grant"
        )
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_framework_superuser_cannot_review_workspace_registrations(self):
        self.reviewer.is_staff = True
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=["is_staff", "is_superuser"])
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_missing_or_inactive_approval_permission_blocks(self):
        RolePermission.objects.filter(
            role=self.admin_role, permission=self.approve_permission
        ).update(is_active=False)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_inactive_governance_service_blocks(self):
        Service.objects.filter(pk=self.governance_service.pk).update(is_active=False)
        with self.assertRaises(RegistrationReviewUnavailable):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_existing_assigned_role_blocks_reapproval(self):
        AccountRole.objects.create(account=self.target, role=self.student_role)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_double_approval_cannot_reassign_or_reaudit(self):
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)

    def test_inactive_requested_role_is_not_assigned(self):
        Role.objects.filter(pk=self.student_role.pk).update(is_active=False)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_requested_admin_role_is_never_approved(self):
        self.target.requested_role = self.admin_role
        self.target.save(update_fields=["requested_role"])
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_target_with_framework_flags_is_never_approved(self):
        self.target.is_staff = True
        self.target.save(update_fields=["is_staff"])
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)

    def test_bad_rejection_code_is_rejected_before_writes(self):
        with self.assertRaises(RegistrationReviewDenied):
            reject_registration(
                actor=self.reviewer, target_id=self.target.pk,
                rejection_code="Student said SECRET 123",
            )
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_audit_failure_rolls_back_review_and_role_assignment(self):
        with patch(
            "apps.accounts.registration_review.record_access_audit",
            side_effect=RuntimeError("audit store unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertIsNone(self.target.reviewed_by_id)
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
