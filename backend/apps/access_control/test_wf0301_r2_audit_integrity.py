"""WF-03.01 R-2 Option D phase 1 (owner-authorized): audit-receipt integrity, session revival, least privilege.

Run: python manage.py test apps.access_control.test_wf0301_r2_audit_integrity --settings=config.test_settings --noinput
Disposable MySQL ONLY. Temporary MySQL accounts are created with random names, granted ONLY on this run's
disposable database (or a second disposable database created and dropped here), never on ctug_workspace,
and dropped in cleanup; their passwords exist only in memory. Nothing here changes the application's real
connection, backend/.env, any migration or any trigger.

What each group shows, and its trust boundary:
- SessionRevival: the session epoch is derived from audit receipts, so a database-privileged deletion of the
  latest role-change receipt revives an UNUSED revoked session (SR-1, documented as a known vulnerability).
- LeastPrivilege: a runtime account with SELECT/INSERT/LOCK TABLES on the schema and UPDATE/DELETE on every
  table EXCEPT access_audit_logs runs the real governance paths, yet cannot change, delete, truncate or drop
  receipts, or create triggers, tables or users. It does NOT stop a database administrator.
- Checkpoint: the read-only prototype detects changes up to a checkpoint held OUTSIDE the database; rows
  committed later are only reported as unanchored, and a checkpoint taken while a lower receipt ID is still
  uncommitted later fails closed (checkpoints need a quiescent window).
"""

import json
import os
import secrets
from datetime import datetime, timezone as dt_timezone
import tempfile
import threading
from io import StringIO

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, connections, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.access_control import audit_checkpoint as checkpoint
from apps.access_control import framework_roles
from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccessAuditLog, AccountRole, Role
from apps.access_control.technical_admin import has_technical_authority
from apps.accounts.account_status import status_epoch
from apps.accounts.models import Account

from . import test_wf0301_d85_p3b_compatibility as d85  # module only: its TestCase is not collected here

