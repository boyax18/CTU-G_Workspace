"""P3C6B/P3C7/P4/P5 isolated MySQL execution candidate, NEVER production.

Uses actual application tables plus two separately created scratch ledger tables.
No migrations, production models, runtime imports, configurable SQL, or live CLI.
The ordinary test DB principal is privileged: writer fencing is NOT proven here.
Use the separate-server privilege rehearsal for its narrower DB denial evidence.
"""

from django.db import connection, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.delegation import is_reserved_role
from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.protected_requests import (
    CORE_PERMISSIONS, canonical, digest, require, verify_request,
)
from apps.access_control.technical_admin import has_technical_authority
from .g1d_p1_ledger_transaction_test_only import ACK, disposable_only


CONTROL = "task2_candidate_control"
LEDGER = "task2_candidate_ledger"


class OutcomeUnknown(RuntimeError):
    """Never retry automatically. Reconcile by exact request digest."""


class IsolatedProtectedExecutor:
    def __init__(self):
        self.schema = disposable_only(ACK)

    def guard(self):
        require(disposable_only(ACK) == self.schema)
        require(not connection.needs_rollback)

    def create(self, trust):
        self.guard()
        require(not connection.in_atomic_block and trust.schema == self.schema)
        # MySQL DDL commits implicitly. It is deliberately outside all mutations.
        # No IF NOT EXISTS: an existing ledger is never adopted or overwritten.
        with connection.cursor() as cursor:
            cursor.execute(f"""CREATE TABLE {CONTROL} (
                id INT PRIMARY KEY CHECK (id=1), epoch INT NOT NULL,
                incarnation CHAR(64) NOT NULL, halted BOOLEAN NOT NULL,
                release_hash CHAR(64) NOT NULL, fence_hash CHAR(64) NOT NULL,
                recovery_hash CHAR(64) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""")
            cursor.execute(f"""CREATE TABLE {LEDGER} (
                request_id CHAR(64) PRIMARY KEY, nonce CHAR(64) NOT NULL UNIQUE,
                request_hash CHAR(64) NOT NULL UNIQUE,
                operation VARCHAR(40) NOT NULL UNIQUE,
                evidence MEDIUMBLOB NOT NULL,
                status ENUM('CLAIMED','ATTEMPTED','APPLIED') NOT NULL,
                actor_id INT NOT NULL, target_id INT,
                role_id INT, audit_id INT UNIQUE,
                claimed_at BIGINT NOT NULL, applied_at BIGINT,
                FOREIGN KEY (actor_id) REFERENCES accounts(account_id),
                FOREIGN KEY (target_id) REFERENCES accounts(account_id),
                FOREIGN KEY (role_id) REFERENCES roles(role_id),
                FOREIGN KEY (audit_id) REFERENCES access_audit_logs(access_audit_log_id),
                CHECK ((status IN ('CLAIMED','ATTEMPTED') AND audit_id IS NULL AND applied_at IS NULL AND role_id IS NULL)
                  OR (status='APPLIED' AND audit_id IS NOT NULL AND applied_at IS NOT NULL AND role_id IS NOT NULL))
            ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""")
            cursor.execute(f"INSERT INTO {CONTROL} VALUES (1,%s,%s,0,%s,%s,%s)", (
                trust.epoch, trust.incarnation, trust.release_hash, trust.fence_hash, trust.recovery_hash,
            ))

    def drop(self):
        self.guard()
        require(not connection.in_atomic_block)
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE {LEDGER}")
            cursor.execute(f"DROP TABLE {CONTROL}")

    def _control(self, trust):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT epoch,incarnation,halted,release_hash,fence_hash,recovery_hash FROM {CONTROL} WHERE id=1 FOR UPDATE")
            require(cursor.fetchone() == (
                trust.epoch, trust.incarnation, 0, trust.release_hash, trust.fence_hash, trust.recovery_hash,
            ))

    def before_hash(self):
        self.guard()
        # The digest binds current credential hashes without storing credentials
        # or putting arbitrary approval payloads in access-audit snapshots.
        tables = (
            (Account, ("account_id", "password", "is_active", "request_status", "is_staff", "is_superuser")),
            (Role, ("role_id", "role_name", "is_active")),
            (Service, ("service_id", "service_code", "is_active")),
            (Permission, ("permission_id", "permission_code", "service_id", "module_name", "action_name")),
            (AccountRole, ("account_role_id", "account_id", "role_id", "assigned_by_id")),
            (RolePermission, ("role_permission_id", "role_id", "permission_id", "is_active", "granted_by_id")),
            (AccountPermission, ("account_permission_id", "account_id", "permission_id", "is_active", "effect")),
        )
        return digest({model._meta.db_table: list(model.objects.order_by("pk").values_list(*fields))
                       for model, fields in tables})

    def claim(self, bundle, trust, *, now):
        self.guard()
        require(not connection.in_atomic_block)
        request = verify_request(bundle, trust, now=now)
        require(request["schema"] == self.schema)
        try:
            with transaction.atomic(durable=True):
                self._control(trust)
                require(request["before_hash"] == self.before_hash())
                with connection.cursor() as cursor:
                    cursor.execute(f"""INSERT INTO {LEDGER}
                        (request_id,nonce,request_hash,operation,evidence,status,actor_id,target_id,claimed_at)
                        VALUES (%s,%s,%s,%s,%s,'CLAIMED',%s,%s,%s)""", (
                            request["request_id"], request["nonce"], digest(request), request["operation"],
                            canonical(bundle), request["actor_id"], request["target_id"], now,
                        ))
        except Exception:
            # Even admission COMMIT can have an ambiguous outcome.
            raise OutcomeUnknown("Claim outcome unresolved; reconcile before any further action.") from None
        return request["request_id"]

    def _catalogue(self):
        service = Service.objects.select_for_update().get(service_code="access_control")
        require(service.service_code == "access_control" and service.is_active)
        permissions = list(Permission.objects.select_for_update().filter(
            permission_code__in=CORE_PERMISSIONS,
        ).order_by("permission_code"))
        require(tuple(p.permission_code for p in permissions) == CORE_PERMISSIONS)
        for permission in permissions:
            module, action = permission.permission_code.split(".")[1:]
            require(permission.service_id == service.pk and permission.module_name == module
                    and permission.action_name == action)
        return permissions

    def _provision(self, request, actor):
        # Refuse aliases as well as exact collisions under MySQL collation.
        require(not any(is_reserved_role(name) and name != "Admin"
                        for name in Role.objects.values_list("role_name", flat=True)))
        permissions = self._catalogue()
        role = Role.objects.create(role_name="Technical Super Admin", is_active=False)
        for permission in permissions:
            RolePermission.objects.create(role=role, permission=permission, is_active=False, granted_by=actor)
        audit_id = record_access_audit_receipt(
            actor=actor, role=role, action="technical_role.provision",
            old_value=None, new_value={"role_id": role.pk, "is_active": False,
                                       "permission_ids": [p.pk for p in permissions]},
            reason="permission_change",
        )
        return role, audit_id

    def _bootstrap(self, request, actor):
        permissions = self._catalogue()
        role = Role.objects.select_for_update().get(role_name="Technical Super Admin", is_active=False)
        require(role.role_name == "Technical Super Admin")
        require(not AccountRole.objects.filter(role=role).exists())
        target = Account.objects.select_for_update().get(pk=request["target_id"])
        require(target.is_active and target.request_status == "Approved" and target.has_usable_password()
                and not target.is_staff and not target.is_superuser)
        assignments = list(AccountRole.objects.select_for_update().filter(account=target).select_related("role"))
        require(any(a.role.role_name == "Admin" and a.role.is_active for a in assignments))
        require(not any(is_reserved_role(a.role.role_name) and a.role.role_name != "Admin" for a in assignments))
        bindings = list(RolePermission.objects.select_for_update().filter(role=role).order_by("permission_id"))
        require({b.permission_id for b in bindings} == {p.pk for p in permissions}
                and len(bindings) == len(permissions) and not any(b.is_active for b in bindings))
        require(not AccountPermission.objects.filter(account=target, is_active=True,
                                                     permission_id__in=[p.pk for p in permissions]).exists())
        role.is_active = True
        role.save(update_fields=["is_active"])
        for binding in bindings:
            binding.is_active, binding.granted_by = True, actor
            binding.save(update_fields=["is_active", "granted_by"])
        AccountRole.objects.create(account=target, role=role, assigned_by=actor)
        require(all(has_technical_authority(target, code) for code in CORE_PERMISSIONS))
        audit_id = record_access_audit_receipt(
            actor=actor, target=target, role=role, action="technical_admin.bootstrap",
            old_value={"account_id": target.pk, "is_active": True},
            new_value={"account_id": target.pk, "role_id": role.pk, "is_active": True,
                       "permission_ids": [p.pk for p in permissions]}, reason="assignment_change",
        )
        return role, audit_id

    def execute(self, request_id, trust, *, now):
        self.guard()
        require(not connection.in_atomic_block)
        try:
            # Commit the one-use attempt BEFORE beginning application writes.
            # A process death from here onward produces HOLD, never retry.
            with transaction.atomic(durable=True):
                self._control(trust)
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT status FROM {LEDGER} WHERE request_id=%s FOR UPDATE", (request_id,))
                    require(cursor.fetchone() == ("CLAIMED",))
                    cursor.execute(f"UPDATE {LEDGER} SET status='ATTEMPTED' WHERE request_id=%s", (request_id,))
            with transaction.atomic(durable=True):
                self._control(trust)
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT evidence,status,request_hash FROM {LEDGER} WHERE request_id=%s FOR UPDATE", (request_id,))
                    row = cursor.fetchone()
                require(row is not None and row[1] == "ATTEMPTED")
                import json
                bundle = json.loads(bytes(row[0]))
                request = verify_request(bundle, trust, now=now)
                require(request["request_id"] == request_id and digest(request) == row[2])
                require(request["before_hash"] == self.before_hash())
                actor = Account.objects.select_for_update().get(pk=request["actor_id"])
                require(actor.is_active and actor.request_status == "Approved")
                role, audit_id = (self._provision(request, actor) if request["operation"] == "technical_role.provision"
                                  else self._bootstrap(request, actor))
                with connection.cursor() as cursor:
                    cursor.execute(f"UPDATE {LEDGER} SET status='APPLIED',role_id=%s,audit_id=%s,applied_at=%s WHERE request_id=%s AND status='ATTEMPTED'",
                                   (role.pk, audit_id, now, request_id))
                    require(cursor.rowcount == 1)
        except Exception:
            raise OutcomeUnknown("Execution outcome unresolved; keep writers held and reconcile.") from None
        return audit_id

    def reconcile(self, request_id, request_hash):
        self.guard()
        require(not connection.in_atomic_block)
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT status,request_hash,audit_id FROM {LEDGER} WHERE request_id=%s FOR UPDATE", (request_id,))
                row = cursor.fetchone()
            require(row is not None and row[1] == request_hash)
            # CLAIMED means HOLD, including expired/revoked requests. Never a
            # retry authorization. APPLIED is authoritative after reconnection.
            return {"status": "APPLIED" if row[0] == "APPLIED" else "HOLD", "audit_id": row[2]}

    def hold(self):
        self.guard()
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT id FROM {CONTROL} WHERE id=1 FOR UPDATE")
                require(cursor.fetchone() == (1,))
                cursor.execute(f"UPDATE {CONTROL} SET halted=1 WHERE id=1")
        # There is intentionally no automated resume/rollback/demotion method.
