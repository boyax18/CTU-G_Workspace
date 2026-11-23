"""Normal WF-02 read surface: synthetic fixtures in config.test_settings only."""
import os
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import Resolver404, include, path, resolve
from django.utils import timezone
from types import ModuleType

from apps.access_control.models import AccountPermission, Permission, RolePermission
from .active_role_context import SESSION_ROLE_KEY
from .models import Account
from .rejection_test_support import fresh_test_key
from .test_wf0205_account_status import World

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use config.test_settings and a disposable MySQL database.")

ROOT = "/api/v1/admin/school-accounts/"
REVIEWS = "/api/v1/admin/registration-requests/"
MIDDLEWARE = [*settings.MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware"]


@override_settings(
    ROOT_URLCONF="config.urls", WORKSPACE_ACCOUNT_DIRECTORY_ENABLED=True,
    WORKSPACE_ACCOUNT_STATUS_ENABLED=False, WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=False, WORKSPACE_REGISTRATION_APPROVAL_ENABLED=False,
    WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True, MIDDLEWARE=MIDDLEWARE,
)
class DashboardIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.reviewer = cls.w.reviewer
        cls.technical = cls.w.account("WF02-TECH", "Instructor", "Admin", "Technical Super Admin")
        cls.student = cls.w.account("WF02-STUDENT", "Student")
        cls.instructor = cls.w.account("WF02-INSTRUCTOR", "Instructor")
        cls.pending = cls.w.account("WF02-PENDING", status="Pending", active=False)
        Account.objects.filter(pk=cls.pending.pk).update(
            email="synthetic@example.edu", email_verified_address="synthetic@example.edu",
            email_verified_at=timezone.now(),
        )
        cls.review_permissions = {}
        for action in ("read", "approve", "reject"):
            perm = Permission.objects.create(service=cls.w.accounts_service,
                permission_code=f"accounts.registration_requests.{action}", permission_name=action,
                module_name="registration_requests", action_name=action)
            RolePermission.objects.create(role=cls.w.roles["Admin"], permission=perm)
            cls.review_permissions[action] = perm

    def setUp(self):
        cache.clear()

    def client_for(self, account, role):
        client = Client(enforce_csrf_checks=True)
        client.force_login(account)
        session = client.session
        session[SESSION_ROLE_KEY] = self.w.roles[role].pk
        session.save()
        return client

    def test_school_and_technical_contexts_read_real_synthetic_records(self):
        for actor, role in ((self.reviewer, "Admin"), (self.technical, "Technical Super Admin")):
            with self.subTest(role=role):
                client = self.client_for(actor, role)
                response = client.get(REVIEWS)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([r["account_id"] for r in response.json()["results"]], [self.pending.pk])
                detail = client.get(f"{REVIEWS}{self.pending.pk}/")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail["X-Workspace-Available-Actions"], "")
                directory = client.get(ROOT)
                self.assertEqual(directory.status_code, 200)
                ids = {r["account_id"] for r in directory.json()["results"]}
                self.assertEqual(ids, {self.student.pk, self.instructor.pk})
                for suffix in ("", "history/"):
                    result = client.get(f"{ROOT}{self.student.pk}/{suffix}")
                    self.assertEqual(result.status_code, 200)
                    self.assertIn("no-store", result["Cache-Control"])
                self.assertEqual(client.get(f"{ROOT}{self.student.pk}/")["X-Workspace-Available-Actions"], "")

    def test_role_switch_and_unauthorized_identities_are_denied(self):
        client = self.client_for(self.technical, "Technical Super Admin")
        csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/role-context/", {"role_id": self.w.roles["Instructor"].pk},
                               content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        for url in (ROOT, REVIEWS, f"{ROOT}{self.student.pk}/history/"):
            self.assertEqual(client.get(url).status_code, 403)
        for actor, role in ((self.student, "Student"), (self.instructor, "Instructor")):
            for url in (ROOT, REVIEWS):
                self.assertEqual(self.client_for(actor, role).get(url).status_code, 403)
        self.assertEqual(Client().get(ROOT).status_code, 401)
        self.assertEqual(Client().get(REVIEWS).status_code, 401)

    def test_deny_and_revoked_inherited_assignment_are_authoritative(self):
        from apps.access_control.models import AccountRole
        client = self.client_for(self.technical, "Technical Super Admin")
        AccountPermission.objects.create(account=self.technical, permission=self.w.perms["read"], effect="Deny")
        self.assertEqual(client.get(ROOT).status_code, 403)
        AccountRole.objects.filter(account=self.technical, role=self.w.roles["Admin"]).delete()
        self.assertEqual(client.get(REVIEWS).status_code, 403)

    def test_read_gate_never_mounts_mutations_or_opens_governance(self):
        for url in (f"{ROOT}1/suspend/", f"{ROOT}1/activate/", f"{REVIEWS}1/approve/",
                    f"{REVIEWS}1/reject/", "/api/v1/admin/role-assignments/"):
            with self.subTest(url=url), self.assertRaises(Resolver404):
                resolve(url, urlconf="config.urls")
        client = self.client_for(self.reviewer, "Admin")
        with override_settings(WORKSPACE_ACCOUNT_DIRECTORY_ENABLED=False):
            for url in (ROOT, f"{ROOT}{self.student.pk}/", f"{ROOT}{self.student.pk}/history/"):
                self.assertEqual(client.get(url).status_code, 503)

    def test_server_hints_require_route_gate_permission_and_executor_boundary(self):
        from .registration_review_api import PendingRegistrationDetailView
        conf = ModuleType("wf02_available_actions")
        conf.urlpatterns = [
            path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls")),
            path("api/v1/admin/registration-requests/<int:account_id>/", PendingRegistrationDetailView.as_view()),
            path("api/v1/admin/registration-requests/", include("apps.accounts.registration_review_urls")),
        ]
        client = self.client_for(self.technical, "Technical Super Admin")
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()}), override_settings(
            ROOT_URLCONF=conf, WORKSPACE_ACCOUNT_STATUS_ENABLED=True,
            WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True, WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
        ):
            detail = client.get(f"{ROOT}{self.student.pk}/")
            self.assertEqual(detail["X-Workspace-Available-Actions"], "suspend,activate")
            self.assertEqual(client.get(f"{REVIEWS}{self.pending.pk}/")["X-Workspace-Available-Actions"], "")
            with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True, WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True):
                self.assertEqual(client.get(f"{REVIEWS}{self.pending.pk}/")["X-Workspace-Available-Actions"], "approve,reject")
            AccountPermission.objects.create(account=self.technical, permission=self.w.perms["suspend"], effect="Deny")
            self.assertEqual(client.get(f"{ROOT}{self.student.pk}/")["X-Workspace-Available-Actions"], "activate")
            with patch("apps.access_control.executor.client.enabled", return_value=True), override_settings(
                WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED=True,
            ):
                self.assertEqual(client.get(f"{ROOT}{self.student.pk}/")["X-Workspace-Available-Actions"], "")

    def test_protected_targets_and_search_are_scoped(self):
        client = self.client_for(self.reviewer, "Admin")
        self.assertEqual(client.get(f"{ROOT}{self.technical.pk}/").status_code, 404)
        self.assertEqual(client.get(f"{ROOT}{self.pending.pk}/history/").status_code, 404)
        response = client.get(ROOT, {"q": "WF02-STUDENT", "status": "active"})
        self.assertEqual([r["account_id"] for r in response.json()["results"]], [self.student.pk])
        self.assertEqual(client.get(ROOT, {"role": "Admin"}).status_code, 400)
