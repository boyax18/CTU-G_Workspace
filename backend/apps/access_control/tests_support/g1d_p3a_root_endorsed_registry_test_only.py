"""G1D-P3A: OFFLINE/SYNTHETIC root-endorsed registry contract, TEST ONLY.

NEVER imported into a production service or CLI. No database access, key
provisioning, institutional identity enrollment, or live write authorization.
The trusted public-root pins and minimum epoch must ultimately come from a
separate, independently authenticated deployment process; callers supplying
these parameters cannot establish real-world trust themselves.
"""

from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import g1d_p1_authorization_design_test_only as auth


POLICY = "G1D-P3A-SYNTHETIC-ROOT-ROSTER-V1"
DOMAIN = b"CTUG:G1D-P3A:DISPOSABLE:ROOT-ROSTER:v1\0"
MANIFEST_FIELDS = frozenset({
    "policy", "schema", "incarnation", "trust_epoch", "roster_sha256",
    "issued_at", "expires_at",
})
ROOT_DUTIES = frozenset({"institutional_root", "technical_root"})
IDENTITY_DUTIES = frozenset({"institutional", "technical", "executor", "issuer"})


@dataclass(frozen=True)
class RootPin:
    key_id: str
    person_id: str
    duty: str
    public_key: bytes
    revoked: bool = False
    valid_until: int = 2_147_483_647


@dataclass(frozen=True)
class RootEndorsement:
    key_id: str
    person_id: str
    duty: str
    signature: bytes


@dataclass(frozen=True)
class RootEndorsedRegistry:
    manifest: bytes
    trust: auth.SyntheticTrust
    endorsements: tuple[RootEndorsement, ...]


def roster_bytes(trust):
    """Deterministic bounded test encoding, NOT general-purpose JCS."""
    auth.validate_trust(trust)
    records = []
    for identity in sorted(trust.identities, key=lambda item: item.key_id):
        records.append(auth.canonical({
            "key_id": identity.key_id,
            "person_id": identity.person_id,
            "duty": identity.duty,
            "public_key_hex": identity.public_key.hex(),
            "account_id": identity.account_id,
            "revoked": identity.revoked,
            "valid_until": identity.valid_until,
        }))
    return b"CTUG:P3A:ROSTER:v1\n" + b"\n".join(records) + b"\n"


def make_unsigned_manifest(trust, *, issued_at, expires_at):
    """Convenience for synthetic fixture creation; deliberately NOT signing."""
    return auth.canonical({
        "policy": POLICY,
        "schema": trust.schema,
        "incarnation": trust.incarnation,
        "trust_epoch": trust.epoch,
        "roster_sha256": auth.digest(roster_bytes(trust)),
        "issued_at": issued_at,
        "expires_at": expires_at,
    })


def verify_root_endorsed_registry(
    registry, pinned_roots, *, expected_schema, expected_incarnation,
    minimum_epoch, now,
):
    """Return synthetic trust only if two independently PINNED roots sign it.

    The pins and epoch are external verifier inputs; this function cannot prove
    their custody, authenticity, current revocation state, or real identities.
    """
    auth.require(type(registry) is RootEndorsedRegistry)
    auth.require(type(pinned_roots) is tuple and len(pinned_roots) == 2)
    auth.require(type(registry.endorsements) is tuple and len(registry.endorsements) == 2)
    auth.require(type(expected_schema) is str and auth.SCHEMA.fullmatch(expected_schema) is not None)
    auth.require(auth.uuid_value(expected_incarnation))
    auth.require(type(minimum_epoch) is int and minimum_epoch > 0)
    auth.require(type(now) is int and now >= 0)

    # Validate the independently pinned roots, not any keys embedded in the
    # signed manifest. A single person's two keys are NOT two independent roots.
    roots_by_duty = {}
    root_people, root_keys, root_ids = set(), set(), set()
    for pin in pinned_roots:
        auth.require(type(pin) is RootPin)
        auth.require(pin.duty in ROOT_DUTIES and pin.duty not in roots_by_duty)
        auth.require(type(pin.key_id) is str and auth.KEY_ID.fullmatch(pin.key_id) is not None)
        auth.require(auth.uuid_value(pin.person_id))
        auth.require(type(pin.public_key) is bytes and len(pin.public_key) == 32)
        auth.require(type(pin.revoked) is bool and pin.revoked is False)
        auth.require(type(pin.valid_until) is int and now < pin.valid_until)
        auth.require(pin.key_id not in root_ids and pin.person_id not in root_people)
        auth.require(pin.public_key not in root_keys)
        roots_by_duty[pin.duty] = pin
        root_ids.add(pin.key_id)
        root_people.add(pin.person_id)
        root_keys.add(pin.public_key)
    auth.require(set(roots_by_duty) == ROOT_DUTIES)

    trust = registry.trust
    auth.validate_trust(trust)
    auth.require(trust.schema == expected_schema and trust.incarnation == expected_incarnation)
    auth.require(trust.epoch >= minimum_epoch)
    manifest = auth.parse(registry.manifest, MANIFEST_FIELDS)
    auth.require(manifest["policy"] == POLICY)
    auth.require(manifest["schema"] == expected_schema)
    auth.require(manifest["incarnation"] == expected_incarnation)
    auth.require(type(manifest["trust_epoch"]) is int and manifest["trust_epoch"] == trust.epoch)
    auth.require(manifest["roster_sha256"] == auth.digest(roster_bytes(trust)))
    auth.time_window(manifest, now, 86400)

    # A separately authorized, root-endorsed roster must not allow one person
    # to impersonate distinct human duties using multiple signing keys.
    people = set(root_people)
    all_keys = set(root_keys)
    all_ids = set(root_ids)
    active_duties = set()
    for identity in trust.identities:
        auth.require(identity.person_id not in people and identity.key_id not in all_ids)
        auth.require(identity.public_key not in all_keys)
        people.add(identity.person_id)
        all_keys.add(identity.public_key)
        all_ids.add(identity.key_id)
        if not identity.revoked and now < identity.valid_until:
            auth.require(identity.duty in IDENTITY_DUTIES and identity.duty not in active_duties)
            active_duties.add(identity.duty)
    auth.require(active_duties == IDENTITY_DUTIES)

    seen = set()
    for endorsement in registry.endorsements:
        auth.require(type(endorsement) is RootEndorsement)
        auth.require(endorsement.duty in ROOT_DUTIES and endorsement.duty not in seen)
        pin = roots_by_duty[endorsement.duty]
        auth.require(endorsement.key_id == pin.key_id and endorsement.person_id == pin.person_id)
        auth.require(type(endorsement.signature) is bytes and len(endorsement.signature) == 64)
        try:
            Ed25519PublicKey.from_public_bytes(pin.public_key).verify(
                endorsement.signature, DOMAIN + registry.manifest
            )
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise auth.ContractRefused("Synthetic root endorsement refused.") from exc
        seen.add(endorsement.duty)
    auth.require(seen == ROOT_DUTIES)
    return trust
