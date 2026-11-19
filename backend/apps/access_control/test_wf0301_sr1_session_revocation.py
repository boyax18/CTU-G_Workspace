"""WF-03.01 SR-1 Stage A (owner-authorized 19 Nov 2026): persistent session revocation that receipts cannot undo.

Run: python manage.py test apps.access_control.test_wf0301_sr1_session_revocation --settings=config.test_settings --noinput
Disposable MySQL ONLY (IsolatedMySQLRunner: a fresh random test_ctug_registration_<hex> database, re-verified
below before any trigger, grant or migration). Temporary MySQL accounts are random, granted only on disposable
databases and dropped in cleanup; their passwords exist only in memory. The test-only trigger is created only in
the disposable database and dropped in cleanup. Nothing here touches ctug_workspace, backend/.env, real grants or
real triggers.

What each group shows, and its trust boundary:
- Counter: every approved session-ending event advances Account.session_revocation_version exactly once, in the
  same transaction; deleting, changing or forging receipts never changes session validity; failures roll the
  change, the receipt and the counter back together; concurrent advances never lose an increment.
- Persistence: application-level guards (stale full save, update_fields, QuerySet.update/bulk_update) and their
  limit (the base manager, raw SQL and privileged users are not bound by them).
- Trigger: a non-decrease trigger refuses lower values for EVERY database user, including the proposed restricted
  runtime account, which also cannot drop or replace it. A privileged administrator can drop it (asserted).
- Contract: the v2 hash, the one-time invalidation of sessions bound to either earlier hash, the login race,
  deletion/recreation, session-row restore, CSRF, idle/absolute limits, Deny, lock order, D-83 bootstrap.
- SR-1a: polling the public CSRF endpoint refreshes a revoked session's activity without verifying it (confirmed,
  documented, NOT changed: the middleware change needs separate owner approval). After Stage A it cannot
  authenticate, and the 8-hour absolute limit still ends it.
- Migration: 0006 adds only the counter (BIGINT UNSIGNED NOT NULL DEFAULT 0) on a fresh database and on an
  upgraded database with existing rows, and reverses cleanly.
"""

import inspect
import threading
import time
from unittest import mock

from django.conf import settings
from django.contrib.auth import HASH_SESSION_KEY
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils.crypto import salted_hmac
from rest_framework.test import APIClient

from apps.access_control import framework_roles, role_assignment
from apps.access_control.audit import record_access_audit
from apps.access_control.executor import provisioning
from apps.access_control.executor import role_assignment as executor_role_assignment
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission
from apps.access_control.services import get_effective_permissions, has_permission
from apps.accounts import account_status, password_reset, recovery_mail, session_auth, session_revocation, session_timeout
from apps.accounts.account_status import activate_account, status_epoch, suspend_account
from apps.accounts.models import SESSION_HASH_SALT, Account, SessionRevocationWriteRefused
from apps.accounts.test_password_reset import EMAIL, NEW, OLD, RECOVERY_SETTINGS, codes, make_account
from apps.accounts.test_wf0205_account_status import GATE as STATUS_GATE, World

from .test_wf0301_d85_p3b_compatibility import GATES  # constants only: its TestCase is not collected here
from .test_wf0301_r2_audit_integrity import DENIED, JOIN, PASSWORD, Harness

TRIGGER = "ctug_sr1_test_session_revocation_no_decrease"
TRIGGER_SQL = (f"CREATE TRIGGER `{TRIGGER}` BEFORE UPDATE ON `accounts` FOR EACH ROW BEGIN "
               "IF NEW.session_revocation_version < OLD.session_revocation_version THEN "
               "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'session_revocation_version cannot decrease'; END IF; END")
SIGNALLED = 1644  # ER_SIGNAL_EXCEPTION: the trigger refused the statement
LOCK_WAIT_SECONDS = 15  # test-only, session scope; the server default stays untouched
WAIT = 30
BLOCKED = 1.5
IDLE, ABSOLUTE = 30 * 60, 8 * 60 * 60
REGISTRATION_READ = "accounts.registration_requests.read"
V1_SALT = "ctug.workspace.accounts.session_status_epoch.v1"  # the retired receipt-epoch contract


def counter(account):
    return Account._base_manager.values_list("session_revocation_version", flat=True).get(pk=account.pk)


