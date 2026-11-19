"""WF-03.01 R-1 (Option A, owner-authorized): the protected P3B snapshot locks the shared service rows first.

Run: python manage.py test apps.access_control.test_wf0301_r1_lock_order --settings=config.test_settings --noinput
Disposable MySQL ONLY. Before the correction, p3b._snapshot (used by P3B, P3D and P4) locked the Admin role,
the actor's account, every Admin assignment and the account overrides BEFORE the service rows, while the
Django-Superuser procedure and the Technical Super Admin assignment path (role_management.lock_state) lock the
service rows FIRST and those rows afterwards. A role change and a P3D/P4 transaction could therefore wait on
each other (K-1 Admin role, K-2 actor account, K-3 Admin assignments) and deadlock. Each test pauses the
snapshot exactly inside that former window, starts the role change, and requires the two operations to
serialize on the service rows: no database error, consistent outcomes, nothing partial.

Safety: every wait and join is bounded, both worker connections use a test-only 15-second
innodb_lock_wait_timeout (session scope), every worker closes its connections, and the environment check
requires InnoDB deadlock detection. Nothing here touches ctug_workspace.
"""

import threading
import time
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection, connections, transaction
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.access_control import framework_roles
from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_metadata_local_dev as p1,
)
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, Service
from apps.access_control.role_management import RoleChangeDenied, RoleChangeUnavailable
from apps.access_control.technical_admin import has_technical_authority
from apps.accounts.account_status import status_epoch
from apps.accounts.models import Account

from . import test_wf0301_d85_p3b_compatibility as d85  # module only: its TestCase is not collected here

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("R-1 lock-order tests require the disposable MySQL test settings.")

LOCK_WAIT_SECONDS = 15   # test-only, session scope; the server default stays untouched
WAIT = 30                # bound for every Event.wait
JOIN = 60                # bound for every Thread.join
BLOCKED = 1.5            # time allowed for the role change to reach its first contended lock
NOTHING = ([], [], [])   # governance permissions, Technical Super Admin bindings, framework.* receipts


