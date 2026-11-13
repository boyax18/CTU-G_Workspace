"""G1D-P3B: offline synthetic executor-to-release binding, TEST ONLY.

No database connection, real authority, signing keys, credential enrollment, or
live role provisioning. External expectations and root pins must be trusted
independently; caller-controlled expectations are not an authorization source.
"""

from dataclasses import dataclass

from . import g1d_p1_authorization_design_test_only as auth
from . import g1d_p3a_root_endorsed_registry_test_only as roots


@dataclass(frozen=True)
class IndependentTestExpectation:
    """Exact values supplied by an independently approved TEST fixture."""

    schema: str
    incarnation: str
    minimum_epoch: int
    roster_sha256: str
    actor_id: int
    challenge: str
    request_sha256: str
    bundle_sha256: str
    ticket_nonce: str
    before_sha256: str
    backup_sha256: str
    release_sha256: str


@dataclass(frozen=True)
class VerifiedTestExecutor:
    """A non-transferable TEST receipt; NOT a live capability or permission."""

    request_id: str
    actor_id: int
    request_sha256: str
    bundle_sha256: str
    ticket_nonce: str
    roster_sha256: str
    trust_epoch: int
    ticket_expires_at: int


def verify_root_bound_executor(registry, pinned_roots, bundle, *, expected, now):
    """Compose P3A root verification with P1 signed executor proof verification.

    Tests bind to independent hashes of the roster, request, complete bundle,
    release artifact, backup, before-state, and signed ticket nonce. This is
    cryptographic TEST validation only: it cannot establish account eligibility,
    one-use ledger consumption, independent custody, or the database writer fence.
    """
    auth.require(type(expected) is IndependentTestExpectation)
    auth.require(type(expected.schema) is str and auth.SCHEMA.fullmatch(expected.schema) is not None)
    auth.require(auth.uuid_value(expected.incarnation))
    auth.require(type(expected.minimum_epoch) is int and expected.minimum_epoch > 0)
    auth.require(type(expected.actor_id) is int and 1 <= expected.actor_id <= 2_147_483_647)
    for field in (
        "roster_sha256", "challenge", "request_sha256", "bundle_sha256",
        "ticket_nonce", "before_sha256", "backup_sha256", "release_sha256",
    ):
        auth.require(auth.hash_value(getattr(expected, field)))
    auth.require(type(now) is int and now >= 0)

    trust = roots.verify_root_endorsed_registry(
        registry, pinned_roots,
        expected_schema=expected.schema,
        expected_incarnation=expected.incarnation,
        minimum_epoch=expected.minimum_epoch,
        now=now,
    )
    roster_hash = auth.digest(roots.roster_bytes(trust))
    auth.require(roster_hash == expected.roster_sha256)
    request = auth.verify_bundle(
        bundle, trust,
        now=now,
        expected_actor_id=expected.actor_id,
        expected_challenge=expected.challenge,
    )
    ticket = auth.parse(bundle.ticket.payload, auth.TICKET_FIELDS)
    bundle_hash = auth.digest(auth.encode_bundle(bundle))
    auth.require(auth.digest(bundle.request) == expected.request_sha256)
    auth.require(bundle_hash == expected.bundle_sha256)
    auth.require(ticket["nonce"] == expected.ticket_nonce)
    auth.require(request["before_sha256"] == expected.before_sha256)
    auth.require(request["backup_sha256"] == expected.backup_sha256)
    auth.require(request["release_sha256"] == expected.release_sha256)
    auth.require(request["trust_epoch"] == trust.epoch)
    return VerifiedTestExecutor(
        request_id=request["request_id"],
        actor_id=expected.actor_id,
        request_sha256=expected.request_sha256,
        bundle_sha256=expected.bundle_sha256,
        ticket_nonce=expected.ticket_nonce,
        roster_sha256=roster_hash,
        trust_epoch=trust.epoch,
        ticket_expires_at=ticket["expires_at"],
    )