def verify_disposable(test):
    """Positively re-verify the isolated target before any trigger, grant, privilege or migration operation."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        current = cursor.fetchone()[0]
    test.assertEqual(current, settings.REGISTRATION_TEST_DATABASE)
    test.assertRegex(current, r"\Atest_ctug_registration_[0-9a-f]{16}\Z")
    test.assertNotEqual(current, "ctug_workspace")
    test.assertEqual(connection.settings_dict["NAME"], current)
    return current


class Base(Harness):
    def setUp(self):
        super().setUp()
        verify_disposable(self)

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

    def session_key(self, client):
        return client.cookies[settings.SESSION_COOKIE_NAME].value

    def receipt(self, holder, action):
        return AccessAuditLog.objects.filter(target_account=holder, action=action).order_by("-pk").first()


class RevocationCounterTests(Base):
    def test_role_grant_and_revocation_end_earlier_sessions_advance_once_and_re_adding_revives_none(self):
        self.release()
        holder = self.password_account("0042901", "Instructor")
        self.assertEqual(counter(holder), 0)
        before_grant = self.signed_in_client(holder)
        self.configure("grant-school-admin", holder)
        self.assertEqual(counter(holder), 1)
        self.assertFalse(self.authenticated(before_grant)[0])  # elevation needs a fresh sign-in (D-83)
        while_admin = self.signed_in_client(holder)
        unused_while_admin = self.signed_in_client(holder)
        ok, response = self.authenticated(while_admin)
        self.assertTrue(ok)
        self.assertEqual(response.json()["account"]["roles"], ["Admin", "Instructor"])
        self.assertIn(REGISTRATION_READ, response.json()["permissions"])

        self.configure("revoke-school-admin", holder)
        self.assertEqual(counter(holder), 2)
        self.assertFalse(self.authenticated(while_admin)[0])
        after = self.signed_in_client(holder)
        ok, response = self.authenticated(after)
        self.assertTrue(ok)
        self.assertEqual(response.json()["account"]["roles"], ["Instructor"])
        self.assertNotIn(REGISTRATION_READ, response.json()["permissions"])  # no stale permission (fail closed)
        self.assertFalse(has_permission(Account.objects.get(pk=holder.pk), REGISTRATION_READ))

        self.configure("grant-school-admin", holder)  # re-adding the removed role revives nothing
        self.assertEqual(counter(holder), 3)
        self.assertFalse(self.authenticated(unused_while_admin)[0])
        self.assertFalse(self.authenticated(after)[0])
        self.assertEqual((counter(self.actor), counter(self.root)), (0, 0))  # only the target advances

    def test_a_technical_super_admin_grant_and_revocation_advance_exactly_once_each(self):
        self.release()
        holder = self.password_account("0042902", "Instructor")
        second = self.password_account("0042903", "Instructor")
        before = self.signed_in_client(holder)
        self.configure("grant-technical-super-admin", holder)  # adds Admin AND Technical Super Admin: one advance
        self.assertEqual(counter(holder), 1)
        self.assertFalse(self.authenticated(before)[0])
        elevated = self.signed_in_client(holder)
        self.configure("grant-technical-super-admin", second)
        self.configure("revoke-technical-super-admin", holder)
        self.assertEqual((counter(holder), counter(second)), (2, 1))
        self.assertFalse(self.authenticated(elevated)[0])
        ok, response = self.authenticated(self.signed_in_client(holder))
        self.assertTrue(ok)
        self.assertEqual(response.json()["account"]["roles"], ["Admin", "Instructor"])

    def test_the_technical_super_admin_assignment_path_advances_once_per_change(self):
        self.release()
        tsa = self.password_account("0042904", "Instructor")
        self.configure("grant-technical-super-admin", tsa)
        target = self.password_account("0042905", "Instructor")
        old = self.signed_in_client(target)
        with override_settings(**GATES):
            role_assignment.assign_school_admin(actor=Account.objects.get(pk=tsa.pk), target_id=target.pk)
            self.assertEqual(counter(target), 1)
            self.assertFalse(self.authenticated(old)[0])
            middle = self.signed_in_client(target)
            role_assignment.revoke_school_admin(actor=Account.objects.get(pk=tsa.pk), target_id=target.pk)
        self.assertEqual(counter(target), 2)
        self.assertFalse(self.authenticated(middle)[0])
        self.assertEqual(counter(tsa), 1)  # the actor's own counter is untouched by changes to another account

    def test_receipt_deletion_modification_and_forgery_never_change_session_validity(self):
        self.release()
        holder = self.password_account("0042906", "Instructor")
        self.configure("grant-school-admin", holder)
        unused = {name: self.signed_in_client(holder) for name in ("action", "target", "id", "delete", "forge")}
        self.configure("revoke-school-admin", holder)
        current = self.signed_in_client(holder)  # valid, bound to the current counter
        self.assertTrue(self.authenticated(current)[0])
        revoke = self.receipt(holder, framework_roles.FRAMEWORK_REVOKE_ACTION)
        assign = self.receipt(holder, framework_roles.FRAMEWORK_ASSIGN_ACTION)
        table = AccessAuditLog._meta.db_table
        steps = (
            ("action", f"UPDATE `{table}` SET action='tampered.action' WHERE access_audit_log_id=%s", [revoke.pk]),
            ("target", f"UPDATE `{table}` SET action=%s, target_account_id=%s WHERE access_audit_log_id=%s",
             [framework_roles.FRAMEWORK_REVOKE_ACTION, self.actor.pk, revoke.pk]),
            ("id", f"UPDATE `{table}` SET target_account_id=%s, access_audit_log_id=%s WHERE access_audit_log_id=%s",
             [holder.pk, -revoke.pk, revoke.pk]),
            ("delete", f"DELETE FROM `{table}` WHERE access_audit_log_id=%s", [-revoke.pk]),
        )
        for name, sql, params in steps:  # privileged, test-only connection on the disposable database
            with self.subTest(tamper=name):
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                self.assertEqual(status_epoch(holder.pk), assign.pk)  # the diagnostic epoch moved BACKWARDS
                self.assertEqual(counter(holder), 2)
                self.assertFalse(self.authenticated(unused[name])[0], f"{name}: a revoked session was revived")
                self.assertTrue(self.authenticated(current)[0], f"{name}: tampering ended a valid session")
        with transaction.atomic():  # forged receipts: an apparently newer role change and an apparent re-grant
            for action in (framework_roles.FRAMEWORK_REVOKE_ACTION, framework_roles.FRAMEWORK_ASSIGN_ACTION,
                           account_status.SUSPEND_ACTION):
                record_access_audit(actor=self.root, target=holder, action=action, reason="correction")
        self.assertGreater(status_epoch(holder.pk), assign.pk)
        self.assertEqual(counter(holder), 2)
        self.assertFalse(self.authenticated(unused["forge"])[0])
        self.assertTrue(self.authenticated(current)[0])  # forged receipts neither revive nor end sessions

    def test_a_failure_after_the_advance_rolls_back_the_change_receipt_and_counter_together(self):
        self.release()
        holder = self.password_account("0042907", "Instructor")
        session = self.signed_in_client(holder)
        before = self.everything()
        real = session_revocation.advance
        seen = {}

        def advance_then_fail(account_id, **kwargs):
            real(account_id, **kwargs)
            seen["inside"] = Account._base_manager.get(pk=account_id).session_revocation_version
            raise RuntimeError("forced failure after the counter advanced")
        with mock.patch.object(session_revocation, "advance", side_effect=advance_then_fail):
            with self.assertRaises(RuntimeError):
                self.configure("grant-school-admin", holder)
        self.assertEqual(seen["inside"], 1)  # it had advanced inside the transaction ...
        self.assertEqual(counter(holder), 0)  # ... and rolled back with the role and the receipt
        self.assertEqual(self.everything(), before)
        self.assertTrue(self.authenticated(session)[0])  # nothing committed, so nothing ended

    def test_refused_changes_write_no_receipt_and_never_advance(self):
        self.release()
        holder = self.password_account("0042908", "Instructor")
        before = self.everything()
        with self.assertRaises(framework_roles.RoleChangeConflict):
            self.configure("revoke-school-admin", holder)  # nothing to revoke
        with self.assertRaises(framework_roles.RoleChangeConflict):
            self.configure("grant-school-admin", self.student)  # not an Instructor
        self.assertEqual(self.everything(), before)
        self.assertEqual((counter(holder), counter(self.student)), (0, 0))

    def test_advance_refuses_outside_a_transaction_and_for_a_missing_account(self):
        holder = self.password_account("0042909", "Instructor")
        with self.assertRaises(session_revocation.SessionRevocationUnavailable):
            session_revocation.advance(holder.pk)  # never opens or commits a transaction of its own
        for bad in (0, -1, 2_147_483_648, "1", None, True):
            with self.subTest(bad=bad), transaction.atomic(), self.assertRaises(session_revocation.SessionRevocationUnavailable):
                session_revocation.advance(bad)
        with transaction.atomic(), self.assertRaises(session_revocation.SessionRevocationUnavailable):
            session_revocation.advance(2_147_483_000)  # no such account: never creates one
        self.assertFalse(Account.objects.filter(pk=2_147_483_000).exists())
        self.assertEqual(counter(holder), 0)

    def test_concurrent_advances_never_lose_an_increment(self):
        holder = self.password_account("0042910", "Instructor")
        workers, barrier, results = 6, threading.Barrier(6, timeout=WAIT), {}

        def advance():
            barrier.wait()
            with transaction.atomic():
                session_revocation.advance(holder.pk)
            return "advanced"
        threads = [self.worker(advance, results, n) for n in range(workers)]
        for thread in threads:
            thread.join(JOIN)
        self.assertFalse(any(t.is_alive() for t in threads), "an advance is still waiting")
        self.assertEqual(list(results.values()), ["advanced"] * workers, results)
        self.assertEqual(counter(holder), workers)

    def test_a_role_change_waits_for_a_concurrent_password_reset_style_advance_and_both_count(self):
        """Password reset locks only the account row; the role change locks services first. Hold the reset-style
        lock, start the real role change, release: no deadlock, no lost increment."""
        self.release()
        holder = self.password_account("0042911", "Instructor")
        locked, go, results = threading.Event(), threading.Event(), {}

        def reset_style():
            with transaction.atomic():
                Account.objects.select_for_update().get(pk=holder.pk)
                session_revocation.advance(holder.pk)
                locked.set()
                self.assertTrue(go.wait(WAIT))
            return "reset"
        reset = self.worker(reset_style, results, "reset")
        self.assertTrue(locked.wait(WAIT))
        role = self.worker(lambda: self.configure("grant-school-admin", holder), results, "role")
        time.sleep(BLOCKED)
        self.assertTrue(role.is_alive(), "the role change must wait for the account row lock")
        go.set()
        reset.join(JOIN)
        role.join(JOIN)
        self.assertFalse(reset.is_alive() or role.is_alive())
        for key, value in results.items():
            self.assertNotIsInstance(value, Exception, f"{key}: {value!r}")
        self.assertEqual(counter(holder), 2)

    def test_the_advance_reuses_the_existing_lock_order(self):
        """The counter UPDATE comes after the service locks and the target's account-row lock (R-1/K-4/K-6)."""
        self.release()
        holder = self.password_account("0042912", "Instructor")
        with CaptureQueriesContext(connection) as captured:
            self.configure("grant-school-admin", holder)
        sql = [q["sql"] for q in captured.captured_queries]
        service_lock = next(i for i, s in enumerate(sql) if "FOR UPDATE" in s.upper() and "`services`" in s)
        account_locks = [i for i, s in enumerate(sql) if "FOR UPDATE" in s.upper() and "FROM `accounts`" in s
                         and str(holder.pk) in s]
        advance = [i for i, s in enumerate(sql) if s.upper().startswith("UPDATE `ACCOUNTS`")
                   and "session_revocation_version" in s]
        self.assertEqual(len(advance), 1, "exactly one counter UPDATE per operation")
        self.assertTrue(account_locks)
        self.assertLess(service_lock, account_locks[0])
        self.assertLess(account_locks[0], advance[0])
        self.assertEqual(sql.index(next(s for s in sql if "FOR UPDATE" in s.upper())), service_lock)


