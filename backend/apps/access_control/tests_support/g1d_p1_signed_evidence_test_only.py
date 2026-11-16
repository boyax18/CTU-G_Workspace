"""G1D-P1: purely fictional independent-approval evidence contracts.

This is NOT identity verification, an authorized live ticket or a trust store.
Test callers inject fictional, independent HMAC keys. No production key is known.
No database access, and no privileged user or grant is authorized by this module.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import re


ROLE_NAME = "Technical Super Admin"
ROLE_DESCRIPTION = (
    "Protected technical administration role. Activation and assignment require "
    "independently approved governance procedures."
)
ACTION = "create_inactive_technical_super_admin_role"
POLICY = "G1D-P1-LOCAL-DESIGN-V1"
MAX_LIFETIME = timedelta(minutes=15)
SCHEMA_PATTERN = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z", re.ASCII)
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
TOKEN = re.compile(r"[A-Za-z0-9_-]{16,80}\Z", re.ASCII)
SIGNER = re.compile(r"[A-Za-z0-9_-]{8,80}\Z", re.ASCII)


@dataclass(frozen=True)
class FictionalRoleRequest:
    operation: str
    target_schema: str
    executor_account_id: int
    role_name: str
    description: str
    is_active: bool
    backup_sha256: str
    before_sha256: str
    ticket_nonce: str
    issued_at: datetime
    expires_at: datetime
    policy: str


@dataclass(frozen=True)
class FictionalSignedApproval:
    duty: str
    signer_id: str
    signer_account_id: int
    request_sha256: str
    signature_hex: str
    decision: str = "approve"


@dataclass(frozen=True)
class FictionalIndependentEvidence:
    request: FictionalRoleRequest
    approvals: tuple[FictionalSignedApproval, ...]


def _valid_time(value):
    return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None


def canonical_request_sha256(request):
    """Serialize the FULL proposed mutation and execution scope; not a signature."""
    if type(request) is not FictionalRoleRequest:
        return None
    if (
        request.operation != ACTION
        or type(request.target_schema) is not str
        or not SCHEMA_PATTERN.fullmatch(request.target_schema)
        or type(request.executor_account_id) is not int
        or not 1 <= request.executor_account_id <= 2_147_483_647
        or request.role_name != ROLE_NAME
        or request.description != ROLE_DESCRIPTION
        or request.is_active is not False
        or type(request.backup_sha256) is not str
        or not HEX_SHA.fullmatch(request.backup_sha256)
        or type(request.before_sha256) is not str
        or not HEX_SHA.fullmatch(request.before_sha256)
        or type(request.ticket_nonce) is not str
        or not TOKEN.fullmatch(request.ticket_nonce)
        or not _valid_time(request.issued_at)
        or not _valid_time(request.expires_at)
        or not timedelta(0) < request.expires_at - request.issued_at <= MAX_LIFETIME
        or request.policy != POLICY
    ):
        return None
    payload = {
        "operation": request.operation,
        "target_schema": request.target_schema,
        "executor_account_id": request.executor_account_id,
        "role_name": request.role_name,
        "description": request.description,
        "is_active": request.is_active,
        "backup_sha256": request.backup_sha256,
        "before_sha256": request.before_sha256,
        "ticket_nonce": request.ticket_nonce,
        "issued_at": request.issued_at.isoformat(),
        "expires_at": request.expires_at.isoformat(),
        "policy": request.policy,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def fictional_approval_signature(request_sha256, *, duty, signer_id, signer_account_id, test_key):
    """For disposable tests ONLY. Never use a caller-provided key as live trust."""
    if (
        type(request_sha256) is not str or not HEX_SHA.fullmatch(request_sha256)
        or duty not in ("institutional", "technical")
        or type(signer_id) is not str or not SIGNER.fullmatch(signer_id)
        or type(signer_account_id) is not int or not 1 <= signer_account_id <= 2_147_483_647
        or type(test_key) is not bytes or len(test_key) < 32
    ):
        return None
    message = f"G1D-P1-TEST:{request_sha256}:{duty}:{signer_id}:{signer_account_id}:approve".encode("ascii")
    return hmac.new(test_key, message, hashlib.sha256).hexdigest()


def fictional_independent_approval_issues(evidence, *, now, expected_schema, expected_executor_id, trusted_test_signers):
    """Verify fictional HMAC/structural evidence; NEVER proves a real signer.

    trusted_test_signers is a dict of signer_id -> (duty, signer_account_id, secret_bytes).
    In a real service, caller-supplied trust roots are UNACCEPTABLE.
    """
    if type(evidence) is not FictionalIndependentEvidence:
        return ("invalid-evidence",)
    req = evidence.request
    digest = canonical_request_sha256(req)
    if digest is None:
        return ("invalid-request",)
    issues = set()
    if req.target_schema != expected_schema or not SCHEMA_PATTERN.fullmatch(str(expected_schema)):
        issues.add("wrong-schema")
    if type(expected_executor_id) is not int or req.executor_account_id != expected_executor_id:
        issues.add("wrong-executor")
    if not _valid_time(now) or not req.issued_at <= now < req.expires_at:
        issues.add("expired-or-invalid-ticket")
    if type(trusted_test_signers) is not dict:
        issues.add("missing-test-trust-registry")
        trusted_test_signers = {}
    approvals = evidence.approvals
    if type(approvals) is not tuple or len(approvals) != 2 or any(type(a) is not FictionalSignedApproval for a in approvals):
        issues.add("incorrect-approval-set")
    else:
        if any(type(a.duty) is not str for a in approvals) or {a.duty for a in approvals} != {"institutional", "technical"}:
            issues.add("incorrect-duties")
        if any(type(a.signer_id) is not str for a in approvals):
            issues.add("invalid-signer")
        elif len({a.signer_id for a in approvals}) != 2:
            issues.add("same-signer")
        person_ids = [a.signer_account_id for a in approvals]
        if any(type(i) is not int or not 1 <= i <= 2_147_483_647 for i in person_ids):
            issues.add("invalid-signer-account")
        elif len(set(person_ids + [req.executor_account_id])) != 3:
            issues.add("separation-failed")
        for approval in approvals:
            if (
                type(approval.signer_id) is not str
                or not SIGNER.fullmatch(approval.signer_id)
                or approval.decision != "approve"
                or approval.request_sha256 != digest
                or type(approval.signature_hex) is not str
                or not HEX_SHA.fullmatch(approval.signature_hex)
            ):
                issues.add("approval-invalid")
                continue
            trusted = trusted_test_signers.get(approval.signer_id)
            if (
                type(trusted) is not tuple or len(trusted) != 3
                or trusted[0] != approval.duty
                or trusted[1] != approval.signer_account_id
            ):
                issues.add("untrusted-signer")
                continue
            expected_sig = fictional_approval_signature(
                digest, duty=approval.duty, signer_id=approval.signer_id,
                signer_account_id=approval.signer_account_id, test_key=trusted[2]
            )
            if expected_sig is None or not hmac.compare_digest(expected_sig, approval.signature_hex):
                issues.add("bad-test-signature")
    return tuple(sorted(issues))
