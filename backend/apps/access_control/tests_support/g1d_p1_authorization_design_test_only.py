"""Synthetic Ed25519 contracts ONLY; no institutional trust or live authority.

Test callers supply public keys for fictional people. Private keys are generated
in memory by tests, never loaded here. The flat printable-ASCII/integer encoding
is a deliberately restricted canonical JSON subset, NOT a general JCS library.
No database calls, signing implementation, production import or release path.
"""

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .g1d_p1_signed_evidence_test_only import ACTION, ROLE_DESCRIPTION, ROLE_NAME


POLICY = "G1D-P1-SYNTHETIC-ED25519-V1"
ENVIRONMENT = "DISPOSABLE_TEST_ONLY"
SCHEMA = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z", re.ASCII)
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
KEY_ID = re.compile(r"test_[a-z0-9_]{1,50}\Z", re.ASCII)
REQUEST_FIELDS = frozenset({
    "request_id", "idempotency_key", "operation", "role_name", "description",
    "is_active", "target_schema", "environment", "incarnation", "policy",
    "executor_account_id", "executor_person", "executor_key", "trust_epoch",
    "before_sha256", "backup_sha256", "release_sha256", "issued_at", "expires_at",
})
APPROVAL_FIELDS = frozenset({
    "approval_id", "key_id", "person_id", "duty", "request_sha256", "decision",
    "trust_epoch", "issued_at", "expires_at",
})
TICKET_FIELDS = frozenset({
    "key_id", "person_id", "request_sha256", "institutional_sha256", "technical_sha256",
    "nonce", "executor_account_id", "release_sha256", "trust_epoch", "issued_at", "expires_at",
})
EXECUTOR_FIELDS = frozenset({
    "key_id", "person_id", "request_sha256", "nonce", "executor_account_id",
    "release_sha256", "challenge", "trust_epoch", "issued_at", "expires_at",
})
CANCEL_FIELDS = frozenset({"key_id", "person_id", "request_sha256", "decision", "trust_epoch", "issued_at", "expires_at"})


class ContractRefused(RuntimeError):
    """Bounded denial; never echo submitted evidence or identifiers."""