class PersistenceGuardTests(Base):
    def test_a_stale_full_save_never_lowers_or_writes_the_counter(self):
        holder = self.password_account("0042920", "Instructor")
        stale = Account.objects.get(pk=holder.pk)
        with transaction.atomic():
            session_revocation.advance(holder.pk)
            session_revocation.advance(holder.pk)
        stale.is_active = False
        stale.save()  # a full save of the stale instance (counter 0 in memory)
        self.assertEqual(counter(holder), 2)
        self.assertFalse(Account.objects.get(pk=holder.pk).is_active)
        with self.assertRaises(SessionRevocationWriteRefused):
            stale.save(update_fields=["session_revocation_version"])
        with self.assertRaises(SessionRevocationWriteRefused):
            Account.objects.filter(pk=holder.pk).update(session_revocation_version=0)
        with self.assertRaises(SessionRevocationWriteRefused):
            Account.objects.bulk_update([stale], ["session_revocation_version"])
        self.assertEqual(counter(holder), 2)
        partial = Account.objects.only("school_id").get(pk=holder.pk)  # deferred fields stay deferred
        partial.school_id = "0042920"
        partial.save()
        self.assertEqual(counter(holder), 2)
        # Documented limit: the base manager, raw SQL and privileged users are NOT bound by these guards.
        Account._base_manager.filter(pk=holder.pk).update(session_revocation_version=0)
        self.assertEqual(counter(holder), 0)

    def test_a_stale_full_save_never_recreates_a_deleted_account(self):
        account = Account.objects.create_user(school_id="0042921", password=None)
        stale = Account.objects.get(pk=account.pk)
        Account.objects.filter(pk=account.pk).delete()
        with self.assertRaises(DatabaseError):
            stale.save()
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())

    def test_the_counter_is_not_editable_or_exposed(self):
        field = Account._meta.get_field("session_revocation_version")
        self.assertFalse(field.editable)
        from apps.accounts.admin import AccountReadOnlyAdmin
        self.assertNotIn("session_revocation_version", AccountReadOnlyAdmin.fields)
        holder = self.password_account("0042922", "Instructor")
        _, response = self.authenticated(self.signed_in_client(holder))
        self.assertNotIn("session_revocation", response.content.decode())


