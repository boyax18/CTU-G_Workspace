"""Read-only static checks for CTU-G Workspace AR-6B1 candidate catalogue.

This script does not import Django or connect to MySQL. It only reads a local
JSON manifest and deliberately refuses any non-planning manifest. It does not
approve a catalogue, seed definitions or activate permissions.

Run from backend/: python scripts/check_registration_review_catalogue.py
"""

import json
import sys
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "apps" / "access_control" / "catalogue" / "v2_0.json"
EXPECTED = (
    "accounts.registration_requests.read",
    "accounts.registration_requests.approve",
    "accounts.registration_requests.reject",
)
REQUIRED_GATES = (
    "initialization", "grants", "service_activation", "live_mutations",
    "first_operator_attribution", "independent_review_evidence",
    "object_authorization", "session_revocation",
)


def inspect_manifest(path: Path = MANIFEST) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = []
    definitions = payload.get("permissions", [])
    bindings = payload.get("default_bindings", [])
    services = payload.get("services", [])
    gates = payload.get("operational_gates", {})
    if payload.get("planning_only") is not True:
        issues.append("Manifest is not explicitly planning_only=true")
    if not isinstance(definitions, list) or not isinstance(bindings, list):
        raise ValueError("Invalid permissions or default_bindings collection")
    if len(definitions) != 95 or len(bindings) != 106 or len(services) != 10:
        issues.append("Manifest totals differ from reviewed V2 candidate (95/106/10)")
    codes = [x.get("permission_code") for x in definitions]
    if len(codes) != len(set(codes)):
        issues.append("Duplicated permission_code in manifest")
    pairs = [(x.get("role_name"), x.get("permission_code")) for x in bindings]
    if len(pairs) != len(set(pairs)):
        issues.append("Duplicated role/permission binding in manifest")
    details = []
    for code in EXPECTED:
        rows = [x for x in definitions if x.get("permission_code") == code]
        if len(rows) != 1:
            issues.append(f"Expected exactly one definition for {code}; found {len(rows)}")
            continue
        row = rows[0]
        expected_fields = {
            "service_code": "accounts",
            "readiness": "P",
            "scope": "SCHOOL",
            "grant_protection": "GOV",
        }
        for field, value in expected_fields.items():
            if row.get(field) != value:
                issues.append(f"{code}: {field} must be {value!r}, found {row.get(field)!r}")
        actual_roles = sorted(role for role, permission in pairs if permission == code)
        if actual_roles != ["Admin"]:
            issues.append(f"{code}: expected proposed binding [Admin], found {actual_roles!r}")
        details.append({"code": code, "roles": actual_roles, "scope": row.get("scope")})
    for gate in REQUIRED_GATES:
        if gates.get(gate) != "BLOCKED":
            issues.append(f"Operational gate {gate!r} is no longer BLOCKED")
    return {
        "manifest": payload.get("manifest_version"),
        "planning_only": payload.get("planning_only"),
        "definitions": len(definitions),
        "bindings": len(bindings),
        "services": len(services),
        "details": details,
        "issues": issues,
    }


def main() -> int:
    print("AR-6B1 STATIC CATALOGUE INSPECTION — NO DATABASE CONNECTION")
    try:
        report = inspect_manifest()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAILED TO INSPECT: {exc}", file=sys.stderr)
        return 2
    print(f"Manifest: {report['manifest']}; planning_only={report['planning_only']}")
    print(f"Counts: {report['services']} services, {report['definitions']} permissions, {report['bindings']} proposed bindings")
    for row in report["details"]:
        print(f"REVIEW: {row['code']} -> {','.join(row['roles'])}; scope={row['scope']}")
    if report["issues"]:
        for issue in report["issues"]:
            print(f"CHECK FAILED: {issue}", file=sys.stderr)
        return 1
    print("STATIC CHECK PASSED. The candidate is STILL NOT APPROVED FOR ACTIVATION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