class R1LockOrderTests(TransactionTestCase):
    # The D-85 harness (real P1, P2, P4, P3D and Django-Superuser code paths), borrowed method by method.
    setUp = d85.D85CompatibilityTests.setUp
    tearDown = d85.D85CompatibilityTests.tearDown
    account = d85.D85CompatibilityTests.account
    scope = d85.D85CompatibilityTests.scope
    release = d85.D85CompatibilityTests.release
    p4 = d85.D85CompatibilityTests.p4
    preview = d85.D85CompatibilityTests.preview
    configure = d85.D85CompatibilityTests.configure
    governed = d85.D85CompatibilityTests.governed
    everything = d85.D85CompatibilityTests.everything
    governance_state = d85.D85CompatibilityTests.governance_state
    refused = d85.D85CompatibilityTests.refused

    # -- concurrency harness -------------------------------------------------------------------------
    @staticmethod
    def worker(fn, results, key):
        def target():
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", [LOCK_WAIT_SECONDS])
                results[key] = fn()
            except Exception as exc:  # recorded and asserted by the caller
                results[key] = exc
            finally:
                connections.close_all()
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread

    @staticmethod
    def pause_after(module, name, locked, go):
        """Pause the FIRST call of module.name right after it returns (its row locks are then held)."""
        original = getattr(module, name)
        state = {"first": True}

        def paused(*args, **kwargs):
            value = original(*args, **kwargs)
            if state["first"]:
                state["first"] = False
                locked.set()
                go.wait(WAIT)
            return value
        return patch.object(module, name, paused)

    def race(self, snapshot_fn, role_fn, *, pause=(p1, "_actor")):
        """Hold the snapshot inside the former inversion window, start the role change, then release."""
        locked, go, results = threading.Event(), threading.Event(), {}
        with self.pause_after(*pause, locked, go):
            snap = self.worker(snapshot_fn, results, "snapshot")
            self.assertTrue(locked.wait(WAIT), "the snapshot did not reach the pause point")
            role = self.worker(role_fn, results, "role")
            time.sleep(BLOCKED)
            self.assertTrue(role.is_alive(), "the role change must wait for a lock the snapshot holds")
            go.set()
            snap.join(JOIN)
            role.join(JOIN)
        self.assertFalse(snap.is_alive() or role.is_alive(), "a transaction is still waiting")
        for key, value in results.items():
            self.assertNotIsInstance(value, DatabaseError, f"{key}: lock-order deadlock or lock-wait timeout: {value!r}")
        return results

    def assert_unchanged_roles(self, account, *names):
        self.assertEqual(set(AccountRole.objects.filter(account=account).values_list("role__role_name", flat=True)), set(names))

    # -- environment and lock order ------------------------------------------------------------------
    def test_environment_detects_deadlocks_and_bounds_lock_waits(self):
        with connection.cursor() as cursor:
            cursor.execute("SHOW VARIABLES LIKE 'innodb_deadlock_detect'")
            self.assertEqual(cursor.fetchone()[1], "ON")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", [LOCK_WAIT_SECONDS])
            cursor.execute("SELECT @@SESSION.innodb_lock_wait_timeout")
            self.assertEqual(int(cursor.fetchone()[0]), LOCK_WAIT_SECONDS)

    def test_the_snapshot_locks_the_service_rows_before_any_other_row(self):
        self.release()
        tables = (Service._meta.db_table, Role._meta.db_table)
        with transaction.atomic(), CaptureQueriesContext(connection) as captured:
            p3b._snapshot(actor_id=self.actor.pk, expected_ids=p3b._expected_ids(self.scope()), active=True)
            transaction.set_rollback(True)
        locking = [q["sql"] for q in captured.captured_queries if "FOR UPDATE" in q["sql"].upper()]
        self.assertTrue(locking)
        self.assertIn(f"`{tables[0]}`", locking[0], "the first locking read must be on the service rows")
        first_role = next(i for i, sql in enumerate(locking) if f"FROM `{tables[1]}`" in sql)
        self.assertGreater(first_role, 0, "the Admin role must be locked after the service rows")

    def test_the_superuser_procedure_locks_the_service_rows_before_the_operator_account(self):
        """K-5 (approved Option 1): the framework operator's account is locked only after the service rows,
        and taking the lock never stands in for authentication (a wrong password still refuses, nothing written)."""
        self.release()
        holder = self.account("0039108", "Instructor")
        tables = (Service._meta.db_table, Account._meta.db_table)
        with CaptureQueriesContext(connection) as captured:
            self.configure("grant-school-admin", holder)
        locking = [q["sql"] for q in captured.captured_queries if "FOR UPDATE" in q["sql"].upper()]
        self.assertIn(f"FROM `{tables[0]}`", locking[0], "the first locking read must be on the service rows")
        operator = next(i for i, sql in enumerate(locking) if f"FROM `{tables[1]}`" in sql and "`is_superuser`" in sql)
        self.assertGreater(operator, 0, "the operator account must be locked after the service rows")
        other = self.account("0039109", "Instructor")
        before = self.everything()
        with override_settings(**d85.GATES), self.assertRaisesRegex(RoleChangeDenied, "Operator authentication failed"):
            framework_roles.configure_role(
                operation="grant-school-admin", operator_school_id=d85.ROOT, operator_password="wrong-password",
                target_id=other.pk, confirmation=framework_roles.confirmation_for("grant-school-admin", other.pk))
        self.assertEqual(self.everything(), before)

    # -- K-1: Admin role row ----------------------------------------------------------------------------
    def test_k1_a_technical_super_admin_grant_and_p4_compensation_serialize(self):
        self.release()
        target = self.account("0039101", "Instructor")  # no Admin: the grant meets the Admin role via role_row(ADMIN)
        results = self.race(lambda: self.p4("compensate", self.scope()),
                            lambda: self.configure("grant-technical-super-admin", target))
        self.assertEqual(results["snapshot"], "LOCAL_COMPENSATED")
        self.assertIsInstance(results["role"], RoleChangeUnavailable)  # then finds the services inactive
        self.assertFalse(Role.objects.filter(role_name=d85.TSA).exists())
        self.assertEqual(self.governance_state(), NOTHING)
        self.assert_unchanged_roles(target, "Instructor")
        self.assertEqual(status_epoch(target.pk), 0)  # no successful change, no session invalidation

    # -- K-2: the P3B/P4 actor's account row --------------------------------------------------------
    def test_k2_a_role_change_on_the_p4_actor_and_compensation_serialize(self):
        self.release()
        results = self.race(lambda: self.p4("compensate", self.scope()),
                            lambda: self.configure("revoke-school-admin", self.actor))
        self.assertEqual(results["snapshot"], "LOCAL_COMPENSATED")
        self.assertIsInstance(results["role"], RoleChangeUnavailable)
        self.assert_unchanged_roles(self.actor, "Admin")
        self.assertFalse(AccessAuditLog.objects.filter(action=framework_roles.FRAMEWORK_REVOKE_ACTION).exists())
        self.assertEqual(status_epoch(self.actor.pk), 0)

    # -- K-3: the Admin role assignments ----------------------------------------------------------------
    def test_k3_a_grant_to_another_school_admin_and_compensation_serialize(self):
        self.release()
        holder = self.account("0039103", "Instructor")
        self.configure("grant-school-admin", holder)
        epoch = status_epoch(holder.pk)
        results = self.race(lambda: self.p4("compensate", self.scope(holder)),
                            lambda: self.configure("grant-technical-super-admin", holder),
                            pause=(p3b, "_eligible_admin_ids"))
        self.assertEqual(results["snapshot"], "LOCAL_COMPENSATED")
        self.assertIsInstance(results["role"], RoleChangeUnavailable)
        self.assert_unchanged_roles(holder, "Instructor", "Admin")
        self.assertEqual(self.governance_state(), NOTHING)
        self.assertEqual(status_epoch(holder.pk), epoch)

    # -- revocation against compensation while the governance profile exists -------------------------
    def test_a_technical_super_admin_revocation_and_compensation_serialize_and_compensation_still_refuses(self):
        first = self.governed()
        second = self.account("0039104", "Instructor")
        self.configure("grant-technical-super-admin", second)
        profile, epoch = self.governance_state(), status_epoch(second.pk)
        results = self.race(lambda: self.p4("compensate", self.scope(first, second)),
                            lambda: self.configure("revoke-technical-super-admin", second))
        self.assertIsInstance(results["snapshot"], p3b.ActivationExerciseRefused)
        self.assertIn(d85.EFFECTIVE, str(results["snapshot"]))  # D-85 unchanged
        self.assertEqual(results["role"], {"account_id": second.pk, "operation": "revoke-technical-super-admin"})
        self.assert_unchanged_roles(second, "Instructor", "Admin")  # Technical Super Admin removed, Admin kept
        self.assertGreater(status_epoch(second.pk), epoch)  # session invalidation after the successful change
        self.assertEqual(self.governance_state(), profile)  # role, permissions, bindings and receipts intact
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertFalse(AccessAuditLog.objects.filter(action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)).exists())

    # -- P3D preview against a grant; D-85 refusal afterwards -----------------------------------------
    def test_a_p3d_preview_and_a_grant_serialize_and_the_grant_then_ends_sessions(self):
        self.release()
        target = self.account("0039105", "Instructor")
        before = self.everything()
        results = self.race(lambda: self.preview(self.scope()),
                            lambda: self.configure("grant-technical-super-admin", target))
        self.assertEqual(results["snapshot"], 1)  # the read-only preview completes unchanged
        self.assertEqual(results["role"], {"account_id": target.pk, "operation": "grant-technical-super-admin"})
        self.assertNotEqual(self.everything(), before)
        permissions, bindings, receipts = self.governance_state()
        self.assertEqual((len(permissions), len(bindings), len(receipts)), (6, 6, 13))  # 1 + 6 + 6, complete
        self.assertTrue(all(has_technical_authority(target, code) for code in d85.GOVERNANCE))
        self.assertGreater(status_epoch(target.pk), 0)
        self.refused(self.scope(target), d85.EFFECTIVE)  # compensation refused while the profile exists

    # -- rollback of a failed grant that waited behind the snapshot ------------------------------------
    def test_a_failed_grant_that_waited_rolls_back_completely(self):
        self.release()
        target = self.account("0039106", "Instructor")
        before = self.everything()
        original = framework_roles.record_access_audit_receipt

        def failing(**kwargs):
            if kwargs.get("action") == framework_roles.BINDING_CREATE:
                raise RuntimeError("injected audit failure")
            return original(**kwargs)

        with patch.object(framework_roles, "record_access_audit_receipt", failing):
            results = self.race(lambda: self.preview(self.scope()),
                                lambda: self.configure("grant-technical-super-admin", target))
        self.assertEqual(results["snapshot"], 1)
        self.assertIsInstance(results["role"], RuntimeError)
        self.assertEqual(self.everything(), before)  # no role, permission, binding, assignment or receipt left
        self.assertEqual(self.governance_state(), NOTHING)
        self.assertEqual(status_epoch(target.pk), 0)

    # -- account-specific Deny records are never touched -----------------------------------------------
    def test_deny_records_are_unchanged_while_a_grant_and_a_compensation_serialize(self):
        self.release()
        target = self.account("0039107", "Instructor")
        AccountPermission.objects.create(account=self.student, effect="Deny",
                                         permission=Permission.objects.get(permission_code=sorted(d85.REGISTRATION)[0]))
        denies = list(AccountPermission.objects.order_by("pk").values())
        results = self.race(lambda: self.p4("compensate", self.scope()),
                            lambda: self.configure("grant-technical-super-admin", target))
        self.assertIsInstance(results["snapshot"], p3b.ActivationExerciseRefused)
        self.assertIn("Account-level overrides", str(results["snapshot"]))  # existing safeguard unchanged
        self.assertEqual(results["role"], {"account_id": target.pk, "operation": "grant-technical-super-admin"})
        self.assertEqual(list(AccountPermission.objects.order_by("pk").values()), denies)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
