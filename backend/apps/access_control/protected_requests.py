"""Strict signed Task 2 request verification, without keys, DB I/O or writes.

Trust must come from an independently authenticated deployment channel, never
from the request. A verified request is evidence, NOT a writer capability.
Production enrollment, revocation refresh, DB fencing and durable consumption
remain separate requirements. No test identities are enrolled by this module.
"""

from dataclasses import dataclass
import hashlib
import json
import re


class ProtectedRequestRefused(RuntimeError):
    pass


def require(condition):
    if not condition:
        raise ProtectedRequestRefused("Protected execution evidence is invalid or unavailable.")


def canonical(value):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
        require(len(encoded) <= 32768)
        return encoded
    except (TypeError, ValueError, RecursionError):
        raise ProtectedRequestRefused("Protected execution evidence is invalid or unavailable.") from None


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _hex(value, length=64):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None


def _id(value):
    return type(value) is int and 1 <= value <= 2_147_483_647


CORE_PERMISSIONS = (
    "access_control.account_permissions.manage",
    "access_control.admin_assignments.manage",
    "access_control.audit.read",
    "access_control.catalogue.read",
    "access_control.effective_permissions.inspect",
    "access_control.role_permissions.manage",
)
OPERATIONS = frozenset({"technical_role.provision", "technical_admin.bootstrap"})
REQUEST_FIELDS = frozenset({
    "version", "operation", "request_id", "nonce", "actor_id", "target_id",
    "schema", "incarnation", "epoch", "release_hash", "fence_hash",
    "recovery_hash", "before_hash", "issued_at", "expires_at", "permission_codes",
})
DOMAIN = b"CTUG:TASK2:PROTECTED:v1\x00"


@dataclass(frozen=True)
class TrustedSigner:
    key_id: str
    person_id: str
    duty: str
    public_key: bytes
    account_id: int | None = None


@dataclass(frozen=True)
class ExecutionTrust:
    schema: str
    incarnation: str
    epoch: int
    release_hash: str
    fence_hash: str
    recovery_hash: str
    signers: tuple[TrustedSigner, ...]
    valid_until: int


def validate_trust(trust, now):
    require(type(trust) is ExecutionTrust and type(now) is int and now > 0)
    require(type(trust.schema) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", trust.schema) is not None)
    require(_hex(trust.incarnation) and _id(trust.epoch))
    require(all(_hex(v) for v in (trust.release_hash, trust.fence_hash, trust.recovery_hash)))
    require(type(trust.valid_until) is int and now < trust.valid_until <= now + 300)
    require(type(trust.signers) is tuple and 3 <= len(trust.signers) <= 64)
    require(all(type(s) is TrustedSigner for s in trust.signers))
    for signer in trust.signers:
        require(_hex(signer.key_id) and _hex(signer.person_id))
        require(signer.duty in ("actor", "institutional", "technical"))
        require(type(signer.public_key) is bytes and len(signer.public_key) == 32)
        require(_id(signer.account_id) if signer.duty == "actor" else signer.account_id is None)
    require(len({s.key_id for s in trust.signers}) == len(trust.signers))
    require(len({s.public_key for s in trust.signers}) == len(trust.signers))
    # Enrollment cannot assign one real person multiple approval duties.
    require(len({s.person_id for s in trust.signers}) == len(trust.signers))


def verify_request(bundle, trust, *, now):
    """Verify actor possession plus two distinct, exact-request approvals.

    Detached signatures include their duty/key ID and the entire canonical
    request. Public keys, trust epochs, release gates and DB identity are never
    accepted from a bundle as trust anchors. Return a detached plain request.
    Reverify against fresh trust inside the owning ledger transaction.
    """
    validate_trust(trust, now)
    require(type(bundle) is dict and set(bundle) == {"request", "signatures"})
    # Roundtrip first: reject exotic values and detach caller-owned containers.
    bundle = json.loads(canonical(bundle))
    request, signatures = bundle["request"], bundle["signatures"]
    require(type(request) is dict and set(request) == REQUEST_FIELDS)
    require(type(request["version"]) is int and request["version"] == 1)
    require(type(request["operation"]) is str and request["operation"] in OPERATIONS)
    require(_hex(request["request_id"]) and _hex(request["nonce"]))
    require(_id(request["actor_id"]))
    require(request["target_id"] is None if request["operation"] == "technical_role.provision"
            else _id(request["target_id"]) and request["target_id"] != request["actor_id"])
    for field in ("schema", "incarnation", "epoch", "release_hash", "fence_hash", "recovery_hash"):
        expected = getattr(trust, field)
        require(type(request[field]) is type(expected) and request[field] == expected)
    require(_hex(request["before_hash"]))
    issued, expires = request["issued_at"], request["expires_at"]
    require(type(issued) is int and type(expires) is int)
    require(0 < issued <= now < expires <= issued + 120 and expires <= trust.valid_until)
    require(request["permission_codes"] == list(CORE_PERMISSIONS))
    require(type(signatures) is list and len(signatures) == 3)
    signers = {s.key_id: s for s in trust.signers}
    duties, people, keys = set(), set(), set()
    for envelope in signatures:
        require(type(envelope) is dict and set(envelope) == {"key_id", "duty", "signature"})
        require(_hex(envelope["key_id"]) and _hex(envelope["signature"], 128))
        signer = signers.get(envelope["key_id"])
        require(signer is not None and type(envelope["duty"]) is str and signer.duty == envelope["duty"])
        require(signer.key_id not in keys and signer.person_id not in people and signer.duty not in duties)
        if signer.duty == "actor":
            require(signer.account_id == request["actor_id"])
        message = DOMAIN + canonical({"request": request, "key_id": signer.key_id, "duty": signer.duty})
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(signer.public_key).verify(bytes.fromhex(envelope["signature"]), message)
        except Exception:
            raise ProtectedRequestRefused("Protected execution evidence is invalid or unavailable.") from None
        keys.add(signer.key_id)
        people.add(signer.person_id)
        duties.add(signer.duty)
    require(duties == {"actor", "institutional", "technical"})
    return request