class TriggerTests(Base):
    """Test-only trigger on the disposable database; the real installation is a separate DBA authorization."""

    def install(self):
        schema = verify_disposable(self)
        with connection.cursor() as cursor:
            cursor.execute(TRIGGER_SQL)
        self.addCleanup(self.uninstall, schema)
        return schema

    def uninstall(self, schema):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS `{schema}`.`{TRIGGER}`")
            cursor.execute("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=%s", [schema])
            assert cursor.fetchone()[0] == 0, "a test trigger was left behind"

    def test_the_trigger_refuses_decreases_and_allows_increments_and_ordinary_updates(self):
        self.install()
        holder = self.password_account("0042930", "Instructor")
        with transaction.atomic():
            session_revocation.advance(holder.pk)
            session_revocation.advance(holder.pk)
        self.assertEqual(counter(holder), 2)
        for sql in ("UPDATE accounts SET session_revocation_version = 0 WHERE account_id = %s",
                    "UPDATE accounts SET session_revocation_version = session_revocation_version - 1 WHERE account_id = %s",
                    "UPDATE accounts SET session_revocation_version = 1, is_active = 0 WHERE account_id = %s"):
            with self.subTest(sql=sql):
                self.assertEqual(self.refused(sql, [holder.pk]), SIGNALLED)
        with self.assertRaises(DatabaseError):  # an ORM write on the base manager is refused the same way
            Account._base_manager.filter(pk=holder.pk).update(session_revocation_version=1)
        self.assertEqual(counter(holder), 2)
        self.assertTrue(Account.objects.get(pk=holder.pk).is_active)
        self.assertIsNone(self.refused("UPDATE accounts SET session_revocation_version = session_revocation_version "
                                       "WHERE account_id = %s", [holder.pk]))  # unchanged value: allowed
        stale = Account.objects.get(pk=holder.pk)
        with transaction.atomic():
            session_revocation.advance(holder.pk)
        stale.request_status = "Approved"
        stale.save()  # ordinary updates and full saves still work (the counter is never written)
        self.assertEqual(counter(holder), 3)
        with self.assertRaises(RuntimeError), transaction.atomic():
            session_revocation.advance(holder.pk)
            raise RuntimeError("rolled back")
        self.assertEqual(counter(holder), 3)  # a rollback restores the earlier value without tripping the trigger

    def test_the_restricted_runtime_account_cannot_lower_drop_or_replace_the_protection(self):
        schema = self.install()
        holder = self.password_account("0042931", "Instructor")
        user, password = self.temporary_account(self.runtime_grants(schema))
        migrate_user, migrate_password = self.temporary_account([
            f"GRANT CREATE, ALTER, DROP, INDEX, REFERENCES, SELECT, INSERT, UPDATE, DELETE ON `{schema}`.* TO {{user}}"])

        def runtime():
            with transaction.atomic():
                session_revocation.advance(holder.pk)  # the legitimate path works under the restricted account
            return {
                "decrease": self.refused("UPDATE accounts SET session_revocation_version = 0 WHERE account_id = %s",
                                         [holder.pk]),
                "drop trigger": self.refused(f"DROP TRIGGER `{TRIGGER}`"),
                "replace trigger": self.refused(
                    "CREATE TRIGGER sr1_probe BEFORE UPDATE ON accounts FOR EACH ROW SET NEW.is_active = NEW.is_active"),
                "drop column": self.refused("ALTER TABLE accounts DROP COLUMN session_revocation_version"),
                "modify column": self.refused("ALTER TABLE accounts MODIFY session_revocation_version BIGINT NULL"),
                "ordinary update": self.refused("UPDATE accounts SET is_active = is_active WHERE account_id = %s",
                                                [holder.pk]),
            }
        codes_ = self.run_as(user, password, runtime)
        self.assertNotIsInstance(codes_, Exception, repr(codes_))
        self.assertEqual(codes_["decrease"], SIGNALLED)
        for name in ("drop trigger", "replace trigger", "drop column", "modify column"):
            self.assertIn(codes_[name], DENIED, f"{name}: {codes_[name]}")
        self.assertIsNone(codes_["ordinary update"])
        self.assertEqual(counter(holder), 1)
        dropped = self.run_as(migrate_user, migrate_password, lambda: self.refused(f"DROP TRIGGER `{TRIGGER}`"))
        self.assertIn(dropped, DENIED)  # the migration account has no TRIGGER privilege either

        def grants():
            with connection.cursor() as cursor:
                cursor.execute("SHOW GRANTS")
                return " ".join(row[0] for row in cursor.fetchall()).upper()
        for who in ((user, password), (migrate_user, migrate_password)):
            granted = self.run_as(*who, grants)
            for privilege in ("TRIGGER", "SUPER", "ALL PRIVILEGES", "GRANT OPTION"):
                self.assertNotIn(privilege, granted)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=%s AND TRIGGER_NAME=%s",
                           [schema, TRIGGER])
            self.assertEqual(cursor.fetchone()[0], 1)  # still installed

    def test_a_privileged_administrator_can_still_remove_the_protection(self):
        """Honest boundary: the trigger binds application and migration accounts, NOT a database administrator."""
        schema = self.install()
        holder = self.password_account("0042932", "Instructor")
        with transaction.atomic():
            session_revocation.advance(holder.pk)
        with connection.cursor() as cursor:  # the privileged test runner account
            cursor.execute(f"DROP TRIGGER `{schema}`.`{TRIGGER}`")
        self.assertIsNone(self.refused("UPDATE accounts SET session_revocation_version = 0 WHERE account_id = %s",
                                       [holder.pk]))
        self.assertEqual(counter(holder), 0)

    def test_a_counter_restore_by_update_is_refused_so_an_old_session_stays_revoked(self):
        self.install()
        self.release()
        holder = self.password_account("0042933", "Instructor")
        self.configure("grant-school-admin", holder)
        unused = self.signed_in_client(holder)  # bound to counter 1
        self.configure("revoke-school-admin", holder)
        self.assertEqual(self.refused("UPDATE accounts SET session_revocation_version = 1 WHERE account_id = %s",
                                      [holder.pk]), SIGNALLED)
        self.assertFalse(self.authenticated(unused)[0])


