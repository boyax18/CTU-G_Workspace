"""Audit validation, real commit/rollback, and concurrency in disposable MySQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Account

from . import audit
from .audit import AuditTransactionError, AuditValidationError, record_access_audit
from .models import AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service
from .services import get_effective_permissions

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Audit tests require --settings=config.test_settings; development data must never be used.")


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing audit fixtures on an unexpected database.")


def fixtures():
    verify_database()
    actor = Account(school_id="AUDIT-ACTOR")
    actor.set_unusable_password()
    actor.save()
    target = Account(school_id="AUDIT-TARGET")
    target.set_unusable_password()
    target.save()
    role = Role.objects.create(role_name="Student")
    service = Service.objects.create(service_code="test_audit", service_name="Audit fixture")
    permission = Permission.objects.create(
        service=service, permission_code="test.audit.reference", permission_name="Audit fixture",
        module_name="test", action_name="reference",
    )
    return actor, target, role, service, permission


class AuditValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor, cls.target, cls.role, cls.service, cls.permission = fixtures()

    def record(self, **kwargs):
        return record_access_audit(**{"actor": self.actor, "action": "test.audit.record", **kwargs})

    def assert_invalid(self, **kwargs):
        with self.assertRaises(AuditValidationError) as captured:
            with transaction.atomic():
                self.record(**kwargs)
        self.assertEqual(AccessAuditLog.objects.count(), 0)
        return str(captured.exception)

    def test_valid_audit_insertion_with_all_references_and_authorization_snapshots(self):
        old = {"effect": "Deny", "is_active": False, "role_id": None}
        new = {"effect": "Grant", "is_active": True, "role_id": self.role.pk}
        with transaction.atomic():
            result = self.record(target=self.target, role=self.role, permission=self.permission,
                                 old_value=old, new_value=new, reason="access_review")
        self.assertIsNone(result)
        row = AccessAuditLog.objects.get()
        self.assertEqual(row.actor_account_id, self.actor.pk)
        self.assertEqual(row.target_account_id, self.target.pk)
        self.assertEqual(row.role_id, self.role.pk)
        self.assertEqual(row.permission_id, self.permission.pk)
        self.assertEqual(row.action, "test.audit.record")
        self.assertEqual(row.old_value, old)
        self.assertEqual(row.new_value, new)
        self.assertEqual(row.reason, "access_review")

    def test_actor_is_required_and_no_placeholder_is_created(self):
        self.assert_invalid(actor=None)
        self.assertEqual(Account.objects.count(), 2)
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())

    def test_actor_parameter_cannot_be_omitted(self):
        with self.assertRaises(TypeError):
            record_access_audit(action="test.audit.record")
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_wrong_type_anonymous_raw_id_and_unsaved_actors_are_rejected(self):
        for actor in (AnonymousUser(), self.actor.pk, str(self.actor.pk), self.role, Account(), Account(account_id=self.actor.pk)):
            with self.subTest(actor_type=type(actor).__name__):
                self.assert_invalid(actor=actor)

    def test_actor_from_another_database_alias_is_rejected(self):
        self.actor._state.db = "untrusted"
        self.assert_invalid()

    def test_invalid_actor_primary_key_type_is_rejected(self):
        self.actor.pk = True
        self.assert_invalid()

    def test_deleted_actor_is_rejected(self):
        Account.objects.filter(pk=self.actor.pk).delete()
        self.assert_invalid()

    def test_optional_references_and_nullable_payloads(self):
        self.record()
        row = AccessAuditLog.objects.get()
        self.assertIsNone(row.target_account_id)
        self.assertIsNone(row.role_id)
        self.assertIsNone(row.permission_id)
        self.assertIsNone(row.old_value)
        self.assertIsNone(row.new_value)
        self.assertIsNone(row.reason)

    def test_optional_target_can_be_a_persisted_account(self):
        self.record(target=self.target)
        self.assertEqual(AccessAuditLog.objects.get().target_account_id, self.target.pk)

    def test_optional_role_and_permission_can_be_persisted_records(self):
        self.record(role=self.role, permission=self.permission)
        row = AccessAuditLog.objects.get()
        self.assertEqual(row.role_id, self.role.pk)
        self.assertEqual(row.permission_id, self.permission.pk)

    def test_wrong_optional_reference_types_and_raw_ids_are_rejected(self):
        for field, value in (("target", self.role), ("role", self.permission), ("permission", self.actor),
                             ("target", self.target.pk), ("role", self.role.pk), ("permission", self.permission.pk)):
            with self.subTest(field=field, reference_type=type(value).__name__):
                self.assert_invalid(**{field: value})

    def test_unsaved_optional_references_are_rejected(self):
        for field, value in (("target", Account(account_id=self.target.pk)), ("role", Role(role_id=self.role.pk)),
                             ("permission", Permission(permission_id=self.permission.pk))):
            with self.subTest(field=field):
                self.assert_invalid(**{field: value})

    def test_deleted_target_reference_is_rejected(self):
        Account.objects.filter(pk=self.target.pk).delete()
        self.assert_invalid(target=self.target)

    def test_deleted_role_reference_is_rejected(self):
        Role.objects.filter(pk=self.role.pk).delete()
        self.assert_invalid(role=self.role)

    def test_deleted_permission_reference_is_rejected(self):
        Permission.objects.filter(pk=self.permission.pk).delete()
        self.assert_invalid(permission=self.permission)

    def test_action_length_uses_existing_schema_limit(self):
        self.assert_invalid(action="a" * 51)
        self.record(action="a" * 50)
        self.assertEqual(len(AccessAuditLog.objects.get().action), 50)

    def test_action_is_a_nonempty_plain_machine_code(self):
        for value in (None, 1, "", " ", "bad action", "action\n", "password=secret"):
            with self.subTest(value_type=type(value).__name__):
                self.assert_invalid(action=value)

    def test_reason_schema_length_and_type_are_validated(self):
        for value in ("r" * 256, 1, [], {}):
            with self.subTest(value_type=type(value).__name__):
                self.assert_invalid(reason=value)

    def test_reason_accepts_only_controlled_non_sensitive_codes(self):
        for value in ("password=private-value", "Bearer private-token", "person@example.edu", "unreviewed human text"):
            with self.subTest(reason_kind=value.split("=", 1)[0]):
                message = self.assert_invalid(reason=value)
                self.assertNotIn(value, message)
        self.record(reason="policy_enforcement")
        self.assertEqual(AccessAuditLog.objects.get().reason, "policy_enforcement")

    def test_valid_json_objects_ids_enums_booleans_lists_and_null(self):
        previous = {"account_id": self.actor.pk, "role_ids": [], "request_status": "Pending"}
        following = {"permission_ids": [self.permission.pk], "account_permission_id": None,
                     "service_id": self.service.pk, "request_status": "Approved"}
        self.record(old_value=previous, new_value=following)
        row = AccessAuditLog.objects.get()
        self.assertEqual(row.old_value, previous)
        self.assertEqual(row.new_value, following)

    def test_json_scalars_arrays_custom_objects_and_non_string_keys_are_rejected(self):
        for value in ([], "text", True, 1, 1.5, object(), {1: True}):
            with self.subTest(value_type=type(value).__name__):
                self.assert_invalid(old_value=value)

    def test_known_fields_reject_unsupported_values_and_implicit_conversions(self):
        for value in (True, 0, -1, 2_147_483_648, 1.5, float("nan"), float("inf"), Decimal("1"),
                      datetime(2026, 1, 1), b"bytes", {1}, (1,), {"nested": 1}, "1"):
            with self.subTest(value_type=type(value).__name__):
                self.assert_invalid(new_value={"role_id": value})

    def test_flags_and_enums_reject_noncanonical_values(self):
        for value in ({"is_active": 1}, {"effect": "Allow"}, {"effect": "grant"}, {"request_status": "approved"}):
            with self.subTest(field=next(iter(value))):
                self.assert_invalid(new_value=value)

    def test_sensitive_and_personal_state_fields_are_rejected_without_value_echo(self):
        for field in ("password", "password_hash", "password_reset_token", "session_key", "csrf_token",
                      "api_key", "secret", "authorization", "email", "school_id", "first_name", "request_body"):
            with self.subTest(field=field):
                message = self.assert_invalid(new_value={field: "private-value-not-for-audit"})
                self.assertNotIn("private-value", message)

    def test_nested_secret_or_cyclic_payloads_are_rejected(self):
        self.assert_invalid(new_value={"role_ids": [{"password": "private"}]})
        cyclic = []
        cyclic.append(cyclic)
        self.assert_invalid(new_value={"role_ids": cyclic})

    def test_id_lists_are_plain_bounded_integer_lists(self):
        for value in ((1, 2), [True], [None], [0], [1] * 101):
            with self.subTest(value_type=type(value).__name__):
                self.assert_invalid(new_value={"role_ids": value})

    def test_serialized_payload_byte_limit(self):
        self.assert_invalid(new_value={"role_ids": [audit.MAX_ID] * 100, "permission_ids": [audit.MAX_ID] * 100})

    def test_payloads_are_detached_from_caller_mutation(self):
        snapshot = {"role_ids": [self.role.pk], "is_active": True}
        self.record(new_value=snapshot)
        snapshot["role_ids"].append(999)
        snapshot["is_active"] = False
        self.assertEqual(AccessAuditLog.objects.get().new_value, {"role_ids": [self.role.pk], "is_active": True})

    def test_database_timestamp_default_is_preserved(self):
        with patch("django.utils.timezone.now", side_effect=AssertionError("Do not supply audit timestamps")):
            with CaptureQueriesContext(connection) as queries:
                self.record()
        insert = next(entry["sql"] for entry in queries if entry["sql"].lstrip().upper().startswith("INSERT"))
        self.assertNotIn("`created_at`", insert)
        self.assertIsNotNone(AccessAuditLog.objects.get().created_at)
        self.assertEqual(AccessAuditLog.objects.get().created_at.microsecond, 0)

    def test_service_is_append_only_and_returns_no_mutable_model_or_success_receipt(self):
        self.assertIsNone(self.record(new_value={"is_active": True}))
        first = AccessAuditLog.objects.get()
        self.assertIsNone(self.record(new_value={"is_active": False}))
        first.refresh_from_db()
        self.assertEqual(first.new_value, {"is_active": True})
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_audit_insert_is_not_authorization_and_changes_no_account_or_grants(self):
        self.assertEqual(get_effective_permissions(self.actor), frozenset())
        self.record(target=self.target, role=self.role, permission=self.permission, new_value={"effect": "Grant"})
        self.assertEqual(get_effective_permissions(self.actor), frozenset())
        self.assertFalse(self.actor.has_perm(self.permission.permission_code))
        self.actor.refresh_from_db()
        self.assertFalse(self.actor.is_active)
        self.assertEqual(self.actor.request_status, "Pending")
        self.assertEqual(AccountRole.objects.count(), 0)
        self.assertEqual(RolePermission.objects.count(), 0)
        self.assertEqual(Role.objects.count(), 1)


class AuditTransactionTests(TransactionTestCase):
    def setUp(self):
        self.actor, self.target, self.role, self.service, self.permission = fixtures()

    def record(self, **kwargs):
        return record_access_audit(**{"actor": self.actor, "action": "test.audit.transaction", **kwargs})

    def test_audit_outside_explicit_atomic_transaction_is_rejected(self):
        self.assertFalse(connection.in_atomic_block)
        with self.assertRaises(AuditTransactionError):
            self.record()
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_manual_autocommit_disable_does_not_replace_explicit_atomic(self):
        transaction.set_autocommit(False)
        try:
            with self.assertRaises(AuditTransactionError):
                self.record()
        finally:
            transaction.rollback()
            transaction.set_autocommit(True)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_mutation_and_audit_commit_together_and_success_is_deferred_until_commit(self):
        completed = []
        with transaction.atomic():
            Service.objects.filter(pk=self.service.pk).update(is_active=False)
            self.record(old_value={"is_active": True}, new_value={"is_active": False})
            transaction.on_commit(lambda: completed.append((AccessAuditLog.objects.count(), Service.objects.get(pk=self.service.pk).is_active)))
            self.assertEqual(completed, [])
        self.assertEqual(completed, [(1, False)])

    def test_mutation_rolls_back_when_audit_insert_fails(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Service.objects.filter(pk=self.service.pk).update(is_active=False)
                with patch("apps.access_control.audit.AccessAuditLog.objects.using") as manager:
                    manager.return_value.create.side_effect = IntegrityError("simulated write failure")
                    self.record()
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_caught_audit_failure_still_marks_the_owning_transaction_for_rollback(self):
        with transaction.atomic():
            Service.objects.filter(pk=self.service.pk).update(is_active=False)
            try:
                self.record(new_value={"password": "private"})
            except AuditValidationError:
                pass
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_unexpected_audit_failure_propagates_and_rolls_back_mutation(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Service.objects.filter(pk=self.service.pk).update(is_active=False)
                with patch("apps.access_control.audit._state", side_effect=RuntimeError("simulated failure")):
                    self.record()
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_audit_rolls_back_when_enclosing_mutation_fails(self):
        completed = []
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.record()
                transaction.on_commit(lambda: completed.append(True))
                Service.objects.filter(pk=self.service.pk).update(is_active=False)
                raise RuntimeError("simulated mutation failure")
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 0)
        self.assertEqual(completed, [])

    def test_multiple_audit_entries_share_one_transaction(self):
        with transaction.atomic():
            self.record(old_value={"is_active": True})
            self.record(new_value={"is_active": False})
        self.assertEqual(AccessAuditLog.objects.count(), 2)

    def test_real_foreign_key_failure_after_reference_validation_rolls_everything_back(self):
        original = audit._reference_id

        def delete_after_validation(value, model, field, required=False):
            result = original(value, model, field, required)
            if field == "target":
                Account.objects.filter(pk=result).delete()
            return result

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Service.objects.filter(pk=self.service.pk).update(is_active=False)
                with patch("apps.access_control.audit._reference_id", side_effect=delete_after_validation):
                    self.record(target=self.target)
        self.assertTrue(Account.objects.filter(pk=self.target.pk).exists())
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_active)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_uncommitted_mutation_and_audit_are_not_visible_from_another_connection(self):
        service_id = self.service.pk

        def read_committed_state():
            try:
                verify_database()
                return AccessAuditLog.objects.count(), Service.objects.get(pk=service_id).is_active
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as executor:
            with transaction.atomic():
                Service.objects.filter(pk=service_id).update(is_active=False)
                self.record()
                self.assertEqual(executor.submit(read_committed_state).result(timeout=10), (0, True))
            self.assertEqual(executor.submit(read_committed_state).result(timeout=10), (1, False))

    def test_concurrent_independent_appends_are_attributable_and_do_not_overwrite(self):
        barrier = Barrier(2)
        actor_id = self.actor.pk

        def append(action):
            try:
                verify_database()
                actor = Account.objects.get(pk=actor_id)
                barrier.wait(timeout=10)
                with transaction.atomic():
                    record_access_audit(actor=actor, action=action)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(append, action) for action in ("test.concurrent.one", "test.concurrent.two")]
            for future in futures:
                future.result(timeout=15)
        self.assertEqual(set(AccessAuditLog.objects.values_list("action", flat=True)), {"test.concurrent.one", "test.concurrent.two"})
        self.assertEqual(set(AccessAuditLog.objects.values_list("actor_account_id", flat=True)), {actor_id})
