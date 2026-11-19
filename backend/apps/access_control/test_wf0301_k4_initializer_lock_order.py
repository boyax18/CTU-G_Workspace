"""WF-03.01 K-4 / K-6 (owner-authorized Option A, recorded under R-1): the legacy initializers lock the service rows first.

Run: python manage.py test apps.access_control.test_wf0301_k4_initializer_lock_order --settings=config.test_settings --noinput
Disposable MySQL ONLY. P1 (_apply_phase_one), P2 (_apply_phase_two) and WF-02.05 (run) locked the Admin role and the
actor's account BEFORE the service rows, while every path corrected by R-1 (the P3B/P3D/P4 snapshot, including the
read-only compensation previews, and framework_roles.configure_role) and role_management.lock_state lock the service
rows FIRST. The initializers hold an advisory lock, but the role procedures and the previews do not take it, so:
  K-4a  P2 rerun / WF-02.05 (incl. verify)  vs a Django-Superuser role change   (Admin role <-> service rows)
  K-4b  P1 rerun                             vs a role change on the P1 actor    (Admin role <-> actor account)
  K-6   P2 rerun / WF-02.05 verify           vs the P3D or P4 compensation preview (created by the R-1 snapshot change)
Each race pauses the initializer inside that window and requires serialization with no MySQL 1213/1205 anywhere in
the exception chain (P4's preview and WF-02.05 wrap errors as refusals). The fresh-database tests show what the empty
service table means for the prelude: it locks nothing there, and every competing protected path then refuses or waits
while holding nothing. Bounded waits/joins, a test-only 15 s session lock-wait timeout, closed connections.
"""

import threading
import time
from contextlib import contextmanager
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection, connections, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    provision_school_accounts_local_dev as s3,
    release_registration_review_local_dev_p4 as p4,
)
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.role_management import RoleChangeConflict, RoleChangeUnavailable
from apps.access_control.technical_admin import has_technical_authority
from apps.accounts.account_status import status_epoch

from . import test_wf0301_d85_p3b_compatibility as d85  # module only: its TestCase is not collected here

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("K-4 lock-order tests require the disposable MySQL test settings.")

LOCK_WAIT_SECONDS = 15   # test-only, session scope
WAIT = 30
JOIN = 60
BLOCKED = 1.5
NOTHING = ([], [], [])
SCHOOL_PHASES = ("metadata", "bindings", "activate")
S3_ACTIONS = tuple(s3.EVENTS.values())


def database_error_in_chain(value):
    """A DatabaseError anywhere in the exception chain (callers may wrap it as a refusal)."""
    seen = 0
    while isinstance(value, BaseException) and seen < 10:
        if isinstance(value, DatabaseError):
            return value
        value = value.__cause__ or value.__context__
        seen += 1
    return None