def require(condition, message="Synthetic authorization contract refused."):
    if not condition:
        raise ContractRefused(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    """Only flat ASCII objects, booleans and exact safe integers are supported."""
    require(type(data) is dict and 0 < len(data) <= 32)
    for key, value in data.items():
        require(type(key) is str and re.fullmatch(r"[a-z_][a-z0-9_]*", key) is not None)
        if type(value) is str:
            require(len(value) <= 8192 and all(32 <= ord(c) < 127 for c in value))
        else:
            require(type(value) is bool or (type(value) is int and 0 <= value <= 9_007_199_254_740_991))
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    require(len(encoded) <= 65536)
    return encoded


def parse(payload, fields):
    require(type(payload) is bytes and 0 < len(payload) <= 8192)

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    try:
        data = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
        require(type(data) is dict and set(data) == fields and canonical(data) == payload)
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise ContractRefused("Malformed synthetic evidence.") from exc
    return data


def uuid_value(value):
    try:
        return type(value) is str and str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def hash_value(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def time_window(data, now, maximum):
    require(type(now) is int and type(data["issued_at"]) is int and type(data["expires_at"]) is int)
    require(0 <= data["issued_at"] <= now < data["expires_at"])
    require(0 < data["expires_at"] - data["issued_at"] <= maximum)


@dataclass(frozen=True)
class TestPublicIdentity:
    key_id: str
    person_id: str
    duty: str
    public_key: bytes
    account_id: int = 0
    revoked: bool = False
    valid_until: int = 2_147_483_647


@dataclass(frozen=True)
class SyntheticTrust:
    schema: str
    incarnation: str
    epoch: int
    identities: tuple[TestPublicIdentity, ...]


@dataclass(frozen=True)
class SignedTestProof:
    payload: bytes
    signature: bytes


@dataclass(frozen=True)
class SyntheticBundle:
    request: bytes
    approvals: tuple[SignedTestProof, ...]
    ticket: SignedTestProof
    executor: SignedTestProof


def signature_message(purpose, payload):
    require(purpose in {"approval", "ticket", "executor", "cancel"})
    return ("CTUG:G1D-P1:DISPOSABLE:" + purpose + ":v1\0").encode("ascii") + payload


def validate_trust(trust):
    require(type(trust) is SyntheticTrust)
    require(type(trust.schema) is str and SCHEMA.fullmatch(trust.schema) is not None)
    require(uuid_value(trust.incarnation) and type(trust.epoch) is int and trust.epoch > 0)
    require(type(trust.identities) is tuple and 4 <= len(trust.identities) <= 16)
    seen, public_keys = set(), set()
    for identity in trust.identities:
        require(type(identity) is TestPublicIdentity)
        require(type(identity.key_id) is str and KEY_ID.fullmatch(identity.key_id) is not None)
        require(identity.key_id not in seen and uuid_value(identity.person_id))
        require(identity.duty in {"institutional", "technical", "executor", "issuer"})
        require(type(identity.public_key) is bytes and len(identity.public_key) == 32)
        require(identity.public_key not in public_keys)
        require(type(identity.revoked) is bool and type(identity.valid_until) is int)
        require(type(identity.account_id) is int and 0 <= identity.account_id <= 2_147_483_647)
        seen.add(identity.key_id)
        public_keys.add(identity.public_key)


def verify_proof(proof, purpose, fields, trust, now):
    require(type(proof) is SignedTestProof)
    require(type(proof.signature) is bytes and len(proof.signature) == 64)
    data = parse(proof.payload, fields)
    matches = [identity for identity in trust.identities if identity.key_id == data["key_id"]]
    require(len(matches) == 1)
    identity = matches[0]
    require(identity.person_id == data["person_id"] and not identity.revoked and now < identity.valid_until)
    require(type(data["trust_epoch"]) is int and data["trust_epoch"] == trust.epoch)
    try:
        Ed25519PublicKey.from_public_bytes(identity.public_key).verify(
            proof.signature, signature_message(purpose, proof.payload)
        )
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise ContractRefused("Synthetic public-key verification refused.") from exc
    return data, identity


def proof_digest(proof):
    return digest(proof.payload + proof.signature)


def verify_bundle(bundle, trust, *, now, expected_actor_id, expected_challenge):
    """Authenticates ONLY fictional test-key possession; not institutional identity."""
    validate_trust(trust)
    require(type(bundle) is SyntheticBundle and type(now) is int)
    request = parse(bundle.request, REQUEST_FIELDS)
    require(type(expected_actor_id) is int and 1 <= expected_actor_id <= 2_147_483_647)
    require(hash_value(expected_challenge))
    require(uuid_value(request["request_id"]) and uuid_value(request["executor_person"]))
    require(hash_value(request["idempotency_key"]))
    require(request["operation"] == ACTION and request["role_name"] == ROLE_NAME)
    require(request["description"] == ROLE_DESCRIPTION and request["is_active"] is False)
    require(request["target_schema"] == trust.schema and request["environment"] == ENVIRONMENT)
    require(request["incarnation"] == trust.incarnation and request["policy"] == POLICY)
    require(type(request["trust_epoch"]) is int and request["trust_epoch"] == trust.epoch)
    require(type(request["executor_account_id"]) is int and request["executor_account_id"] == expected_actor_id)
    require(all(hash_value(request[field]) for field in ("before_sha256", "backup_sha256", "release_sha256")))
    time_window(request, now, 86400)
    request_hash = digest(bundle.request)
    require(type(bundle.approvals) is tuple and len(bundle.approvals) == 2)
    duties, people, hashes = set(), {request["executor_person"]}, {}
    approval_expiries = []
    for proof in bundle.approvals:
        approval, identity = verify_proof(proof, "approval", APPROVAL_FIELDS, trust, now)
        require(uuid_value(approval["approval_id"]) and approval["request_sha256"] == request_hash)
        require(identity.duty == approval["duty"] and identity.duty in {"institutional", "technical"})
        require(approval["decision"] == "approve" and identity.duty not in duties and identity.person_id not in people)
        time_window(approval, now, 86400)
        require(request["issued_at"] <= approval["issued_at"] and approval["expires_at"] <= request["expires_at"])
        duties.add(identity.duty)
        people.add(identity.person_id)
        hashes[identity.duty + "_sha256"] = proof_digest(proof)
        approval_expiries.append(approval["expires_at"])
    require(duties == {"institutional", "technical"} and len(people) == 3)
    ticket, issuer = verify_proof(bundle.ticket, "ticket", TICKET_FIELDS, trust, now)
    require(issuer.duty == "issuer" and ticket["request_sha256"] == request_hash and hash_value(ticket["nonce"]))
    require(all(ticket[field] == value for field, value in hashes.items()))
    require(ticket["executor_account_id"] == expected_actor_id and type(ticket["executor_account_id"]) is int)
    require(ticket["release_sha256"] == request["release_sha256"])
    time_window(ticket, now, 900)
    require(ticket["issued_at"] >= max(parse(p.payload, APPROVAL_FIELDS)["issued_at"] for p in bundle.approvals))
    require(ticket["expires_at"] <= min(approval_expiries))
    executor, identity = verify_proof(bundle.executor, "executor", EXECUTOR_FIELDS, trust, now)
    require(identity.duty == "executor" and identity.account_id == expected_actor_id)
    require(identity.person_id == request["executor_person"] and identity.key_id == request["executor_key"])
    require(executor["request_sha256"] == request_hash and executor["nonce"] == ticket["nonce"])
    require(type(executor["executor_account_id"]) is int and executor["executor_account_id"] == expected_actor_id)
    require(executor["release_sha256"] == request["release_sha256"] and executor["challenge"] == expected_challenge)
    time_window(executor, now, 300)
    require(ticket["issued_at"] <= executor["issued_at"] and executor["expires_at"] <= ticket["expires_at"])
    return request


def encode_bundle(bundle):
    def encoded(value):
        return base64.b64encode(value).decode("ascii")
    require(type(bundle) is SyntheticBundle and len(bundle.approvals) == 2)
    data = {"request": encoded(bundle.request)}
    for name, proof in zip(("institutional", "technical", "ticket", "executor"), (*bundle.approvals, bundle.ticket, bundle.executor)):
        data[name + "_payload"] = encoded(proof.payload)
        data[name + "_signature"] = encoded(proof.signature)
    return canonical(data)


def decode_bundle(blob):
    fields = {"request"} | {name + suffix for name in ("institutional", "technical", "ticket", "executor") for suffix in ("_payload", "_signature")}
    data = parse(bytes(blob), fields)
    try:
        def decoded(field):
            return base64.b64decode(data[field], validate=True)
        proofs = tuple(SignedTestProof(decoded(name + "_payload"), decoded(name + "_signature"))
                       for name in ("institutional", "technical", "ticket", "executor"))
        return SyntheticBundle(decoded("request"), proofs[:2], proofs[2], proofs[3])
    except (ValueError, TypeError) as exc:
        raise ContractRefused("Malformed stored synthetic evidence.") from exc