class SessionContractTests(Base):
    def test_sessions_bound_to_either_earlier_hash_contract_are_refused_once_and_flushed(self):
        self.release()
        holder = self.password_account("0042940", "Instructor")
        self.configure("grant-school-admin", holder)
        current = Account.objects.get(pk=holder.pk)
        base = AbstractBaseUser._get_session_auth_hash(current)
        legacy = {
            "Django plain hash (receipt epoch 0)": base,
            "receipt epoch v1": salted_hmac(V1_SALT, f"{base}:{status_epoch(holder.pk)}", algorithm="sha256").hexdigest(),
        }
        for label, value in legacy.items():
            with self.subTest(contract=label):
                client = self.signed_in_client(holder)
                key = self.session_key(client)
                store = SessionStore(session_key=key)
                store[HASH_SESSION_KEY] = value
                store.save()
                self.assertFalse(self.authenticated(client)[0])
                self.assertFalse(Session.objects.filter(session_key=key).exists())  # flushed, not migrated
        self.assertNotIn(base, list(current.get_session_auth_fallback_hash()))
        expected = salted_hmac(SESSION_HASH_SALT, f"{base}:1", algorithm="sha256").hexdigest()
        self.assertEqual(current.get_session_auth_hash(), expected)
        self.assertTrue(self.authenticated(self.signed_in_client(holder))[0])  # a fresh sign-in works
        self.assertNotIn("status_epoch", inspect.getsource(Account._get_session_auth_hash))

    def test_a_revocation_committed_during_login_never_leaves_a_valid_stale_session(self):
        self.release()
        holder = self.password_account("0042941", "Instructor")
        self.configure("grant-school-admin", holder)
        real_login = session_auth.login

        def login_then_revoke(request, user, *args, **kwargs):
            real_login(request, user, *args, **kwargs)  # the session is now bound to counter 1
            result = self.run_with({}, lambda: self.configure("revoke-school-admin", holder))
            self.assertNotIsInstance(result, Exception, repr(result))  # committed on another connection
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        with mock.patch.object(session_auth, "login", side_effect=login_then_revoke):
            response = client.post("/api/v1/auth/login/", {"school_id": holder.school_id, "password": PASSWORD},
                                   format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 401, response.content)
        self.assertFalse(self.authenticated(client)[0])
        self.assertEqual(counter(holder), 2)
        # A change committed after the post-login re-read: the very next request is refused.
        late = self.signed_in_client(holder)
        result = self.run_with({}, lambda: self.configure("grant-school-admin", holder))
        self.assertNotIsInstance(result, Exception, repr(result))
        self.assertFalse(self.authenticated(late)[0])

    def test_deleting_and_recreating_an_account_never_authenticates_its_old_sessions(self):
        self.release()
        changed = self.password_account("0042942", "Instructor")
        self.configure("grant-school-admin", changed)  # its receipts now reference it
        with self.assertRaises(ProtectedError):
            Account.objects.get(pk=changed.pk).delete()
        with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts WHERE account_id = %s", [changed.pk])  # database foreign keys refuse
        plain = self.password_account("0042943", "Instructor")
        old_session, old_pk = self.signed_in_client(plain), plain.pk
        AccountRole.objects.filter(account_id=old_pk).delete()
        Account.objects.filter(pk=old_pk).delete()
        recreated = self.password_account("0042943", "Instructor")
        self.assertNotEqual(recreated.pk, old_pk)  # InnoDB keeps the auto-increment counter
        self.assertFalse(self.authenticated(old_session)[0])
        second_session = self.signed_in_client(recreated)
        AccountRole.objects.filter(account_id=recreated.pk).delete()
        Account.objects.filter(pk=recreated.pk).delete()
        with connection.cursor() as cursor:  # privileged re-creation on the SAME primary key, new credentials
            cursor.execute("INSERT INTO accounts (account_id, school_id, password_hash, request_status, is_active, "
                           "is_staff, is_superuser) VALUES (%s, '0042943', %s, 'Approved', 1, 0, 0)",
                           [recreated.pk, make_password("Another!Harbor7731")])
        AccountRole.objects.create(account_id=recreated.pk, role=self.roles["Instructor"])
        self.assertFalse(self.authenticated(second_session)[0])

    def test_restoring_an_old_session_row_does_not_revive_it_while_the_counter_is_newer(self):
        self.release()
        holder = self.password_account("0042944", "Instructor")
        self.configure("grant-school-admin", holder)
        client = self.signed_in_client(holder)
        row = Session.objects.values().get(session_key=self.session_key(client))
        self.configure("revoke-school-admin", holder)
        self.assertFalse(self.authenticated(client)[0])  # used after revocation: flushed
        Session.objects.create(**row)  # restore only the session table from an earlier backup
        self.assertFalse(self.authenticated(client)[0])

    def test_csrf_protection_is_unchanged(self):
        holder = self.password_account("0042945", "Instructor")
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/v1/auth/csrf/")
        response = client.post("/api/v1/auth/login/", {"school_id": holder.school_id, "password": PASSWORD},
                               format="json")
        self.assertEqual((response.status_code, response.json()["error"]["code"]), (403, "csrf_failed"))
        self.assertNotIn(settings.SESSION_COOKIE_NAME, client.cookies)
        signed_in = self.signed_in_client(holder)
        self.assertEqual(signed_in.post("/api/v1/auth/logout/", {}, format="json").status_code, 403)
        self.assertTrue(self.authenticated(signed_in)[0])

    def test_account_specific_deny_still_wins_across_counter_changes(self):
        self.release()
        holder = self.password_account("0042946", "Instructor")
        permission = Permission.objects.get(permission_code=REGISTRATION_READ)
        AccountPermission.objects.create(account=holder, permission=permission, effect="Deny", assigned_by=self.actor)
        self.assertTrue(has_permission(self.actor, REGISTRATION_READ))  # control: School Admins hold it
        self.configure("grant-school-admin", holder)
        ok, response = self.authenticated(self.signed_in_client(holder))
        self.assertTrue(ok)
        self.assertIn("Admin", response.json()["account"]["roles"])
        self.assertNotIn(REGISTRATION_READ, response.json()["permissions"])
        current = Account.objects.get(pk=holder.pk)
        self.assertFalse(has_permission(current, REGISTRATION_READ))
        self.assertNotIn(REGISTRATION_READ, get_effective_permissions(current))
        self.assertEqual(AccountPermission.objects.filter(account=holder, effect="Deny", is_active=True).count(), 1)

    def test_d83_every_session_ending_writer_advances_the_counter(self):
        """Contract guard: each approved session-ending event calls the advance (the executor paths are dormant)."""
        bootstrap = inspect.getsource(provisioning.execute_protected)
        create = bootstrap.index("AccountRole.objects.create(account=target, role=role, assigned_by=actor)")
        self.assertLess(create, bootstrap.index("advance(target.pk)"))
        self.assertLess(bootstrap.index("advance(target.pk)"), bootstrap.index('action="technical_admin.bootstrap"'))
        # configure_role runs _configure_role in a fresh context (D-93/D-95 gate); the advance lives there.
        for function, text in ((framework_roles._configure_role, "session_revocation.advance(target_id)"),
                               (role_assignment._change, "session_revocation.advance(target_id)"),
                               (account_status._change, "session_revocation.advance(target_id)"),
                               (password_reset.PasswordResetConfirmView.post, "session_revocation.advance(account.pk)")):
            with self.subTest(function=function.__qualname__):
                self.assertEqual(inspect.getsource(function).count(text), 1)
        # D-83 (ordinary additions take effect on the next request): the dormant executor's ordinary Student/
        # Instructor assignment does not end sessions, and wex-1 forbids its principal from updating Approved
        # accounts (protected infrastructure; unchanged).
        self.assertNotIn("advance(", inspect.getsource(executor_role_assignment.assign_ordinary_role))


