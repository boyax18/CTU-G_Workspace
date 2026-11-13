"""Four-table scratch ledger: GENERATED DISPOSABLE MYSQL SCHEMA ONLY.

No models, migrations, CLI, production imports, real trust or live release.
All public DB operations validate configuration AND SELECT DATABASE() before
DDL/ORM/SQL. Ordinary shared InnoDB scratch tables allow competing connections.
Fencing is explicitly simulated: this module cannot fence privileged SQL users.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
import secrets

from django.conf import settings
from django.db import DatabaseError, connection, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.delegation import is_reserved_role
from apps.access_control.management.commands.init_system_roles import SYSTEM_ROLES
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from . import g1d_p1_authorization_design_test_only as auth
from .g1b_catalogue_test_only import CORE_K_CODES


ACK = "G1D_P1_SHARED_SCRATCH_DISPOSABLE_ONLY"
CONTROL = "g1d_p1_proto_control"
REQUESTS = "g1d_p1_proto_requests"
APPROVALS = "g1d_p1_proto_approvals"
EVENTS = "g1d_p1_proto_events"
TABLES = (CONTROL, REQUESTS, APPROVALS, EVENTS)
ACTION = "technical_admin.role_metadata.create"
SCOPE = "DISPOSABLE:initial-inactive-Technical-Super-Admin"


class LedgerRefused(RuntimeError):
    pass


class ExecutionUnknown(RuntimeError):
    """Do not retry; resolve from locked durable state on a fresh connection."""


@dataclass(frozen=True)
class TestClaim:
    request_id: str
    secret: bytes


def _require(condition, message="Disposable ledger operation refused."):
    if not condition:
        raise LedgerRefused(message)


def disposable_only(ack):
    """No DB access before exact configuration and acknowledgment checks."""
    config = settings.DATABASES["default"]
    expected = getattr(settings, "REGISTRATION_TEST_DATABASE", None)
    _require(ack == ACK and settings.SETTINGS_MODULE == "config.test_settings")
    _require(tuple(settings.DATABASES) == ("default",) and not settings.DATABASE_ROUTERS)
    _require(type(expected) is str and auth.SCHEMA.fullmatch(expected) is not None)
    _require(settings.TEST_RUNNER == "config.test_runner.IsolatedMySQLRunner")
    for candidate in (config, connection.settings_dict):
        _require(candidate.get("ENGINE") == "django.db.backends.mysql")
        _require(candidate.get("HOST") in {"localhost", "127.0.0.1", "::1"})
        _require(candidate.get("NAME") == expected and candidate.get("TEST", {}).get("NAME") == expected)
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE(), @@transaction_isolation")
        actual, isolation = cursor.fetchone()
    _require(actual == expected and isolation == "READ-COMMITTED" and connection.vendor == "mysql")
    return expected


def _row(cursor):
    values = cursor.fetchone()
    return None if values is None else dict(zip((c[0] for c in cursor.description), values))


def _fault_point(stage):
    """Patchable fault/synchronization boundary, solely in this test harness."""


def _snapshot(actor_id, *, exclude_role=None, exclude_audit=None):
    roles = Role.objects.exclude(pk=exclude_role) if exclude_role is not None else Role.objects.all()
    audits = AccessAuditLog.objects.exclude(pk=exclude_audit) if exclude_audit is not None else AccessAuditLog.objects.all()
    state = {
        "actor": Account.objects.filter(pk=actor_id).values("account_id", "is_active", "request_status").first(),
        "account_count": Account.objects.count(),
        "roles": list(roles.order_by("pk").values_list("pk", "role_name", "description", "is_active")),
        "assignments": list(AccountRole.objects.order_by("pk").values_list("pk", "account_id", "role_id", "assigned_by_id")),
        "services": list(Service.objects.order_by("pk").values_list("pk", "service_code", "service_name", "is_active")),
        "permissions": list(Permission.objects.order_by("pk").values_list("pk", "permission_code", "service_id", "module_name", "action_name")),
        "bindings": list(RolePermission.objects.order_by("pk").values_list("pk", "role_id", "permission_id", "is_active")),
        "overrides": list(AccountPermission.objects.order_by("pk").values_list("pk", "account_id", "permission_id", "effect", "is_active")),
        "audit_ids": list(audits.order_by("pk").values_list("pk", flat=True)),
    }
    return json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


class DisposableLedger:
    def __init__(self, *, ack):
        self.ack = ack
        self.schema = disposable_only(ack)

    def guard(self):
        _require(disposable_only(self.ack) == self.schema)

    def create(self, trust):
        self.guard()
        auth.validate_trust(trust)
        _require(trust.schema == self.schema and not connection.in_atomic_block)
        # No IF NOT EXISTS: never adopt/drop an already existing scratch ledger.
        ddl = (
            f"""CREATE TABLE {CONTROL} (
              id INT PRIMARY KEY CHECK (id = 1), epoch INT NOT NULL CHECK (epoch > 0),
              incarnation CHAR(36) NOT NULL, halted BOOLEAN NOT NULL CHECK (halted IN (0,1)),
              retention_code VARCHAR(32) NOT NULL CHECK (retention_code = 'TEST_RUN_ONLY')
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
            f"""CREATE TABLE {REQUESTS} (
              request_id CHAR(36) PRIMARY KEY, idempotency_key CHAR(64) NOT NULL UNIQUE,
              request_sha256 CHAR(64) NOT NULL UNIQUE, nonce CHAR(64) UNIQUE,
              request_blob BLOB NOT NULL, bundle_blob MEDIUMBLOB NOT NULL, before_blob MEDIUMBLOB NOT NULL,
              challenge CHAR(64) NOT NULL, actor_id INT NOT NULL,
              status ENUM('Pending','Ready','Attempted','Consumed','Rejected','Cancelled','Expired') NOT NULL,
              version INT NOT NULL DEFAULT 1 CHECK (version > 0),
              claim_sha256 CHAR(64), claimed_at BIGINT, expires_at BIGINT NOT NULL,
              role_id INT UNIQUE, audit_id INT UNIQUE, consumed_at BIGINT, success_scope VARCHAR(128) UNIQUE,
              FOREIGN KEY (actor_id) REFERENCES accounts(account_id),
              FOREIGN KEY (role_id) REFERENCES roles(role_id),
              FOREIGN KEY (audit_id) REFERENCES access_audit_logs(access_audit_log_id),
              CHECK (status NOT IN ('Ready','Attempted','Consumed') OR nonce IS NOT NULL),
              CHECK (status NOT IN ('Attempted','Consumed') OR (claim_sha256 IS NOT NULL AND claimed_at IS NOT NULL)),
              CHECK ((status = 'Consumed' AND role_id IS NOT NULL AND audit_id IS NOT NULL AND consumed_at IS NOT NULL AND success_scope IS NOT NULL)
                OR (status <> 'Consumed' AND role_id IS NULL AND audit_id IS NULL AND consumed_at IS NULL AND success_scope IS NULL))
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
            f"""CREATE TABLE {APPROVALS} (
              approval_id CHAR(36) PRIMARY KEY, request_id CHAR(36) NOT NULL,
              duty ENUM('institutional','technical') NOT NULL, person_id CHAR(36) NOT NULL,
              envelope_sha256 CHAR(64) NOT NULL UNIQUE, payload BLOB NOT NULL, signature BINARY(64) NOT NULL,
              UNIQUE (request_id,duty), UNIQUE (request_id,person_id),
              FOREIGN KEY (request_id) REFERENCES {REQUESTS}(request_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
            f"""CREATE TABLE {EVENTS} (
              event_id BIGINT AUTO_INCREMENT PRIMARY KEY, request_id CHAR(36),
              event_uuid CHAR(64) NOT NULL UNIQUE,
              event_type ENUM('ready','claimed','executing','consumed','cancelled','expired','revoked') NOT NULL,
              occurred_at BIGINT NOT NULL, actor_id INT, evidence BLOB,
              UNIQUE (request_id,event_type),
              FOREIGN KEY (request_id) REFERENCES {REQUESTS}(request_id),
              FOREIGN KEY (actor_id) REFERENCES accounts(account_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
        )
        created = []
        try:
            for table, statement in zip(TABLES, ddl):
                self.guard()
                with connection.cursor() as cursor:
                    cursor.execute(statement)
                created.append(table)
            with connection.cursor() as cursor:
                cursor.execute(f"INSERT INTO {CONTROL} VALUES (1,%s,%s,0,'TEST_RUN_ONLY')", (trust.epoch, trust.incarnation))
                cursor.execute("SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN (%s,%s,%s,%s)", (self.schema, *TABLES))
                _require(len(rows := cursor.fetchall()) == 4 and all(engine == "InnoDB" for _, engine in rows))
        except Exception:
            for table in reversed(created):
                self.guard()
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP TABLE {table}")
            raise

    def drop(self):
        self.guard()
        _require(not connection.in_atomic_block)
        for table in reversed(TABLES):
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE {table}")

    def before_hash(self, actor_id):
        self.guard()
        return auth.digest(_snapshot(actor_id))

    @contextmanager
    def _locked(self, request_id=None, trust=None):
        self.guard()
        if trust is not None:
            auth.validate_trust(trust)
            _require(trust.schema == self.schema)
        with transaction.atomic(using="default", durable=True):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {CONTROL} WHERE id=1 FOR UPDATE")
                control = _row(cursor)
                _require(control is not None)
                if trust is not None:
                    _require(control["halted"] == 0 and control["epoch"] == trust.epoch and control["incarnation"] == trust.incarnation)
                service = Service.objects.select_for_update().filter(service_code="access_control").first()
                _require(service is not None and service.service_code == "access_control" and service.is_active)
                request = None
                if request_id is not None:
                    cursor.execute(f"SELECT * FROM {REQUESTS} WHERE request_id=%s FOR UPDATE", (request_id,))
                    request = _row(cursor)
                    _require(request is not None)
                yield cursor, request

    def _event(self, cursor, request_id, kind, now, actor_id=None, evidence=None):
        cursor.execute(f"INSERT INTO {EVENTS} (request_id,event_uuid,event_type,occurred_at,actor_id,evidence) VALUES (%s,%s,%s,%s,%s,%s)",
                       (request_id, secrets.token_hex(32), kind, now, actor_id, evidence))

    def admit(self, bundle, trust, *, now, actor_id, challenge):
        self.guard()
        request = auth.verify_bundle(bundle, trust, now=now, expected_actor_id=actor_id, expected_challenge=challenge)
        _require(trust.schema == self.schema)
        blob = auth.encode_bundle(bundle)
        with self._locked(trust=trust) as (cursor, _):
            cursor.execute(f"SELECT bundle_blob FROM {REQUESTS} WHERE request_id=%s", (request["request_id"],))
            existing = cursor.fetchone()
            if existing is not None:
                _require(bytes(existing[0]) == blob)
                return request["request_id"]  # admission status only; never execution
            before = _snapshot(actor_id)
            _require(auth.digest(before) == request["before_sha256"])
            ticket = auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)
            cursor.execute(f"""INSERT INTO {REQUESTS}
                (request_id,idempotency_key,request_sha256,nonce,request_blob,bundle_blob,before_blob,challenge,actor_id,status,expires_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Ready',%s)""",
                (request["request_id"], request["idempotency_key"], auth.digest(bundle.request), ticket["nonce"], bundle.request, blob, before, challenge, actor_id, ticket["expires_at"]))
            for proof in bundle.approvals:
                approval = auth.parse(proof.payload, auth.APPROVAL_FIELDS)
                cursor.execute(f"INSERT INTO {APPROVALS} VALUES (%s,%s,%s,%s,%s,%s,%s)",
                               (approval["approval_id"], request["request_id"], approval["duty"], approval["person_id"], auth.proof_digest(proof), proof.payload, proof.signature))
            self._event(cursor, request["request_id"], "ready", now, actor_id)
        return request["request_id"]

    def _verified(self, cursor, row, trust, now):
        bundle = auth.decode_bundle(row["bundle_blob"])
        request = auth.verify_bundle(bundle, trust, now=now, expected_actor_id=row["actor_id"], expected_challenge=row["challenge"])
        _require(request["request_id"] == row["request_id"] and auth.digest(bundle.request) == row["request_sha256"])
        _require(bundle.request == bytes(row["request_blob"]) and auth.digest(bytes(row["before_blob"])) == request["before_sha256"])
        _require(auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)["nonce"] == row["nonce"])
        cursor.execute(f"SELECT payload,signature FROM {APPROVALS} WHERE request_id=%s ORDER BY duty FOR UPDATE", (row["request_id"],))
        stored = {(bytes(payload), bytes(signature)) for payload, signature in cursor.fetchall()}
        _require(stored == {(proof.payload, proof.signature) for proof in bundle.approvals})
        return request

    def _eligible(self, actor_id):
        actor = Account.objects.select_for_update().filter(pk=actor_id).first()
        assignments = list(AccountRole.objects.select_for_update().filter(account_id=actor_id).order_by("pk"))
        roles = list(Role.objects.select_for_update().order_by("pk"))
        admin = [role for role in roles if role.role_name == "Admin" and role.is_active]
        _require(actor is not None and actor.is_active and actor.request_status == "Approved")
        _require(len(admin) == 1 and any(assignment.role_id == admin[0].pk for assignment in assignments))
        _require(tuple(name for name, _ in SYSTEM_ROLES) == ("Student", "Instructor", "Treasurer", "Admin"))
        _require(all(role.role_name.isascii() and (not is_reserved_role(role.role_name) or role.role_name == "Admin") for role in roles))
        _require(not Permission.objects.filter(permission_code__in=CORE_K_CODES).exists())
        _require(not AccountPermission.objects.filter(permission__service__service_code="access_control", is_active=True).exists())
        return actor

    def claim(self, request_id, trust, *, now):
        secret = secrets.token_bytes(32)
        with self._locked(request_id, trust) as (cursor, row):
            _require(row["status"] == "Ready")
            request = self._verified(cursor, row, trust, now)
            self._eligible(row["actor_id"])
            _require(auth.digest(_snapshot(row["actor_id"])) == request["before_sha256"])
            cursor.execute(f"UPDATE {REQUESTS} SET status='Attempted',version=version+1,claim_sha256=%s,claimed_at=%s WHERE request_id=%s AND status='Ready'", (auth.digest(secret), now, request_id))
            _require(cursor.rowcount == 1)
            self._event(cursor, request_id, "claimed", now, row["actor_id"])
        return TestClaim(request_id, secret)

    def execute(self, claim, trust, *, clock, simulate_fenced_writers=False):
        self.guard()
        _require(simulate_fenced_writers is True, "Writer fencing is not established, even in the simulation.")
        _require(type(claim) is TestClaim and type(claim.secret) is bytes and len(claim.secret) == 32)
        # A separate durable reservation prevents re-entry even after rollback.
        # Role, audit and final consumption remain in ONE later transaction.
        reservation_committing = False
        try:
            with self._locked(claim.request_id, trust) as (cursor, row):
                _require(row["status"] == "Attempted" and secrets.compare_digest(row["claim_sha256"], auth.digest(claim.secret)))
                self._verified(cursor, row, trust, clock())
                cursor.execute(f"SELECT COUNT(*) FROM {EVENTS} WHERE request_id=%s AND event_type='executing'", (claim.request_id,))
                _require(cursor.fetchone()[0] == 0, "Execution was already reserved; reconcile instead of retrying.")
                self._event(cursor, claim.request_id, "executing", row["claimed_at"], row["actor_id"], auth.digest(claim.secret).encode("ascii"))
                reservation_committing = True
        except Exception as exc:
            if reservation_committing:
                raise ExecutionUnknown("Execution reservation acknowledgment is uncertain; do not retry.") from exc
            raise
        _fault_point("after_execution_reservation")
        commit_started = False
        try:
            with self._locked(claim.request_id, trust) as (cursor, row):
                _fault_point("control_locked")
                _require(row["status"] == "Attempted" and secrets.compare_digest(row["claim_sha256"], auth.digest(claim.secret)))
                now = clock()
                request = self._verified(cursor, row, trust, now)
                actor = self._eligible(row["actor_id"])
                _require(auth.digest(_snapshot(actor.pk)) == request["before_sha256"])
                cursor.execute(f"SELECT COUNT(*) FROM {REQUESTS} WHERE success_scope=%s", (SCOPE,))
                _require(cursor.fetchone()[0] == 0)
                role = Role.objects.create(role_name=auth.ROLE_NAME, description=auth.ROLE_DESCRIPTION, is_active=False)
                _fault_point("after_role")
                audit_id = record_access_audit_receipt(actor=actor, role=role, action=ACTION, old_value=None,
                    new_value={"role_id": role.pk, "is_active": False}, reason="policy_enforcement")
                _fault_point("after_audit")
                self._postconditions(row, role.pk, audit_id)
                consumed_at = clock()
                auth.verify_bundle(auth.decode_bundle(row["bundle_blob"]), trust, now=consumed_at, expected_actor_id=actor.pk, expected_challenge=row["challenge"])
                cursor.execute(f"""UPDATE {REQUESTS} SET status='Consumed',version=version+1,role_id=%s,audit_id=%s,consumed_at=%s,success_scope=%s
                    WHERE request_id=%s AND status='Attempted' AND claim_sha256=%s""",
                    (role.pk, audit_id, consumed_at, SCOPE, claim.request_id, auth.digest(claim.secret)))
                _require(cursor.rowcount == 1)
                self._event(cursor, claim.request_id, "consumed", consumed_at, actor.pk, row["request_sha256"].encode("ascii"))
                _fault_point("after_consumption")
                self._postconditions(row, role.pk, audit_id)
                _fault_point("before_commit")
                commit_started = True
            _fault_point("after_commit")
        except Exception as exc:
            if commit_started:
                raise ExecutionUnknown("Commit acknowledgment is uncertain; do not retry.") from exc
            raise
        return role.pk, audit_id

    def _postconditions(self, row, role_id, audit_id):
        role = Role.objects.get(pk=role_id)
        _require(role.role_name == auth.ROLE_NAME and role.description == auth.ROLE_DESCRIPTION and role.is_active is False)
        _require(not AccountRole.objects.filter(role_id=role_id).exists() and not RolePermission.objects.filter(role_id=role_id).exists())
        audit = AccessAuditLog.objects.filter(pk=audit_id, actor_account_id=row["actor_id"], role_id=role_id, action=ACTION,
            reason="policy_enforcement", target_account_id=None, permission_id=None).first()
        _require(audit is not None and audit.old_value is None and audit.new_value == {"role_id": role_id, "is_active": False})
        _require(_snapshot(row["actor_id"], exclude_role=role_id, exclude_audit=audit_id) == bytes(row["before_blob"]))

    def cancel(self, request_id, proof, trust, *, now, expire=False):
        with self._locked(request_id, trust) as (cursor, row):
            data, identity = auth.verify_proof(proof, "cancel", auth.CANCEL_FIELDS, trust, now)
            auth.time_window(data, now, 300)
            bundle = auth.decode_bundle(row["bundle_blob"])
            request = auth.parse(bundle.request, auth.REQUEST_FIELDS)
            people = {auth.parse(p.payload, auth.APPROVAL_FIELDS)["person_id"] for p in bundle.approvals} | {request["executor_person"]}
            _require(data["request_sha256"] == row["request_sha256"] and data["decision"] == "cancel")
            _require(identity.person_id in people and identity.duty in {"institutional", "technical", "executor"})
            _require(row["status"] in {"Ready", "Attempted"})
            if expire:
                _require(now >= row["expires_at"])
            status = "Expired" if expire else "Cancelled"
            cursor.execute(f"UPDATE {REQUESTS} SET status=%s,version=version+1 WHERE request_id=%s", (status, request_id))
            self._event(cursor, request_id, status.lower(), now, evidence=proof.payload + proof.signature)

    def revoke_epoch_test_fixture(self, *, now):
        """Synthetic fixture transition; NOT an authenticated trust admin service."""
        with self._locked() as (cursor, _):
            cursor.execute(f"UPDATE {CONTROL} SET epoch=epoch+1,halted=1 WHERE id=1")
            self._event(cursor, None, "revoked", now)

    def resolve(self, request_id, trust):
        try:
            self.guard()  # wrong configuration is a refusal, never a live fallback
        except DatabaseError:
            return "UNKNOWN"
        try:
            with self._locked(request_id) as (cursor, row):
                cursor.execute(f"SELECT occurred_at FROM {EVENTS} WHERE request_id=%s AND event_type='ready'", (request_id,))
                admissions = cursor.fetchall()
                _require(len(admissions) == 1)
                historical_time = row["consumed_at"] if row["status"] == "Consumed" else admissions[0][0]
                self._verified(cursor, row, trust, historical_time)
                cursor.execute(f"SELECT actor_id,evidence,occurred_at FROM {EVENTS} WHERE request_id=%s AND event_type='consumed'", (request_id,))
                consumed_events = cursor.fetchall()
                if row["status"] == "Consumed":
                    self._postconditions(row, row["role_id"], row["audit_id"])
                    _require(len(consumed_events) == 1 and row["success_scope"] == SCOPE)
                    _require(consumed_events[0] == (row["actor_id"], row["request_sha256"].encode("ascii"), row["consumed_at"]))
                    return "COMMITTED"
                _require(not consumed_events and row["role_id"] is None and row["audit_id"] is None)
                _require(_snapshot(row["actor_id"]) == bytes(row["before_blob"]))
                _require(not Role.objects.filter(role_name=auth.ROLE_NAME).exists())
                return "NOT_COMMITTED"
        except (DatabaseError, LedgerRefused, auth.ContractRefused):
            return "UNKNOWN"
