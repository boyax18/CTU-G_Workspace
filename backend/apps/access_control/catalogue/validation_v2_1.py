"""Permission Catalogue v2.1 overlay validation (WF-03.01 D-89), standard library only.

The accepted v2.0 catalogue stays authoritative and byte-identical: this module first runs the
unchanged validation_v2.validate_manifest() on the pinned v2_0.json bytes, then verifies the
pinned AR-3B2A v2.1 addendum, requires v2_1_delta.json to be exactly the delta stated by that
addendum AND exactly the owner-authorized change, applies it in memory and re-checks every v2
security guarantee on the result. No Django setup, ORM, database, mutation, activation or
runtime authorization API. The result is a static planning specification, not provisioning.
"""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from . import validation_v2 as v2

ROOT = v2.ROOT
DELTA_PATH = Path(__file__).with_name("v2_1_delta.json")
BASE_MANIFEST = "backend/apps/access_control/catalogue/v2_0.json"
# Independently maintained pins (reviewed code constants; never read from the files they protect).
# v2_0.json is not -text in .gitattributes, so its checkout may use CRLF: the pin covers the
# LF-normalized content (equal to the committed Git blob). The addendum is -text and pinned as raw bytes.
BASE_MANIFEST_SHA256 = "a7e2705236a37522b77468fd4154113d19e7e64bc479cfa420c41d7744a2548b"
ADDENDUM = "docs/architecture/AR-3B2A-ADDENDUM-v2.1.md"
ADDENDUM_SHA256 = "78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7"
DELTA_SCHEMA = "catalogue-delta-v2.1"
RESULT_VERSIONS = {"schema_version": "static-catalogue-v2.1", "manifest_version": "catalogue-v2.1",
                   "source_revision": "v2.1-review-1"}
# The exact owner-authorized change (D-89, 18 Nov 2026). Anything else is refused.
ORDINARY_CODE = "access_control.role_assignments.ordinary.manage"
AUTHORIZED_MOVES = ((ORDINARY_CODE, "Admin", "Technical Super Admin"),)
AUTHORIZED_ELIGIBILITY_ROLES = ("Admin", "Technical Super Admin")
TECHNICAL = "Technical Super Admin"
UNCHANGED_KEYS = ("planning_only", "acceptance_scope", "provenance", "services", "roles", "role_keys", "permissions",
                  "historical_retirements", "delta", "scope_definitions", "composition", "delegation",
                  "policy_blockers", "blocked_permissions", "operational_gates")


class CatalogueV21ValidationError(ValueError):
    """No data is substituted or repaired after a validation failure."""


def _require(condition, message):
    if not condition:
        raise CatalogueV21ValidationError(message)


def _read(relative, label):
    try:
        return (ROOT / relative).read_bytes()
    except OSError as exc:
        raise CatalogueV21ValidationError(f"{label} is unavailable.") from exc


def normalized_lf(raw):
    return raw.replace(b"\r\n", b"\n")


def read_delta():
    try:
        raw = DELTA_PATH.read_bytes()
    except OSError as exc:
        raise CatalogueV21ValidationError("Versioned v2.1 delta is unavailable.") from exc
    try:
        return v2._json(raw)
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV21ValidationError("Invalid v2.1 delta JSON.") from exc


def _table(document, start, end, header):
    try:
        rows = v2._rows(document, start, end)
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV21ValidationError("Pinned addendum section is missing.") from exc
    _require(len(rows) >= 2 and rows[0] == header and set(rows[1]) == {"---"}, "Pinned addendum table is malformed.")
    body = rows[2:]
    _require(body and all(len(r) == len(header) and all(r) for r in body), "Pinned addendum table is malformed.")
    return body