class SessionLifetimeTests(Base):
    def setUp(self):
        super().setUp()
        # D-18 as configured (30 minutes idle, 8 hours absolute); never overridden here, so the P1 target guard
        # still sees the real test settings module.
        self.assertEqual((settings.WORKSPACE_SESSION_IDLE_SECONDS, settings.WORKSPACE_SESSION_ABSOLUTE_SECONDS),
                         (IDLE, ABSOLUTE))
        self.clock = int(time.time())
        patcher = mock.patch.object(session_timeout, "_now", side_effect=lambda: self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def seen_at(self, key):
        row = Session.objects.filter(session_key=key).first()
        return None if row is None else row.get_decoded().get(session_timeout.SEEN_AT)

    def revoked_session(self, school_id):
        self.release()
        holder = self.password_account(school_id, "Instructor")
        self.configure("grant-school-admin", holder)
        client = self.signed_in_client(holder)
        self.configure("revoke-school-admin", holder)
        return client, self.session_key(client)

    def test_sr1a_csrf_polling_refreshes_a_revoked_sessions_activity_without_verifying_it(self):
        """SR-1a CONFIRMED (documented, middleware unchanged): the public CSRF endpoint never runs get_user, yet the
        timeout middleware records activity, so a revoked, unused session row stays alive past the idle limit.
        After Stage A it still cannot authenticate."""
        client, key = self.revoked_session("0042950")
        signed_in_at = self.clock
        for _ in range(3):  # 3 x 20 minutes: well past the 30-minute idle limit
            self.clock += 20 * 60
            self.assertEqual(client.get("/api/v1/auth/csrf/").status_code, 200)
            self.assertEqual(self.seen_at(key), self.clock)  # activity refreshed with no hash check
        self.assertGreater(self.clock - signed_in_at, IDLE)
        self.assertTrue(Session.objects.filter(session_key=key).exists())
        self.assertFalse(self.authenticated(client)[0])  # the counter still refuses it ...
        self.assertFalse(Session.objects.filter(session_key=key).exists())  # ... and the row is flushed

    def test_sr1a_the_absolute_limit_still_ends_a_polled_session(self):
        client, key = self.revoked_session("0042951")
        signed_in_at = self.clock
        while self.clock - signed_in_at < ABSOLUTE - 20 * 60:
            self.clock += 20 * 60
            client.get("/api/v1/auth/csrf/")
            self.assertTrue(Session.objects.filter(session_key=key).exists())
        self.clock = signed_in_at + ABSOLUTE
        client.get("/api/v1/auth/csrf/")
        self.assertFalse(Session.objects.filter(session_key=key).exists())  # 8-hour absolute limit (D-18)

    def test_idle_and_absolute_limits_still_end_valid_sessions(self):
        holder = self.password_account("0042952", "Instructor")
        idle = self.signed_in_client(holder)
        self.clock += IDLE - 60
        self.assertTrue(self.authenticated(idle)[0])
        self.clock += IDLE
        self.assertFalse(self.authenticated(idle)[0])
        busy, start = self.signed_in_client(holder), self.clock
        while self.clock - start < ABSOLUTE - 20 * 60:
            self.clock += 20 * 60
            self.assertTrue(self.authenticated(busy)[0])
        self.clock = start + ABSOLUTE
        self.assertFalse(self.authenticated(busy)[0])


@override_settings(**STATUS_GATE, **RECOVERY_SETTINGS)
class AccountStatusAndRecoveryTests(TransactionTestCase):
    """WF-02.05 suspension/reactivation and WF-01.05 password reset, through their real services and endpoints."""

    worker = staticmethod(Base.worker)
    def setUp(self):
        verify_disposable(self)
        cache.clear()
        self.w = World()

    def tearDown(self):
        connections.close_all()

    def sign_in(self, school_id, password=None):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/login/", {"school_id": school_id, "password": password or PASSWORD},
                               format="json", HTTP_X_CSRFTOKEN=token)
        return client, response.status_code

    @staticmethod
    def signed_in(client):
        response = client.get("/api/v1/auth/session/")
        return response.status_code == 200 and response.json()["authenticated"] is True

    def test_suspension_and_reactivation_each_advance_once_and_end_earlier_sessions(self):
        target = self.w.account("0042960", "Student")
        before, status = self.sign_in(target.school_id)
        self.assertEqual(status, 200)
        with CaptureQueriesContext(connection) as captured:
            suspend_account(actor=self.w.reviewer, target_id=target.pk)
        # Copy now: later HTTP requests fire request_started, which clears the connection's live query log.
        sql = [q["sql"] for q in captured.captured_queries]
        self.assertEqual(counter(target), 1)
        self.assertFalse(self.signed_in(before))
        self.assertEqual(self.sign_in(target.school_id)[1], 401)  # suspended: no new session
        activate_account(actor=self.w.reviewer, target_id=target.pk)
        self.assertEqual(counter(target), 2)  # reactivation also requires a fresh sign-in
        self.assertEqual(counter(self.w.reviewer), 0)
        fresh, status = self.sign_in(target.school_id)
        self.assertEqual(status, 200)
        self.assertTrue(self.signed_in(fresh))
        locking = [i for i, s in enumerate(sql) if "FOR UPDATE" in s.upper()]
        self.assertTrue(locking, sql)
        first_lock = locking[0]
        self.assertIn("`services`", sql[first_lock])
        account_lock = next(i for i, s in enumerate(sql) if "FOR UPDATE" in s.upper() and "FROM `accounts`" in s)
        advance = [i for i, s in enumerate(sql) if "session_revocation_version" in s and s.upper().startswith("UPDATE")]
        self.assertEqual(len(advance), 1)
        self.assertLess(account_lock, advance[0])

    def test_a_refused_status_change_writes_nothing(self):
        target = self.w.account("0042961", "Student")
        receipts = AccessAuditLog.objects.count()
        with self.assertRaises(account_status.AccountStatusConflict):
            suspend_account(actor=self.w.reviewer, target_id=target.pk, expected_active=False)
        with self.assertRaises(account_status.AccountStatusConflict):
            activate_account(actor=self.w.reviewer, target_id=target.pk)  # already active
        self.assertEqual((counter(target), AccessAuditLog.objects.count()), (0, receipts))

    def test_a_failed_suspension_rolls_back_status_receipt_and_counter(self):
        target = self.w.account("0042962", "Student")
        session, _ = self.sign_in(target.school_id)
        receipts = AccessAuditLog.objects.count()
        real = session_revocation.advance

        def advance_then_fail(account_id, **kwargs):
            real(account_id, **kwargs)
            raise RuntimeError("forced failure after the counter advanced")
        with mock.patch.object(session_revocation, "advance", side_effect=advance_then_fail), self.assertRaises(RuntimeError):
            suspend_account(actor=self.w.reviewer, target_id=target.pk)
        self.assertEqual((counter(target), AccessAuditLog.objects.count()), (0, receipts))
        self.assertTrue(Account.objects.get(pk=target.pk).is_active)
        self.assertTrue(self.signed_in(session))

    def test_a_suspension_waits_for_a_concurrent_password_reset_style_advance_and_both_count(self):
        target = self.w.account("0042963", "Student")
        locked, go, results = threading.Event(), threading.Event(), {}

        def reset_style():
            with transaction.atomic():
                Account.objects.select_for_update().get(pk=target.pk)
                session_revocation.advance(target.pk)
                locked.set()
                go.wait(WAIT)
            return "reset"
        reset = self.worker(reset_style, results, "reset")
        self.assertTrue(locked.wait(WAIT))
        suspension = self.worker(lambda: suspend_account(actor=self.w.reviewer, target_id=target.pk), results, "suspend")
        time.sleep(BLOCKED)
        self.assertTrue(suspension.is_alive(), "the suspension must wait for the account row lock")
        go.set()
        reset.join(JOIN)
        suspension.join(JOIN)
        self.assertFalse(reset.is_alive() or suspension.is_alive())
        for key, value in results.items():
            self.assertNotIsInstance(value, Exception, f"{key}: {value!r}")
        self.assertEqual(counter(target), 2)
        self.assertFalse(Account.objects.get(pk=target.pk).is_active)

    def reset_password(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]

        def post(path, data):
            response = client.post(path, data, format="json", HTTP_X_CSRFTOKEN=token)
            recovery_mail.wait_until_idle()
            return response
        recovery_mail.wait_until_idle()
        from django.core import mail
        mail.outbox.clear()
        self.assertEqual(post("/api/v1/auth/forgot-password/", {"email": EMAIL}).status_code, 202)
        self.assertEqual(post("/api/v1/auth/forgot-password/verify/", {"email": EMAIL, "code": codes()[-1]}).status_code, 200)
        done = post("/api/v1/auth/reset-password/", {"email": EMAIL, "password": NEW, "password_confirmation": NEW})
        self.assertEqual(done.status_code, 200, done.content)

    def test_password_reset_advances_once_and_restoring_the_old_password_hash_alone_revives_nothing(self):
        account = make_account(self.w.roles["Student"], "0042964", EMAIL)
        old_hash = Account.objects.get(pk=account.pk).password
        used, status = self.sign_in(account.school_id, OLD)
        self.assertEqual(status, 200)
        unused, status = self.sign_in(account.school_id, OLD)  # signed in before the reset, never used since
        self.assertEqual(status, 200)
        self.reset_password()
        self.assertEqual(counter(account), 1)
        self.assertFalse(self.signed_in(used))  # WF-01.05 invalidation unchanged
        # A privileged restore of ONLY the old password hash: under the receipt-epoch contract the unused session's
        # hash would match again (a reset writes no counted receipt); the counter keeps it revoked.
        Account._base_manager.filter(pk=account.pk).update(password=old_hash)
        self.assertFalse(self.signed_in(unused))
        self.assertEqual(counter(account), 1)
        fresh, status = self.sign_in(account.school_id, OLD)
        self.assertEqual(status, 200)
        self.assertTrue(self.signed_in(fresh))  # new sessions bind the current counter


