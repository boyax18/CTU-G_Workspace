"""AR-6C1 isolated MySQL HTTP tests for proposed, UNWIRED API views.

Run: python manage.py test apps.accounts.test_registration_review_api \\
     --settings=config.test_settings --noinput --verbosity 2
These tests temporarily mount an isolated URLconf and enable flags ONLY in
Django test settings. They do not register routes in config.urls.
"""

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)

from .models import Account


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use --settings=config.test_settings for AR-6C1 tests.")


@override_settings(
    ROOT_URLCONF="apps.accounts.registration_review_urls",
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
)
class RegistrationReviewAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(
            service_code="accounts", service_name="Accounts",
        )
        cls.access_service = Service.objects.create(
            service_code="access_control", service_name="Access Control",
        )
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.admin = Role.objects.create(role_name="Admin")
        cls.reviewer = Account.objects.create_user(
            school_id="REVIEW-ADMIN-001", password="Research!Brick7294",
        )
        cls.reviewer.is_active = True
        cls.reviewer.request_status = "Approved"
        cls.reviewer.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin)
        cls.permissions = {}
        for action in ("read", "approve", "reject"):
            code = f"accounts.registration_requests.{action}"
            perm = Permission.objects.create(
                service=cls.accounts_service, permission_code=code,
                permission_name=f"Registration requests {action}",
                module_name="registration_requests", action_name=action,
            )
            RolePermission.objects.create(role=cls.admin, permission=perm)
            cls.permissions[action] = perm

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.reviewer)
        self.csrf = "a" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.target = Account.objects.create_user(
            school_id="PENDING-STUDENT-001", password="Copper!River7799",
            requested_role=self.student,
        )

    def post(self, path, body, with_csrf=True):
        import json
        return self.client.post(
            path, data=json.dumps(body), content_type="application/json",
            **({"HTTP_X_CSRFTOKEN": self.csrf} if with_csrf else {}),
        )

    def test_feature_off_blocks_get_and_post(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 503)
            self.assertEqual(self.post(f"/{self.target.pk}/reject/", {"rejection_code": "duplicate_request"}).status_code, 503)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_service_feature_off_also_blocks(self):
        with override_settings(WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 503)


    def test_session_required_even_if_csrf_present(self):
        self.client.logout()

        # Restore CSRF cookie after logout clears client cookies.
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf

        self.assertEqual(self.client.get("/").status_code, 401)
        self.assertEqual(
            self.post(f"/{self.target.pk}/approve/", {}).status_code,
            401,
        )

    def test_anonymous_unsafe_call_requires_csrf(self):
        self.client.logout()
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}, with_csrf=False).status_code, 403)

    def test_logged_in_post_without_csrf_denied(self):
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}, with_csrf=False).status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")

    def test_invalid_origin_denied(self):
        import json
        result = self.client.post(
            f"/{self.target.pk}/approve/", data=json.dumps({}),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf,
            HTTP_ORIGIN="https://malicious.example",
        )
        self.assertEqual(result.status_code, 403)

    def test_no_admin_assignment_denied(self):
        AccountRole.objects.filter(account=self.reviewer).delete()
        AccountRole.objects.create(account=self.reviewer, role=self.instructor)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 403)

    def test_admin_name_without_stored_grant_denied(self):
        RolePermission.objects.filter(role=self.admin).update(is_active=False)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 403)

    def test_per_account_deny_overrides_admin_grant(self):
        AccountPermission.objects.create(
            account=self.reviewer, permission=self.permissions["approve"], effect="Deny",
        )
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 403)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_inactive_service_blocks(self):
        self.access_service.is_active = False
        self.access_service.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/").status_code, 503)
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 503)

    def test_minimal_pending_list_and_pagination_validation(self):
        other = Account.objects.create_user(
            school_id="PENDING-INSTRUCTOR-001", password="Copper!River7799",
            requested_role=self.instructor,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            {row["account_id"] for row in response.json()["results"]},
            {self.target.pk, other.pk},
        )
        self.assertEqual(
            set(response.json()["results"][0]),
            {"account_id", "school_id", "requested_role", "created_at"},
        )
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get("/?page=0").status_code, 400)
        self.assertEqual(self.client.get("/?status=Approved").status_code, 400)
        self.assertEqual(self.client.get("/?random=1").status_code, 400)

    def test_approve_assigns_one_role_and_audits(self):
        result = self.post(f"/{self.target.pk}/approve/", {})
        self.assertEqual(result.status_code, 200, result.content)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertEqual(self.target.request_status, "Approved")
        self.assertEqual(AccountRole.objects.get(account=self.target).role_id, self.student.pk)
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.approve")
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 404)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_reject_audits_and_does_not_assign_role(self):
        result = self.post(f"/{self.target.pk}/reject/", {"rejection_code": "identity_mismatch"})
        self.assertEqual(result.status_code, 200, result.content)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.target.request_status, "Rejected")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.reject")

    def test_reject_unlisted_reason_and_extra_keys(self):
        self.assertEqual(self.post(f"/{self.target.pk}/reject/", {"rejection_code": "personal details"}).status_code, 400)
        self.assertEqual(self.post(f"/{self.target.pk}/reject/", {"rejection_code": "identity_mismatch", "role": "Admin"}).status_code, 400)
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {"is_staff": True}).status_code, 400)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_reviewed_target_and_self_review_denied(self):
        self.assertEqual(self.post(f"/{self.reviewer.pk}/approve/", {}).status_code, 404)
        AccountRole.objects.create(account=self.target, role=self.student)
        self.assertEqual(self.post(f"/{self.target.pk}/approve/", {}).status_code, 404)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_django_superuser_session_not_workspace_authority(self):
        superuser = Account.objects.create(
            school_id="FRAMEWORK-ADMIN-001", is_active=True,
            request_status="Approved", is_staff=True, is_superuser=True,
        )
        self.client.force_login(superuser)
        self.assertEqual(self.client.get("/").status_code, 401)

    def test_audit_writer_failure_rolls_back(self):
        with patch("apps.accounts.registration_review.record_access_audit", side_effect=RuntimeError("audit unavailable")):
            response = self.post(f"/{self.target.pk}/approve/", {})
        self.assertEqual(response.status_code, 503)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_revoked_permission_detected_after_session_created(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        RolePermission.objects.filter(permission=self.permissions["read"]).update(is_active=False)
        self.assertEqual(self.client.get("/").status_code, 403)
