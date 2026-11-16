"""P3C isolated authenticated HTTP boundary tests; no live URL wiring.

Only config.test_settings with an unpredictable disposable MySQL DB is allowed.
These tests mount the unexposed candidate URLconf inside Django's test process.
"""

import json

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import Resolver404, resolve

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)

from .models import Account


if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("P3C API tests require --settings=config.test_settings.")


class RegistrationReviewDefaultRoutingTests(SimpleTestCase):
    @override_settings(
        WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
        WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    )
    def test_flags_alone_cannot_mount_live_review_routes(self):
        for path in (
            "/api/v1/registration-requests/",
            "/api/v1/registration-requests/10/approve/",
            "/api/v1/registration-requests/10/reject/",
        ):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path, urlconf="config.urls")


@override_settings(
    ROOT_URLCONF="apps.accounts.registration_review_urls",
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False,
)
class RegistrationReviewP3CAuthenticatedBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(
            service_code="accounts", service_name="Accounts", is_active=True,
        )
        cls.access_service = Service.objects.create(
            service_code="access_control", service_name="Access Control", is_active=True,
        )
        cls.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        cls.student_role = Role.objects.create(role_name="Student", is_active=True)
        cls.instructor_role = Role.objects.create(role_name="Instructor", is_active=True)
        cls.admin = Account.objects.create_user(
            school_id="P3C-API-ADMIN", password="ValidTestOnly!4021",
        )
        cls.admin.request_status = "Approved"
        cls.admin.is_active = True
        cls.admin.save(update_fields=["request_status", "is_active"])
        AccountRole.objects.create(account=cls.admin, role=cls.admin_role)
        cls.permissions = {}
        for action in ("read", "approve", "reject"):
            permission = Permission.objects.create(
                service=cls.accounts_service,
                permission_code=f"accounts.registration_requests.{action}",
                permission_name=f"Registration requests {action}",
                module_name="registration_requests", action_name=action,
            )
            RolePermission.objects.create(
                role=cls.admin_role, permission=permission, is_active=True,
            )
            cls.permissions[action] = permission

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin)
        self.csrf = "a" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.pending = Account.objects.create_user(
            school_id="P3C-API-PENDING", password="ValidTestOnly!4021",
            requested_role=self.student_role,
        )

    def post(self, action, payload, *, csrf=True, origin=None):
        extra = {}
        if csrf:
            extra["HTTP_X_CSRFTOKEN"] = self.csrf
        if origin:
            extra["HTTP_ORIGIN"] = origin
        return self.client.post(
            f"/{self.pending.pk}/{action}/",
            data=json.dumps(payload), content_type="application/json", **extra,
        )

    def assert_still_pending(self):
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Pending")
        self.assertFalse(self.pending.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.pending).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_api_flag_off_denies_all_review_actions(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post("approve", {}).status_code, 503)
            self.assertEqual(self.post("reject", {"rejection_code": "duplicate_request"}).status_code, 503)
        self.assert_still_pending()

    def test_approval_flag_off_denies_all_review_actions(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post("approve", {}).status_code, 503)
        self.assert_still_pending()

    def test_anonymous_user_has_no_review_authority(self):
        self.client.logout()
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.assertEqual(self.client.get("/").status_code, 401)
        self.assertEqual(self.post("approve", {}).status_code, 401)
        self.assert_still_pending()

    def test_student_with_direct_grant_is_not_admin(self):
        student = Account.objects.create_user(
            school_id="P3C-API-STUDENT", password="ValidTestOnly!4021",
        )
        student.request_status = "Approved"
        student.is_active = True
        student.save(update_fields=["request_status", "is_active"])
        AccountRole.objects.create(account=student, role=self.student_role)
        AccountPermission.objects.create(
            account=student, permission=self.permissions["approve"],
            effect="Grant", is_active=True,
        )
        self.client.force_login(student)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.post("approve", {}).status_code, 403)
        self.assert_still_pending()

    def test_instructor_without_admin_assignment_is_denied(self):
        instructor = Account.objects.create_user(
            school_id="P3C-API-INSTRUCTOR", password="ValidTestOnly!4021",
        )
        instructor.request_status = "Approved"
        instructor.is_active = True
        instructor.save(update_fields=["request_status", "is_active"])
        AccountRole.objects.create(account=instructor, role=self.instructor_role)
        self.client.force_login(instructor)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.post("reject", {"rejection_code": "duplicate_request"}).status_code, 403)
        self.assert_still_pending()

    def test_framework_superuser_with_admin_role_is_still_denied(self):
        privileged = Account.objects.create(
            school_id="P3C-API-SUPERUSER", request_status="Approved",
            is_active=True, is_staff=True, is_superuser=True,
        )
        AccountRole.objects.create(account=privileged, role=self.admin_role)
        self.client.force_login(privileged)
        self.assertEqual(self.client.get("/").status_code, 401)
        self.assert_still_pending()

    def test_requested_role_cannot_substitute_for_assignment(self):
        # Direct fixture bypasses the manager intentionally: the public
        # registration manager correctly refuses Admin role requests.
        applicant = Account(
            school_id="P3C-API-REQUESTED-ADMIN", requested_role=self.admin_role,
            request_status="Pending", is_active=False,
        )
        applicant.set_unusable_password()
        applicant.save()
        self.client.force_login(applicant)
        self.assertEqual(self.client.get("/").status_code, 401)
        self.assert_still_pending()

    def test_role_assignment_revoked_during_session(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        AccountRole.objects.filter(account=self.admin).delete()
        AccountRole.objects.create(account=self.admin, role=self.student_role)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.post("approve", {}).status_code, 403)
        self.assert_still_pending()

    def test_read_grant_revoked_during_session(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        RolePermission.objects.filter(permission=self.permissions["read"]).update(is_active=False)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assert_still_pending()

    def test_reject_permission_cannot_be_substituted_by_approve(self):
        RolePermission.objects.filter(permission=self.permissions["reject"]).update(is_active=False)
        self.assertEqual(self.post("reject", {"rejection_code": "duplicate_request"}).status_code, 403)
        self.assert_still_pending()

    def test_account_deny_takes_precedence_over_active_admin_grant(self):
        AccountPermission.objects.create(
            account=self.admin, permission=self.permissions["approve"],
            effect="Deny", is_active=True,
        )
        self.assertEqual(self.post("approve", {}).status_code, 403)
        self.assert_still_pending()

    def test_accounts_service_inactive_denies_review(self):
        Service.objects.filter(pk=self.accounts_service.pk).update(is_active=False)
        self.assertEqual(self.client.get("/").status_code, 503)
        self.assertEqual(self.post("approve", {}).status_code, 503)
        self.assert_still_pending()

    def test_governance_service_inactive_denies_review(self):
        Service.objects.filter(pk=self.access_service.pk).update(is_active=False)
        self.assertEqual(self.post("approve", {}).status_code, 503)
        self.assert_still_pending()

    def test_csrf_required_for_authenticated_approval(self):
        self.assertEqual(self.post("approve", {}, csrf=False).status_code, 403)
        self.assert_still_pending()

    def test_cross_origin_approval_denied(self):
        self.assertEqual(
            self.post("approve", {}, origin="https://untrusted.example").status_code,
            403,
        )
        self.assert_still_pending()

    def test_valid_admin_approval_is_atomic_and_audited_in_test_database(self):
        response = self.post("approve", {})
        self.assertEqual(response.status_code, 200, response.content)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Approved")
        self.assertTrue(self.pending.is_active)
        self.assertEqual(
            list(AccountRole.objects.filter(account=self.pending).values_list("role__role_name", flat=True)),
            ["Student"],
        )
        receipt = AccessAuditLog.objects.get()
        self.assertEqual(receipt.action, "account.registration.approve")
        self.assertEqual(receipt.actor_account_id, self.admin.pk)
        self.assertEqual(receipt.target_account_id, self.pending.pk)
        self.assertEqual(self.post("approve", {}).status_code, 404)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_valid_admin_rejection_is_audited_without_role_assignment(self):
        response = self.post("reject", {"rejection_code": "duplicate_request"})
        self.assertEqual(response.status_code, 200, response.content)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Rejected")
        self.assertFalse(self.pending.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.pending).exists())
        receipt = AccessAuditLog.objects.get()
        self.assertEqual(receipt.action, "account.registration.reject")
        self.assertEqual(receipt.target_account_id, self.pending.pk)
