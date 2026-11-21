"""WF-03 write-path HTTP integration on the disposable MySQL test database.

NEVER run with normal or review-local settings. Explicit test-only mutation
settings simulate the unprotected local writer, not the separately fenced mTLS
executor. No test config, runtime URL, privilege or deployment change is made.
"""
import json
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings

from apps.accounts.active_role_context import SESSION_ROLE_KEY
from . import mutations
from .executor.engine import Executor
from .protected_requests import ProtectedRequestRefused
from .models import AccountPermission, AccountPermissionRoleScope, AccessAuditLog, AccountRole, Permission, RolePermission, Service
from .test_mutations import POLICY, fixtures

if (not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")
        or settings.DATABASES["default"]["NAME"] != settings.REGISTRATION_TEST_DATABASE
        or settings.TEST_RUNNER != "config.test_runner.IsolatedMySQLRunner"):
    raise ImproperlyConfigured("WF-03 write tests require isolated config.test_settings.")

# These values exist in the TestCase context ONLY. Never enable in runserver.
ISOLATED_WRITES = dict(
    ROOT_URLCONF="config.review_local_urls",
    MIDDLEWARE=[*settings.MIDDLEWARE, "apps.accounts.active_role_context.ActiveRoleContextMiddleware"],
    WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True,
    WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False,  # legacy, disposable MySQL ONLY
    ACCESS_CONTROL_DELEGATION_POLICY=POLICY,
    WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED=True,
    WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED=True,
    WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED=True,
    WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED=True,
    WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED=True,
    WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED=True,
    WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED=True,
)
PREFIX = "/api/v1/admin/"


