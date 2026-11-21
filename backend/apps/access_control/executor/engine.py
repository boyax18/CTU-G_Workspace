"""Authenticated fixed dispatcher with persistent one-use, transaction-bound leases."""
from contextlib import contextmanager
import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.db import connection, transaction

from apps.accounts.models import Account
from apps.access_control.protected_requests import canonical, digest, require, verify_request
from .protocol import PUBLIC, actor_from_proof, issue_proof, now, validate_request, sanitize_evidence as evidence
from .runtime import executing
from .schema import FENCED, TABLES, VERSION
from .trust import TrustStore
from .errors import AuthenticationDenied, ExecutionDenied


class OutcomeUnknown(RuntimeError):
    pass


class Executor:
    def __init__(self, config, signing_key):
        require(config["kind"] in {"ordinary", "protected"})
        require(config["policy_hash"] == digest({"delegation": getattr(settings, "ACCESS_CONTROL_DELEGATION_POLICY", {}),
            "ordinary_assignment": getattr(settings, "WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_POLICY", {})}))
        self.config, self.signing_key = config, signing_key
        self.trust = TrustStore(config)

    def identity(self):
        require(getattr(settings, "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER", False) is True)
        require(tuple(settings.DATABASES) == ("default",) and not settings.DATABASE_ROUTERS)
        require(not connection.in_atomic_block and connection.vendor == "mysql")
        with connection.cursor() as c:
            c.execute("SELECT DATABASE(),CURRENT_USER(),@@server_uuid,@@transaction_isolation,CONNECTION_ID(),@@session.time_zone")
            schema, principal, server, isolation, cid, zone = c.fetchone()
            require((schema, principal, server, isolation, zone) ==
                    (self.config["schema"], self.config["principal"], self.config["server_uuid"], "READ-COMMITTED", "+00:00"))
            if "isolated_datadir" in self.config:
                from pathlib import Path
                import tempfile
                data = Path(self.config["isolated_datadir"]).resolve(strict=True)
                require(data.parent.parent == Path(tempfile.gettempdir()).resolve()
                        and data.parent.name.startswith("ctug-p3c5-separate-")
                        and schema.startswith("test_ctug_executor_"))
                c.execute("SELECT @@datadir,@@skip_networking,@@socket")
                actual, skip, pipe = c.fetchone()
                require(Path(actual).resolve() == data and skip == 1 and pipe.lower().endswith(self.config["isolated_pipe"].lower()))
            c.execute("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", (schema,))
            tables = dict(c.fetchall())
            require(all(tables.get(t) == "InnoDB" for t in (*FENCED, *TABLES)))
            c.execute("SHOW GRANTS")
            grants = " ".join(r[0] for r in c.fetchall())
            require(not any(word in grants.upper() for word in ("ALL PRIVILEGES", "GRANT OPTION", "SUPER", "ROLE_ADMIN", "PROXY", "CREATE", "ALTER", "DROP", "TRIGGER")))
            c.execute("SELECT CURRENT_ROLE()")
            require(c.fetchone() == ("NONE",))
        return principal, cid

    def control(self):
        with connection.cursor() as c:
            c.execute("SELECT epoch,incarnation,roster_hash,fence_hash,recovery_hash,release_hash,halted,schema_version,definition_hash,roster_expires FROM wex_control WHERE id=1 FOR UPDATE")
            row = c.fetchone()
        require(row is not None and row[6:8] == (0, VERSION))
        roster, trust, issuers = self.trust.load(row[:6])
        from .trust import definition_hash
        require(definition_hash(roster) == row[8] and roster["expires"] == row[9])
        require(any(k.public_bytes_raw() == self.signing_key.public_key().public_bytes_raw() for k in issuers))
        return roster, trust, issuers

    def peer(self, roster, peer):
        require(peer in roster["peers"] and self.config["kind"] in roster["peers"][peer])

    def authenticate(self, payload, peer):
        self.identity()
        require(type(payload) is dict and set(payload) == {"school_id", "password"})
        require(all(type(v) is str and 0 < len(v) <= 256 for v in payload.values()))
        with transaction.atomic(durable=True):
            roster, trust, issuers = self.control()
            self.peer(roster, peer)
            require(any(k.public_bytes_raw() == self.signing_key.public_key().public_bytes_raw() for k in issuers))
            actor = Account.objects.select_for_update().filter(school_id=payload["school_id"]).first()
            if (actor is None or not actor.is_active or actor.request_status != "Approved"
                    or not check_password(payload["password"], actor.password)):
                raise AuthenticationDenied()
            require(self.config["kind"] == "protected" or not(actor.is_staff or actor.is_superuser))
            proof = issue_proof(self.signing_key, actor_id=actor.pk, peer=peer, epoch=trust.epoch)
        return {"actor_id": actor.pk, "proof": proof}

    def authorized_actor(self, envelope, peer, roster, trust, issuers):
        self.peer(roster, peer)
        if envelope["operation"] == "registration.submit":
            return None
        if envelope["operation"] == "registration.reapply":
            from apps.accounts.reapplication import SALT, LINK_MAX_AGE_SECONDS
            token = envelope["payload"].get("token")
            require(type(token) is str and len(token) <= 1024)
            p = signing.loads(token, salt=SALT, max_age=LINK_MAX_AGE_SECONDS)
            require(type(p) is dict and type(p.get("aid")) is int and p["aid"] > 0)
            return p["aid"]  # token-holder attribution, rechecked by the original service
        return actor_from_proof(envelope["actor_proof"], issuers, peer=peer, epoch=trust.epoch)

    def execute(self, envelope, peer):
        principal, cid = self.identity()
        validate_request(envelope, self.config["kind"])
        request_id, operation = envelope["request_id"], envelope["operation"]
        secret = secrets.token_bytes(32)
        secret_hash = hashlib.sha256(secret).hexdigest()
        safe_evidence = evidence(envelope)
        try:
            with transaction.atomic(durable=True):
                roster, trust, issuers = self.control()
                validate_request(envelope, self.config["kind"])
                actor_id = self.authorized_actor(envelope, peer, roster, trust, issuers)
                from .receipts import EVIDENCE_DOMAIN, RESULT_DOMAIN
                archive = {"request": safe_evidence, "root_roster": self.trust.archive(roster),
                           "principal": principal, "connection_id": cid,
                           "issuer_public_key": self.signing_key.public_key().public_bytes_raw().hex()}
                archive["executor_signature"] = self.signing_key.sign(EVIDENCE_DOMAIN + canonical(archive)).hex()
                if operation.startswith("technical_"):
                    bundle = envelope["payload"].get("bundle")
                    approved = verify_request(bundle, trust, now=now())
                    require(approved["operation"] == operation and approved["actor_id"] == actor_id
                            and approved["request_id"] == request_id and approved["nonce"] == envelope["nonce"])
                with connection.cursor() as c:
                    c.execute("SELECT request_id FROM wex_requests WHERE kind='protected' AND status<>'APPLIED' AND epoch=%s AND incarnation=%s LIMIT 1", (trust.epoch, trust.incarnation))
                    require(c.fetchone() is None)  # an interrupted protected ceremony holds all writers
                    c.execute("""INSERT INTO wex_requests(request_id,nonce,request_hash,operation,success_scope,kind,
                        principal,peer,actor_id,connection_id,claim_hash,epoch,incarnation,evidence,status,issued,expires)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'CLAIMED',%s,%s)""", (
                        request_id, envelope["nonce"], digest(safe_evidence), operation,
                        digest([operation, trust.incarnation]) if operation in {"technical_role.provision", "technical_admin.bootstrap", "bootstrap.initial_admin"} else None,
                        self.config["kind"], principal, peer, actor_id, cid, secret_hash, trust.epoch,
                        trust.incarnation, canonical(archive), envelope["issued"], envelope["expires"],
                    ))
            # A crash after this commit cannot reconstruct the in-memory claim.
            with transaction.atomic(durable=True):
                self.control()
                with connection.cursor() as c:
                    c.execute("UPDATE wex_requests SET status='ATTEMPTED' WHERE request_id=%s AND status='CLAIMED' AND claim_hash=%s AND connection_id=%s",
                              (request_id, hashlib.sha256(secret).hexdigest(), cid))
                    require(c.rowcount == 1)
            with transaction.atomic(durable=True):
                roster, trust, issuers = self.control()
                validate_request(envelope, self.config["kind"])
                require(self.authorized_actor(envelope, peer, roster, trust, issuers) == actor_id)
                with connection.cursor() as c:
                    c.execute("SELECT status,claim_hash,connection_id,epoch,incarnation FROM wex_requests WHERE request_id=%s FOR UPDATE", (request_id,))
                    require(c.fetchone() == ("ATTEMPTED", secret_hash, cid, trust.epoch, trust.incarnation))
                    c.execute("SET @wex_request=%s", (request_id,))
                with executing(operation):
                    value = self.dispatch(operation, envelope["payload"], actor_id, trust)
                with connection.cursor() as c:
                    c.execute("SELECT audit_id FROM wex_audits WHERE request_id=%s ORDER BY audit_id", (request_id,))
                    result = {"value": value, "request_id": request_id, "request_hash": digest(safe_evidence),
                              "audit_ids": [r[0] for r in c.fetchall()], "evidence_hash": digest(archive)}
                    result["executor_signature"] = self.signing_key.sign(RESULT_DOMAIN + canonical(result)).hex()
                    c.execute("UPDATE wex_requests SET status='APPLIED',result=%s WHERE request_id=%s AND status='ATTEMPTED'",
                              (canonical(result).decode(), request_id))
                    require(c.rowcount == 1)
            return result
        except Exception as exc:
            from apps.accounts.registration_review import RegistrationReviewDenied
            from apps.accounts.reapplication import ReapplicationDenied
            from django.core.exceptions import PermissionDenied, ValidationError
            from apps.access_control.protected_requests import ProtectedRequestRefused
            if isinstance(exc, (RegistrationReviewDenied, ReapplicationDenied, PermissionDenied, ValidationError, ProtectedRequestRefused)):
                raise ExecutionDenied() from None
            if self.config.get("isolated_datadir"):
                import traceback
                traceback.print_exc()
            raise OutcomeUnknown("No automatic retry; reconcile using the request identity.") from None
        finally:
            try:
                with connection.cursor() as c:
                    c.execute("SET @wex_request=NULL")
            except Exception:
                connection.close()

    def receipt(self, payload, peer):
        self.identity()
        require(type(payload) is dict and set(payload) == {"request_id", "request_hash", "proof"})
        with transaction.atomic(durable=True):
            # Read-only reconciliation also works when halted/roster revoked;
            # fresh actor authentication still required, no execution capability.
            roster, trust, issuers = self.trust.load()
            self.peer(roster, peer)
            actor = actor_from_proof(payload["proof"], issuers, peer=peer, epoch=trust.epoch)
            with connection.cursor() as c:
                c.execute("SELECT request_hash,actor_id,peer,status,result,evidence FROM wex_requests WHERE request_id=%s FOR UPDATE", (payload["request_id"],))
                row = c.fetchone()
            require(row is not None and row[:3] == (payload["request_hash"], actor, peer))
            import json
            from .receipts import verify_receipt
            result = json.loads(row[4]) if row[4] else None
            verify_receipt(json.loads(bytes(row[5])), result, self.config["root_public_key"])
            return {"status": "APPLIED" if row[3] == "APPLIED" else "HOLD", "result": result}

    def ready(self, peer):
        self.identity()
        with transaction.atomic(durable=True):
            roster, trust, _ = self.control()
            self.peer(roster, peer)
        return {"schema": self.config["schema"], "server_uuid": self.config["server_uuid"],
                "kind": self.config["kind"], "epoch": trust.epoch, "fence_hash": trust.fence_hash,
                "isolated": bool(self.config.get("isolated_datadir"))}

    def dispatch(self, operation, p, actor_id, trust):
        actor = Account.objects.get(pk=actor_id) if actor_id is not None else None
        if operation in PUBLIC:
            require(set(p) == ({"data"} if operation == "registration.submit" else {"data", "token"}))
            from apps.accounts.serializers import RegistrationSerializer
            serializer = RegistrationSerializer(data=p["data"])
            serializer.is_valid(raise_exception=True)
            if operation == "registration.submit":
                from apps.accounts.services import register_account
                return register_account(serializer.validated_data)
            from apps.accounts.reapplication import complete_reapplication
            return complete_reapplication(token=p["token"], data=serializer.validated_data)
        require(actor is not None and actor.is_active and actor.request_status == "Approved")
        if operation.startswith("technical_"):
            require(set(p) == {"bundle"})
            from .provisioning import execute_protected
            return execute_protected(p["bundle"], trust, actor)
        if operation == "bootstrap.initial_admin":
            require(actor.school_id == p.get("operator_school_id"))
            from apps.accounts.admin_bootstrap import provision_first_workspace_admin
            return provision_first_workspace_admin(**p)
        require(type(p.get("actor_id")) is int and p["actor_id"] == actor_id)
        if operation in {"registration.approve", "registration.reject"}:
            require(set(p) == {"actor_id", "target_id", "rejection_code"})
            from apps.accounts.registration_review import approve_registration, reject_registration
            if operation == "registration.approve":
                require(p["rejection_code"] is None)
                return approve_registration(actor=actor, target_id=p["target_id"])
            return reject_registration(actor=actor, target_id=p["target_id"], rejection_code=p["rejection_code"])
        if operation == "role.assign":
            require(set(p) == {"actor_id", "target_id", "role_id"})
            from .role_assignment import assign_ordinary_role
            return assign_ordinary_role(actor=actor, target_id=p["target_id"], role_id=p["role_id"])
        from apps.access_control import mutations
        from apps.access_control.models import Permission, Role
        require(type(p.get("permission_id")) is int)
        permission = Permission.objects.get(pk=p["permission_id"])
        if operation in {"role_permission.grant", "role_permission.revoke"}:
            legacy = {"actor_id", "role_id", "permission_id", "reason"}
            # Preserve the existing fixed legacy operation while admitting
            # an optional boolean CAS precondition for the gated WF-03.02 UI.
            require(set(p) in (legacy, legacy | {"expected_active"})
                    and type(p["role_id"]) is int
                    and ("expected_active" not in p or type(p["expected_active"]) is bool))
            function = mutations.grant_role_permission if operation.endswith("grant") else mutations.revoke_role_permission
            return function(actor=actor, role=Role.objects.get(pk=p["role_id"]), permission=permission,
                            reason=p["reason"], expected_active=p.get("expected_active"))
        # WF-03.03/04: new exact operations are intentionally distinct from
        # the historical unscoped account_permission operations. They are
        # unavailable in every existing executor profile by default.
        if operation in {"account_permission.scoped_grant", "account_permission.restrict"}:
            require(getattr(settings, "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED", False) is True)
            require(getattr(settings, "WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED", False) is True)
            common = {"actor_id", "target_id", "permission_id", "reason", "selected_role_id"}
            grant_fields = common | {"role_id", "expected_active"}
            restriction_fields = common | {"action", "expected_effect", "expected_scope_role_id"}
            require(set(p) == (grant_fields if operation.endswith("scoped_grant") else restriction_fields))
            require(type(p["target_id"]) is int and 0 < p["target_id"] <= 2_147_483_647)
            require(type(p["selected_role_id"]) is int and 0 < p["selected_role_id"] <= 2_147_483_647)
            # Actor proof authenticates the account, not a role-name claim.
            # Rebuild the requested role context from current assigned roles
            # before permission evaluation and inside the ledger transaction.
            from apps.accounts.active_role_context import available_roles, bind_role_scope
            require(any(r["role_id"] == p["selected_role_id"] and r["role_name"] == "Technical Super Admin"
                        for r in available_roles(actor_id)))
            from apps.access_control.technical_admin import has_technical_authority
            with bind_role_scope(actor_id, p["selected_role_id"]):
                require(has_technical_authority(actor, "access_control.account_permissions.manage"))
                target = Account.objects.get(pk=p["target_id"])
                if operation.endswith("scoped_grant"):
                    require(type(p["role_id"]) is int and 0 < p["role_id"] <= 2_147_483_647)
                    require(p["expected_active"] is False)
                    return mutations.grant_account_permission_for_role(
                        actor=actor, target=target, role=Role.objects.get(pk=p["role_id"]),
                        permission=permission, expected_active=p["expected_active"], reason=p["reason"])
                require(type(p["action"]) is str and p["action"] in {"deny", "revoke_grant", "remove_deny"})
                require(p["expected_effect"] is None or
                        type(p["expected_effect"]) is str and p["expected_effect"] in {"Grant", "Deny"})
                require(p["expected_scope_role_id"] is None or
                        type(p["expected_scope_role_id"]) is int and 0 < p["expected_scope_role_id"] <= 2_147_483_647)
                return mutations.change_account_restriction(
                    actor=actor, target=target, permission=permission,
                    action=p["action"], expected_effect=p["expected_effect"],
                    expected_scope_role_id=p["expected_scope_role_id"], reason=p["reason"])
        functions = {"account_permission.grant": mutations.grant_account_permission,
                     "account_permission.deny": mutations.deny_account_permission,
                     "account_permission.deactivate": mutations.deactivate_account_override}
        require(operation in functions and set(p) == {"actor_id", "target_id", "permission_id", "reason"}
                and type(p["target_id"]) is int)
        return functions[operation](actor=actor, target=Account.objects.get(pk=p["target_id"]), permission=permission, reason=p["reason"])