if (settings.SETTINGS_MODULE != "config.test_settings"
        or not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_")):
    raise ImproperlyConfigured("R-2 tests require the disposable MySQL test settings.")

PASSWORD = "Harbor!Lantern5821"
JOIN = 120
# MySQL privilege refusals. 1419: creating a trigger needs SUPER while binary logging is on; the runtime account
# also holds no TRIGGER privilege (asserted separately from SHOW GRANTS).
DENIED = {1044, 1142, 1143, 1227, 1370, 1419}
SCHOOL_PHASES = ("metadata", "bindings", "activate")
TEST_KEY = b"test-only-hmac-key-never-used-outside-tests-0123456789"


class Harness(TransactionTestCase):
    setUp_d85 = d85.D85CompatibilityTests.setUp
    tearDown = d85.D85CompatibilityTests.tearDown
    account = d85.D85CompatibilityTests.account
    scope = d85.D85CompatibilityTests.scope
    release = d85.D85CompatibilityTests.release
    p4 = d85.D85CompatibilityTests.p4
    preview = d85.D85CompatibilityTests.preview
    configure = d85.D85CompatibilityTests.configure
    everything = d85.D85CompatibilityTests.everything

    def setUp(self):
        self.setUp_d85()
        cache.clear()

    # -- disposable databases and temporary accounts (never ctug_workspace) ---------------------------
    def database(self):
        name = connection.settings_dict["NAME"]
        self.assertTrue(name.startswith("test_ctug_registration_") and name != "ctug_workspace")
        return name

    def temporary_database(self, suffix):
        name = f"{self.database()}_{suffix}"
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        self.addCleanup(self._drop_database, name)
        return name

    @staticmethod
    def _drop_database(name):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")

    def temporary_account(self, grants):
        """A random, in-memory-only MySQL account; `grants` are GRANT statements using {user}."""
        user, password = "ctug_r2t_" + secrets.token_hex(6), secrets.token_urlsafe(24)
        with connection.cursor() as cursor:
            cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", [user, password])
            self.addCleanup(self._drop_account, user)
            for statement in grants:
                cursor.execute(statement.format(user=f"'{user}'@'localhost'"))
        return user, password

    @staticmethod
    def _drop_account(user):
        with connection.cursor() as cursor:
            cursor.execute("DROP USER IF EXISTS %s@'localhost'", [user])

    def runtime_grants(self, schema, *, lock_tables=True):
        with connection.cursor() as cursor:
            cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME",
                           [schema])
            tables = [row[0] for row in cursor.fetchall()]
        self.assertIn(AccessAuditLog._meta.db_table, tables)
        privileges = "SELECT, INSERT, LOCK TABLES" if lock_tables else "SELECT, INSERT"
        return ([f"GRANT {privileges} ON `{schema}`.* TO {{user}}"]
                + [f"GRANT UPDATE, DELETE ON `{schema}`.`{t}` TO {{user}}" for t in tables
                   if t != AccessAuditLog._meta.db_table])

    def run_as(self, user, password, fn):
        """Run fn in a worker thread whose default connection authenticates as the temporary account."""
        return self.run_with({"USER": user, "PASSWORD": password}, fn)

    def run_with(self, overrides, fn):
        """Run fn in a worker thread whose default connection uses these settings (account and/or database)."""
        results = {}

        def target():
            conn = connections["default"]
            conn.close()
            conn.settings_dict = {**conn.settings_dict, **overrides}
            try:
                results["value"] = fn()
            except Exception as exc:  # returned to the caller
                results["value"] = exc
            finally:
                connections.close_all()
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(JOIN)
        self.assertFalse(thread.is_alive(), "the restricted-account operation did not finish")
        return results["value"]

    @staticmethod
    def refused(sql, params=()):
        """Execute on the current (worker) connection; return the MySQL error code, or None if it succeeded."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            return None
        except DatabaseError as exc:
            return exc.args[0] if exc.args else -1

    def password_account(self, school_id, *roles):
        account = Account.objects.create_user(school_id=school_id, password=PASSWORD)
        Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved")
        for role in roles:
            AccountRole.objects.create(account=account, role=self.roles[role])
        return Account.objects.get(pk=account.pk)

    def signed_in_client(self, account):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/login/", {"school_id": account.school_id, "password": PASSWORD},
                               format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["authenticated"])
        return client

    @staticmethod
    def authenticated(client):
        response = client.get("/api/v1/auth/session/")
        return response.status_code == 200 and response.json().get("authenticated") is True, response


class SessionRevivalTests(Harness):
    """SR-1: status_epoch = latest suspension/role-change receipt ID, which is part of the session hash."""

    def revoked_holder(self):
        self.release()
        holder = self.password_account("0042101", "Instructor")
        self.configure("grant-school-admin", holder)
        client = self.signed_in_client(holder)  # signed in while School Admin
        self.configure("revoke-school-admin", holder)  # ends every earlier session (D-83)
        revoke = AccessAuditLog.objects.filter(target_account=holder, action=framework_roles.FRAMEWORK_REVOKE_ACTION).get()
        return holder, client, revoke

    def test_a_revocation_ends_the_earlier_session_without_tampering(self):
        holder, client, _ = self.revoked_holder()
        ok, response = self.authenticated(client)
        self.assertFalse(ok, response.content)

    def test_known_vulnerability_sr1_deleting_the_revocation_receipt_revives_an_unused_revoked_session(self):
        """KNOWN VULNERABILITY (R-2 SR-1, activation blocker). This test documents the current behaviour and must
        be inverted when a revocation that cannot be undone by deleting a receipt is approved and implemented."""
        holder, client, revoke = self.revoked_holder()
        assign = AccessAuditLog.objects.filter(target_account=holder, action=framework_roles.FRAMEWORK_ASSIGN_ACTION).get()
        self.assertEqual(status_epoch(holder.pk), revoke.pk)
        AccessAuditLog.objects.filter(pk=revoke.pk).delete()  # privileged test-only connection (disposable DB)
        self.assertEqual(status_epoch(holder.pk), assign.pk)  # the epoch moved BACKWARDS
        ok, response = self.authenticated(client)
        self.assertTrue(ok, "SR-1 no longer reproduces: invert this test and record the fix")
        self.assertEqual(response.json()["account"]["roles"], ["Instructor"])  # the revoked Admin role stays revoked
        self.assertFalse(AccountRole.objects.filter(account=holder, role__role_name="Admin").exists())

    def test_a_session_used_after_the_revocation_is_flushed_and_cannot_be_revived(self):
        holder, client, revoke = self.revoked_holder()
        key = client.cookies[settings.SESSION_COOKIE_NAME].value
        ok, _ = self.authenticated(client)  # Django's get_user flushes the mismatching session
        self.assertFalse(ok)
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        AccessAuditLog.objects.filter(pk=revoke.pk).delete()
        ok, _ = self.authenticated(client)
        self.assertFalse(ok)


class LeastPrivilegeTests(Harness):
    def test_the_runtime_account_runs_governance_but_cannot_rewrite_receipts(self):
        schema = self.database()
        user, password = self.temporary_account(self.runtime_grants(schema))
        holder = self.account("0042201", "Instructor")

        def governance():
            self.release(*SCHOOL_PHASES)  # P1, P2, P4 activation, WF-02.05 metadata/bindings/activate
            grant = self.configure("grant-technical-super-admin", holder)
            verify = d85.s3.run(phase="verify", actor_account_id=self.actor.pk)
            try:
                self.p4("compensate", self.scope(holder))
                compensation = "NOT REFUSED"
            except d85.p3b.ActivationExerciseRefused as exc:
                compensation = str(exc)
            preview_refused = None
            try:
                self.preview(self.scope(holder))
            except d85.p3b.ActivationExerciseRefused as exc:
                preview_refused = str(exc)
            return grant, verify, compensation, preview_refused, checkpoint.compute()

        result = self.run_as(user, password, governance)
        self.assertNotIsInstance(result, Exception, repr(result))
        grant, verify, compensation, preview_refused, summary = result
        self.assertEqual(grant, {"account_id": holder.pk, "operation": "grant-technical-super-admin"})
        self.assertEqual(verify, "VERIFIED")
        self.assertIn(d85.EFFECTIVE, compensation)  # D-85 unchanged under the restricted account
        self.assertIn(d85.EFFECTIVE, preview_refused)
        self.assertTrue(all(has_technical_authority(holder, code) for code in d85.GOVERNANCE))
        self.assertEqual(summary["count"], AccessAuditLog.objects.count())

        receipts = list(AccessAuditLog.objects.order_by("pk").values())
        table = AccessAuditLog._meta.db_table

        def attempts():
            return {
                "update receipt": self.refused(f"UPDATE `{table}` SET reason='correction' WHERE access_audit_log_id=%s",
                                               [receipts[0]["access_audit_log_id"]]),
                "delete receipt": self.refused(f"DELETE FROM `{table}` WHERE access_audit_log_id=%s",
                                               [receipts[-1]["access_audit_log_id"]]),
                "truncate": self.refused(f"TRUNCATE TABLE `{table}`"),
                "drop": self.refused(f"DROP TABLE `{table}`"),
                "alter": self.refused(f"ALTER TABLE `{table}` ADD COLUMN r2_probe INT NULL"),
                "create trigger": self.refused(
                    f"CREATE TRIGGER r2_probe BEFORE UPDATE ON `{table}` FOR EACH ROW SET NEW.reason = NEW.reason"),
                "create table": self.refused("CREATE TABLE r2_probe (id INT)"),
                "create user": self.refused("CREATE USER 'r2_probe_user'@'localhost'"),
                "grant": self.refused(f"GRANT SELECT ON `{schema}`.* TO 'root'@'localhost'"),
                "insert receipt": self.refused(
                    f"INSERT INTO `{table}` (actor_account_id, action, reason) VALUES (%s, 'r2.probe', 'correction')",
                    [self.actor.pk]),
                "update another table": self.refused("UPDATE roles SET description = description WHERE role_id = 0"),
            }

        def grants():
            with connection.cursor() as cursor:
                cursor.execute("SHOW GRANTS")
                return " ".join(row[0] for row in cursor.fetchall()).upper()
        granted = self.run_as(user, password, grants)
        for privilege in ("TRIGGER", "SUPER", "ALL PRIVILEGES", "GRANT OPTION", "CREATE USER", "DROP", "ALTER"):
            self.assertNotIn(privilege, granted)
        codes = self.run_as(user, password, attempts)
        for name in ("update receipt", "delete receipt", "truncate", "drop", "alter", "create trigger", "create table",
                     "create user", "grant"):
            self.assertIn(codes[name], DENIED, f"{name} must be refused by privilege: {codes[name]}")
        self.assertIsNone(codes["insert receipt"])  # INSERT stays possible: the account cannot forbid forgery
        self.assertIsNone(codes["update another table"])
        AccessAuditLog.objects.filter(action="r2.probe").delete()  # test cleanup with the privileged runner account
        self.assertEqual(list(AccessAuditLog.objects.order_by("pk").values()), receipts)

    def test_locking_reads_on_receipts_need_lock_tables_not_update(self):
        schema = self.database()
        self.release()
        without, password_without = self.temporary_account(self.runtime_grants(schema, lock_tables=False))
        with_lock, password_with = self.temporary_account(self.runtime_grants(schema))
        sql = f"SELECT access_audit_log_id FROM `{AccessAuditLog._meta.db_table}` ORDER BY 1 FOR UPDATE"

        def locked_read():
            with transaction.atomic():
                return self.refused(sql)
        self.assertIn(self.run_as(without, password_without, locked_read), DENIED)
        self.assertIsNone(self.run_as(with_lock, password_with, locked_read))

    def test_the_verifier_needs_only_select_on_the_receipts(self):
        self.release()
        schema = self.database()
        user, password = self.temporary_account([f"GRANT SELECT ON `{schema}`.`{AccessAuditLog._meta.db_table}` TO {{user}}"])
        expected = checkpoint.compute()
        self.assertEqual(self.run_as(user, password, checkpoint.compute), expected)
        self.assertIn(self.run_as(user, password, lambda: self.refused("SELECT COUNT(*) FROM roles")), DENIED)

    def test_migrations_run_only_under_the_separate_migration_account(self):
        schema = self.database()
        target = self.temporary_database("r2mig")
        migrate_user, migrate_password = self.temporary_account([
            f"GRANT CREATE, ALTER, DROP, INDEX, REFERENCES, SELECT, INSERT, UPDATE, DELETE ON `{target}`.* TO {{user}}"])
        runtime_user, runtime_password = self.temporary_account(self.runtime_grants(schema))
        from django.contrib.contenttypes.models import ContentType
        self.addCleanup(ContentType.objects.clear_cache)  # the migrated database's content-type IDs must not leak
        result = self.run_with({"NAME": target, "USER": migrate_user, "PASSWORD": migrate_password},
                               lambda: call_command("migrate", verbosity=0, interactive=False))
        self.assertNotIsInstance(result, Exception, repr(result))
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                           [target, AccessAuditLog._meta.db_table])
            self.assertEqual(cursor.fetchone()[0], 1)
        self.assertIn(self.run_as(runtime_user, runtime_password,
                                  lambda: self.refused("CREATE TABLE r2_probe_migration (id INT)")), DENIED)
        self.assertIn(self.run_as(migrate_user, migrate_password,
                                  lambda: self.refused(f"SELECT COUNT(*) FROM `{schema}`.`roles`")), DENIED)



class CheckpointTests(Harness):
    table = AccessAuditLog._meta.db_table

    def setUp(self):
        super().setUp()
        self.release(*SCHOOL_PHASES)
        self.trusted = checkpoint.parse(json.dumps(checkpoint.compute()))

    def assertMismatch(self, trusted=None, **kwargs):
        with self.assertRaises(checkpoint.CheckpointMismatch):
            checkpoint.verify(trusted or self.trusted, **kwargs)

    def receipt(self, **overrides):
        with transaction.atomic():
            record_access_audit(actor=self.actor, action=overrides.pop("action", "workspace.r2.test"),
                                reason="correction", **overrides)
        return AccessAuditLog.objects.order_by("-pk").first()

    def test_unchanged_receipts_verify_and_the_digest_is_stable(self):
        self.assertEqual(checkpoint.compute(), checkpoint.compute())
        self.assertEqual(checkpoint.verify(self.trusted), {"result": "VERIFIED", "anchored": self.trusted["count"],
                                                           "unanchored_newer": 0})
        self.receipt()
        self.assertEqual(checkpoint.verify(self.trusted)["unanchored_newer"], 1)  # newer rows: reported, not verified

    def test_field_timestamp_and_identity_changes_are_detected(self):
        first, last = AccessAuditLog.objects.order_by("pk").first(), AccessAuditLog.objects.order_by("pk").last()
        for label, change in (
                ("reason", lambda: AccessAuditLog.objects.filter(pk=first.pk).update(reason="correction")),
                ("new_value", lambda: AccessAuditLog.objects.filter(pk=first.pk).update(new_value={"is_active": False})),
                ("actor", lambda: AccessAuditLog.objects.filter(pk=first.pk).update(actor_account=self.student)),
                ("timestamp", lambda: AccessAuditLog.objects.filter(pk=first.pk).update(
                    created_at=datetime(2000, 1, 1, tzinfo=dt_timezone.utc))),
                ("renumbered", lambda: AccessAuditLog.objects.filter(pk=last.pk).update(access_audit_log_id=last.pk + 1000)),
        ):
            with self.subTest(label):
                before = list(AccessAuditLog.objects.order_by("pk").values())
                change()
                self.assertMismatch()
                AccessAuditLog.objects.all().delete()  # restore the exact rows (privileged test-only cleanup)
                AccessAuditLog.objects.bulk_create([AccessAuditLog(**row) for row in before])
                checkpoint.verify(self.trusted)

    def test_deleted_middle_and_newest_receipts_are_detected(self):
        ids = list(AccessAuditLog.objects.order_by("pk").values_list("pk", flat=True))
        for label, pk in (("middle", ids[len(ids) // 2]), ("newest anchored", ids[-1])):
            with self.subTest(label):
                row = AccessAuditLog.objects.filter(pk=pk).values().get()
                AccessAuditLog.objects.filter(pk=pk).delete()
                self.assertMismatch()
                AccessAuditLog.objects.create(**row)
                checkpoint.verify(self.trusted)

    def test_forged_and_duplicate_receipts_inside_the_checkpoint_range_are_detected(self):
        # A rolled-back transaction consumes an ID: a gap inside the next checkpoint's range.
        try:
            with transaction.atomic():
                record_access_audit(actor=self.actor, action="workspace.r2.test", reason="correction")
                raise RuntimeError("roll back")
        except RuntimeError:
            pass
        anchor = self.receipt()
        trusted = checkpoint.parse(json.dumps(checkpoint.compute()))
        gap = anchor.pk - 1
        self.assertFalse(AccessAuditLog.objects.filter(pk=gap).exists())
        for label, row in (("forged", {"action": "framework.role.assign", "reason": "assignment_change"}),
                           ("duplicate", {k: v for k, v in AccessAuditLog.objects.filter(pk=anchor.pk).values().get().items()
                                          if k not in ("access_audit_log_id", "created_at")})):
            with self.subTest(label):
                AccessAuditLog.objects.create(access_audit_log_id=gap, **{"actor_account_id": self.actor.pk, **row})
                self.assertMismatch(trusted)
                AccessAuditLog.objects.filter(pk=gap).delete()
                checkpoint.verify(trusted)
        # Limit of the design: a forged receipt AFTER the checkpoint is only reported as unanchored.
        self.receipt(action="framework.role.assign")
        self.assertEqual(checkpoint.verify(trusted)["unanchored_newer"], 1)

    def test_malformed_or_unauthenticated_checkpoints_fail_closed(self):
        good = checkpoint.compute()
        for label, text in (("not json", "{"), ("list", "[]"), ("extra field", json.dumps({**good, "x": 1})),
                            ("missing field", json.dumps({k: v for k, v in good.items() if k != "head"})),
                            ("version", json.dumps({**good, "version": "v0"})),
                            ("bool count", json.dumps({**good, "count": True})),
                            ("negative", json.dumps({**good, "count": -1})),
                            ("count without rows", json.dumps({**good, "max_id": 0})),
                            ("head", json.dumps({**good, "head": "ABC"})),
                            ("hmac", json.dumps({**good, "hmac": "zz"})),
                            ("nan", '{"version": "%s", "count": NaN, "max_id": 1, "head": "%s"}' % (good["version"], good["head"]))):
            with self.subTest(label), self.assertRaises(checkpoint.CheckpointError):
                checkpoint.parse(text)
        signed = checkpoint.parse(json.dumps(checkpoint.compute(key=TEST_KEY)))
        self.assertEqual(checkpoint.verify(signed, key=TEST_KEY)["result"], "VERIFIED")
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.verify(signed)  # an authenticated checkpoint needs its key
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.verify(self.trusted, key=TEST_KEY)  # and an unauthenticated one refuses a key
        with self.assertRaises(checkpoint.CheckpointMismatch):
            checkpoint.verify(signed, key=TEST_KEY[::-1])  # wrong key
        forged = {**signed, "head": "0" * 64}
        with self.assertRaises(checkpoint.CheckpointMismatch):
            checkpoint.verify(forged, key=TEST_KEY)  # a rewritten head without the key cannot carry a valid HMAC
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.compute(key=b"short")

    def test_a_restored_copy_verifies_and_a_tampered_restore_is_detected(self):
        target = self.temporary_database("r2restore")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE TABLE `{target}`.`{self.table}` LIKE `{self.database()}`.`{self.table}`")
            cursor.execute(f"INSERT INTO `{target}`.`{self.table}` SELECT * FROM `{self.database()}`.`{self.table}`")
        restored = {"NAME": target}  # same privileged test account, the restored disposable database
        self.assertEqual(self.run_with(restored, checkpoint.compute), checkpoint.compute())
        self.assertEqual(self.run_with(restored, lambda: checkpoint.verify(self.trusted))["result"], "VERIFIED")
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE `{target}`.`{self.table}` SET reason='correction' ORDER BY access_audit_log_id LIMIT 1")
        self.assertIsInstance(self.run_with(restored, lambda: checkpoint.verify(self.trusted)), checkpoint.CheckpointMismatch)

    def test_concurrent_inserts_and_a_late_committing_lower_id(self):
        # (a) Inserts committing while checkpoints are taken: each checkpoint is internally consistent and verifies.
        stop, taken = threading.Event(), []

        def writer():
            try:
                while not stop.is_set():
                    with transaction.atomic():
                        record_access_audit(actor=self.actor, action="workspace.r2.test", reason="correction")
            finally:
                connections.close_all()
        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            for _ in range(5):
                taken.append(checkpoint.compute())
        finally:
            stop.set()
            thread.join(JOIN)
        self.assertFalse(thread.is_alive())
        for summary in taken:
            self.assertEqual(checkpoint.verify(checkpoint.parse(json.dumps(summary)))["result"], "VERIFIED")
        # (b) A lower ID still uncommitted when the checkpoint is taken: fails closed later (needs a quiescent window).
        inserted, release = threading.Event(), threading.Event()

        def slow():
            try:
                with transaction.atomic():
                    record_access_audit(actor=self.actor, action="workspace.r2.test", reason="correction")
                    inserted.set()
                    release.wait(30)
            finally:
                connections.close_all()
        late = threading.Thread(target=slow, daemon=True)
        late.start()
        self.assertTrue(inserted.wait(30))
        self.receipt()  # a higher ID commits first
        early = checkpoint.parse(json.dumps(checkpoint.compute()))
        release.set()
        late.join(JOIN)
        self.assertFalse(late.is_alive())
        self.assertMismatch(early)

    def test_a_failed_operation_leaves_no_receipt_and_the_checkpoint_unchanged(self):
        before = checkpoint.compute()
        target = self.account("0042301", "Instructor")
        original = framework_roles.record_access_audit_receipt

        def failing(**kwargs):
            if kwargs.get("action") == framework_roles.BINDING_CREATE:
                raise RuntimeError("injected audit failure")
            return original(**kwargs)

        from unittest.mock import patch
        with patch.object(framework_roles, "record_access_audit_receipt", failing), self.assertRaises(RuntimeError):
            self.configure("grant-technical-super-admin", target)
        self.assertEqual(checkpoint.compute(), before)
        self.assertFalse(Role.objects.filter(role_name=d85.TSA).exists())

    def test_the_verifier_is_read_only_and_its_command_output_has_no_receipt_data_or_secrets(self):
        before = self.everything()
        with transaction.atomic(), self.assertRaises(checkpoint.CheckpointError):
            checkpoint.compute()  # refuses to run inside another transaction
        out = StringIO()
        call_command("report_access_audit_checkpoint", stdout=out)
        printed = json.loads(out.getvalue())
        self.assertEqual(set(printed), {"version", "count", "max_id", "head"})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trusted.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(out.getvalue())
            out = StringIO()
            call_command("report_access_audit_checkpoint", verify=path, stdout=out)
            self.assertEqual(json.loads(out.getvalue())["result"], "VERIFIED")
            os.environ["CTUG_R2_TEST_KEY"] = TEST_KEY.decode()
            self.addCleanup(os.environ.pop, "CTUG_R2_TEST_KEY", None)
            out = StringIO()
            call_command("report_access_audit_checkpoint", hmac_key_env="CTUG_R2_TEST_KEY", stdout=out)
            self.assertNotIn(TEST_KEY.decode(), out.getvalue())
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{")
            with self.assertRaisesRegex(CommandError, "Refused"):
                call_command("report_access_audit_checkpoint", verify=path, stdout=StringIO())
        with self.assertRaisesRegex(CommandError, "not set"):
            call_command("report_access_audit_checkpoint", hmac_key_env="CTUG_R2_UNSET_VARIABLE", stdout=StringIO())
        text = out.getvalue()
        for secret in (self.actor.school_id, self.student.school_id, "workspace.review", "password"):
            self.assertNotIn(secret, text)
        self.assertEqual(self.everything(), before)