def _expected_delta(addendum, base):
    """Derive the delta in memory from the pinned addendum's tables; never generates files."""
    base_rows = dict(_table(addendum, "## 1.", "## 2.", ["Field", "Value"]))
    _require(set(base_rows) == {"base_manifest_version", "base_manifest_path", "base_manifest_sha256",
                                "base_manifest_digest_rule", "base_validator"}, "Addendum base table differs.")
    _require(base_rows.get("base_manifest_version") == base["manifest_version"]
             and base_rows.get("base_manifest_path") == BASE_MANIFEST
             and base_rows.get("base_manifest_sha256") == BASE_MANIFEST_SHA256, "Addendum base catalogue differs.")
    moves = _table(addendum, "### 3.1", "### 3.2", ["Permission code", "From role", "To role"])
    eligibility = _table(addendum, "### 3.2", "### 3.3", ["Role name", "Requirement"])
    versions = dict(_table(addendum, "### 3.3", "## 4.", ["Field", "Value"]))
    _require(tuple(tuple(r) for r in moves) == AUTHORIZED_MOVES, "Addendum binding moves differ from the authorized change.")
    _require(tuple(r[0] for r in eligibility) == AUTHORIZED_ELIGIBILITY_ROLES, "Addendum eligibility scope differs.")
    _require(versions == RESULT_VERSIONS, "Addendum result versions differ.")
    old = {row["role_name"]: row["requirement"] for row in base["role_eligibility"]}
    operations = [{"op": "move_default_binding", "permission_code": code, "from_role": src, "to_role": dst}
                  for code, src, dst in moves]
    operations += [{"op": "restate_role_eligibility", "role_name": role, "old": old[role], "new": text}
                   for role, text in eligibility]
    return {
        "schema_version": DELTA_SCHEMA,
        "base": {"manifest_version": base["manifest_version"], "path": BASE_MANIFEST, "sha256": BASE_MANIFEST_SHA256},
        "addendum": {"path": ADDENDUM, "sha256": ADDENDUM_SHA256},
        "result": dict(RESULT_VERSIONS),
        "operations": operations,
        "independent_review": {"status": "OPEN", "note": "Independent approval or signing of the addendum pin not performed."},
    }


def _apply(base, delta):
    data = deepcopy(base)
    for operation in delta["operations"]:
        if operation["op"] == "move_default_binding":
            source = {"role_name": operation["from_role"], "permission_code": operation["permission_code"]}
            index = [i for i, b in enumerate(data["default_bindings"]) if b == source]
            _require(len(index) == 1, "Binding to move is missing or duplicated in v2.")
            data["default_bindings"][index[0]] = {"role_name": operation["to_role"],
                                                  "permission_code": operation["permission_code"]}
        else:
            row = [r for r in data["role_eligibility"] if r["role_name"] == operation["role_name"]]
            _require(len(row) == 1 and row[0]["requirement"] == operation["old"], "Eligibility to restate differs in v2.")
            row[0]["requirement"] = operation["new"]
    data.update(RESULT_VERSIONS)
    data["revision"] = {
        "base_manifest_version": base["manifest_version"], "base_manifest_sha256": BASE_MANIFEST_SHA256,
        "addendum": {"path": ADDENDUM, "sha256": ADDENDUM_SHA256},
        "operations": deepcopy(delta["operations"]), "independent_review": "OPEN",
        "database_provisioning": "NOT_AUTHORIZED",
    }
    return data