class K4InitializerLockOrderTests(TransactionTestCase):
    setUp = d85.D85CompatibilityTests.setUp
    tearDown = d85.D85CompatibilityTests.tearDown
    account = d85.D85CompatibilityTests.account
    scope = d85.D85CompatibilityTests.scope
    release = d85.D85CompatibilityTests.release
    p4 = d85.D85CompatibilityTests.p4
    preview = d85.D85CompatibilityTests.preview
    configure = d85.D85CompatibilityTests.configure
    governed = d85.D85CompatibilityTests.governed
    governance_state = d85.D85CompatibilityTests.governance_state
    everything = d85.D85CompatibilityTests.everything
    refused = d85.D85CompatibilityTests.refused

    # -- the three initializers and the P4 preview, called as the commands call them --------------------
    def p1_apply(self):
        return p1._apply_phase_one(actor_account_id=self.actor.pk, confirmation=p1.TEST_CONFIRM)

    def p2_apply(self):
        return p2._apply_phase_two(actor_account_id=self.actor.pk, confirmation=p2.TEST_CONFIRM)

    def s3_verify(self):
        return s3.run(phase="verify", actor_account_id=self.actor.pk)

    def p4_preview(self, scope):
        return p4._preview("compensate", self.actor.pk, scope, None)

    # -- concurrency harness --------------------------------------------------------------------------
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
    def pause(module, name, locked, go, *, before=False):
        """Pause the FIRST call of module.name, after it returns (its locks held) or before it runs."""
        original = getattr(module, name)
        state = {"first": True}

        def paused(*args, **kwargs):
            first, state["first"] = state["first"], False
            if first and before:
                locked.set()
                go.wait(WAIT)
            value = original(*args, **kwargs)
            if first and not before:
                locked.set()
                go.wait(WAIT)
            return value
        return patch.object(module, name, paused)

    def race(self, initializer_fn, other_fn, *, at=(p1, "_actor"), before=False, other_waits=True):
        """Hold the initializer inside its former Admin-role-first window, start the other operation, release."""
        locked, go, results = threading.Event(), threading.Event(), {}
        with self.pause(*at, locked, go, before=before):
            first = self.worker(initializer_fn, results, "initializer")
            self.assertTrue(locked.wait(WAIT), "the initializer did not reach the pause point")
            second = self.worker(other_fn, results, "other")
            if other_waits:
                time.sleep(BLOCKED)
                self.assertTrue(second.is_alive(), "the other operation must wait for a lock the initializer holds")
            else:
                second.join(JOIN)
                self.assertFalse(second.is_alive(), "the other operation must not wait here")
            go.set()
            first.join(JOIN)
            second.join(JOIN)
        self.assertFalse(first.is_alive() or second.is_alive(), "a transaction is still waiting")
        for key, value in results.items():
            error = database_error_in_chain(value)
            self.assertIsNone(error, f"{key}: lock-order deadlock or lock-wait timeout: {error!r} (raised as {value!r})")
        return results

    def receipts(self, *actions):
        return list(AccessAuditLog.objects.filter(action__in=actions).order_by("pk").values())

    def assert_roles(self, account, *names):
        self.assertEqual(set(AccountRole.objects.filter(account=account).values_list("role__role_name", flat=True)), set(names))

    @contextmanager
    def captured_locks(self):
        with CaptureQueriesContext(connection) as captured:
            yield captured

    def first_locking_table(self, captured):
        locking = [q["sql"] for q in captured.captured_queries if "FOR UPDATE" in q["sql"].upper()]
        self.assertTrue(locking)
        return locking[0]

    # -- lock order ---------------------------------------------------------------------------------------
    def test_each_initializer_locks_the_service_rows_first(self):
        self.release(*SCHOOL_PHASES)
        services = f"FROM `{Service._meta.db_table}`"
        for label, call, refusal in (("P1 rerun", self.p1_apply, p1.MetadataRefused),
                                     ("P2 rerun", self.p2_apply, p2.InactiveBindingRefused),
                                     ("WF-02.05 verify", self.s3_verify, None)):
            with self.subTest(label), self.captured_locks() as captured:
                if refusal is None:
                    self.assertEqual(call(), "VERIFIED")
                else:
                    with self.assertRaises(refusal):
                        call()
            self.assertIn(services, self.first_locking_table(captured), f"{label}: first locking read")

    # -- K-4a: initializer vs Django-Superuser role change ------------------------------------------------
    def test_k4a_school_account_verify_and_a_technical_super_admin_grant_serialize(self):
        self.release(*SCHOOL_PHASES)
        target = self.account("0040101", "Instructor")
        AccountPermission.objects.create(account=self.student, effect="Deny",
                                         permission=Permission.objects.get(permission_code=sorted(d85.REGISTRATION)[0]))
        denies, school = list(AccountPermission.objects.order_by("pk").values()), self.receipts(*S3_ACTIONS)
        results = self.race(self.s3_verify, lambda: self.configure("grant-technical-super-admin", target))
        self.assertEqual(results["initializer"], "VERIFIED")  # read-only verification, unchanged result
        self.assertEqual(results["other"], {"account_id": target.pk, "operation": "grant-technical-super-admin"})
        permissions, bindings, receipts = self.governance_state()
        self.assertEqual((len(permissions), len(bindings), len(receipts)), (6, 6, 13))
        self.assertTrue(all(has_technical_authority(target, code) for code in d85.GOVERNANCE))
        self.assertGreater(status_epoch(target.pk), 0)
        self.assertEqual(list(AccountPermission.objects.order_by("pk").values()), denies)
        self.assertEqual(self.receipts(*S3_ACTIONS), school)

    def test_k4a_school_account_verify_and_a_technical_super_admin_revocation_serialize(self):
        first = self.governed(*SCHOOL_PHASES)
        second = self.account("0040102", "Instructor")
        self.configure("grant-technical-super-admin", second)
        profile, epoch, school = self.governance_state(), status_epoch(second.pk), self.receipts(*S3_ACTIONS)
        results = self.race(self.s3_verify, lambda: self.configure("revoke-technical-super-admin", second))
        self.assertEqual(results["initializer"], "VERIFIED")
        self.assertEqual(results["other"], {"account_id": second.pk, "operation": "revoke-technical-super-admin"})
        self.assert_roles(second, "Instructor", "Admin")
        self.assertGreater(status_epoch(second.pk), epoch)
        self.assertEqual(self.governance_state(), profile)
        self.assertEqual(self.receipts(*S3_ACTIONS), school)
        self.assertTrue(all(has_technical_authority(first, code) for code in d85.GOVERNANCE))
        self.refused(self.scope(first, second), d85.EFFECTIVE)  # D-85 compensation refusal unchanged

    def sequential_refusal(self, call, refusal):
        """The initializer's own refusal when it runs alone (the concurrent run must refuse identically)."""
        with self.assertRaises(refusal) as caught:
            call()
        return str(caught.exception)

    def test_k4a_a_p2_rerun_and_a_technical_super_admin_grant_serialize(self):
        self.release()
        target = self.account("0040103", "Instructor")
        expected = self.sequential_refusal(self.p2_apply, p2.InactiveBindingRefused)
        bindings = list(RolePermission.objects.order_by("pk").values())
        results = self.race(self.p2_apply, lambda: self.configure("grant-technical-super-admin", target))
        self.assertIsInstance(results["initializer"], p2.InactiveBindingRefused)
        self.assertEqual(str(results["initializer"]), expected)  # P2's original refusal, unchanged
        self.assertEqual(results["other"], {"account_id": target.pk, "operation": "grant-technical-super-admin"})
        self.assertEqual(list(RolePermission.objects.exclude(role__role_name=d85.TSA).order_by("pk").values()), bindings)

    # -- K-4b: P1 rerun vs a role change on the P1 actor ----------------------------------------------------
    def test_k4b_a_p1_rerun_and_a_role_change_on_the_p1_actor_serialize(self):
        self.release()
        expected = self.sequential_refusal(self.p1_apply, p1.MetadataRefused)
        # Pause P1 holding the Admin role (and, after the fix, the service rows) but BEFORE it locks the actor.
        results = self.race(self.p1_apply, lambda: self.configure("revoke-school-admin", self.actor), before=True)
        self.assertIsInstance(results["initializer"], p1.MetadataRefused)
        self.assertEqual(str(results["initializer"]), expected)  # P1's original refusal, unchanged
        self.assertIsInstance(results["other"], RoleChangeConflict)
        self.assertEqual(results["other"].reason, "protected_account")  # legacy Admin-only operator (D-94)
        self.assert_roles(self.actor, "Admin")
        self.assertEqual(status_epoch(self.actor.pk), 0)

    # -- K-6: initializer vs the read-only compensation previews (R-1 follow-up) ---------------------------
    def test_k6_school_account_verify_and_the_p3d_preview_serialize(self):
        self.release(*SCHOOL_PHASES)
        school = self.receipts(*S3_ACTIONS)
        results = self.race(self.s3_verify, lambda: self.preview(self.scope()))
        self.assertEqual(results["initializer"], "VERIFIED")
        self.assertEqual(results["other"], 1)
        self.assertEqual(self.receipts(*S3_ACTIONS), school)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)

    def test_k6_a_p2_rerun_and_the_p4_preview_serialize(self):
        self.release()
        expected = self.sequential_refusal(self.p2_apply, p2.InactiveBindingRefused)
        results = self.race(self.p2_apply, lambda: self.p4_preview(self.scope()))
        self.assertIsInstance(results["initializer"], p2.InactiveBindingRefused)
        self.assertEqual(str(results["initializer"]), expected)
        self.assertIsNone(results["other"])  # P4's compensation preview is available and writes nothing
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertFalse(AccessAuditLog.objects.filter(action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)).exists())

    # -- fresh database: the prelude locks nothing while the service table is empty --------------------------
    def test_fresh_p1_with_empty_services_lets_a_grant_refuse_without_waiting(self):
        target = self.account("0040104", "Instructor")
        self.assertFalse(Service.objects.exists())
        results = self.race(self.p1_apply, lambda: self.configure("grant-technical-super-admin", target),
                            other_waits=False)  # nothing to wait for: no service rows exist yet
        self.assertEqual(results["initializer"], "CREATED")
        self.assertIsInstance(results["other"], RoleChangeUnavailable)  # services absent: refused before any write
        self.assertFalse(Role.objects.filter(role_name=d85.TSA).exists())
        self.assertEqual(self.governance_state(), NOTHING)
        self.assert_roles(target, "Instructor")

    def test_fresh_p1_with_uncommitted_services_makes_a_grant_and_a_preview_wait_holding_nothing(self):
        target = self.account("0040105", "Instructor")
        for label, other, expected in (
                ("grant", lambda: self.configure("grant-technical-super-admin", target), RoleChangeUnavailable),
                ("P3D preview", lambda: self.preview(self.scope()), p3b.ActivationExerciseRefused)):
            with self.subTest(label):
                AccessAuditLog.objects.all().delete()  # receipts reference permissions and services (PROTECT)
                Permission.objects.all().delete()
                Service.objects.all().delete()
                # Pause P1 right after its first service INSERT (uncommitted) and its receipt.
                results = self.race(self.p1_apply, other, at=(p1, "record_access_audit_receipt"))
                self.assertEqual(results["initializer"], "CREATED")
                self.assertIsInstance(results["other"], expected)  # the services are new and inactive
                self.assertEqual(Service.objects.count(), 2)
                self.assertFalse(Service.objects.filter(is_active=True).exists())
                self.assertEqual(self.governance_state(), NOTHING)

    def test_fresh_initializers_are_serialized_by_the_advisory_lock(self):
        locked, go, results = threading.Event(), threading.Event(), {}
        with self.pause(p1, "_actor", locked, go):
            first = self.worker(self.p1_apply, results, "p1")
            self.assertTrue(locked.wait(WAIT))
            for key, fn in (("p2", self.p2_apply),
                            ("s3", lambda: s3.run(phase="metadata", actor_account_id=self.actor.pk,
                                                  confirmation=s3.TEST_CONFIRM["metadata"], apply=True))):
                thread = self.worker(fn, results, key)
                thread.join(JOIN)
                self.assertFalse(thread.is_alive(), f"{key} must be refused immediately, not wait")
            go.set()
            first.join(JOIN)
        self.assertFalse(first.is_alive())
        self.assertEqual(results["p1"], "CREATED")
        self.assertIn("Another registration metadata operation is running", str(results["p2"]))
        self.assertIn("Another governance operation is running", str(results["s3"]))
        self.assertFalse(RolePermission.objects.exists())

    def test_fresh_bootstrap_produces_the_same_records_and_receipts(self):
        self.release(*SCHOOL_PHASES)
        self.assertEqual(Service.objects.filter(is_active=True).count(), 2)
        self.assertEqual(set(Permission.objects.values_list("permission_code", flat=True)),
                         set(p1.PERMISSION_CODES) | set(s3.CODES))
        self.assertEqual(RolePermission.objects.filter(role__role_name="Admin", is_active=True).count(), 6)
        counts = {action: AccessAuditLog.objects.filter(action=action).count() for action in (
            p1.SERVICE_EVENT, p1.PERMISSION_EVENT, p2.EVENT, p3b.SERVICE_ACTIVATE, p3b.BINDING_ACTIVATE, *S3_ACTIONS)}
        self.assertEqual(counts, {p1.SERVICE_EVENT: 2, p1.PERMISSION_EVENT: 3, p2.EVENT: 3, p3b.SERVICE_ACTIVATE: 2,
                                  p3b.BINDING_ACTIVATE: 3, **{action: 3 for action in S3_ACTIONS}})
        self.assertEqual(self.s3_verify(), "VERIFIED")
        with self.assertRaisesRegex(p1.MetadataRefused, "Existing grants"):
            self.p1_apply()
        with self.assertRaises(p2.InactiveBindingRefused):
            self.p2_apply()
        self.assertEqual({a: AccessAuditLog.objects.filter(action=a).count() for a in counts}, counts)  # reruns write nothing
