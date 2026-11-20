"""AR-6C7C.5 draft contract validator. OFFLINE ONLY: never loads Django or a database.

This is intentionally NOT an initializer and does not grant permission or authenticate
operators. Its purpose is to catch silent scope expansion before an implementation
or governance approval is even considered.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SOURCE_DIGEST = "12746bcb7b5b73041606768b9641ced10cec75fec0c6ea7d1b9dae16f3f6f315"
SERVICES = ("accounts", "access_control")
PERMISSIONS = (
    "accounts.registration_requests.read",
    "accounts.registration_requests.approve",
    "accounts.registration_requests.reject",
)
STAGES = ("metadata", "role_grants", "service_activation", "api_activation")
AUTH_FIELDS = (
    "system_owner", "security_reviewer", "change_ticket", "executor_identity",
    "independent_approval_evidence",
)
AUDIT_STATE_FIELDS = frozenset({
    "account_id", "role_id", "permission_id", "service_id", "account_role_id",
    "role_permission_id", "account_permission_id", "role_ids", "permission_ids",
    "effect", "request_status", "is_active",
})
INVARIANTS = frozenset({
    "no_external_writes_from_draft", "no_self_grant",
    "no_framework_superuser_workspace_bypass", "deny_precedence",
    "multi_role_union", "no_erd_change", "no_full_catalogue_seed",
    "no_bulk_queue_changes",
})


class ContractRejected(ValueError):
    """DRAFT scope or provenance differs from reviewed baseline."""


def need(condition, message):
    if not condition:
        raise ContractRejected(message)


def unique(values):
    return type(values) is list and len(values) == len(set(values))


def verify_contract(contract, profile, source, source_raw):
    """Validate a frozen, unapproved contract using only in-memory data.

    Returns a report declaring execution blocked. Never returns an authorization
    token or a callable that could mutate records.
    """
    need(type(contract) is dict and type(profile) is dict and type(source) is dict,
         "Contract, profile and source must be plain objects.")
    need(contract.get("schema_version") ==
         "ctug-registration-review-protected-execution-contract/v0.1", "Unexpected contract schema.")
    need(contract.get("contract_id") == "AR-6C7C5-REGISTRATION-REVIEW-DRAFT", "Contract ID differs.")
    need(contract.get("status") == "DRAFT_UNAPPROVED", "Contract must remain unapproved.")
    need(contract.get("execution_authorized") is False and
         contract.get("database_writes_authorized") is False,
         "An unreviewed contract must never claim authorization.")
    need(type(source_raw) is bytes and hashlib.sha256(source_raw).hexdigest() == SOURCE_DIGEST,
         "Pinned catalogue byte digest differs.")
    need(json.loads(source_raw) == source,
         "In-memory source differs from pinned bytes.")
    need(source.get("manifest_version") == "catalogue-v2.0" and
         source.get("source_revision") == "v2.0-review-1" and
         source.get("planning_only") is True,
         "Source is no longer the reviewed planning-only catalogue.")
    need(contract.get("source") == {
        "manifest_version": "catalogue-v2.0", "source_revision": "v2.0-review-1", "sha256": SOURCE_DIGEST,
    }, "Contract provenance differs.")
    need(profile.get("profile_id") == contract.get("profile_id") ==
         "AR-6C7C-REGISTRATION-REVIEW-V0.1-DRAFT", "Unrecognized draft profile.")
    need(profile.get("status") == "DRAFT_UNAPPROVED" and
         profile.get("source") == {
             "manifest_version": "catalogue-v2.0", "source_revision": "v2.0-review-1",
             "manifest_sha256": SOURCE_DIGEST,
         }, "Profile is not the pinned unapproved draft.")
    need(type(profile.get("gates")) is dict and len(profile["gates"]) == 4 and
         set(profile["gates"]) == {"metadata_initialization", "role_grants", "service_activation", "api_activation"} and
         all(v == "BLOCKED" for v in profile["gates"].values()),
         "Profile gates must all remain blocked.")
    need(type(source.get("operational_gates")) is dict and source["operational_gates"] and
         all(v == "BLOCKED" for v in source["operational_gates"].values()),
         "Source operational gates must remain blocked.")

    allow = profile.get("allowlist")
    intended = contract.get("intended_records")
    need(type(allow) is dict and type(intended) is dict, "Missing exact allowlist.")
    need(allow.get("services") == list(SERVICES) and
         allow.get("permissions") == list(PERMISSIONS) and
         allow.get("role_bindings") == [
             {"role_name": "Admin", "permission_code": code} for code in PERMISSIONS
         ], "Profile includes an unreviewed service, permission or binding.")
    need(intended == {
        "services": list(SERVICES), "permissions": list(PERMISSIONS),
        "role_name": "Admin", "role_bindings": list(PERMISSIONS),
    }, "Execution draft expands or changes the minimum scope.")
    need(type(source.get("services")) is list and
         all(len([x for x in source["services"] if x.get("service_code") == code]) == 1 for code in SERVICES),
         "Missing/duplicate source service.")
    for code in PERMISSIONS:
        matches = [x for x in source.get("permissions", []) if x.get("permission_code") == code]
        need(len(matches) == 1, "Missing or duplicate source permission.")
        p = matches[0]
        need(p.get("service_code") == "accounts" and p.get("scope") == "SCHOOL" and
             p.get("grant_protection") == "GOV" and p.get("readiness") == "P",
             "Permission governance or school scope differs.")
        need({"role_name": "Admin", "permission_code": code} in source.get("default_bindings", []),
             "Missing proposed Admin binding.")

    stages = contract.get("allowed_future_sequence")
    need(type(stages) is list and [s.get("id") for s in stages if type(s) is dict] == list(STAGES) and
         len(stages) == len(STAGES), "Required phase separation differs.")
    need(all(s.get("decision") == "BLOCKED" and type(s.get("future_effect")) is str
             and len(s["future_effect"]) > 20 for s in stages),
         "No phase may be pre-authorized.")
    authorization = contract.get("authorization")
    need(type(authorization) is dict and set(authorization) == set(AUTH_FIELDS) and
         all(authorization[field] is None for field in AUTH_FIELDS),
         "This draft cannot be used to assert approval identities or evidence.")
    need(profile.get("approval") == {
         "system_owner": None, "security_reviewer": None, "change_ticket": None,
    }, "Profile approval must remain blank.")
    audit = contract.get("audit_limits")
    need(type(audit) is dict and audit.get("reason_code") == "permission_change" and
         type(audit.get("action_code_max_length")) is int and audit["action_code_max_length"] == 50 and
         type(audit.get("max_snapshot_bytes")) is int and audit["max_snapshot_bytes"] == 2048 and
         unique(audit.get("old_new_fields")) and
         frozenset(audit["old_new_fields"]) == AUDIT_STATE_FIELDS,
         "Audit contract must match the bounded existing writer.")
    flags = contract.get("invariants")
    need(unique(flags) and frozenset(flags) == INVARIANTS,
         "Core authorization and preservation invariants changed.")
    return {
        "mode": "OFFLINE DRAFT CONTRACT VALIDATION ONLY",
        "contract": contract["contract_id"],
        "metadata": {"services": len(SERVICES), "permissions": len(PERMISSIONS)},
        "protected_admin_bindings": len(PERMISSIONS),
        "phases": list(STAGES),
        "all_gates_blocked": True,
        "operator_approved": False,
        "database_accessed": False,
        "writes_performed": False,
        "execution_authorized": False,
    }


def load_local():
    """Read only this script's known repository-local, non-secret JSON files."""
    backend = Path(__file__).resolve().parents[1]
    catalog_dir = backend / "apps" / "access_control" / "catalogue"
    paths = (
        catalog_dir / "registration_review_execution_contract_v0_1_draft.json",
        catalog_dir / "registration_review_profile_v0_1_draft.json",
        catalog_dir / "v2_0.json",
    )
    files = [path.read_bytes() for path in paths]
    contract, profile, source = [json.loads(data) for data in files]
    return contract, profile, source, files[2]


if __name__ == "__main__":
    try:
        report = verify_contract(*load_local())
    except (ContractRejected, OSError, ValueError, TypeError) as exc:
        raise SystemExit(f"CONTRACT REFUSED: {exc}") from None
    for key, value in report.items():
        print(f"{key}: {value}")
