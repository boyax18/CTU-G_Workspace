"""G1A: deliberately NON-OPERATIONAL simulations for disposable tests only.

These functions MUST NOT be used by production endpoints or command handlers.
They provide no persistence, replay safety across processes, transaction locks,
trusted identity evidence, or privileged operation implementation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.access_control.services import has_permission
from apps.access_control.tests_support.technical_super_admin_test_only import composed_profile_test_only


@dataclass(frozen=True)
class SimulatedApprovalEvidence:
    """In-memory test fixture, not an approval record or credential."""

    request_id: str
    action: str
    target_account_id: int
    before_digest: str
    policy_version: str
    institutional_approver_id: int
    technical_custodian_id: int
    executor_id: int
    issued_at: datetime
    expires_at: datetime
    consumed: bool = False


def evidence_matches_test_only(
    evidence, *, action, target_account_id, before_digest, policy_version, now
):
    """Demonstrate exact-scope/expiry/separation checks in memory; authorizes nothing."""
    if type(evidence) is not SimulatedApprovalEvidence:
        return False
    if not isinstance(now, datetime) or now.tzinfo is None:
        return False
    if (
        not isinstance(evidence.expires_at, datetime)
        or evidence.expires_at.tzinfo is None
        or not isinstance(evidence.issued_at, datetime)
        or evidence.issued_at.tzinfo is None
    ):
        return False
    if (
        type(evidence.consumed) is not bool
        or evidence.consumed
        or type(evidence.request_id) is not str
        or not 1 <= len(evidence.request_id.strip()) <= 80
    ):
        return False
    if (
        type(action) is not str or not action.strip()
        or type(target_account_id) is not int or target_account_id <= 0
        or type(before_digest) is not str or len(before_digest) != 64
        or any(ch not in "0123456789abcdef" for ch in before_digest)
        or type(policy_version) is not str or not policy_version.strip()
    ):
        return False
    principals = (
        evidence.target_account_id,
        evidence.institutional_approver_id,
        evidence.technical_custodian_id,
        evidence.executor_id,
    )
    if any(type(identity) is not int or identity <= 0 for identity in principals):
        return False
    # For these test-only fixtures, target, independent approvers and executor
    # are all distinct. A real policy must review identity attestations first.
    if len(set(principals)) != len(principals):
        return False
    return (
        evidence.action == action
        and evidence.target_account_id == target_account_id
        and evidence.before_digest == before_digest
        and evidence.policy_version == policy_version
        and evidence.issued_at <= now < evidence.expires_at
        and timedelta(0) < evidence.expires_at - evidence.issued_at <= timedelta(minutes=15)
    )


def eligible_core_operator_ids_test_only(accounts, core_codes):
    """Snapshot existing evaluator + both active roles; no locking or writes.

    Never call the snapshot inside a real protected mutation. That operation
    will require a separately approved consistent MySQL locking protocol.
    """
    if type(core_codes) not in (tuple, frozenset) or not core_codes:
        return frozenset()
    if any(type(code) is not str or not code.startswith("access_control.") for code in core_codes):
        return frozenset()
    if len(set(core_codes)) != len(core_codes):
        return frozenset()
    try:
        return frozenset(
            account.pk for account in accounts
            if composed_profile_test_only(account)
            and all(has_permission(account, code) for code in core_codes)
        )
    except Exception:
        return frozenset()


def preserves_operator_floor_test_only(before_ids, after_ids, *, minimum_remaining=1):
    """Test-only last-operator/quorum policy; NEVER a concurrency guard."""
    if (
        type(before_ids) is not frozenset
        or type(after_ids) is not frozenset
        or type(minimum_remaining) is not int
        or minimum_remaining not in {1, 2}
        or not before_ids
        or any(type(pk) is not int or pk <= 0 for pk in before_ids | after_ids)
    ):
        return False
    return len(after_ids) >= minimum_remaining


def protected_action_preview_test_only(
    actor, *, action_permission, target_account_id, evidence,
    action, before_digest, policy_version, now
):
    """Reference negative/positive test conditions only; not executable authority."""
    if (
        type(target_account_id) is not int or target_account_id <= 0
        or type(action_permission) is not str
        or not action_permission.startswith("access_control.")
        or not composed_profile_test_only(actor)
        or actor.pk == target_account_id
        or not has_permission(actor, action_permission)
    ):
        return False
    return (
        evidence_matches_test_only(
            evidence, action=action, target_account_id=target_account_id,
            before_digest=before_digest, policy_version=policy_version, now=now,
        ) and evidence.executor_id == actor.pk
    )
