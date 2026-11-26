"""Offline v2.3 candidate only. No Django, connection, installer or runtime import."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from apps.access_control.catalogue import validation_v2 as v2
from apps.access_control.catalogue import validation_v2_2 as v22

HERE = Path(__file__).resolve().parent
BASE_DIGEST = "192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d"
ADDENDUM = "review_only/academic_settings_v2_3/ADDENDUM_PROPOSED.md"
# Implementer-authored integrity check only; NOT an independently approved/protected pin.
CANDIDATE_ADDENDUM_SHA256 = "e9c3d4f094a465cf946c7ab89167b84a367a9d122957c71a7f130914a315e552"
VERSIONS = {"schema_version": "static-catalogue-v2.3", "manifest_version": "catalogue-v2.3",
            "source_revision": "v2.3-candidate-1"}
NEW = (
    ("academic.enrollment_verifications.record", "Record official enrollment verification", "enrollment_verifications",
     "record", "SCHOOL", "Admin",
     "Record or revoke official in-person enrollment evidence and verified historical gaps; no self-verification or Student onboarding confirmation."),
    ("academic.semester_onboarding.self.submit", "Submit own semester onboarding", "semester_onboarding",
     "submit_self", "OWN", "Student",
     "Save and confirm own Active-semester onboarding; internal atomic participation, clearance and fee snapshots only; no signing or fee management."),
    ("academic.historical_participation.correct", "Correct missing historical participation", "historical_participation",
     "correct", "SCHOOL", "Admin",
     "Create one missing evidenced Closed/Archived-semester participation with original fee and pending clearance; never by the evidence recorder; no rewriting existing records or reopening periods."),
)
DEFINITIONS = (
    ("academic.courses.manage", "Maintain approved course definitions; preserve referenced historical records.",
     "Maintain approved course definitions and versioned curricula; published curriculum versions are immutable; preserve referenced historical records."),
    ("academic.periods.manage", "Maintain school-year/semester dates and activation with consistency and historical-data checks.",
     "Maintain school-year/semester dates, activation and section subject offerings with consistency and historical-data checks; instructor assignments require their separate permission."),
)
DENY_PREDECESSORS = {
    NEW[0][0]: ("academic.profiles.manage",),
    NEW[1][0]: ("clearance.requests.self.submit",),
    NEW[2][0]: ("academic.periods.manage", "academic.profiles.manage"),
}


def expected_delta():
    ops = [{"op": "move_default_binding", "permission_code": "finance.fee_schedule.manage",
            "from_role": "Treasurer", "to_role": "Admin"}]
    for code, name, module, action, scope, role, description in NEW:
        ops.extend([
            {"op": "add_permission", "permission": {
                "service_code": "academic", "permission_code": code, "permission_name": name,
                "module_name": module, "action_name": action, "description": description,
                "readiness": "P", "origin": "ADD", "scope": scope, "grant_protection": "ORD"}},
            {"op": "add_default_binding", "role_name": role, "permission_code": code},
        ])
    ops.extend({"op": "restate_permission_definition", "permission_code": code, "old": old, "new": new}
               for code, old, new in DEFINITIONS)
    return {"schema_version": "catalogue-delta-v2.3",
            "base": {"manifest_version": "catalogue-v2.2", "effective_digest": BASE_DIGEST,
                     "addendum_sha256": v22.ADDENDUM_SHA256},
            "addendum": {"path": ADDENDUM, "sha256": CANDIDATE_ADDENDUM_SHA256},
            "result": dict(VERSIONS), "operations": ops,
            "independent_review": {"status": "OPEN", "note": "Candidate only; independent governance and pin approval not performed. Provisioning NOT_AUTHORIZED."}}


def validate_candidate(delta=None, *, addendum_bytes=None):
    base = v22.validate_catalogue()  # unchanged, source-pinned complete base chain
    if base.digest != BASE_DIGEST:
        raise ValueError("Base v2.2 changed; stop for review.")
    addendum = (ROOT / ADDENDUM).read_bytes() if addendum_bytes is None else addendum_bytes
    if sha256(addendum).hexdigest() != CANDIDATE_ADDENDUM_SHA256:
        raise ValueError("Candidate addendum changed; update review evidence explicitly.")
    if delta is None:
        delta = v2._json((HERE / "v2_3_delta.json").read_bytes())
    if not v2._strict_equal(delta, expected_delta()):
        raise ValueError("Candidate differs from the exact review-only operations.")
    before = v22._thaw(base.data)
    data = deepcopy(before)
    for op in delta["operations"]:
        if op["op"] == "move_default_binding":
            old = {"role_name": op["from_role"], "permission_code": op["permission_code"]}
            data["default_bindings"][data["default_bindings"].index(old)] = {
                "role_name": op["to_role"], "permission_code": op["permission_code"]}
        elif op["op"] == "add_permission":
            data["permissions"].append(deepcopy(op["permission"]))
        elif op["op"] == "add_default_binding":
            data["default_bindings"].append({k: op[k] for k in ("role_name", "permission_code")})
        elif op["op"] == "restate_permission_definition":
            row = next(p for p in data["permissions"] if p["permission_code"] == op["permission_code"])
            if row["description"] != op["old"]:
                raise ValueError("Definition precondition differs.")
            row["description"] = op["new"]
    for key in before.keys() - {"permissions", "default_bindings"}:
        if data[key] != before[key]:
            raise ValueError(f"Unexpected change: {key}")
    data.update(VERSIONS)
    data["revision"] = {"base_manifest_version": "catalogue-v2.2", "base_effective_digest": BASE_DIGEST,
                        "addendum": deepcopy(delta["addendum"]), "operations": deepcopy(delta["operations"]),
                        "independent_review": "OPEN", "database_provisioning": "NOT_AUTHORIZED",
                        "previous_revision": deepcopy(before["revision"])}
    codes = [p["permission_code"] for p in data["permissions"]]
    bindings = [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]
    if len(codes) != 98 or len(set(codes)) != 98 or len(bindings) != 109 or len(set(bindings)) != 109:
        raise ValueError("Candidate counts or uniqueness differ.")
    if any(r == "Admin" and c.startswith("access_control.") for r, c in bindings):
        raise ValueError("School Admin governance expansion is prohibited.")
    if [(r, c) for r, c in bindings if r == "Technical Super Admin"] != [
        (b["role_name"], b["permission_code"]) for b in before["default_bindings"]
        if b["role_name"] == "Technical Super Admin"]:
        raise ValueError("Technical Super Admin defaults must be unchanged.")
    return data


if __name__ == "__main__":
    data = validate_candidate()
    print(json.dumps({"status": "PROPOSED_NOT_ACTIVE", "independent_review": "OPEN",
                      "base_digest": BASE_DIGEST, "permissions": len(data["permissions"]),
                      "default_bindings": len(data["default_bindings"]),
                      "candidate_sha256": sha256((HERE / "v2_3_delta.json").read_bytes()).hexdigest()}, indent=2))