@override_settings(**ISOLATED_WRITES)
class WF03IsolatedPermissionWriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)
        # The shared registration-review session prerequisite requires BOTH
        # accounts and access_control services to be active. WF-03 write
        # assertions must reach their own authorization/mutation logic.
        Service.objects.create(service_code="accounts", service_name="Accounts fixture")
        AccountRole.objects.create(account=cls.target, role=cls.instructor)
        for entry in (cls.role_manage, cls.account_manage, cls.delegate):
            RolePermission.objects.create(role=cls.technical_role, permission=entry)
        inspector = Permission.objects.create(
            service=cls.governance, permission_code="access_control.effective_permissions.inspect",
            permission_name="Inspect effective permissions", module_name="access_control", action_name="read",
        )
        RolePermission.objects.create(role=cls.technical_role, permission=inspector)

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.select(self.actor, self.technical_role)

    def select(self, account, role):
        self.client.force_login(account)
        session = self.client.session
        session[SESSION_ROLE_KEY] = role.pk
        session.save()
        self.client.cookies[settings.CSRF_COOKIE_NAME] = "d" * 32

    def post(self, suffix, data):
        return self.client.post(PREFIX + suffix, data=json.dumps(data),
                                content_type="application/json", HTTP_ACCEPT="application/json",
                                HTTP_X_CSRFTOKEN="d" * 32)

    def inspect(self, role, permission):
        url = f"effective-access/accounts/{self.target.pk}/roles/{role.pk}/"
        response = self.client.get(PREFIX + url)
        self.assertEqual(response.status_code, 200, response.content)
        return next(p for p in response.json()["permissions"]
                    if p["permission_code"] == permission.permission_code)

    def role_change(self, action, expected):
        return self.post(f"role-permissions/roles/{self.student.pk}/permissions/{self.read.pk}/{action}/",
                         {"expected_active": expected})

    def scoped_grant(self, role=None):
        role = role or self.student
        return self.post(f"account-grants/accounts/{self.target.pk}/grants/{self.read.pk}/",
                         {"role_id": role.pk, "expected_active": False})

    def restrict(self, action, effect, role_id=None):
        return self.post(f"account-restrictions/accounts/{self.target.pk}/overrides/{self.read.pk}/",
                         {"action": action, "expected_effect": effect,
                          "expected_scope_role_id": role_id})

    def test_role_grant_and_revoke_are_effective_and_audited_over_http(self):
        self.assertFalse(self.inspect(self.student, self.read)["effective"])
        grant = self.role_change("grant", False)
        self.assertEqual(grant.status_code, 200, grant.content)
        self.assertTrue(grant.json()["changed"])
        self.assertTrue(self.inspect(self.student, self.read)["effective"])
        self.assertFalse(self.inspect(self.instructor, self.read)["effective"])
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "role_permission.grant")
        revoke = self.role_change("revoke", True)
        self.assertEqual(revoke.status_code, 200, revoke.content)
        self.assertTrue(revoke.json()["changed"])
        self.assertFalse(self.inspect(self.student, self.read)["effective"])
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "role_permission.revoke")

    def test_stale_role_write_rejected_without_extra_audit(self):
        self.assertEqual(self.role_change("grant", False).status_code, 200)
        before = AccessAuditLog.objects.count()
        stale = self.role_change("grant", False)
        self.assertEqual(stale.status_code, 409, stale.content)
        self.assertEqual(AccessAuditLog.objects.count(), before)

    def test_role_scoped_grant_effective_only_in_selected_role_and_audited(self):
        grant = self.scoped_grant()
        self.assertEqual(grant.status_code, 200, grant.content)
        row = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.assertEqual((row.effect, row.is_active), ("Grant", True))
        self.assertEqual(AccountPermissionRoleScope.objects.get(account_permission=row).role_id, self.student.pk)
        self.assertTrue(self.inspect(self.student, self.read)["effective"])
        self.assertFalse(self.inspect(self.instructor, self.read)["effective"])
        event = AccessAuditLog.objects.latest("pk")
        self.assertEqual((event.action, event.role_id), ("account_permission.grant", self.student.pk))

    def test_duplicate_scoped_grant_is_conflict_without_audit(self):
        self.assertEqual(self.scoped_grant().status_code, 200)
        before = AccessAuditLog.objects.count()
        repeat = self.scoped_grant()
        self.assertEqual(repeat.status_code, 409, repeat.content)
        self.assertEqual(AccessAuditLog.objects.count(), before)
        self.assertEqual(AccountPermissionRoleScope.objects.count(), 1)

    def test_deny_clears_grant_scope_and_remove_deny_is_audited(self):
        self.assertEqual(self.scoped_grant().status_code, 200)
        deny = self.restrict("deny", "Grant", self.student.pk)
        self.assertEqual(deny.status_code, 200, deny.content)
        row = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.assertEqual((row.effect, row.is_active), ("Deny", True))
        self.assertFalse(AccountPermissionRoleScope.objects.filter(account_permission=row).exists())
        self.assertFalse(self.inspect(self.student, self.read)["effective"])
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "account_permission.deny")
        remove = self.restrict("remove_deny", "Deny")
        self.assertEqual(remove.status_code, 200, remove.content)
        row.refresh_from_db()
        self.assertFalse(row.is_active)
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "account_permission.deny.deactivate")

    def test_revoke_scoped_grant_preserves_role_permission(self):
        RolePermission.objects.create(role=self.student, permission=self.read)
        self.assertEqual(self.scoped_grant().status_code, 200)
        revoke = self.restrict("revoke_grant", "Grant", self.student.pk)
        self.assertEqual(revoke.status_code, 200, revoke.content)
        self.assertFalse(AccountPermission.objects.get(account=self.target, permission=self.read).is_active)
        self.assertFalse(AccountPermissionRoleScope.objects.exists())
        self.assertTrue(self.inspect(self.student, self.read)["effective"])
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "account_permission.grant.deactivate")

    def test_deny_has_priority_over_two_role_grants_then_restores(self):
        RolePermission.objects.create(role=self.student, permission=self.read)
        RolePermission.objects.create(role=self.instructor, permission=self.read)
        self.assertEqual(self.restrict("deny", None).status_code, 200)
        self.assertFalse(self.inspect(self.student, self.read)["effective"])
        self.assertFalse(self.inspect(self.instructor, self.read)["effective"])
        self.assertEqual(self.restrict("remove_deny", "Deny").status_code, 200)
        self.assertTrue(self.inspect(self.student, self.read)["effective"])
        self.assertTrue(self.inspect(self.instructor, self.read)["effective"])

    def test_unprivileged_role_context_refuses_mutations(self):
        self.select(self.actor, self.admin_role)
        before = (AccountPermission.objects.count(), AccessAuditLog.objects.count())
        response = self.scoped_grant()
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(before, (AccountPermission.objects.count(), AccessAuditLog.objects.count()))

    def test_revoking_delegation_refuses_writer_and_preserves_data(self):
        RolePermission.objects.filter(role=self.technical_role, permission=self.delegate).update(is_active=False)
        before = AccessAuditLog.objects.count()
        response = self.scoped_grant()
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(AccessAuditLog.objects.count(), before)
        self.assertFalse(AccountPermission.objects.exists())

    def test_audit_failure_rolls_back_grant(self):
        self.client.raise_request_exception = False
        with patch("apps.access_control.audit.record_access_audit", side_effect=RuntimeError("synthetic audit failure")) as audit_writer:
            response = self.scoped_grant()
        # WorkspaceSessionAPI deliberately masks unhandled errors as an opaque
        # fail-closed 503. Confirm we actually reached the audit write, rather
        # than accepting an unrelated 503 from an earlier gate.
        audit_writer.assert_called_once()
        self.assertEqual(response.status_code, 503, response.content)
        self.assertEqual(response.json()["error"]["code"], "auth_unavailable")
        self.assertFalse(AccountPermission.objects.exists())
        self.assertFalse(AccountPermissionRoleScope.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_protected_executor_setting_remains_inaccessible(self):
        before = AccessAuditLog.objects.count()
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            response = self.scoped_grant()
        self.assertEqual(response.status_code, 503, response.content)
        self.assertEqual(AccessAuditLog.objects.count(), before)
        self.assertFalse(AccountPermission.objects.exists())

    def test_role_cas_precondition_sent_to_executor_client(self):
        # This verifies transport payload construction, NOT mTLS authorization.
        with patch("apps.access_control.executor.client.remote_call", return_value=True) as remote:
            value = mutations.grant_role_permission(actor=self.actor, role=self.student,
                      permission=self.read, expected_active=False)
        self.assertTrue(value)
        self.assertEqual(remote.call_args.args[0], "role_permission.grant")
        self.assertIs(remote.call_args.args[1]["expected_active"], False)
        self.assertFalse(RolePermission.objects.filter(role=self.student, permission=self.read).exists())

    def test_executor_dispatch_validates_cas_type_and_passes_boolean(self):
        actor_id = self.actor.pk
        payload = {"actor_id": actor_id, "role_id": self.student.pk,
                   "permission_id": self.read.pk, "reason": "permission_change", "expected_active": False}
        with patch("apps.access_control.mutations.grant_role_permission", return_value=True) as writer:
            self.assertTrue(Executor.dispatch(None, "role_permission.grant", payload, actor_id, None))
        self.assertIs(writer.call_args.kwargs["expected_active"], False)
        for bad in ("false", 0, None, [], {}):
            with self.subTest(bad=bad):
                invalid = {**payload, "expected_active": bad}
                with patch("apps.access_control.mutations.grant_role_permission") as writer:
                    with self.assertRaises(ProtectedRequestRefused):
                        Executor.dispatch(None, "role_permission.grant", invalid, actor_id, None)
                    writer.assert_not_called()
