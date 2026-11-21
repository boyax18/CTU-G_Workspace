"""No-Docker second-server proof using the real migrated Django application.

No normal settings, live server, real identity, production grant activation or
official ERD writes. Temporary certificates, keys and credentials are destroyed.
"""
from datetime import datetime, timedelta, timezone
import base64
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

from .g1d_p3c5_windows_pipe_fence_test_only import WindowsNamedPipeRehearsal, _client_options


def tls_fixture(directory):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    now = datetime.now(timezone.utc)
    root = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fictional disposable executor CA")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(root.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
          .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
          .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, None, None), True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(root.public_key()), False)
          .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root.public_key()), False)
          .sign(root, hashes.SHA256()))
    ca_path = directory / "ca.pem"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    result = {"ca": str(ca_path)}
    for label in ("server", "runtime", "operator"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)]))
                .issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, None, None), True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root.public_key()), False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if label == "server" else ExtendedKeyUsageOID.CLIENT_AUTH]), False)
                .sign(root, hashes.SHA256()))
        certificate, private_key = directory / (label + ".pem"), directory / (label + ".key")
        certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private_key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        result[label] = {"certificate": str(certificate), "private_key": str(private_key), "fingerprint": cert.fingerprint(hashes.SHA256()).hex()}
    return result


