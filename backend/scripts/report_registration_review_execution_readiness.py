"""AR-6C7D.5 offline-only registration review execution readiness report.

No Django, ORM, SQL, network, .env, credentials or filesystem writes.
This script validates only the existing frozen DRAFT contract and makes the
remaining governance blockers visible. It CANNOT authorize execution.
"""

from __future__ import annotations

import argparse
import json
import sys

from scripts.validate_registration_review_execution_contract import (
    ContractRejected,
    load_local,
    verify_contract,
)


class ReadinessRefused(ValueError):
    """Source, profile or frozen execution contract was inconsistent."""


def build_readiness_report(contract, profile, source, source_raw):
    """Produce only a non-executable, blocked-stage evidence report."""
    verified = verify_contract(contract, profile, source, source_raw)
    stages = contract["allowed_future_sequence"]
    required = ("metadata", "role_grants", "service_activation", "api_activation")
    if tuple(item["id"] for item in stages) != required:
        raise ReadinessRefused("Unexpected stage order.")
    if not all(item["decision"] == "BLOCKED" for item in stages):
        raise ReadinessRefused("A future stage was prematurely unblocked.")

    # This validator cannot authenticate any person or witness a signature.
    # Owner scope approval is documented in the separate D4 draft; it does not
    # populate the intentionally blank independent-review/operator fields.
    return {
        "mode": "AR-6C7D.5 OFFLINE EXECUTION READINESS REVIEW ONLY",
        "contract_id": verified["contract"],
        "source_sha256": contract["source"]["sha256"],
        "scope": {
            "services": list(contract["intended_records"]["services"]),
            "permission_definitions": list(contract["intended_records"]["permissions"]),
            "role_name": contract["intended_records"]["role_name"],
            "role_bindings": list(contract["intended_records"]["role_bindings"]),
        },
        "stages": [{"id": item["id"], "status": "BLOCKED"} for item in stages],
        "owner_scope_decision": "RECORDED IN AR-6C7D.4 DRAFT; NOT INDEPENDENT EXECUTION APPROVAL",
        "unverified_requirements": [
            "Authentic system-owner approval evidence linked to exact scope and source digest",
            "Independent security reviewer identity and signoff",
            "Approved change ticket, authorized executor identity and execution window",
            "Reviewed real initializer with exact audited write-set and concurrency/rollback design",
            "Fresh read-only MySQL diff, backup/restore plan and same-database postchecks",
            "Separate approvals for metadata, protected bindings, service activation and API rollout",
            "Authenticated role/CSRF/negative-case E2E tests before any release",
        ],
        "live_database_checked": False,
        "route_and_runtime_gates_checked": False,
        "database_writes_performed": False,
        "live_execution_authorized": False,
        "release_ready": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        result = build_readiness_report(*load_local())
    except (ContractRejected, ReadinessRefused, OSError, ValueError,
            TypeError, KeyError, json.JSONDecodeError) as exc:
        # Never report a valid plan from a corrupted or changed proposal.
        print(f"READINESS REFUSED: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["mode"])
        print("CONTRACT:", result["contract_id"])
        print("SOURCE SHA-256:", result["source_sha256"])
        print("SCOPE:", len(result["scope"]["services"]), "services,",
              len(result["scope"]["permission_definitions"]), "permissions,",
              len(result["scope"]["role_bindings"]), "Admin bindings")
        for stage in result["stages"]:
            print("GATE:", stage["id"], stage["status"])
        print("OUTSTANDING EVIDENCE:", len(result["unverified_requirements"]), "items")
        print("LIVE DB CHECKED: NO")
        print("WRITES PERFORMED: NO")
        print("EXECUTION AUTHORIZED: NO")
        print("RELEASE READY: NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
