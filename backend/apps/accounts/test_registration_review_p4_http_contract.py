"""AR-6C7E.2: Django HTTP contract for the disabled React Registration Review panel.

Only config.test_settings and its disposable MySQL schema may run this suite.
Mounts the unexposed URLconf inside the isolated test process; DOES NOT
activate services, role bindings, URLs, or live account decisions.
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


if (
    settings.SETTINGS_MODULE != "config.test_settings"
    or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")
    or settings.DATABASES["default"]["NAME"] == "ctug_workspace"
):
    raise ImproperlyConfigured("P4 contract tests require the disposable MySQL test settings.")


class RegistrationReviewP4LiveRoutingLockTests(SimpleTestCase):
    @override_settings(
        WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
        WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    )
    def test_production_urlconf_remains_unmounted_even_with_test_flags(self):
        for path in (
            "/api/v1/registration-requests/",
            "/api/v1/registration-requests/4/approve/",
            "/api/v1/registration-requests/4/reject/",
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
class RegistrationReviewP4HTTPContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        accounts_service = Service.objects.create(
            service_code="accounts", service_name="Accounts", is_active=True,
        )
        Service.objects.create(
            service_code="access_control", service_name="Access Control", is_active=True,
        )
        cls.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        cls.student_role = Role.objects.create(role_name="Student", is_active=True)
        cls.instructor_role = Role.objects.create(role_name="Instructor", is_active=True)
        cls.admin = Account.objects.create_user(
            school_id="P4-CONTRACT-ADMIN", password="ValidTestOnly!4021",
        )
        cls.admin.request_status = "Approved"
        cls.admin.is_active = True
        cls.admin.save(update_fields=["request_status", "is_active"])
        AccountRole.objects.create(account=cls.admin, role=cls.admin_role)
        for action in ("read", "approve", "reject"):
            perm = Permission.objects.create(
                service=accounts_service,
                permission_code=f"accounts.registration_requests.{action}",
                permission_name=f"Registration requests {action}",
                module_name="registration_requests", action_name=action,
            )
            RolePermission.objects.create(role=cls.admin_role, permission=perm, is_active=True)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin)
        self.csrf = "a" * 32
        self.client.cookies[settings.CSRF_COOKIE_NAME] = self.csrf
        self.pending = Account.objects.create_user(
            school_id="P4-CONTRACT-PENDING", password="ValidTestOnly!4021",
            requested_role=self.student_role,
        )

    def post(self, action, body, *, csrf=True, origin=None):
        headers = {}
        if csrf:
            headers["HTTP_X_CSRFTOKEN"] = self.csrf
        if origin:
            headers["HTTP_ORIGIN"] = origin
        return self.client.post(
            f"/{self.pending.pk}/{action}/",
            data=json.dumps(body), content_type="application/json", **headers,
        )

    def assert_not_decided(self):
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Pending")
        self.assertFalse(self.pending.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.pending).exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_pending_list_exact_envelope_matches_frontend_parser(self):
        response = self.client.get("/?page=1&status=Pending")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        payload = response.json()
        self.assertEqual(set(payload), {"results", "page", "page_size"})
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 20)
        self.assertEqual(len(payload["results"]), 1)
        item = payload["results"][0]
        self.assertEqual(set(item), {"account_id", "school_id", "requested_role", "created_at"})
        self.assertEqual(item["account_id"], self.pending.pk)
        self.assertEqual(item["school_id"], "P4-CONTRACT-PENDING")
        self.assertEqual(item["requested_role"], "Student")
        self.assertIn("T", item["created_at"])
        self.assertNotIn("email", item)
        self.assertNotIn("password_hash", item)

    def test_pending_list_page_two_and_empty_page_are_bounded(self):
        for number in range(20):
            Account.objects.create_user(
                school_id=f"P4-CONTRACT-{number:02d}",
                password="ValidTestOnly!4021", requested_role=self.instructor_role,
            )
        first = self.client.get("/?page=1&status=Pending").json()
        second = self.client.get("/?page=2&status=Pending").json()
        third = self.client.get("/?page=3&status=Pending").json()
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(len(second["results"]), 1)
        self.assertEqual(second["page_size"], 20)
        self.assertEqual(third, {"results": [], "page": 3, "page_size": 20})
        self.assertEqual(len({row["account_id"] for row in first["results"] + second["results"]}), 21)

    def test_pending_list_rejects_unsupported_filters_and_pages(self):
        for query in ("?status=Approved", "?page=0", "?page=10001", "?page=abc", "?page=1.5", "?unknown=1"):
            with self.subTest(query=query):
                response = self.client.get("/" + query)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(set(response.json()), {"error"})
        self.assert_not_decided()

    def test_list_excludes_previously_assigned_pending_accounts(self):
        other = Account.objects.create_user(
            school_id="P4-CONTRACT-ASSIGNED", password="ValidTestOnly!4021",
            requested_role=self.student_role,
        )
        AccountRole.objects.create(account=other, role=self.student_role)
        self.assertEqual(
            [item["account_id"] for item in self.client.get("/").json()["results"]],
            [self.pending.pk],
        )

    def test_approve_empty_json_returns_exact_decision_and_audit(self):
        response = self.post("approve", {})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"account_id": self.pending.pk, "status": "Approved"})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Approved")
        self.assertTrue(self.pending.is_active)
        self.assertEqual(
            list(AccountRole.objects.filter(account=self.pending).values_list("role__role_name", flat=True)),
            ["Student"],
        )
        audit = AccessAuditLog.objects.get()
        self.assertEqual(audit.action, "account.registration.approve")
        self.assertEqual(audit.actor_account_id, self.admin.pk)
        self.assertEqual(audit.target_account_id, self.pending.pk)

    def test_approve_rejects_extra_fields_without_writing(self):
        response = self.post("approve", {"role": "Admin"})
        self.assertEqual(response.status_code, 400, response.content)
        self.assert_not_decided()

    def test_reject_one_of_four_codes_returns_exact_decision_without_role(self):
        response = self.post("reject", {"rejection_code": "identity_mismatch"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"account_id": self.pending.pk, "status": "Rejected"})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.request_status, "Rejected")
        self.assertFalse(self.pending.is_active)
        self.assertFalse(AccountRole.objects.filter(account=self.pending).exists())
        audit = AccessAuditLog.objects.get()
        self.assertEqual(audit.action, "account.registration.reject")
        self.assertEqual(audit.target_account_id, self.pending.pk)

    def test_reject_requires_exact_one_valid_code(self):
        for value in ({}, {"rejection_code": "custom"}, {"rejection_code": "duplicate_request", "admin": True}):
            with self.subTest(value=value):
                response = self.post("reject", value)
                self.assertEqual(response.status_code, 400, response.content)
        self.assert_not_decided()

    def test_no_csrf_and_bad_origin_never_mutate_account(self):
        self.assertEqual(self.post("approve", {}, csrf=False).status_code, 403)
        self.assertEqual(self.post("approve", {}, origin="https://invalid.example").status_code, 403)
        self.assert_not_decided()

    def test_deactivated_review_gate_refuses_both_read_and_write(self):
        with override_settings(WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.post("approve", {}).status_code, 503)
        self.assert_not_decided()

    def test_deny_override_blocks_approval_even_with_active_role_permission(self):
        permission = Permission.objects.get(permission_code="accounts.registration_requests.approve")
        AccountPermission.objects.create(
            account=self.admin, permission=permission, effect="Deny", is_active=True,
        )
        self.assertEqual(self.post("approve", {}).status_code, 403)
        self.assert_not_decided()
