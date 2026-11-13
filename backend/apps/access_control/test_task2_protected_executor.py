"""Actual-schema MySQL candidate tests; production execution is unavailable."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.db import DatabaseError, connection, connections
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from apps.accounts.models import Account
from .models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from .protected_requests import CORE_PERMISSIONS, ProtectedRequestRefused, digest
from .technical_admin import has_technical_authority
from .tests_support.task2_protected_executor_test_only import (
    CONTROL, LEDGER, IsolatedProtectedExecutor, OutcomeUnknown,
)
from .tests_support.task2_signed_fixture_test_only import request_fixture, trust_fixture


class CandidateIsolationTests(SimpleTestCase):
    @override_settings(SETTINGS_MODULE="config.settings")
    def test_live_settings_refused_before_connection(self):
        with patch("django.db.backends.utils.CursorWrapper.execute") as execute:
            with self.assertRaises(Exception):
                IsolatedProtectedExecutor()
            execute.assert_not_called()

    def test_unsaved_account_never_has_technical_authority(self):
        self.assertFalse(has_technical_authority(Account(account_id=1), CORE_PERMISSIONS[0]))


class ProtectedExecutorMySQLTests(TransactionTestCase):
    def setUp(self):
        self.now = 1_800_000_000
        self.executor = IsolatedProtectedExecutor()
        self.service = Service.objects.create(service_code="access_control", service_name="Access Control")
        self.permissions = []
        for code in CORE_PERMISSIONS:
            module, action = code.split(".")[1:]
            self.permissions.append(Permission.objects.create(
                service=self.service, permission_code=code, permission_name=code.rsplit(".", 1)[1],
                module_name=module, action_name=action,
            ))
        self.admin = Role.objects.create(role_name="Admin")
        self.actor = Account.objects.create(school_id="CANDIDATE-ACTOR", is_active=True, request_status="Approved")
        self.actor.set_unusable_password()
        self.actor.save(update_fields=["password"])
        self.target = Account.objects.create(school_id="CANDIDATE-TARGET", is_active=True, request_status="Approved")
        self.target.set_password("Fictional-Test-Password!2030")
        self.target.save(update_fields=["password"])
        AccountRole.objects.create(account=self.target, role=self.admin, assigned_by=self.actor)
        self.trust, self.keys = trust_fixture(settings.REGISTRATION_TEST_DATABASE, self.actor.pk, self.now)
        self.executor.create(self.trust)
        self.addCleanup(self.executor.drop)

    def bundle(self, target_id=None):
        return request_fixture(self.trust, self.keys, self.actor.pk, now=self.now,
                               before_hash=self.executor.before_hash(), target_id=target_id)

    def run_bundle(self, bundle):
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        return self.executor.execute(request_id, self.trust, now=self.now)

    def provision(self):
        self.run_bundle(self.bundle())
        return Role.objects.get(role_name="Technical Super Admin")

    def ledger_status(self):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT status FROM {LEDGER} ORDER BY claimed_at,operation")
            return [r[0] for r in cursor.fetchall()]

    def test_provision_creates_only_inactive_protected_role_and_exact_bindings(self):
        role = self.provision()
        self.assertFalse(role.is_active)
        self.assertEqual(6, RolePermission.objects.filter(role=role, is_active=False).count())
        self.assertFalse(AccountRole.objects.filter(role=role).exists())
        self.assertEqual(1, AccessAuditLog.objects.count())
        self.assertEqual(["APPLIED"], self.ledger_status())

    def test_bootstrap_composes_roles_without_creating_or_activating_an_account(self):
        role = self.provision()
        count = Account.objects.count()
        self.run_bundle(self.bundle(self.target.pk))
        role.refresh_from_db()
        self.assertTrue(role.is_active)
        self.assertEqual(count, Account.objects.count())
        self.assertEqual({"Admin", "Technical Super Admin"}, set(
            AccountRole.objects.filter(account=self.target).values_list("role__role_name", flat=True)))
        self.assertTrue(all(has_technical_authority(self.target, code) for code in CORE_PERMISSIONS))
        self.assertEqual(2, AccessAuditLog.objects.count())

    def test_school_admin_direct_grant_does_not_create_protected_authority(self):
        AccountPermission.objects.create(account=self.target, permission=self.permissions[0], effect="Grant")
        self.assertFalse(has_technical_authority(self.target, CORE_PERMISSIONS[0]))

    def test_framework_flags_do_not_grant_application_authority(self):
        self.target.is_staff = self.target.is_superuser = True
        self.target.save(update_fields=["is_staff", "is_superuser"])
        self.assertFalse(has_technical_authority(self.target, CORE_PERMISSIONS[0]))

    def test_direct_deny_overrides_successful_bootstrap_and_refreshes_same_object(self):
        self.provision()
        self.run_bundle(self.bundle(self.target.pk))
        self.assertTrue(has_technical_authority(self.target, CORE_PERMISSIONS[0]))
        AccountPermission.objects.create(account=self.target, permission=self.permissions[0], effect="Deny")
        self.assertFalse(has_technical_authority(self.target, CORE_PERMISSIONS[0]))
        self.assertTrue(has_technical_authority(self.target, CORE_PERMISSIONS[1]))

    def test_provision_replay_cannot_create_second_audit(self):
        bundle = self.bundle()
        self.run_bundle(bundle)
        with self.assertRaises(OutcomeUnknown):
            self.executor.claim(bundle, self.trust, now=self.now)
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(bundle["request"]["request_id"], self.trust, now=self.now)
        self.assertEqual(1, AccessAuditLog.objects.count())

    def test_new_nonce_cannot_repeat_provision_scope(self):
        self.provision()
        with self.assertRaises(OutcomeUnknown):
            self.executor.claim(self.bundle(), self.trust, now=self.now)

    def test_audit_failure_rolls_back_role_bindings_and_leaves_durable_attempt(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        with patch("apps.access_control.tests_support.task2_protected_executor_test_only.record_access_audit_receipt",
                   side_effect=RuntimeError("synthetic interruption")):
            with self.assertRaises(OutcomeUnknown):
                self.executor.execute(request_id, self.trust, now=self.now)
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())
        self.assertFalse(RolePermission.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertEqual(["ATTEMPTED"], self.ledger_status())
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now)
        self.assertEqual({"status": "HOLD", "audit_id": None}, self.executor.reconcile(request_id, digest(bundle["request"])))

    def test_bootstrap_audit_failure_rolls_back_activation_and_assignment(self):
        role = self.provision()
        bundle = self.bundle(self.target.pk)
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        with patch("apps.access_control.tests_support.task2_protected_executor_test_only.record_access_audit_receipt", side_effect=RuntimeError):
            with self.assertRaises(OutcomeUnknown):
                self.executor.execute(request_id, self.trust, now=self.now)
        role.refresh_from_db()
        self.assertFalse(role.is_active)
        self.assertFalse(AccountRole.objects.filter(role=role).exists())
        self.assertFalse(RolePermission.objects.filter(role=role, is_active=True).exists())
        self.assertEqual(1, AccessAuditLog.objects.count())

    def test_state_drift_after_claim_is_held(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now)
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())

    def test_expiry_after_claim_cannot_be_retried(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now + 60)
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now)

    def test_hold_prevents_claim_and_execution(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        self.executor.hold()
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now)
        with self.assertRaises(OutcomeUnknown):
            self.executor.claim(self.bundle(), self.trust, now=self.now)
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_epoch_rotation_prevents_old_claim_execution(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE {CONTROL} SET epoch=epoch+1 WHERE id=1")
        with self.assertRaises(OutcomeUnknown):
            self.executor.execute(request_id, self.trust, now=self.now)

    def test_reconcile_success_on_new_connection_without_reexecution(self):
        bundle = self.bundle()
        audit_id = self.run_bundle(bundle)
        connection.close()
        self.assertEqual({"status": "APPLIED", "audit_id": audit_id}, self.executor.reconcile(
            bundle["request"]["request_id"], digest(bundle["request"])))
        self.assertEqual(1, AccessAuditLog.objects.count())

    def test_lost_commit_acknowledgment_reconciles_applied_without_retry(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        original_commit = connection.commit
        commits = []

        def lost_ack():
            original_commit()
            commits.append(True)
            if len(commits) == 2:  # attempt commit, then application+audit commit
                raise DatabaseError("synthetic lost acknowledgment after successful commit")

        with patch.object(connection, "commit", side_effect=lost_ack):
            with self.assertRaises(OutcomeUnknown):
                self.executor.execute(request_id, self.trust, now=self.now)
        connection.close()
        result = self.executor.reconcile(request_id, digest(bundle["request"]))
        self.assertEqual("APPLIED", result["status"])
        self.assertIsNotNone(result["audit_id"])
        self.assertEqual(1, AccessAuditLog.objects.count())

    def test_process_interruption_after_attempt_stays_held(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        with patch.object(self.executor, "_provision", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                self.executor.execute(request_id, self.trust, now=self.now)
        connection.close()
        self.assertEqual("HOLD", self.executor.reconcile(request_id, digest(bundle["request"]))["status"])
        self.assertFalse(AccessAuditLog.objects.exists())

    def test_concurrent_claim_and_execution_cannot_double_apply(self):
        bundle = self.bundle()
        barrier = Barrier(2)

        def run():
            try:
                executor = IsolatedProtectedExecutor()
                barrier.wait(timeout=10)
                request_id = executor.claim(bundle, self.trust, now=self.now)
                return executor.execute(request_id, self.trust, now=self.now)
            except OutcomeUnknown:
                return None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]
        self.assertEqual(1, sum(value is not None for value in results))
        self.assertEqual(1, AccessAuditLog.objects.count())
        self.assertEqual(["APPLIED"], self.ledger_status())

    def test_concurrent_execution_of_one_claim_has_one_winner(self):
        bundle = self.bundle()
        request_id = self.executor.claim(bundle, self.trust, now=self.now)
        barrier = Barrier(2)

        def run():
            try:
                executor = IsolatedProtectedExecutor()
                barrier.wait(timeout=10)
                return executor.execute(request_id, self.trust, now=self.now)
            except OutcomeUnknown:
                return None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]
        self.assertEqual(1, sum(value is not None for value in results))
        self.assertEqual(1, AccessAuditLog.objects.count())

    def test_reconcile_refuses_unknown_or_mismatched_request(self):
        bundle = self.bundle()
        self.run_bundle(bundle)
        with self.assertRaises(ProtectedRequestRefused):
            self.executor.reconcile(bundle["request"]["request_id"], "0" * 64)
        with self.assertRaises(ProtectedRequestRefused):
            self.executor.reconcile("0" * 64, digest(bundle["request"]))

    def test_missing_or_misplaced_catalogue_rolls_back(self):
        Permission.objects.filter(pk=self.permissions[0].pk).update(module_name="unreviewed")
        with self.assertRaises(OutcomeUnknown):
            self.run_bundle(self.bundle())
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())

    def test_alias_collision_refuses_provision(self):
        Role.objects.create(role_name="technical-super-admin")
        with self.assertRaises(OutcomeUnknown):
            self.run_bundle(self.bundle())
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())

    def test_bootstrap_refuses_inactive_target(self):
        self.provision()
        Account.objects.filter(pk=self.target.pk).update(is_active=False)
        with self.assertRaises(OutcomeUnknown):
            self.run_bundle(self.bundle(self.target.pk))
        self.assertFalse(AccountRole.objects.filter(role__role_name="Technical Super Admin").exists())

    def test_bootstrap_refuses_target_without_school_admin(self):
        self.provision()
        AccountRole.objects.filter(account=self.target).delete()
        with self.assertRaises(OutcomeUnknown):
            self.run_bundle(self.bundle(self.target.pk))

    def test_bootstrap_refuses_existing_governance_override(self):
        self.provision()
        AccountPermission.objects.create(account=self.target, permission=self.permissions[0], effect="Deny")
        with self.assertRaises(OutcomeUnknown):
            self.run_bundle(self.bundle(self.target.pk))

    def test_bootstrap_preserves_unrelated_operational_role(self):
        self.provision()
        instructor = Role.objects.create(role_name="Instructor")
        AccountRole.objects.create(account=self.target, role=instructor)
        self.run_bundle(self.bundle(self.target.pk))
        self.assertTrue(AccountRole.objects.filter(account=self.target, role=instructor).exists())

    def test_inactive_role_and_service_revoke_fresh_authority(self):
        self.provision()
        self.run_bundle(self.bundle(self.target.pk))
        self.service.is_active = False
        self.service.save(update_fields=["is_active"])
        self.assertFalse(has_technical_authority(self.target, CORE_PERMISSIONS[0]))

    def test_evaluation_error_fails_closed(self):
        with patch("apps.access_control.technical_admin.AccountRole.objects") as manager:
            manager.using.side_effect = RuntimeError("synthetic DB outage")
            self.assertFalse(has_technical_authority(self.target, CORE_PERMISSIONS[0]))