def _check_guarantees(base, data):
    """Every v2 security guarantee, re-checked on the effective v2.1 data."""
    for key in UNCHANGED_KEYS:
        _require(v2._strict_equal(data[key], base[key]), f"v2.1 must not change {key}.")
    _require(data["planning_only"] is True, "Only static planning is authorized.")
    permissions = {p["permission_code"]: p for p in data["permissions"]}
    roles = {r["role_name"] for r in data["roles"]}
    before = [(b["role_name"], b["permission_code"]) for b in base["default_bindings"]]
    after = [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]
    moved = {(src, code) for code, src, _ in AUTHORIZED_MOVES}
    added = {(dst, code) for code, _, dst in AUTHORIZED_MOVES}
    _require(len(after) == len(before) == 106 and len(set(after)) == len(after), "Default binding count or uniqueness differs.")
    _require(set(after) == (set(before) - moved) | added, "Default bindings differ from the authorized change.")
    _require([p for p in after if p not in added] == [p for p in before if p not in moved], "Unchanged bindings were reordered.")
    for role, code in after:
        _require(role in roles and code in permissions, "Binding has invalid role/permission reference.")
        _require(permissions[code]["readiness"] != "B", "Blocked permissions cannot have defaults.")
        _require(not code.startswith("access_control.delegate."), "Delegation authority cannot have defaults.")
        _require(role != TECHNICAL or permissions[code]["service_code"] in {"accounts", "access_control"},
                 "Governance role cannot have business defaults.")
    bound = {}
    for role, code in after:
        bound.setdefault(code, set()).add(role)
    governance = data["composition"]["application_super_admin"]["required_effective_permissions"]
    _require(all(bound.get(code) == {TECHNICAL} for code in governance), "Governance codes must stay bound only to Technical Super Admin.")
    _require("access_control.governance_assignments.manage" not in bound, "Blocked governance assignment must stay unbound.")
    _require(not any(role == "Admin" and code.startswith("access_control.") and code.endswith(".manage") for role, code in after),
             "School Admin must not hold any access-control management default.")
    _require({code for role, code in after if role == "SSG Advisor"} == set(v2.ADVISOR_CODES), "Advisor defaults differ.")
    eligibility = {r["role_name"]: r for r in data["role_eligibility"]}
    old = {r["role_name"]: r for r in base["role_eligibility"]}
    _require(list(eligibility) == list(old) and all(set(r) == {"role_name", "requirement"} for r in data["role_eligibility"]),
             "Role eligibility structure differs.")
    _require({role for role in old if eligibility[role] != old[role]} <= set(AUTHORIZED_ELIGIBILITY_ROLES),
             "Only the authorized eligibility rules may change.")
    counts = Counter(role for role, _ in after)
    _require(counts["Admin"] == 34 and counts[TECHNICAL] == 11, "Role default totals differ from the authorized change.")
    return counts


def effective_digest(data):
    """Deterministic SHA-256 of the effective catalogue (canonical JSON: sorted keys, no whitespace)."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ValidatedCatalogueV21:
    data: MappingProxyType
    counts: MappingProxyType
    base_counts: MappingProxyType
    digest: str


def validate_catalogue(delta=None, *, base_manifest_bytes=None, addendum_bytes=None):
    """Validate v2 unchanged, the pinned addendum and the exact delta; return the effective v2.1 catalogue."""
    raw = _read(BASE_MANIFEST, "Versioned v2 manifest") if base_manifest_bytes is None else base_manifest_bytes
    _require(sha256(normalized_lf(raw)).hexdigest() == BASE_MANIFEST_SHA256,
             "Pinned v2 manifest digest mismatch; revision review required.")
    try:
        validated = v2.validate_manifest(v2._json(raw))
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV21ValidationError("The base v2 catalogue does not validate.") from exc
    base = v2._json(raw)  # the exact bytes hashed and validated above; never a second read
    text = _read(ADDENDUM, "Pinned v2.1 addendum") if addendum_bytes is None else addendum_bytes
    _require(sha256(text).hexdigest() == ADDENDUM_SHA256, "Pinned v2.1 addendum digest mismatch; revision review required.")
    try:
        addendum = text.decode("utf-8")
    except UnicodeError as exc:
        raise CatalogueV21ValidationError("Pinned v2.1 addendum is not UTF-8.") from exc
    delta = read_delta() if delta is None else delta
    expected = _expected_delta(addendum, base)
    _require(type(delta) is dict and set(delta) == set(expected), "v2.1 delta: invalid structure or unexpected fields.")
    _require(type(delta["operations"]) is list and all(type(o) is dict for o in delta["operations"]),
             "v2.1 delta operations are malformed.")
    _require(v2._strict_equal(delta, expected), "v2.1 delta differs from the exact pinned, owner-authorized change.")
    data = _apply(base, delta)
    role_counts = _check_guarantees(base, data)
    counts = dict(validated.counts)
    counts.update(default_bindings=len(data["default_bindings"]), admin_defaults=role_counts["Admin"],
                  technical_super_admin_defaults=role_counts[TECHNICAL], moved_bindings=len(AUTHORIZED_MOVES),
                  restated_eligibility=len(AUTHORIZED_ELIGIBILITY_ROLES))
    return ValidatedCatalogueV21(v2._freeze(data), MappingProxyType(counts), validated.counts, effective_digest(data))
