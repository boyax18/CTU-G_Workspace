"""P3C6A contract tests: no DB writes, no database configuration changes."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.access_control import writer_boundary as boundary
from apps.access_control.delegation import (
    ACCOUNT_PERMISSION_MANAGE, ROLE_PERMISSION_MANAGE,
)
from apps.access_control.mutations import _management_context
from apps.accounts.admin_bootstrap import provision_first_workspace_admin
from apps.accounts.registration_review import approve_registration, reject_registration


class WriterBoundaryContractTests(SimpleTestCase):
    def test_release_remains_blocked(self):
        self.assertEqual("BLOCKED", boundary.RELEASE_STATUS)

    def test_exactly_five_known_write_operations(self):
        self.assertEqual(frozenset({
            "registration.approve", "registration.reject",
            "role_permission.change", "account_permission.change",
            "bootstrap.initial_admin",
        }), boundary.COVERED_OPERATIONS)

    def test_known_operation_preserves_legacy_behavior_with_flag_off(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False):
            for op in boundary.COVERED_OPERATIONS:
                self.assertIsNone(boundary.require_verified_writer(op))

    def test_gate_always_denies_when_enabled(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            for op in boundary.COVERED_OPERATIONS:
                with self.subTest(op=op), self.assertRaises(boundary.WriterBoundaryUnavailable):
                    boundary.require_verified_writer(op)

    def test_gate_rejects_invalid_config_values(self):
        for config in (None, 0, 1, "true", "false", "require", {}, []):
            with self.subTest(type=type(config).__name__, value=repr(config)):
                with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=config):
                    with self.assertRaises(boundary.WriterBoundaryUnavailable):
                        boundary.require_verified_writer("registration.approve")

    def test_gate_rejects_unknown_operation_even_when_disabled(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False):
            for operation in (None, "", "role.create", "admin.bootstrap", 1, True, {}, []):
                with self.subTest(operation=repr(operation)), self.assertRaises(boundary.WriterBoundaryUnavailable):
                    boundary.require_verified_writer(operation)

    @override_settings(
        WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
        WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True,
    )
    def test_approval_stops_before_transaction(self):
        with patch("apps.accounts.registration_review.transaction.atomic") as atomic:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                approve_registration(actor=None, target_id=1)
            atomic.assert_not_called()

    @override_settings(
        WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
        WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True,
    )
    def test_rejection_stops_before_transaction(self):
        with patch("apps.accounts.registration_review.transaction.atomic") as atomic:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                reject_registration(actor=None, target_id=1, rejection_code="duplicate_request")
            atomic.assert_not_called()

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_role_permission_context_stops_before_transaction(self):
        with patch("apps.access_control.mutations.transaction.atomic") as atomic:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                with _management_context(None, None, ROLE_PERMISSION_MANAGE):
                    self.fail("Must never enter write transaction")
            atomic.assert_not_called()

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_account_permission_context_stops_before_transaction(self):
        with patch("apps.access_control.mutations.transaction.atomic") as atomic:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                with _management_context(None, None, ACCOUNT_PERMISSION_MANAGE):
                    self.fail("Must never enter write transaction")
            atomic.assert_not_called()

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=False)
    def test_unknown_management_code_denied_even_in_legacy_mode(self):
        with patch("apps.access_control.mutations.transaction.atomic") as atomic:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                with _management_context(None, None, "not.an.approved.management.code"):
                    self.fail("Unknown writer operation must fail")
            atomic.assert_not_called()

    @override_settings(
        WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED=True,
        WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True,
    )
    def test_first_admin_bootstrap_stops_before_database_preflight(self):
        with patch("apps.accounts.admin_bootstrap._require_local_primary_mysql") as preflight:
            with self.assertRaises(boundary.WriterBoundaryUnavailable):
                provision_first_workspace_admin(
                    operator_school_id="operator", operator_password="test",
                    new_school_id="new", new_email="unused@example.invalid",
                    new_password="test",
                )
            preflight.assert_not_called()

    def test_error_messages_do_not_echo_secret_or_names(self):
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True):
            with self.assertRaises(boundary.WriterBoundaryUnavailable) as result:
                boundary.require_verified_writer("registration.approve")
        message = str(result.exception)
        self.assertNotIn("school_id", message)
        self.assertNotIn("password", message)
        self.assertNotIn("ctug_workspace", message)

    def test_gate_has_no_success_token_or_executor_override(self):
        import inspect
        self.assertEqual(["operation"], list(inspect.signature(boundary.require_verified_writer).parameters))

    def test_failed_gate_is_not_a_permission_denial_for_user(self):
        # The current exception represents infrastructure unavailable,
        # not a signed authorization outcome or confirmed DB denial.
        self.assertTrue(issubclass(boundary.WriterBoundaryUnavailable, RuntimeError))