class MigrationTests(Base):
    def column(self, schema):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS "
                           "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts' AND COLUMN_NAME='session_revocation_version'",
                           [schema])
            return cursor.fetchone()

    def test_the_fresh_test_database_has_exactly_the_approved_column(self):
        schema = verify_disposable(self)
        column_type, nullable, default = self.column(schema)
        self.assertEqual((column_type.lower(), nullable, str(default)), ("bigint unsigned", "NO", "0"))
        holder = Account.objects.create_user(school_id="0042970", password=None)
        self.assertEqual(counter(holder), 0)
        with connection.cursor() as cursor:  # raw inserts get the database default
            cursor.execute("INSERT INTO accounts (school_id, password_hash, request_status, is_active, is_staff, "
                           "is_superuser) VALUES ('0042971', '!', 'Pending', 0, 0, 0)")
        self.assertEqual(Account._base_manager.get(school_id="0042971").session_revocation_version, 0)

    def test_upgrade_from_0005_with_existing_rows_reverse_and_reapply(self):
        verify_disposable(self)
        target = self.temporary_database("sr1mig")
        self.assertRegex(target, r"\Atest_ctug_registration_[0-9a-f]{16}_sr1mig\Z")
        from django.contrib.contenttypes.models import ContentType
        self.addCleanup(ContentType.objects.clear_cache)

        def migrate(name):
            return lambda: call_command("migrate", "accounts", name, verbosity=0, interactive=False)

        def insert_existing():
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                assert cursor.fetchone()[0] == target
                for school_id in ("0042980", "0042981"):
                    cursor.execute("INSERT INTO accounts (school_id, password_hash, request_status, is_active, "
                                   "is_staff, is_superuser) VALUES (%s, '!', 'Approved', 1, 0, 0)", [school_id])
                cursor.execute("SELECT COUNT(*) FROM accounts")
                return cursor.fetchone()[0]
        overrides = {"NAME": target}
        self.assertIsNone(self.run_with(overrides, migrate("0005_student_registration_otp")))
        self.assertIsNone(self.column(target))
        self.assertEqual(self.run_with(overrides, insert_existing), 2)
        self.assertIsNone(self.run_with(overrides, migrate("0006_account_session_revocation_version")))
        self.assertEqual(self.column(target)[0].lower(), "bigint unsigned")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT school_id, session_revocation_version FROM `{target}`.accounts ORDER BY school_id")
            self.assertEqual(cursor.fetchall(), (("0042980", 0), ("0042981", 0)))
        self.assertIsNone(self.run_with(overrides, migrate("0005_student_registration_otp")))  # reversible
        self.assertIsNone(self.column(target))
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM `{target}`.accounts")
            self.assertEqual(cursor.fetchone()[0], 2)  # existing rows preserved
        self.assertIsNone(self.run_with(overrides, migrate("0006_account_session_revocation_version")))
        self.assertEqual(self.column(target)[1:], ("NO", "0"))
