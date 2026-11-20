"""G1C non-operational planning fixtures. NEVER import into live services.

No database, signer verification, ticket issuance, lock, write or authorization.
A structurally consistent fictional approval is NOT an authorized request.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import re

from apps.access_control.tests_support.g1b_catalogue_test_only import CORE_K_CODES

NORMAL_ROLE = "Admin"
TECHNICAL_ROLE = "Technical Super Admin"
PROFILE = (NORMAL_ROLE, TECHNICAL_ROLE)
POLICY = "G1C-PLANNING-ONLY-V1"
MANIFEST = "catalogue-v2.0/v2.0-review-1"
MAX_TICKET_LIFETIME = timedelta(minutes=15)
_ALLOWED_ACTIONS = frozenset({"first_bootstrap", "technical_role_change"})
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,80}\Z", re.ASCII)
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,80}\Z", re.ASCII)


@dataclass(frozen=True)
class FictionalRequest:
    request_id: str
    idempotency_key: str
    operation: str
    target_account_id: int
    environment: str
    before_digest: str
    proposed_roles: tuple[str, ...]
    proposed_core_codes: tuple[str, ...]
    policy_version: str
    catalogue_revision: str


@dataclass(frozen=True)
class FictionalApproval:
    duty: str  # institutional or technical, NOT a new application Admin role
    claimed_person_id: int
    request_digest: str
    decision: str


@dataclass(frozen=True)
class FictionalTicket:
    request_digest: str
    nonce: str
    issued_at: datetime
    expires_at: datetime
    consumed: bool = False


@dataclass(frozen=True)
class FictionalBundle:
    request: FictionalRequest
    approvals: tuple[FictionalApproval, ...]
    ticket: FictionalTicket
    executor_id: int


@dataclass(frozen=True)
class FictionalLedgerReceipt:
    request_id: str
    idempotency_key: str
    nonce: str


@dataclass(frozen=True)
class FictionalOperator:
    account_id: int
    approved: bool
    active: bool
    active_roles: frozenset[str]
    effective_codes: frozenset[str]
    session_usable: bool


def _is_valid_hash(value):
    return type(value) is str and _HEX_SHA256.fullmatch(value) is not None


def _is_valid_id(value):
    return type(value) is int and 0 < value <= 2_147_483_647


def _is_disposable_environment(value):
    return type(value) is str and re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", value) is not None


def canonical_request_digest_test_only(request):
    """Pure canonical request fingerprint; not a signature or trust assertion."""
    if type(request) is not FictionalRequest:
        return None
    if (
        type(request.request_id) is not str or _REQUEST_ID.fullmatch(request.request_id) is None
        or type(request.idempotency_key) is not str or _NONCE.fullmatch(request.idempotency_key) is None
        or type(request.operation) is not str or request.operation not in _ALLOWED_ACTIONS
        or not _is_valid_id(request.target_account_id)
        or not _is_disposable_environment(request.environment)
        or not _is_valid_hash(request.before_digest)
        or type(request.proposed_roles) is not tuple or request.proposed_roles != PROFILE
        or type(request.proposed_core_codes) is not tuple or request.proposed_core_codes != CORE_K_CODES
        or type(request.policy_version) is not str or request.policy_version != POLICY
        or type(request.catalogue_revision) is not str or request.catalogue_revision != MANIFEST
    ):
        return None
    payload = {
        "catalogue_revision": request.catalogue_revision,
        "environment": request.environment,
        "idempotency_key": request.idempotency_key,
        "operation": request.operation,
        "policy_version": request.policy_version,
        "proposed_core_codes": list(request.proposed_core_codes),
        "proposed_roles": list(request.proposed_roles),
        "request_id": request.request_id,
        "target_account_id": request.target_account_id,
        "before_digest": request.before_digest,
    }
    encoding = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoding).hexdigest()


def structural_evidence_issues_test_only(bundle, *, now, expected_environment, expected_before_digest):
    """List structural problems in FICTIONAL evidence. An empty list grants NOTHING.

    In particular claimed_person_id is not verified identity, and this function
    never verifies signatures, durable uniqueness, session state or atomic usage.
    """
    if type(bundle) is not FictionalBundle:
        return ("invalid-bundle",)
    r, t = bundle.request, bundle.ticket
    digest = canonical_request_digest_test_only(r)
    if digest is None:
        return ("invalid-request",)
    problems = set()
    if not _is_disposable_environment(expected_environment) or r.environment != expected_environment:
        problems.add("wrong-environment")
    if not _is_valid_hash(expected_before_digest) or r.before_digest != expected_before_digest:
        problems.add("stale-before-state")
    if not _is_valid_id(bundle.executor_id) or bundle.executor_id == r.target_account_id:
        problems.add("invalid-executor")
    if type(bundle.approvals) is not tuple or len(bundle.approvals) != 2 or any(type(a) is not FictionalApproval for a in bundle.approvals):
        problems.add("invalid-approvers")
    else:
        if set(a.duty for a in bundle.approvals) != {"institutional", "technical"}:
            problems.add("invalid-duties")
        identities = [a.claimed_person_id for a in bundle.approvals]
        if (
            any(not _is_valid_id(i) for i in identities)
            or len(set(identities + [bundle.executor_id, r.target_account_id])) != 4
        ):
            problems.add("separation-failed")
        if any(a.request_digest != digest or a.decision != "approve" for a in bundle.approvals):
            problems.add("approval-mismatch")
    if type(t) is not FictionalTicket:
        problems.add("invalid-ticket")
    else:
        if t.request_digest != digest or type(t.nonce) is not str or _NONCE.fullmatch(t.nonce) is None:
            problems.add("ticket-scope-mismatch")
        if type(t.consumed) is not bool or t.consumed:
            problems.add("ticket-spent")
        if (
            type(now) is not datetime or now.tzinfo is None
            or type(t.issued_at) is not datetime or t.issued_at.tzinfo is None
            or type(t.expires_at) is not datetime or t.expires_at.tzinfo is None
        ):
            problems.add("invalid-ticket-time")
        elif not (
            timedelta(0) < t.expires_at - t.issued_at <= MAX_TICKET_LIFETIME
            and t.issued_at <= now < t.expires_at
        ):
            problems.add("ticket-expired-or-invalid")
    return tuple(sorted(problems))


def proposed_ledger_conflicts_test_only(receipts, new_receipt):
    """Snapshot uniqueness preview only; NOT a durable single-use ledger."""
    if (
        type(receipts) is not tuple or type(new_receipt) is not FictionalLedgerReceipt
        or any(type(item) is not FictionalLedgerReceipt for item in receipts)
    ):
        return ("invalid-ledger",)
    values = (new_receipt.request_id, new_receipt.idempotency_key, new_receipt.nonce)
    if (
        type(values[0]) is not str or type(values[1]) is not str or type(values[2]) is not str
        or _REQUEST_ID.fullmatch(values[0]) is None
        or _NONCE.fullmatch(values[1]) is None
        or _NONCE.fullmatch(values[2]) is None
    ):
        return ("invalid-receipt",)
    conflicts = set()
    for old in receipts:
        if new_receipt.request_id == old.request_id:
            conflicts.add("duplicate-request")
        if new_receipt.idempotency_key == old.idempotency_key:
            conflicts.add("duplicate-idempotency")
        if new_receipt.nonce == old.nonce:
            conflicts.add("replayed-nonce")
    return tuple(sorted(conflicts))


def effective_operator_ids_test_only(operators, required_codes=CORE_K_CODES):
    """Pure after-state planning snapshot, not a production permission evaluator."""
    if (
        type(operators) not in (tuple, frozenset)
        or type(required_codes) is not tuple
        or not required_codes
        or any(type(c) is not str or not c.startswith("access_control.") for c in required_codes)
        or len(set(required_codes)) != len(required_codes)
        or any(type(o) is not FictionalOperator for o in operators)
    ):
        return frozenset()
    return frozenset(
        o.account_id for o in operators
        if _is_valid_id(o.account_id)
        and o.approved is True and o.active is True and o.session_usable is True
        and type(o.active_roles) is frozenset
        and {NORMAL_ROLE, TECHNICAL_ROLE}.issubset(o.active_roles)
        and type(o.effective_codes) is frozenset
        and set(required_codes).issubset(o.effective_codes)
    )


def floor_transition_issues_test_only(before, after, *, routine=True, minimum_remaining=1):
    """Unserialized in-memory floor illustration; cannot guard concurrent writes."""
    if (
        type(before) not in (tuple, frozenset) or type(after) not in (tuple, frozenset)
        or type(routine) is not bool or type(minimum_remaining) is not int
        or minimum_remaining not in (1, 2)
        or any(type(x) is not FictionalOperator for x in before)
        or any(type(x) is not FictionalOperator for x in after)
    ):
        return ("invalid-state",)
    b = effective_operator_ids_test_only(before)
    a = effective_operator_ids_test_only(after)
    if not routine:  # first-bootstrap is a distinct, NOT IMPLEMENTED ceremony
        return ("bootstrap-requires-separate-approval",)
    if not b:
        return ("not-bootstrapped",)
    if len(a) < minimum_remaining:
        return ("operator-floor-lost",)
    return ()


def static_contract_issues_test_only():
    """Static consistency with the six planning codes, no DB or authority."""
    issues = set()
    if PROFILE != ("Admin", "Technical Super Admin") or len(PROFILE) != 2:
        issues.add("admin-profile-drift")
    if len(CORE_K_CODES) != 6 or len(set(CORE_K_CODES)) != 6:
        issues.add("core-k-drift")
    if MAX_TICKET_LIFETIME != timedelta(minutes=15):
        issues.add("ticket-policy-drift")
    return tuple(sorted(issues))
