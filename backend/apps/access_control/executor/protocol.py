"""Bounded wire format and executor-issued, certificate-bound actor proofs."""
import hashlib
import json
import secrets
import time

from apps.access_control.protected_requests import canonical, require, _hex, _id

DOMAIN = b"CTUG:EXECUTOR:ACTOR:v1\x00"
ORDINARY = frozenset({"registration.approve", "registration.reject", "role.assign",
    "role_permission.grant", "role_permission.revoke", "account_permission.grant",
    "account_permission.deny", "account_permission.deactivate", "registration.submit",
    "registration.reapply"})
PROTECTED = frozenset({"technical_role.provision", "technical_admin.bootstrap", "bootstrap.initial_admin"})
PUBLIC = frozenset({"registration.submit", "registration.reapply"})


def now():
    return int(time.time())


def decode(data):
    require(type(data) is bytes and 0 < len(data) <= 32768)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    try:
        result = json.loads(data, object_pairs_hook=pairs)
        canonical(result)
        return result
    except (ValueError, TypeError, RecursionError):
        require(False)


def issue_proof(key, *, actor_id, peer, epoch, issued=None):
    issued = now() if issued is None else issued
    payload = {"actor_id": actor_id, "peer": peer, "epoch": epoch,
               "issued": issued, "expires": issued + 300, "nonce": secrets.token_hex(32)}
    return {"payload": payload, "signature": key.sign(DOMAIN + canonical(payload)).hex()}


def actor_from_proof(proof, public_keys, *, peer, epoch, at=None):
    at = now() if at is None else at
    require(type(proof) is dict and set(proof) == {"payload", "signature"})
    p = proof["payload"]
    require(type(p) is dict and set(p) == {"actor_id", "peer", "epoch", "issued", "expires", "nonce"})
    require(_id(p["actor_id"]) and _hex(p["nonce"]) and _hex(proof["signature"], 128))
    require(p["peer"] == peer and type(p["epoch"]) is int and p["epoch"] == epoch)
    require(type(p["issued"]) is int and type(p["expires"]) is int
            and 0 < p["issued"] <= at < p["expires"] <= p["issued"] + 300)
    for key in public_keys:
        try:
            key.verify(bytes.fromhex(proof["signature"]), DOMAIN + canonical(p))
            return p["actor_id"]
        except Exception:
            pass
    require(False)


def request(operation, payload, proof=None):
    issued = now()
    return {"version": 1, "request_id": secrets.token_hex(32), "nonce": secrets.token_hex(32),
            "operation": operation, "payload": payload, "actor_proof": proof,
            "issued": issued, "expires": issued + 120}


def validate_request(value, kind, *, at=None):
    at = now() if at is None else at
    require(type(value) is dict and set(value) == {"version", "request_id", "nonce", "operation",
                                                "payload", "actor_proof", "issued", "expires"})
    canonical(value)
    require(type(value["version"]) is int and value["version"] == 1)
    require(_hex(value["request_id"]) and _hex(value["nonce"]))
    require(type(value["operation"]) is str and value["operation"] in (ORDINARY if kind == "ordinary" else PROTECTED))
    require(type(value["payload"]) is dict)
    require(type(value["issued"]) is int and type(value["expires"]) is int
            and 0 < value["issued"] <= at < value["expires"] <= value["issued"] + 120)
    # Passwords/reapplication secrets never enter the durable evidence ledger.
    return value


def fingerprint(certificate):
    return hashlib.sha256(certificate).hexdigest()


def sanitize_evidence(value):
    """Keep recovery hashes reproducible without persisting secrets or applicant PII."""
    if type(value) is dict:
        sensitive = {"password", "password_confirmation", "operator_password", "new_password", "token",
                     "school_id", "email", "first_name", "middle_name", "last_name", "suffix", "operator_school_id", "new_school_id", "new_email"}
        return {k: "[REDACTED]" if k in sensitive else sanitize_evidence(v) for k, v in value.items()}
    if type(value) is list:
        return [sanitize_evidence(v) for v in value]
    return value
