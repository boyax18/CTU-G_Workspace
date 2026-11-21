"""WF-03 isolated HTTP contracts across the five staged governance APIs.

Run ONLY via --settings=config.test_settings. Real Django Client requests use
synthetic account/role/service rows in a disposable MySQL test database.
Test-only overrides mount isolated URLs and enable READ gates. Mutations remain
OFF, and no deployment/settings/database/provisioning files are changed.
"""
import json
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings

from apps.accounts.active_role_context import SESSION_ROLE_KEY
from apps.accounts.models import Account
from .models import (
    AccessAuditLog, AccountPermission, AccountPermissionRoleScope,
    AccountRole, Permission, Role, RolePermission, Service,
)

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-03 HTTP integration requires isolated config.test_settings.")
if settings.DATABASES["default"]["NAME"] != settings.REGISTRATION_TEST_DATABASE:
    raise ImproperlyConfigured("WF-03 HTTP integration refuses a non-isolated database.")

# These settings exist only inside the disposable Django TestCase process.
# Never copy this block to a runserver config or deployment environment.
READ_ONLY_TEST_CONFIG = dict(
    ROOT_URLCONF="config.review_local_urls",
    MIDDLEWARE=[*settings.MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware"],
    WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True,
    WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED=True,
    WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED=True,
    WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED=True,
    WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED=True,
)

ROOT = "/api/v1/admin/"


@override_settings(**READ_ONLY_TEST_CONFIG)
class WF03IsolatedHTTPIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # No framework superuser is created or granted any privilege.
        cls.accounts_service = Service.objects.create(service_code="accounts", service_name="Accounts")
        cls.governance_service = Service.objects.create(service_code="access_control", service_name="Access Control")
        cls.data_service = Service.objects.create(service_code="wf03_integration", service_name="Synthetic WF03 Data")
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.tech_role = Role.objects.create(role_name="Technical Super Admin")
        cls.student_role = Role.objects.create(role_name="Student")
        cls.instructor_role = Role.objects.create(role_name="Instructor")

        def account(code, *roles):
            entry = Account.objects.create_user(school_id=code, password="Synthetic-Only!5319")
            Account.objects.filter(pk=entry.pk).update(request_status="Approved", is_active=True)
            for role in roles:
                AccountRole.objects.create(account=entry, role=role)
            return Account.objects.get(pk=entry.pk)

        cls.actor = account("WF03-HTTP-TECH", cls.admin_role, cls.tech_role)
        cls.school_admin = account("WF03-HTTP-ADMIN", cls.admin_role)
        cls.student = account("WF03-HTTP-STUDENT", cls.student_role, cls.instructor_role)
        cls.unapproved = account("WF03-HTTP-PENDING", cls.student_role)
        Account.objects.filter(pk=cls.unapproved.pk).update(request_status="Pending", is_active=False)

        codes = (
            "access_control.role_permissions.manage",
            "access_control.account_permissions.manage",
            "access_control.effective_permissions.inspect",
            "access_control.audit.read",
        )
        for code in codes:
            permission = Permission.objects.create(
                service=cls.governance_service, permission_code=code,
                permission_name=code, module_name="test", action_name="read",
            )
            RolePermission.objects.create(role=cls.tech_role, permission=permission)

        cls.student_read = Permission.objects.create(
            service=cls.data_service, permission_code="wf03.student.read",
            permission_name="Student read", module_name="test", action_name="read",
        )
        cls.individual = Permission.objects.create(
            service=cls.data_service, permission_code="wf03.individual.read",
            permission_name="Individual read", module_name="test", action_name="read",
        )
        cls.instructor_read = Permission.objects.create(
            service=cls.data_service, permission_code="wf03.instructor.read",
            permission_name="Instructor read", module_name="test", action_name="read",
        )
        RolePermission.objects.create(role=cls.student_role, permission=cls.student_read)
        RolePermission.objects.create(role=cls.instructor_role, permission=cls.instructor_read)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.select_actor(self.actor, self.tech_role)

    def select_actor(self, actor, role):
        self.client.force_login(Account.objects.get(pk=actor.pk))
        session = self.client.session
        session[SESSION_ROLE_KEY] = role.pk
        session.save()
        self.client.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32

    def get(self, suffix):
        return self.client.get(ROOT + suffix, HTTP_ACCEPT="application/json")

    def post(self, suffix, body):
        return self.client.post(
            ROOT + suffix, data=json.dumps(body), content_type="application/json",
            HTTP_ACCEPT="application/json", HTTP_X_CSRFTOKEN="d" * 32,
        )

    def test_five_read_apis_return_frontend_contracts(self):
        url_checks = (
            ("role-permissions/roles/", "roles"),
            ("role-permissions/roles/%d/permissions/" % self.student_role.pk, "permissions"),
            ("account-grants/accounts/?q=WF03-HTTP-STUDENT", "accounts"),
            ("account-grants/accounts/%d/grants/" % self.student.pk, "permissions"),
            ("account-restrictions/accounts/?q=WF03-HTTP-STUDENT", "accounts"),
            ("account-restrictions/accounts/%d/overrides/" % self.student.pk, "permissions"),
            ("effective-access/accounts/?q=WF03-HTTP-STUDENT", "accounts"),
            ("effective-access/accounts/%d/roles/" % self.student.pk, "roles"),
            ("effective-access/accounts/%d/roles/%d/" % (self.student.pk, self.student_role.pk), "permissions"),
            ("access-audit/events/?page=1", "events"),
        )
        before = (AccountPermission.objects.count(), AccessAuditLog.objects.count())
        for url, key in url_checks:
            with self.subTest(url=url):
                reply = self.get(url)
                self.assertEqual(reply.status_code, 200, reply.content)
                self.assertIn(key, reply.json())
                self.assertEqual(reply.get("Cache-Control"), "no-store")
        self.assertEqual((AccountPermission.objects.count(), AccessAuditLog.objects.count()), before)

    def test_each_api_denies_without_technical_role_context(self):
        # Same account, but selected School Admin context: technical-only
        # permissions are not inherited in reverse.
        self.select_actor(self.actor, self.admin_role)
        for url in (
            "role-permissions/roles/", "account-grants/accounts/?q=WF03-HTTP-STUDENT",
            "account-restrictions/accounts/?q=WF03-HTTP-STUDENT",
            "effective-access/accounts/?q=WF03-HTTP-STUDENT",
            "access-audit/events/?page=1",
        ):
            with self.subTest(url=url):
                reply = self.get(url)
                self.assertEqual(reply.status_code, 403, reply.content)

    def test_school_admin_with_audit_code_still_cannot_read_audit(self):
        # Test-only deliberately invalid Admin permission placement. Even the
        # exact stored code cannot substitute for Technical Super Admin role.
        audit_code = Permission.objects.get(permission_code="access_control.audit.read")
        RolePermission.objects.create(role=self.admin_role, permission=audit_code)
        self.select_actor(self.school_admin, self.admin_role)
        reply = self.get("access-audit/events/?page=1")
        self.assertEqual(reply.status_code, 403, reply.content)

    def test_anonymous_and_pending_accounts_cannot_read_directory(self):
        self.client.logout()
        self.assertEqual(self.get("role-permissions/roles/").status_code, 401)
        self.select_actor(self.unapproved, self.student_role)
        self.assertEqual(self.get("role-permissions/roles/").status_code, 401)

    def test_unapproved_accounts_not_exposed_in_directory_results(self):
        for url in (
            "account-grants/accounts/?q=WF03-HTTP-PENDING",
            "account-restrictions/accounts/?q=WF03-HTTP-PENDING",
            "effective-access/accounts/?q=WF03-HTTP-PENDING",
        ):
            with self.subTest(url=url):
                reply = self.get(url)
                self.assertEqual(reply.status_code, 200, reply.content)
                self.assertEqual(reply.json()["accounts"], [])

    def test_inspector_evaluates_selected_role_grant_deny_and_service_state(self):
        def inspection(role):
            reply = self.get("effective-access/accounts/%d/roles/%d/" % (self.student.pk, role.pk))
            self.assertEqual(reply.status_code, 200, reply.content)
            rows = {item["permission_code"]: item for item in reply.json()["permissions"]}
            self.assertEqual(reply.json()["effective_count"], sum(item["effective"] for item in rows.values()))
            return rows

        initial = inspection(self.student_role)
        self.assertTrue(initial["wf03.student.read"]["effective"])
        self.assertFalse(initial["wf03.instructor.read"]["effective"])
        self.assertFalse(initial["wf03.individual.read"]["effective"])

        grant = AccountPermission.objects.create(
            account=self.student, permission=self.individual, effect="Grant",
        )
        AccountPermissionRoleScope.objects.create(account_permission=grant, role=self.student_role)
        self.assertTrue(inspection(self.student_role)["wf03.individual.read"]["effective"])
        self.assertFalse(inspection(self.instructor_role)["wf03.individual.read"]["effective"])

        AccountPermission.objects.create(account=self.student, permission=self.student_read, effect="Deny")
        denied = inspection(self.student_role)["wf03.student.read"]
        self.assertTrue(denied["explicit_deny"])
        self.assertFalse(denied["effective"])

        Service.objects.filter(pk=self.data_service.pk).update(is_active=False)
        disabled = inspection(self.student_role)["wf03.individual.read"]
        self.assertFalse(disabled["service_active"])
        self.assertFalse(disabled["effective"])

    def test_audit_list_detail_and_redaction_match_readonly_contract(self):
        record = AccessAuditLog.objects.create(
            actor_account=self.actor, target_account=self.student, role=self.student_role,
            action="account.role.assign", old_value={"password": "never-show-this"},
        )
        listing = self.get("access-audit/events/?page=1&actor=WF03-HTTP-TECH")
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertEqual(listing.json()["page_size"], 20)
        self.assertEqual(listing.json()["events"][0]["audit_id"], record.pk)
        detail = self.get("access-audit/events/%d/" % record.pk)
        self.assertEqual(detail.status_code, 200, detail.content)
        self.assertTrue(detail.json()["old_redacted"])
        self.assertIsNone(detail.json()["old_value"])
        self.assertNotIn("never-show-this", detail.content.decode("utf-8"))

    def test_mutations_remain_disabled_even_when_directories_are_readable(self):
        before = (
            RolePermission.objects.count(), AccountPermission.objects.count(),
            AccessAuditLog.objects.count(),
        )
        attempted_writes = (
            ("role-permissions/roles/%d/permissions/%d/revoke/" % (self.student_role.pk, self.student_read.pk),
             {"expected_active": True}),
            ("account-grants/accounts/%d/grants/%d/" % (self.student.pk, self.individual.pk),
             {"role_id": self.student_role.pk, "expected_active": False}),
            ("account-restrictions/accounts/%d/overrides/%d/" % (self.student.pk, self.student_read.pk),
             {"action": "deny", "expected_effect": None, "expected_scope_role_id": None}),
        )
        for url, body in attempted_writes:
            with self.subTest(url=url):
                reply = self.post(url, body)
                self.assertEqual(reply.status_code, 503, reply.content)
        self.assertEqual((RolePermission.objects.count(), AccountPermission.objects.count(),
                          AccessAuditLog.objects.count()), before)

    def test_executor_mode_still_refuses_audit_inspection(self):
        with patch("apps.access_control.access_audit_api.executor_enabled", return_value=True):
            reply = self.get("access-audit/events/")
        self.assertEqual(reply.status_code, 503, reply.content)
