"""G1D-P3C3 offline recovery triage. SYNTHETIC / TEST-ONLY.

Never used by a production command, connection, migration, or API. The caller
provides synthetic facts; the function does not authenticate their origin.
A returned label must NEVER authorize retry or privileged database writes.
"""

from dataclasses import dataclass
import re
from uuid import UUID


SCHEMA = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z")
STATES = frozenset({"Pending", "Ready", "Attempted", "Consumed", "Rejected", "Cancelled", "Expired"})
RESOLUTIONS = frozenset({"COMMITTED", "NOT_COMMITTED", "UNKNOWN"})
RELEASE_STATUS = "BLOCKED"


class RecoveryRefused(ValueError):
    """Malformed synthetic facts: fail closed rather than guessing."""


@dataclass(frozen=True)
class SyntheticRecoveryFacts:
    schema: str
    incarnation: str
    request_id: str
    status: str
    resolution: str
    execution_reservations: int
    consumption_events: int
    attached_role_ids: tuple[int, ...]
    attached_audit_ids: tuple[int, ...]
    role_is_inactive: bool | None
    before_state_matches: bool | None
    after_state_matches: bool | None
    independent_receipt_matches: bool | None
    trust_epoch_consistent: bool | None


@dataclass(frozen=True)
class RecoveryTriage:
    classification: str
    issues: tuple[str, ...]
    release_status: str = RELEASE_STATUS
    allow_retry: bool = False
    allow_provisioning: bool = False


def _uuid_valid(value):
    if type(value) is not str:
        return False
    try:
        obj = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return str(obj) == value and obj.version == 4


def _valid_ids(values):
    return (type(values) is tuple and len(values) <= 1
            and all(type(x) is int and 0 < x <= 2_147_483_647 for x in values))


def triage_recovery(facts):
    """Classify *untrusted* crash/recovery observations; never authorize action.

    The existing disposable ledger's NOT_COMMITTED result means that a role
    mutation was not observed, NOT that an execution reservation can be reused.
    In particular Attempted + NOT_COMMITTED is permanently a human hold here.
    """
    if type(facts) is not SyntheticRecoveryFacts:
        raise RecoveryRefused("Expected exact synthetic fact structure")
    if not (type(facts.schema) is str and SCHEMA.fullmatch(facts.schema)
            and _uuid_valid(facts.incarnation) and _uuid_valid(facts.request_id)):
        raise RecoveryRefused("Wrong environment or invalid request identity")
    if not (type(facts.status) is str and facts.status in STATES
            and type(facts.resolution) is str and facts.resolution in RESOLUTIONS):
        raise RecoveryRefused("Invalid status or resolution")
    if (type(facts.execution_reservations) is not int
            or facts.execution_reservations not in (0, 1)
            or type(facts.consumption_events) is not int
            or facts.consumption_events not in (0, 1)
            or not _valid_ids(facts.attached_role_ids)
            or not _valid_ids(facts.attached_audit_ids)):
        raise RecoveryRefused("Unbounded or malformed lifecycle values")
    for evidence in (
        facts.role_is_inactive, facts.before_state_matches,
        facts.after_state_matches, facts.independent_receipt_matches,
        facts.trust_epoch_consistent,
    ):
        if evidence is not None and type(evidence) is not bool:
            raise RecoveryRefused("Evidence requires exact booleans or unknown")

    issues = []
    # These checks detect inconsistency in a caller-provided snapshot, NOT
    # authenticity. No positive conclusion can authorize or unblock a release.
    if facts.trust_epoch_consistent is not True:
        issues.append("TRUST_EPOCH_NOT_VERIFIED")
    if facts.resolution == "UNKNOWN":
        issues.append("TRANSACTION_OUTCOME_UNKNOWN")
    if facts.execution_reservations == 1:
        issues.append("EXECUTION_RESERVED_NEVER_RETRY")

    if facts.resolution == "COMMITTED" or facts.status == "Consumed":
        if facts.resolution != "COMMITTED" or facts.status != "Consumed":
            issues.append("CONSUMED_RESOLUTION_CONFLICT")
        if (facts.execution_reservations != 1 or facts.consumption_events != 1
                or len(facts.attached_role_ids) != 1 or len(facts.attached_audit_ids) != 1):
            issues.append("COMMITTED_REFERENCES_INCOMPLETE")
        if facts.role_is_inactive is not True or facts.after_state_matches is not True:
            issues.append("COMMITTED_POSTCONDITIONS_UNVERIFIED")
        if facts.independent_receipt_matches is not True:
            issues.append("INDEPENDENT_RECEIPT_UNVERIFIED")
        if facts.before_state_matches is not None:
            # The current after-state is not supposed to equal before-state.
            # We require a separately measured after-state instead.
            pass
        if not issues or issues == ["EXECUTION_RESERVED_NEVER_RETRY"]:
            return RecoveryTriage("SYNTHETIC_COMMIT_COHERENT", tuple(issues))
        return RecoveryTriage("SECURITY_HOLD", tuple(sorted(set(issues))))

    if (facts.consumption_events or facts.attached_role_ids or facts.attached_audit_ids):
        issues.append("UNCONSUMED_REFERENCES_PRESENT")
    if facts.role_is_inactive is not None or facts.after_state_matches is True:
        issues.append("UNCONSUMED_POSTCONDITION_CONFLICT")
    if facts.independent_receipt_matches is True:
        issues.append("UNCONSUMED_RECEIPT_CONFLICT")
    if facts.resolution != "NOT_COMMITTED":
        issues.append("NOT_COMMITTED_NOT_ESTABLISHED")
    if facts.before_state_matches is not True:
        issues.append("BEFORE_STATE_NOT_VERIFIED")
    if facts.status == "Attempted" and facts.execution_reservations != 1:
        issues.append("ATTEMPTED_RESERVATION_MISSING")
    if facts.status in ("Pending", "Ready", "Rejected", "Cancelled", "Expired") and facts.execution_reservations:
        issues.append("RESERVATION_STATE_CONFLICT")
    if facts.execution_reservations:
        issues.append("ATTEMPTED_OUTCOME_REQUIRES_RECONCILIATION")
    if issues:
        return RecoveryTriage("SECURITY_HOLD", tuple(sorted(set(issues))))
    return RecoveryTriage("SYNTHETIC_NO_MUTATION_OBSERVED", ())


OPERATIONAL_EVIDENCE = (
    "all_principals_and_definers_inventoried",
    "dba_fence_attested_independently",
    "least_privilege_credentials_attested",
    "competing_sessions_drained",
    "real_signer_custody_verified",
    "fresh_protected_backup_restored_and_compared",
    "independent_receipt_custody_verified",
    "emergency_halt_and_recovery_rehearsed",
)


def operational_release_triage(observations):
    """Summarize self-reported operational evidence, never certify it.

    The user-controlled flags cannot authenticate a DBA, backup or custodian;
    even all True MUST remain BLOCKED until external release procedures exist.
    """
    if type(observations) is not dict or set(observations) != set(OPERATIONAL_EVIDENCE):
        raise RecoveryRefused("Operational evidence shape is incomplete")
    if any(type(v) is not bool for v in observations.values()):
        raise RecoveryRefused("Operational evidence must be exact booleans")
    missing = tuple(sorted(name for name, value in observations.items() if not value))
    return {
        "release_status": RELEASE_STATUS,
        "independent_attestation_verified": False,
        "claimed_complete_count": len(OPERATIONAL_EVIDENCE) - len(missing),
        "missing_evidence_categories": missing,
        "reason": "Caller claims do not establish verified writer fencing or live approval.",
    }