def run():
    if sys.flags.optimize:
        raise RuntimeError("Security verification requires enabled assertions.")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    driver = WindowsNamedPipeRehearsal(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "MySQL/MySQL Server 8.4/bin")
    children, checks = [], []
    try:
        driver._start()
        work = driver.work
        name = "test_ctug_executor_" + secrets.token_hex(8)
        driver._good("create_actual_schema", "root", f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        database = {"ENGINE": "django.db.backends.mysql", "NAME": name, "HOST": ".", "PORT": "3306",
                    "USER": "root", "PASSWORD": driver.root_password, "OPTIONS": {
                        "named_pipe": True, "unix_socket": driver.pipe,
                        "server_public_key_path": str(driver.data / "public_key.pem"),
                        "isolation_level": "read committed", "init_command": "SET time_zone = '+00:00'"}}
        root_file = work / "migration.json"
        root_file.write_text(json.dumps({"database": database, "datadir": str(driver.data)}))
        os.environ["WORKSPACE_ISOLATED_CONFIG"] = str(root_file)
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.executor_isolated_settings"
        os.environ["DJANGO_SECRET_KEY"] = secrets.token_hex(32)
        os.environ["WORKSPACE_OUTBOX_KEK_V1_B64"] = base64.b64encode(secrets.token_bytes(32)).decode()
        import django
        django.setup()
        from django.conf import settings
        from django.core.management import call_command
        from django.db import connection, connections, DatabaseError
        from django.test import override_settings
        from apps.accounts.models import Account, UserProfile
        from apps.accounts.services import register_account
        from apps.accounts.registration_review import approve_registration, reject_registration
        from apps.accounts.outbox_models import RegistrationNotificationOutbox
        from apps.access_control.models import Role, AccountRole, Service, Permission, RolePermission, AccountPermission, AccessAuditLog
        from apps.access_control import mutations
        from apps.access_control.executor.schema import statements, grants, VERSION
        from apps.access_control.executor.client import authenticate_actor, using_actor_proof, transport, remote_call
        from apps.access_control.executor.protocol import request
        from apps.access_control.executor.provisioning import before_hash
        from apps.access_control.executor.trust import DOMAIN, definition_hash
        from apps.access_control.protected_requests import canonical, digest
        from apps.access_control.tests_support.task2_signed_fixture_test_only import trust_fixture, request_fixture
        call_command("migrate", interactive=False, verbosity=0)
        print("Actual-schema stage: Django migrations applied", flush=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@server_uuid")
            uuid = cursor.fetchone()[0]
            cursor.execute("SHOW TABLES")
            migrated_tables = len(cursor.fetchall())
        checks.append("actual_django_migrations_applied")
        roles = {n: Role.objects.create(role_name=n) for n in ("Admin", "Student", "Instructor")}
        governance = Service.objects.create(service_code="access_control", service_name="Governance")
        accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
        records = Service.objects.create(service_code="fixture_records", service_name="Fixture records")
        password = "Fictional-River!92817"
        def account(school_id, role=None, pending=False):
            a = Account(school_id=school_id, email=school_id + "@example.invalid", is_active=not pending,
                        request_status="Pending" if pending else "Approved", requested_role=roles["Student"] if pending else None)
            a.set_password(password)
            a.save()
            UserProfile.objects.create(account=a, first_name="Fictional", last_name="Fixture")
            if role:
                AccountRole.objects.create(account=a, role=roles[role])
            return a
        operator, technical, school = (account("fixture-operator", "Admin"), account("fixture-technical", "Admin"), account("fixture-school", "Admin"))
        pending = [account("600000" + str(i), pending=True) for i in range(7)]
        # A synthetic approved target for the opt-in WF-03 actual-lease write test.
        # No change to the default historical rehearsal or its WF-02 safeguards.
        approved_lease_target = None
        if os.environ.get("CTUG_WF03_ACTUAL_LEASE_WRITE") == "1":
            if os.environ.get("CTUG_WF03_ACTUAL_FENCE_ONLY") != "1":
                raise RuntimeError("Isolated lease-write test requires WF-03 fence-only mode.")
            approved_lease_target = account("fixture-approved-lease-target", "Student")
        for code in ("accounts.registration_requests.approve", "accounts.registration_requests.reject", "accounts.role_assignments.manage"):
            p = Permission.objects.create(service=accounts, permission_code=code, permission_name="Fixture", module_name="registration_requests", action_name=code.rsplit(".", 1)[1])
            RolePermission.objects.create(role=roles["Admin"], permission=p)
        delegated = Permission.objects.create(service=governance, permission_code="access_control.delegate.fixture_records", permission_name="Fixture delegation", module_name="access_control", action_name="delegate")
        RolePermission.objects.create(role=roles["Admin"], permission=delegated)
        read = Permission.objects.create(service=records, permission_code="fixture.records.read", permission_name="Fixture read", module_name="records", action_name="read")
        policy = {"fixture_records": {"authority_permission": delegated.permission_code,
                  "permission_codes": [read.permission_code], "role_names": ["Student", "Instructor"]}}
        policy_hash = digest({"delegation": policy, "ordinary_assignment": {"Instructor": ["Student", "Instructor"]}})
        trust, keys = trust_fixture(name, operator.pk, int(time.time()))
        tls = tls_fixture(work)
        issuer_keys = {k: Ed25519PrivateKey.generate() for k in ("ordinary", "protected")}
        for kind, key in issuer_keys.items():
            (work / (kind + "-issuer.key")).write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        root = Ed25519PrivateKey.generate()
        roster = {k: getattr(trust, k) for k in ("schema", "incarnation", "epoch", "release_hash", "fence_hash", "recovery_hash")}
        roster.update(server_uuid=uuid, policy_hash=policy_hash, issued=int(time.time()), expires=int(time.time()) + 290,
                      signers=[{**s.__dict__, "public_key": s.public_key.hex()} for s in trust.signers],
                      issuers=[k.public_key().public_bytes_raw().hex() for k in issuer_keys.values()],
                      peers={tls["runtime"]["fingerprint"]: ["ordinary"], tls["operator"]["fingerprint"]: ["protected"]})
        roster_file = work / "roster.json"
        roster_file.write_bytes(canonical({"payload": roster, "signature": root.sign(DOMAIN + canonical(roster)).hex()}))
        credentials = {kind: ("wex_" + kind, secrets.token_hex(24)) for kind in ("runtime", "ordinary", "protected", "recovery", "notifications")}
        trust = replace(trust, fence_hash=digest({"ddl": statements(), "grants": grants(name, *(credentials[k][0] for k in ("runtime", "ordinary", "protected", "recovery")))}))
        roster["fence_hash"] = trust.fence_hash
        roster_file.write_bytes(canonical({"payload": roster, "signature": root.sign(DOMAIN + canonical(roster)).hex()}))
        with connection.cursor() as cursor:
            for kind, (user, pw) in credentials.items():
                cursor.execute(f"CREATE USER '{user}'@'localhost' IDENTIFIED BY %s", (pw,))
            for sql in statements():
                cursor.execute(sql)
            cursor.execute("INSERT INTO wex_control VALUES(1,%s,%s,%s,%s,%s,%s,0,%s,%s,%s)",
                           (trust.epoch, trust.incarnation, digest(roster), trust.fence_hash, trust.recovery_hash, trust.release_hash, VERSION, definition_hash(roster), roster["expires"]))
            for sql in grants(name, *(credentials[k][0] for k in ("runtime", "ordinary", "protected", "recovery"))):
                cursor.execute(sql)
        checks.append("review_schema_and_fences_installed_only_on_second_server")
        print("Actual-schema stage: grants and transaction fences installed", flush=True)
        # Windows mysqlclient's named-pipe full caching_sha2 exchange is not the
        # production TLS path. Prime each disposable user's authentication cache
        # with stock mysql.exe's explicit RSA exchange before exercising DML.
        for kind, (user, pw) in credentials.items():
            login = driver._invoke(_client_options(driver.bin, driver.pipe, user, False), "SELECT CURRENT_USER();", pw)
            assert login.returncode == 0 and login.stdout.strip() == user + "@localhost", "Disposable credential authentication failed"
        checks.append("separate_principals_authenticated_before_privilege_denial_tests")
        clients, configs = {}, {}
        for kind in ("ordinary", "protected"):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            db = copy.deepcopy(database)
            db["USER"], db["PASSWORD"] = credentials[kind]
            config = {"database": db, "isolated_test": True, "outbox_enabled": True, "server": {
                "kind": kind, "schema": name, "server_uuid": uuid, "minimum_epoch": 1,
                "policy_hash": policy_hash,
                "principal": credentials[kind][0] + "@localhost", "roster": str(roster_file),
                "root_public_key": root.public_key().public_bytes_raw().hex(), "issuer_private_key": str(work / (kind + "-issuer.key")),
                "host": "127.0.0.1", "port": port, "ca": tls["ca"],
                "certificate": tls["server"]["certificate"], "private_key": tls["server"]["private_key"],
                "isolated_datadir": str(driver.data), "isolated_pipe": driver.pipe,
            }}
            path = work / (kind + ".json")
            path.write_text(json.dumps(config))
            configs[kind] = path
            client = tls["runtime" if kind == "ordinary" else "operator"]
            clients[kind] = {"url": f"https://localhost:{port}", "ca": tls["ca"],
                             "certificate": client["certificate"], "private_key": client["private_key"],
                             "server_fingerprint": tls["server"]["fingerprint"]}
        # Swap only this disposable harness's ORM connection to runtime grants.
        connection.close()
        connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = credentials["runtime"]
        policy = {"fixture_records": {"authority_permission": delegated.permission_code,
                  "permission_codes": [read.permission_code], "role_names": ["Student", "Instructor"]}}
        # Executors get their own immutable server policy, never request policy.
        # Supplied through a deployment file, loaded before their first request.
        # See settings profile: each process reloads only at startup.
        for kind, path in configs.items():
            c = json.loads(path.read_text())
            c["delegation_policy"] = policy
            c["ordinary_assignment_policy"] = {"Instructor": ["Student", "Instructor"]}
            path.write_text(json.dumps(c))
        # Restart ensures configuration is fixed before accepting any requests.
        for child, log in children:
            child.terminate(); child.wait(timeout=10); log.close()
        children.clear()
        for kind, path in configs.items():
            env = {k: v for k, v in os.environ.items() if not k.startswith("DB_") and k not in {"WORKSPACE_ISOLATED_CONFIG", "MYSQL_PWD"}}
            env.update(WORKSPACE_EXECUTOR_CONFIG=str(path), DJANGO_SETTINGS_MODULE="config.executor_settings")
            log = (work / (kind + ".log")).open("ab")
            child = subprocess.Popen([sys.executable, "-B", "manage.py", "serve_workspace_executor", "--settings=config.executor_settings"], env=env,
                                     stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            children.append((child, log))
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True, WORKSPACE_EXECUTOR_CLIENTS=clients):
            deadline = time.monotonic() + 15
            while True:
                try:
                    school_auth = authenticate_actor(school.school_id, password)
                    break
                except Exception:
                    if time.monotonic() > deadline:
                        # Logs contain generic errors only; never print config/key data.
                        raise RuntimeError("Executor did not start: " + (work / "ordinary.log").read_text(errors="replace"))
                    time.sleep(0.1)
            checks.append("mtls_and_independent_actor_password_authentication")
            print("Actual-schema stage: mTLS and actor authentication passed", flush=True)
            # WF-03 Task 3: isolate actual-schema SQL fence checks from WF-02.03.
            # Registration approval is intentionally refused under protected
            # executor mode (D-51), irrespective of attestation. This branch
            # never attempts to change that restriction or create an approval.
            if os.environ.get("CTUG_WF03_ACTUAL_FENCE_ONLY") == "1":
                import MySQLdb
                from apps.access_control.executor.schema import FENCED, TABLES

                def _fence_db(principal):
                    user, pw = credentials[principal]
                    dbh = MySQLdb.connect(
                        host=".", user=user, passwd=pw, db=name,
                        named_pipe=True, unix_socket=driver.pipe,
                        server_public_key_path=str(driver.data / "public_key.pem"),
                        autocommit=True,
                    )
                    with dbh.cursor() as c:
                        c.execute("SELECT CURRENT_USER()")
                        assert c.fetchone()[0] == user + "@localhost"
                    return dbh

                def _must_deny(cursor, label, sql, params=()):
                    try:
                        cursor.execute(sql, params)
                    except (MySQLdb.Error, DatabaseError) as exc:
                        assert exc.args and exc.args[0] in {1142, 1143, 1227, 1370, 1644}, (
                            label, type(exc).__name__, exc.args[0] if exc.args else None
                        )
                        checks.append(label)
                        return
                    raise AssertionError(label + " unexpectedly succeeded")

                try:
                    assert len(FENCED) == 11 and "account_permission_role_scopes" in FENCED
                    # Inspection uses the root credential of the disposable
                    # second server. Runtime has intentionally no TRIGGER grant.
                    inspection = MySQLdb.connect(
                        host=".", user="root", passwd=driver.root_password, db=name,
                        named_pipe=True, unix_socket=driver.pipe,
                        server_public_key_path=str(driver.data / "public_key.pem"),
                        autocommit=True,
                    )
                    try:
                        with inspection.cursor() as c:
                            c.execute("SHOW TABLES")
                            present = {r[0] for r in c.fetchall()}
                            assert set(FENCED).issubset(present) and set(TABLES).issubset(present)
                            c.execute("SHOW TRIGGERS")
                            present_triggers = {r[0] for r in c.fetchall()}
                            expected_triggers = {
                                f"wex_{table}_{event}"
                                for table in FENCED
                                for event in ("insert", "update", "delete")
                            }
                            assert expected_triggers.issubset(present_triggers)
                    finally:
                        inspection.close()
                    checks.append("actual_11_table_fence_and_scope_triggers_installed")
                    with connection.cursor() as c:
                        c.execute("SELECT COUNT(*) FROM account_permission_role_scopes")
                        prior_scope_count = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM access_audit_logs")
                        prior_audit_count = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM role_permissions")
                        prior_role_grant_count = c.fetchone()[0]

                    # A successful TLS 1.3 client-certificate handshake and
                    # readiness response is read-only, not mutation authority.
                    assert transport("/ready", {})["epoch"] == trust.epoch
                    checks.append("isolated_executor_authenticated_ready")

                    runtime_db = _fence_db("runtime")
                    ordinary_db = _fence_db("ordinary")
                    protected_db = _fence_db("protected")
                    recovery_db = _fence_db("recovery")
                    try:
                        with runtime_db.cursor() as c:
                            _must_deny(c, "runtime_cannot_update_accounts", "UPDATE accounts SET is_active=1 WHERE account_id=%s", (pending[0].pk,))
                            _must_deny(c, "runtime_cannot_write_roles", "UPDATE roles SET is_active=1")
                            _must_deny(c, "runtime_cannot_write_role_permissions", "INSERT INTO role_permissions(role_id,permission_id,is_active) VALUES(%s,%s,1)", (roles["Student"].pk, read.pk))
                            _must_deny(c, "runtime_cannot_write_account_permissions", "INSERT INTO account_permissions(account_id,permission_id,effect,is_active) VALUES(%s,%s,'Grant',1)", (pending[0].pk,read.pk))
                            _must_deny(c, "runtime_cannot_write_scope_table", "INSERT INTO account_permission_role_scopes(account_permission_id,role_id) VALUES(%s,%s)", (999999,roles["Student"].pk))
                            _must_deny(c, "runtime_cannot_forge_audit", "INSERT INTO access_audit_logs(actor_account_id,action) VALUES(%s,'forged')", (operator.pk,))
                            _must_deny(c, "runtime_cannot_reset_executor_hold", "UPDATE wex_control SET halted=0")
                        with ordinary_db.cursor() as c:
                            _must_deny(c, "ordinary_cannot_mutate_accounts_without_lease", "UPDATE accounts SET is_active=1 WHERE account_id=%s", (pending[0].pk,))
                            _must_deny(c, "ordinary_cannot_mutate_role_grants_without_lease", "INSERT INTO role_permissions(role_id,permission_id,is_active) VALUES(%s,%s,1)", (roles["Student"].pk,read.pk))
                            _must_deny(c, "ordinary_cannot_mutate_scopes_without_lease", "INSERT INTO account_permission_role_scopes(account_permission_id,role_id) VALUES(%s,%s)", (999999,roles["Student"].pk))
                            _must_deny(c, "ordinary_cannot_forge_audit_without_lease", "INSERT INTO access_audit_logs(actor_account_id,action) VALUES(%s,'forged')", (operator.pk,))
                            _must_deny(c, "ordinary_cannot_modify_catalogue", "UPDATE roles SET is_active=0")
                            _must_deny(c, "ordinary_cannot_delete_audit", "DELETE FROM access_audit_logs")
                            _must_deny(c, "ordinary_cannot_alter_triggers", "DROP TRIGGER wex_accounts_update")
                            c.execute("SET @wex_request=%s", (secrets.token_hex(32),))
                            _must_deny(c, "forged_lease_name_does_not_grant_writer", "UPDATE accounts SET is_active=1 WHERE account_id=%s", (pending[0].pk,))
                        with protected_db.cursor() as c:
                            _must_deny(c, "protected_cannot_edit_roles_without_lease", "UPDATE roles SET is_active=0")
                            _must_deny(c, "protected_cannot_mutate_scopes_without_lease", "INSERT INTO account_permission_role_scopes(account_permission_id,role_id) VALUES(%s,%s)", (999999,roles["Student"].pk))
                        with recovery_db.cursor() as c:
                            _must_deny(c, "recovery_cannot_grant_permissions", "INSERT INTO role_permissions(role_id,permission_id,is_active) VALUES(%s,%s,1)", (roles["Student"].pk,read.pk))
                        with runtime_db.cursor() as c:
                            c.execute("SELECT request_status,is_active FROM accounts WHERE account_id=%s", (pending[0].pk,))
                            assert c.fetchone() == ("Pending", 0)
                            c.execute("SELECT COUNT(*) FROM account_permission_role_scopes")
                            assert c.fetchone() == (prior_scope_count,)
                            c.execute("SELECT COUNT(*) FROM access_audit_logs")
                            assert c.fetchone() == (prior_audit_count,)
                            c.execute("SELECT COUNT(*) FROM role_permissions")
                            assert c.fetchone() == (prior_role_grant_count,)
                        checks.append("negative_tests_leave_permission_audit_and_registration_state_unchanged")
                    finally:
                        runtime_db.close()
                        ordinary_db.close()
                        protected_db.close()
                        recovery_db.close()
                    # Positive test: ordinary executor must perform a real,
                    # authenticated, leased and audited WF-03.01 role assignment.
                    # This does NOT activate protected Technical Super Admin
                    # governance or the gated WF-03.03/.04 account mutations.
                    authorized_lease_write_tested = False
                    if os.environ.get("CTUG_WF03_ACTUAL_LEASE_WRITE") == "1":
                        from apps.access_control.executor.role_assignment import assign_ordinary_role
                        assert approved_lease_target is not None
                        target_id = approved_lease_target.pk
                        instructor_id = roles["Instructor"].pk
                        assert not AccountRole.objects.filter(
                            account_id=target_id, role_id=instructor_id
                        ).exists()
                        initial_audit_count = AccessAuditLog.objects.filter(
                            action="account.role.assign", actor_account_id=school.pk,
                            target_account_id=target_id
                        ).count()
                        with using_actor_proof(school_auth["proof"]):
                            assigned = assign_ordinary_role(
                                actor=school, target_id=target_id, role_id=instructor_id
                            )
                        assert assigned is True, "Authorized ordinary role assignment did not succeed"
                        checks.append("authorized_ordinary_executor_role_assignment_succeeded")

                        with connection.cursor() as c:
                            c.execute("SELECT COUNT(*) FROM account_roles WHERE account_id=%s AND role_id=%s",
                                      (target_id, instructor_id))
                            assert c.fetchone() == (1,)
                            c.execute("SELECT COUNT(*) FROM account_roles WHERE account_id=%s", (target_id,))
                            assert c.fetchone() == (2,), "The existing Student assignment must be retained"
                        assert AccessAuditLog.objects.filter(
                            action="account.role.assign", actor_account_id=school.pk,
                            target_account_id=target_id, role_id=instructor_id
                        ).count() == initial_audit_count + 1
                        checks.append("authorized_assignment_persisted_without_erasing_student_role")

                        # The runtime has no ledger-write privilege. Root is used
                        # for READ-ONLY inspection of this disposable server.
                        inspection = MySQLdb.connect(
                            host=".", user="root", passwd=driver.root_password, db=name,
                            named_pipe=True, unix_socket=driver.pipe,
                            server_public_key_path=str(driver.data / "public_key.pem"),
                            autocommit=True,
                        )
                        try:
                            with inspection.cursor() as c:
                                c.execute(
                                    "SELECT request_id,kind,principal,actor_id,status,epoch,result "
                                    "FROM wex_requests WHERE operation='role.assign'",
                                )
                                ledger_rows = c.fetchall()
                                assert len(ledger_rows) == 1, "Exactly one leased assignment request expected"
                                request_id, kind, principal, actor_id, status, epoch, raw_result = ledger_rows[0]
                                assert (kind, principal, actor_id, status, epoch) == (
                                    "ordinary", credentials["ordinary"][0] + "@localhost",
                                    school.pk, "APPLIED", trust.epoch,
                                ), "Executor ledger identity/status/epoch mismatch"
                                receipt = json.loads(raw_result) if isinstance(raw_result, (str, bytes)) else raw_result
                                assert isinstance(receipt, dict)
                                assert receipt.get("request_id") == request_id and receipt.get("value") is True
                                assert isinstance(receipt.get("executor_signature"), str)
                                checks.append("authorized_request_has_applied_executor_ledger_and_receipt")
                                c.execute(
                                    "SELECT a.access_audit_log_id,a.actor_account_id,a.target_account_id,"
                                    "a.role_id,a.action FROM wex_audits l "
                                    "JOIN access_audit_logs a ON a.access_audit_log_id=l.audit_id "
                                    "WHERE l.request_id=%s", (request_id,),
                                )
                                linked = c.fetchall()
                                assert len(linked) == 1, "An authorized assignment needs one linked audit event"
                                audit_id, audit_actor, audit_target, audit_role, audit_action = linked[0]
                                assert (audit_actor, audit_target, audit_role, audit_action) == (
                                    school.pk, target_id, instructor_id, "account.role.assign",
                                )
                                assert receipt.get("audit_ids") == [audit_id]
                                checks.append("authorized_ledger_receipt_links_real_append_only_audit")
                        finally:
                            inspection.close()
                        authorized_lease_write_tested = True
                    return {
                        "mode": "WF03_ACTUAL_SCHEMA_FENCE_ONLY",
                        "verified_checks": len(checks),
                        "checks": checks,
                        "application_tables_migrated": migrated_tables,
                        "wf02_approval_unmodified_and_not_tested": True,
                        "authorized_executor_writes_tested": authorized_lease_write_tested,
                        "authorized_executor_operations": ["role.assign"] if authorized_lease_write_tested else [],
                        "protected_governance_writes_tested": False,
                        "production_release_authorized": False,
                        "official_erd_changed": False,
                    }
                except Exception:
                    # Let the enclosing cleanup stop both temporary executor
                    # processes, close connections, and destroy the temp DB.
                    raise

            with using_actor_proof(school_auth["proof"]):
                assert approve_registration(actor=school, target_id=pending[0].pk) == pending[0].pk
            assert Account.objects.get(pk=pending[0].pk).is_active
            assert RegistrationNotificationOutbox.objects.count() == 1
            checks.append("existing_registration_approval_assignment_audit_outbox_atomic")
            print("Actual-schema stage: existing approval and outbox committed", flush=True)
            # Execute protected P4/P5 through the same production implementation.
            privileged = authenticate_actor(operator.school_id, password, kind="protected")
            for target_id in (None, technical.pk):
                b = request_fixture(trust, keys, operator.pk, now=int(time.time()), before_hash=before_hash(), target_id=target_id)
                env = request(b["request"]["operation"], {"bundle": b}, privileged["proof"])
                env.update(request_id=b["request"]["request_id"], nonce=b["request"]["nonce"])
                transport("/execute", env, kind="protected")
                checks.append("protected_role_provisioned_inactive" if target_id is None else "protected_initial_bootstrap_composes_admin_and_explicit_core")
            technical_auth = authenticate_actor(technical.school_id, password)
            with using_actor_proof(technical_auth["proof"]):
                assert mutations.grant_role_permission(actor=technical, role=roles["Student"], permission=read)
                assert mutations.grant_account_permission(actor=technical, target=pending[0], permission=read)
            checks.append("existing_role_and_account_permission_mutations_via_restricted_executor")
            with using_actor_proof(school_auth["proof"]):
                reject_registration(actor=school, target_id=pending[1].pk, rejection_code="duplicate_request")
            assert not Account.objects.filter(pk=pending[1].pk).exists()
            assert not UserProfile.objects.filter(account_id=pending[1].pk).exists()
            rejection = AccessAuditLog.objects.get(action="account.registration.reject", new_value__account_id=pending[1].pk)
            assert rejection.target_account_id is None and rejection.new_value["account_deleted"] is True
            checks.append("registration_rejection_deletes_account_profile_and_preserves_audit_via_executor")
            public_data = {"school_id": "7000001", "email": "fictional@example.invalid", "first_name": "Fictional", "last_name": "Applicant",
                           "middle_name": "", "suffix": "", "requested_role": "Student", "password": password, "password_confirmation": password}
            register_account(public_data)
            submitted = Account.objects.get(school_id="7000001")
            assert not submitted.is_active and submitted.request_status == "Pending" and not AccountRole.objects.filter(account=submitted).exists()
            checks.append("existing_public_registration_works_without_runtime_account_write_grant")
            register_account({**public_data, "school_id": pending[1].school_id, "email": pending[1].email})
            replacement = Account.objects.get(school_id=pending[1].school_id)
            assert replacement.pk != pending[1].pk and replacement.request_status == "Pending"
            assert not replacement.is_active and UserProfile.objects.filter(account=replacement).exists()
            checks.append("rejected_applicant_can_register_again_without_previous_credentials_or_token")
            from apps.access_control.executor.role_assignment import assign_ordinary_role
            with using_actor_proof(school_auth["proof"]):
                assert assign_ordinary_role(actor=school, target_id=pending[0].pk, role_id=roles["Instructor"].pk)
            checks.append("authorized_school_admin_ordinary_role_assignment")
            def refused(label, sql, params=()):
                try:
                    with connection.cursor() as c:
                        c.execute(sql, params)
                except Exception as exc:
                    assert exc.args[0] in {1142, 1143, 1370, 1644}, (label, type(exc).__name__)
                    checks.append(label)
                    return
                raise AssertionError(label + " unexpectedly succeeded")
            for label, sql in (
                ("runtime_direct_approval_denied", "UPDATE accounts SET is_active=1,request_status='Approved' WHERE account_id=" + str(pending[2].pk)),
                ("runtime_direct_account_deletion_denied", "DELETE FROM accounts WHERE account_id=" + str(pending[2].pk)),
                ("runtime_direct_profile_deletion_denied", "DELETE FROM users WHERE account_id=" + str(pending[2].pk)),
                ("runtime_direct_account_password_hijack_denied", "UPDATE accounts SET password_hash='forged' WHERE account_id=" + str(technical.pk)),
                ("runtime_direct_role_assignment_denied", f"INSERT INTO account_roles(account_id,role_id) VALUES({pending[2].pk},{roles['Admin'].pk})"),
                ("runtime_direct_role_grant_denied", f"UPDATE role_permissions SET is_active=1"),
                ("runtime_direct_override_denied", "UPDATE account_permissions SET effect='Grant'"),
                ("runtime_catalogue_edit_denied", "UPDATE permissions SET module_name='forged'"),
                ("runtime_role_edit_denied", "UPDATE roles SET is_active=1"),
                ("runtime_service_edit_denied", "UPDATE services SET is_active=1"),
                ("runtime_audit_forgery_denied", f"INSERT INTO access_audit_logs(actor_account_id,action) VALUES({technical.pk},'forged')"),
                ("runtime_ledger_forgery_denied", "UPDATE wex_requests SET status='APPLIED'"),
                ("runtime_epoch_or_hold_bypass_denied", "UPDATE wex_control SET halted=0"),
                ("runtime_drop_trigger_denied", "DROP TRIGGER wex_roles_update"),
            ):
                refused(label, sql)
            with using_actor_proof(school_auth["proof"]):
                try:
                    mutations.grant_role_permission(actor=school, role=roles["Student"], permission=read)
                    raise AssertionError("School Admin governed access control")
                except Exception as exc:
                    assert not isinstance(exc, AssertionError)
            checks.append("school_admin_management_denied_in_dispatch")
            from apps.access_control.writer_boundary import WriterBoundaryUnavailable
            from apps.access_control.executor.errors import ExecutionDenied, AuthenticationDenied
            def denied_call(label, callback, expected=(WriterBoundaryUnavailable, ExecutionDenied)):
                try:
                    callback()
                except expected:
                    checks.append(label)
                    return
                raise AssertionError(label + " unexpectedly succeeded")

            denied_call("wrong_password_cannot_obtain_actor_proof", lambda: authenticate_actor(school.school_id, "wrong-password"), (AuthenticationDenied,))
            unpinned = copy.deepcopy(clients)
            unpinned["ordinary"]["server_fingerprint"] = "0" * 64
            with override_settings(WORKSPACE_EXECUTOR_CLIENTS=unpinned):
                denied_call("wrong_server_certificate_pin_denied", lambda: transport("/ready", {}))
            wrong_peer = copy.deepcopy(clients)
            wrong_peer["protected"] = {**clients["protected"], "certificate": tls["runtime"]["certificate"], "private_key": tls["runtime"]["private_key"]}
            with override_settings(WORKSPACE_EXECUTOR_CLIENTS=wrong_peer):
                denied_call("runtime_certificate_cannot_enter_protected_executor", lambda: transport("/ready", {}, kind="protected"))
            import ssl, http.client
            from urllib.parse import urlsplit
            ordinary_url = urlsplit(clients["ordinary"]["url"])
            no_certificate = http.client.HTTPSConnection("localhost", ordinary_url.port, context=ssl.create_default_context(cafile=tls["ca"]), timeout=5)
            try:
                denied_call("missing_client_certificate_denied", lambda: (no_certificate.request("POST", "/ready", b"{}", {"Content-Length": "2"}), no_certificate.getresponse()), (ssl.SSLError, ConnectionError))
            finally:
                no_certificate.close()

            def approve_envelope(target):
                return request("registration.approve", {"actor_id": school.pk, "target_id": target.pk, "rejection_code": None}, school_auth["proof"])
            e = approve_envelope(pending[2])
            committed = transport("/execute", e)
            denied_call("exact_request_replay_denied", lambda: transport("/execute", e))
            receipt = transport("/receipt", {"request_id": e["request_id"], "request_hash": committed["request_hash"], "proof": school_auth["proof"]})
            assert receipt["status"] == "APPLIED" and receipt["result"]["audit_ids"] == committed["audit_ids"]
            checks.append("lost_response_reconciles_durable_result_without_reexecution")
            from concurrent.futures import ThreadPoolExecutor
            e = approve_envelope(pending[3])
            def concurrent():
                try:
                    return transport("/execute", e)
                except (WriterBoundaryUnavailable, ExecutionDenied):
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: concurrent(), range(2)))
            assert sum(r is not None for r in results) == 1
            assert AccessAuditLog.objects.filter(target_account=pending[3], action="account.registration.approve").count() == 1
            checks.append("concurrent_network_replay_has_one_commit_and_one_audit")

            import MySQLdb
            def raw(kind):
                user, pw = ("root", driver.root_password) if kind == "root" else credentials[kind]
                return MySQLdb.connect(host=".", user=user, passwd=pw, db=name, named_pipe=True, unix_socket=driver.pipe,
                    server_public_key_path=str(driver.data / "public_key.pem"), autocommit=True)
            def denied_sql(cursor, label, sql, params=(), errors=(1142, 1143, 1644)):
                try:
                    cursor.execute(sql, params)
                except (MySQLdb.Error, DatabaseError) as exc:
                    assert exc.args[0] in errors, (label, exc.args[0])
                    checks.append(label)
                    return
                raise AssertionError(label + " unexpectedly succeeded")
            ordinary_db = raw("ordinary")
            try:
                with ordinary_db.cursor() as c:
                    denied_sql(c, "ordinary_database_credential_without_lease_denied", "UPDATE accounts SET is_active=1 WHERE account_id=%s", (pending[4].pk,), (1644,))
                    denied_sql(c, "ordinary_account_delete_without_lease_denied", "DELETE FROM accounts WHERE account_id=%s", (pending[4].pk,), (1644,))
                    denied_sql(c, "ordinary_profile_delete_without_lease_denied", "DELETE FROM users WHERE account_id=%s", (pending[4].pk,), (1644,))
                    columns = "request_id,nonce,request_hash,operation,kind,principal,peer,actor_id,connection_id,claim_hash,epoch,incarnation,evidence,status,issued,expires"
                    values = (secrets.token_hex(32), secrets.token_hex(32), "0" * 64, "role.assign", "protected", "wex_ordinary@localhost", tls["runtime"]["fingerprint"], school.pk, "0" * 64, trust.epoch, trust.incarnation, b"{}", int(time.time()), int(time.time()) + 60)
                    sql = "INSERT INTO wex_requests(" + columns + ") VALUES(%s,%s,%s,%s,%s,%s,%s,%s,CONNECTION_ID(),%s,%s,%s,%s,'CLAIMED',%s,%s)"
                    denied_sql(c, "ordinary_cannot_forge_protected_ledger_identity", sql, values, (1644,))
                    ordinary_values = (*values[:4], "ordinary", *values[5:])
                    c.execute(sql, ordinary_values)
                    c.execute("UPDATE wex_requests SET status='ATTEMPTED' WHERE request_id=%s", (ordinary_values[0],))
                    c.execute("SET @wex_request=%s", (ordinary_values[0],))
                    denied_sql(c, "ordinary_unrelated_operation_cannot_delete_account", "DELETE FROM accounts WHERE account_id=%s", (pending[4].pk,), (1644,))
                    denied_sql(c, "ordinary_unrelated_operation_cannot_delete_profile", "DELETE FROM users WHERE account_id=%s", (pending[4].pk,), (1644,))
                    denied_sql(c, "ordinary_cannot_delete_approved_account", "DELETE FROM accounts WHERE account_id=%s", (pending[0].pk,), (1644,))
                    denied_sql(c, "ordinary_active_lease_cannot_assign_admin", "INSERT INTO account_roles(account_id,role_id,assigned_by) VALUES(%s,%s,%s)", (pending[4].pk, roles["Admin"].pk, school.pk), (1644,))
                    denied_sql(c, "ordinary_active_lease_cannot_grant_governance", "INSERT INTO account_permissions(account_id,permission_id,effect,is_active) SELECT %s,permission_id,'Grant',1 FROM permissions WHERE permission_code='access_control.audit.read'", (pending[0].pk,), (1644,))
                    denied_sql(c, "ordinary_active_lease_cannot_hijack_technical_password", "UPDATE accounts SET password_hash='forged' WHERE account_id=%s", (technical.pk,), (1644,))
                    denied_sql(c, "ordinary_cannot_reset_evidence_state", "UPDATE wex_requests SET status='CLAIMED' WHERE request_id=%s", (ordinary_values[0],), (1644,))
                    denied_sql(c, "ordinary_cannot_forge_release_or_revocation_floor", "UPDATE wex_control SET epoch=2", (), (1142,))
            finally:
                ordinary_db.close()

            # Force an audit failure, proving account/assignment/outbox rollback
            # while the separately committed one-use attempt remains durable.
            admin_db = raw("root")
            with admin_db.cursor() as c:
                c.execute("CREATE TRIGGER fixture_audit_failure BEFORE INSERT ON access_audit_logs FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='fictional audit interruption'")
            failure = approve_envelope(pending[4])
            outbox_count = RegistrationNotificationOutbox.objects.count()
            denied_call("audit_interruption_refuses_success", lambda: transport("/execute", failure))
            assert Account.objects.get(pk=pending[4].pk).request_status == "Pending"
            assert not AccountRole.objects.filter(account=pending[4]).exists()
            assert RegistrationNotificationOutbox.objects.count() == outbox_count
            with admin_db.cursor() as c:
                c.execute("DROP TRIGGER fixture_audit_failure")
                c.execute("SELECT status,result FROM wex_requests WHERE request_id=%s", (failure["request_id"],))
                assert c.fetchone() == ("ATTEMPTED", None)
            checks.append("audit_failure_rolls_back_account_role_audit_outbox_but_keeps_attempt")

            # Kill only this harness's ordinary Python service while it waits for
            # a real target-row lock after its ATTEMPTED commit.
            blocker = raw("root")
            blocker.autocommit(False)
            with blocker.cursor() as c:
                c.execute("SELECT account_id FROM accounts WHERE account_id=%s FOR UPDATE", (pending[5].pk,))
            interrupted = approve_envelope(pending[5])
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(transport, "/execute", interrupted)
                deadline = time.monotonic() + 8
                while True:
                    with admin_db.cursor() as c:
                        c.execute("SELECT status FROM wex_requests WHERE request_id=%s", (interrupted["request_id"],))
                        row = c.fetchone()
                    if row == ("ATTEMPTED",):
                        break
                    assert time.monotonic() < deadline, "No persisted attempt observed before interruption"
                    time.sleep(0.05)
                children[0][0].terminate(); children[0][0].wait(timeout=10)
                blocker.rollback(); blocker.close()
                try:
                    future.result(timeout=12)
                    raise AssertionError("Interrupted server returned success")
                except WriterBoundaryUnavailable:
                    pass
            assert Account.objects.get(pk=pending[5].pk).request_status == "Pending"
            with admin_db.cursor() as c:
                c.execute("SELECT status,result FROM wex_requests WHERE request_id=%s", (interrupted["request_id"],))
                assert c.fetchone() == ("ATTEMPTED", None)
            checks.append("actual_executor_process_interruption_preserves_hold_and_rolls_back")
            # Restart with the same persistent schema/trust; requests cannot be
            # silently re-executed after a process restart.
            env = {k: v for k, v in os.environ.items() if not k.startswith("DB_") and k not in {"WORKSPACE_ISOLATED_CONFIG", "MYSQL_PWD"}}
            env.update(WORKSPACE_EXECUTOR_CONFIG=str(configs["ordinary"]), DJANGO_SETTINGS_MODULE="config.executor_settings")
            log = (work / "ordinary-restart.log").open("wb")
            restarted = subprocess.Popen([sys.executable, "-B", "manage.py", "serve_workspace_executor", "--settings=config.executor_settings"], env=env,
                stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            children.append((restarted, log))
            deadline = time.monotonic() + 10
            while True:
                try:
                    transport("/ready", {})
                    break
                except WriterBoundaryUnavailable:
                    assert time.monotonic() < deadline, "Executor restart failed"
                    time.sleep(0.1)
            held = transport("/receipt", {"request_id": interrupted["request_id"], "request_hash": digest(__import__("apps.access_control.executor.engine", fromlist=["evidence"]).evidence(interrupted)), "proof": school_auth["proof"]})
            assert held["status"] == "HOLD"
            denied_call("interrupted_request_cannot_replay_after_process_restart", lambda: transport("/execute", interrupted))
            checks.append("restarted_executor_reconciles_unfinished_work_as_hold")
            from apps.access_control.executor.recovery import RecoveryControl
            recovery_config = {**json.loads(configs["ordinary"].read_text())["server"], "principal": credentials["recovery"][0] + "@localhost"}
            def as_recovery(function):
                connection.close()
                connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = credentials["recovery"]
                try:
                    return function(RecoveryControl(recovery_config))
                finally:
                    connection.close()
                    connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = credentials["runtime"]
            as_recovery(lambda control: control.hold("a" * 64))
            denied_call("recovery_hold_fences_new_network_writes", lambda: transport("/execute", approve_envelope(pending[6])))
            roster.update(epoch=2, incarnation=secrets.token_hex(32), issued=int(time.time()), expires=int(time.time()) + 290)
            approved_roster = {"payload": roster, "signature": root.sign(DOMAIN + canonical(roster)).hex()}
            roster_file.write_bytes(canonical({**approved_roster, "signature": "0" * 128}))
            from apps.access_control.protected_requests import ProtectedRequestRefused
            denied_call("recovery_refuses_untrusted_roster_rotation", lambda: as_recovery(lambda control: control.rotate("b" * 64)), (ProtectedRequestRefused,))
            roster_file.write_bytes(canonical(approved_roster))
            as_recovery(lambda control: control.rotate("c" * 64))
            checks.append("root_approved_recovery_rotates_epoch_and_incarnation_with_durable_event")
            denied_call("revoked_old_actor_proof_cannot_authorize_after_rotation", lambda: transport("/execute", approve_envelope(pending[6])))
            new_auth = authenticate_actor(school.school_id, password)
            transport("/execute", request("registration.approve", {"actor_id": school.pk, "target_id": pending[6].pk, "rejection_code": None}, new_auth["proof"]))
            checks.append("fresh_authentication_works_after_explicit_recovery_rotation")
            with admin_db.cursor() as c:
                c.execute("SELECT COUNT(*) FROM wex_recovery_events")
                assert c.fetchone() == (2,)
                c.execute("SELECT evidence FROM wex_requests")
                stored = b" ".join(bytes(r[0]) for r in c.fetchall())
                assert password.encode() not in stored and public_data["email"].encode() not in stored
            checks.append("persistent_evidence_excludes_passwords_and_registration_email")
            roster.update(issued=int(time.time()), expires=int(time.time()) + 299)
            roster_file.write_bytes(canonical({"payload": roster, "signature": root.sign(DOMAIN + canonical(roster)).hex()}))
            as_recovery(lambda control: control.refresh("d" * 64))
            assert transport("/ready", {})["epoch"] == 2
            checks.append("root_signed_roster_refresh_preserves_generation_and_service_availability")
            denied_call("same_roster_refresh_cannot_replay_or_reset_validity_floor", lambda: as_recovery(lambda control: control.refresh("e" * 64)), (ProtectedRequestRefused,))
            with admin_db.cursor() as c:
                c.execute("SELECT COUNT(*) FROM wex_recovery_events")
                assert c.fetchone() == (3,)
            from apps.access_control.executor.receipts import verify_receipt
            with admin_db.cursor() as c:
                c.execute("SELECT evidence,result FROM wex_requests WHERE request_id=%s", (e["request_id"],))
                persisted_evidence, persisted_result = c.fetchone()
            persisted_evidence = json.loads(bytes(persisted_evidence))
            persisted_result = json.loads(persisted_result)
            assert verify_receipt(persisted_evidence, persisted_result, root.public_key().public_bytes_raw().hex())
            checks.append("archived_root_and_executor_signatures_verify_after_epoch_rotation")
            forged_result = {**persisted_result, "value": "forged-success"}
            denied_call("forged_commit_result_signature_refused", lambda: verify_receipt(persisted_evidence, forged_result, root.public_key().public_bytes_raw().hex()), (ProtectedRequestRefused,))
            forged_evidence = copy.deepcopy(persisted_evidence)
            forged_evidence["request"]["payload"]["actor_id"] = operator.pk
            denied_call("forged_persistent_authorization_evidence_refused", lambda: verify_receipt(forged_evidence, persisted_result, root.public_key().public_bytes_raw().hex()), (ProtectedRequestRefused,))
            # Preserve the existing separately gated delivery worker without
            # exposing account, role, audit-write or recipient-edit privileges.
            from apps.accounts.outbox_worker import process_one
            connection.close()
            connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = credentials["notifications"]
            try:
                from unittest.mock import patch
                with patch.dict(os.environ, {"WORKSPACE_OUTBOX_WORKER_ENABLED": "1"}), override_settings(
                    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                    WORKSPACE_NOTIFICATIONS_IDENTITY={"schema": name, "principal": "wex_notifications@localhost", "server_uuid": uuid}):
                    assert process_one() == "delivered"
                checks.append("existing_outbox_worker_runs_with_delivery_columns_only_and_no_smtp")
                with connection.cursor() as c:
                    denied_sql(c, "notification_worker_cannot_change_recipient_envelope", "UPDATE registration_notification_outbox SET wrapped_data_key=NULL", (), (1143,))
                    denied_sql(c, "notification_worker_cannot_modify_account_authority", "UPDATE accounts SET is_superuser=1", (), (1142,))
            finally:
                connection.close()
                connection.settings_dict["USER"], connection.settings_dict["PASSWORD"] = credentials["runtime"]
            admin_db.close()
            # No credentials or private artifacts are returned by this report.
        connections.close_all()
        return {"actual_schema_security_checks": len(checks), "checks": checks, "application_tables_migrated": migrated_tables,
                "production_release_authorized": False, "official_erd_changed": False}
    except Exception:
        if driver.work is not None:
            for label in ("ordinary", "protected"):
                file = driver.work / (label + ".log")
                if file.exists():
                    print("Isolated " + label + " diagnostics:\n" + file.read_text(errors="replace"), flush=True)
        raise
    finally:
        for child, log in children:
            if child.poll() is None:
                child.terminate(); child.wait(timeout=10)
            log.close()
        try:
            from django.db import connections
            connections.close_all()
        finally:
            driver._cleanup()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
