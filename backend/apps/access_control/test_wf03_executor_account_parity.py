"""WF-03 protected executor parity staging — fail-closed contracts.

Runs with the existing isolated test settings. No live writer is provisioned.
The fenced DB operations require an independently deployed DBA-approved schema.
"""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from apps.access_control.executor import protocol, schema
from apps.access_control.executor.engine import Executor
from apps.access_control.writer_boundary import WriterBoundaryUnavailable, require_verified_writer
from apps.access_control.executor.runtime import executing
from apps.access_control.executor.client import LOCAL, remote_call
from apps.access_control.protected_requests import ProtectedRequestRefused
from apps.access_control.account_grant_api import AccountGrantAPI
from apps.access_control.account_restriction_api import RestrictionAPI
from apps.accounts.active_role_context_api import RoleContextSwitchView
from apps.accounts.registration_review_api import ReviewAPIUnavailable


class WF03ExecutorAccountContracts(SimpleTestCase):
    def test_new_operations_are_ordinary_only(self):
        self.assertIn("account_permission.scoped_grant", protocol.ORDINARY)
        self.assertIn("account_permission.restrict", protocol.ORDINARY)
        self.assertNotIn("account_permission.scoped_grant", protocol.PROTECTED)
        self.assertNotIn("account_permission.restrict", protocol.PROTECTED)
        for op in ("account_permission.scoped_grant", "account_permission.restrict"):
            env = protocol.request(op, {"actor_id": 1})
            self.assertEqual(protocol.validate_request(env, "ordinary"), env)
            with self.assertRaises(ProtectedRequestRefused):
                protocol.validate_request(env, "protected")

    def test_default_off_refuses_before_authentication(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True,
                               WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED=False,
                               WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            for api in (AccountGrantAPI, RestrictionAPI):
                with self.subTest(api=api.__name__), self.assertRaises(ReviewAPIUnavailable):
                    api().initial(None)
            self.assertEqual(RoleContextSwitchView().post(None).status_code, 503)

    def test_writer_is_ledger_transaction_only(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            for operation in ("account_permission.scoped_grant", "account_permission.restrict"):
                with self.subTest(operation=operation), executing(operation):
                    with self.assertRaises(WriterBoundaryUnavailable):
                        require_verified_writer("account_permission.change")

    def test_scope_table_is_fenced_and_delete_privilege_is_bounded(self):
        name = "account_permission_role_scopes"
        self.assertIn(name, schema.FENCED)
        statements = schema.statements()
        for event in ("insert", "update", "delete"):
            line = next(s for s in statements if s.startswith(f"CREATE TRIGGER wex_{name}_{event} "))
            self.assertIn("wex_lease(0)", line)
            self.assertIn("scoped permission operation required", line)
            self.assertIn("account_permission.restrict" if event == "delete" else "account_permission.scoped_grant", line)
        statements = schema.grants("test_ctug_executor_demo", "web_runtime", "wex_ordinary", "wex_protected", "wex_recovery")
        self.assertFalse(any("INSERT" in line and "web_runtime" in line and name in line for line in statements))
        self.assertTrue(any("DELETE" in line and name in line and "wex_ordinary" in line for line in statements))

    def test_executor_revalidates_selected_role_instead_of_trusting_payload(self):
        instance = object.__new__(Executor)
        class FakeAccount:
            is_active = True
            request_status = "Approved"
        with patch("apps.access_control.executor.engine.Account.objects.get", return_value=FakeAccount()),              patch("apps.access_control.models.Permission.objects.get", return_value=object()),              patch("apps.accounts.active_role_context.available_roles", return_value=[]) as available:
            with override_settings(WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED=True,
                                   WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
                payload = {"actor_id": 10, "target_id": 12, "permission_id": 3,
                           "reason": "permission_change", "selected_role_id": 99,
                           "role_id": 4, "expected_active": False}
                with self.assertRaises(ProtectedRequestRefused):
                    instance.dispatch("account_permission.scoped_grant", payload, 10, None)
                available.assert_called_once_with(10)

    def test_verified_selected_context_is_bound_to_scoped_grant_dispatch(self):
        from types import SimpleNamespace
        from apps.accounts.active_role_context import selected_scope
        actor = SimpleNamespace(pk=10, is_active=True, request_status="Approved")
        target = SimpleNamespace(pk=12)
        permission = SimpleNamespace(pk=3)
        role = SimpleNamespace(pk=4)
        def lookup_account(pk):
            return actor if pk == 10 else target
        def bound_grant(**kwargs):
            scope = selected_scope()
            self.assertEqual((scope.account_id, scope.role_id), (10, 99))
            self.assertIs(kwargs["actor"], actor)
            self.assertIs(kwargs["target"], target)
            self.assertIs(kwargs["role"], role)
            self.assertIs(kwargs["permission"], permission)
            self.assertIs(kwargs["expected_active"], False)
            return True
        with patch("apps.access_control.executor.engine.Account.objects.get", side_effect=lookup_account),              patch("apps.access_control.models.Permission.objects.get", return_value=permission),              patch("apps.access_control.models.Role.objects.get", return_value=role),              patch("apps.accounts.active_role_context.available_roles",
                   return_value=[{"role_id": 99, "role_name": "Technical Super Admin"}]),              patch("apps.access_control.technical_admin.has_technical_authority", return_value=True),              patch("apps.access_control.mutations.grant_account_permission_for_role", side_effect=bound_grant):
            with override_settings(WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED=True,
                                   WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
                payload = {"actor_id": 10, "target_id": 12, "permission_id": 3,
                           "reason": "permission_change", "selected_role_id": 99,
                           "role_id": 4, "expected_active": False}
                self.assertTrue(object.__new__(Executor).dispatch(
                    "account_permission.scoped_grant", payload, 10, None))
        self.assertIsNone(selected_scope())

    def test_executor_gate_refuses_before_account_scope_mutation(self):
        instance = object.__new__(Executor)
        class FakeAccount:
            is_active = True
            request_status = "Approved"
        # dispatch does an actor lookup first; patch without opening a database.
        with patch("apps.access_control.executor.engine.Account.objects.get", return_value=FakeAccount()), \
             patch("apps.access_control.models.Permission.objects.get") as get_permission:
            get_permission.return_value = object()
            with override_settings(WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED=False):
                for op in ("account_permission.scoped_grant", "account_permission.restrict"):
                    with self.subTest(op=op), self.assertRaises(ProtectedRequestRefused):
                        instance.dispatch(op, {"actor_id": 10, "permission_id": 3}, 10, None)
