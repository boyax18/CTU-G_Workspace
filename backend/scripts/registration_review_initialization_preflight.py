"""AR-6C7C.4: pure, fail-closed preparation of a NON-EXECUTABLE plan.

Inputs: already produced read-only v2 planner report and the unchanged,
versioned catalogue/profile. No ORM imports, I/O, writes, or grant functions.
This module is NOT an initializer and cannot authorize one.
"""

from __future__ import annotations

from scripts.plan_registration_review_profile import (
    BINDINGS, PERMISSIONS, SERVICES, verify,
)


class InitializationPreflightError(ValueError):
    """Review-only preparation was refused; never repair automatically."""


def _require(condition, message):
    if not condition:
        raise InitializationPreflightError(message)


def build_preflight(*, profile, source, source_sha256, database_report):
    """Return an exact, non-executable proposal or fail closed.

    The caller must obtain database_report from the existing v2 planner's
    MySQL READ ONLY, SELECT-only snapshot. Neither this function nor its
    caller has an apply, seed, grant, activation or commit path.
    """
    try:
        static = verify(profile, source, source_sha256)
    except (ValueError, TypeError, KeyError) as exc:
        raise InitializationPreflightError("Static profile/source validation failed.") from exc

    r = database_report
    _require(type(r) is dict, "Read-only planner report is missing.")
    _require(r.get("mode") == "READ-ONLY V2 PLANNING",
             "Only the existing read-only v2 planner may supply a report.")
    _require(r.get("database_vendor") == "mysql", "Expected MySQL snapshot.")
    _require(r.get("application_approved") is False
             and type(r.get("database_modifications")) is int
             and r["database_modifications"] == 0,
             "Planner did not explicitly refuse approval or writes.")
    _require("SELECT-only" in r.get("guarantee", "")
             and "READ ONLY" in r.get("guarantee", ""),
             "Read-only transaction guarantee is missing.")
    _require(r.get("manifest") == source["manifest_version"]
             and r.get("source_revision") == source["source_revision"]
             and r.get("provenance") == source["provenance"]["proposal"],
             "Read-only report does not match the pinned catalogue proposal.")
    expected_proposed = {
        "services": len(source["services"]),
        "permissions": len(source["permissions"]),
        "roles": len(source["roles"]),
        "role_bindings": len(source["default_bindings"]),
        "retired_tombstones": len(source["historical_retirements"]),
    }
    _require(r.get("proposed") == expected_proposed,
             "Planner totals do not match the source proposal.")
    _require(type(r.get("totals")) is dict and r["totals"].get("CONFLICT") == 0
             and type(r.get("review_totals")) is dict
             and r["review_totals"].get("CONFLICT") == 0,
             "Unresolved catalogue or review conflict; stop.")
    for key in ("unexpected", "retirement_review", "account_override_review"):
        _require(r.get(key) == [], f"Existing {key} requires separate review; stop.")
    _require(type(r.get("blocked_dependencies")) is list
             and bool(r["blocked_dependencies"]),
             "The planner did not preserve blocked dependencies.")
    _require(type(source.get("operational_gates")) is dict
             and bool(source["operational_gates"])
             and all(status == "BLOCKED"
                     for status in source["operational_gates"].values()),
             "Source operational gates are not all blocked.")

    records = r.get("records")
    _require(type(records) is list, "Read-only planner has no records.")

    def exact(kind, key, allowed):
        matches = [row for row in records if type(row) is dict
                   and row.get("kind") == kind and row.get("key") == key]
        _require(len(matches) == 1, f"Missing/duplicate {kind} record: {key}.")
        status = matches[0].get("classification")
        _require(status in allowed, f"Unsafe state for {kind}: {key}.")
        _require(matches[0].get("application_approved") is not True,
                 f"Unreviewed activation assertion: {kind} {key}.")
        return status

    _require(exact("role", "Admin", {"MATCH"}) == "MATCH",
             "Base Admin role must already exist.")

    # Do not create, activate, or grant: these are classifications only.
    proposed_metadata = [
        {"kind": "service", "code": code,
         "state": exact("service", code, {"CREATE", "MATCH"}),
         "allowed_future_state": "INACTIVE_METADATA_ONLY"}
        for code in SERVICES
    ]
    proposed_metadata += [
        {"kind": "permission", "code": code,
         "state": exact("permission", code, {"CREATE", "MATCH"}),
         "allowed_future_state": "DEFINITION_ONLY"}
        for code in PERMISSIONS
    ]
    deferred_grants = [
        {"kind": "role_binding", "role": role, "permission_code": code,
         "state": exact("role_binding", f"{role} -> {code}", {"DEFER"}),
         "allowed_future_state": "BLOCKED_UNTIL_INDEPENDENT_APPROVAL"}
        for role, code in BINDINGS
    ]
    return {
        "mode": "READ-ONLY INITIALIZATION PREFLIGHT — NO EXECUTION",
        "profile": static["profile"],
        "source_sha256": source_sha256,
        "database_snapshot_source": "existing v2 READ ONLY planner",
        "metadata_proposals": proposed_metadata,
        "deferred_role_grants": deferred_grants,
        "activation_gates": {key: "BLOCKED" for key in sorted(profile["gates"])},
        "execution_authorized": False,
        "writes_performed": False,
        "release_ready": False,
        "outstanding": [
            "System owner and independent security review of exact profile and source digest",
            "Attributable protected operator, audit schema/actions and concurrency design",
            "Isolated MySQL write/rollback tests and explicit metadata execution approval",
            "Separate role-grant and service activation approvals",
            "Separate Registration Review API activation and browser E2E acceptance",
        ],
    }
