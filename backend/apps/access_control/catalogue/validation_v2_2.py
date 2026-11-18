"""Permission Catalogue v2.2 overlay validation (WF-03.01 D-103 Option A), standard library only.

Chain: the unchanged validation_v2_1.validate_catalogue() runs first (it validates v2.0 with its
original checks, then the v2.1 overlay); its effective digest and addendum pin must equal this
module's reviewed constants. Then the pinned AR-3B2A v2.2 addendum is verified, v2_2_delta.json must
be exactly the delta stated by that addendum AND exactly the owner-authorized two binding moves, the
delta is applied in memory and every authorization and governance guarantee is re-checked on the
result. No Django setup, ORM, database, mutation, activation or runtime authorization API. The result
is a static planning specification, not provisioning; independent review of the pin is OPEN (D-101).
"""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from . import validation_v2 as v2
from . import validation_v2_1 as v21

ROOT = v2.ROOT
DELTA_PATH = Path(__file__).with_name("v2_2_delta.json")
# Independently maintained pins (reviewed code constants; never read from the files they protect).
BASE_MANIFEST_VERSION = "catalogue-v2.1"
BASE_EFFECTIVE_DIGEST = "1adb16465e9d32712f890a95ee13dd5f21f4441790715aeaf91aa10c53183362"
BASE_ADDENDUM_SHA256 = "78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7"
BASE_VALIDATOR = "backend/apps/access_control/catalogue/validation_v2_1.py"
ADDENDUM = "docs/architecture/AR-3B2A-ADDENDUM-v2.2.md"
ADDENDUM_SHA256 = "4285837e51f5331bb54fab50246c25d4efb0bbd65905a567368ba7e6681f8fdd"
DELTA_SCHEMA = "catalogue-delta-v2.2"
RESULT_VERSIONS = {"schema_version": "static-catalogue-v2.2", "manifest_version": "catalogue-v2.2",
                   "source_revision": "v2.2-review-1"}
TECHNICAL = "Technical Super Admin"
# The exact owner-authorized change (D-103 Option A, 19 Nov 2026), in default-binding index order.
AUTHORIZED_MOVES = (
    ("access_control.school_access.inspect", "Admin", TECHNICAL),
    ("access_control.audit.school.read", "Admin", TECHNICAL),
)
EXPECTED_INDICES = (97, 102)
EXPECTED_TOTALS = {"Admin": 32, TECHNICAL: 13}
UNCHANGED_KEYS = ("planning_only", "acceptance_scope", "provenance", "services", "roles", "role_keys", "role_eligibility",
                  "permissions", "historical_retirements", "delta", "scope_definitions", "composition", "delegation",
                  "policy_blockers", "blocked_permissions", "operational_gates")


class CatalogueV22ValidationError(ValueError):
    """No data is substituted or repaired after a validation failure."""


def _require(condition, message):
    if not condition:
        raise CatalogueV22ValidationError(message)


def _thaw(value):
    if isinstance(value, MappingProxyType) or type(value) is dict:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_thaw(item) for item in value]
    return value


def read_delta():
    try:
        raw = DELTA_PATH.read_bytes()
    except OSError as exc:
        raise CatalogueV22ValidationError("Versioned v2.2 delta is unavailable.") from exc
    try:
        return v2._json(raw)
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV22ValidationError("Invalid v2.2 delta JSON.") from exc


def _table(document, start, end, header):
    try:
        rows = v2._rows(document, start, end)
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV22ValidationError("Pinned addendum section is missing.") from exc
    _require(len(rows) >= 2 and rows[0] == header and set(rows[1]) == {"---"}, "Pinned addendum table is malformed.")
    body = rows[2:]
    _require(body and all(len(r) == len(header) and all(r) for r in body), "Pinned addendum table is malformed.")
    return body


def _expected_delta(addendum):
    """Derive the delta in memory from the pinned addendum's tables; never generates files."""
    base_rows = dict(_table(addendum, "## 1.", "## 2.", ["Field", "Value"]))
    _require(set(base_rows) == {"base_manifest_version", "base_effective_digest", "base_effective_digest_rule",
                                "base_addendum_sha256", "base_validator"}, "Addendum base table differs.")
    _require(base_rows["base_manifest_version"] == BASE_MANIFEST_VERSION
             and base_rows["base_effective_digest"] == BASE_EFFECTIVE_DIGEST
             and base_rows["base_addendum_sha256"] == BASE_ADDENDUM_SHA256
             and base_rows["base_validator"].startswith(BASE_VALIDATOR + " "), "Addendum base catalogue differs.")
    moves = _table(addendum, "### 3.1", "### 3.2", ["Permission code", "From role", "To role"])
    versions = dict(_table(addendum, "### 3.2", "## 4.", ["Field", "Value"]))
    _require(tuple(tuple(r) for r in moves) == AUTHORIZED_MOVES, "Addendum binding moves differ from the authorized change.")
    _require(versions == RESULT_VERSIONS, "Addendum result versions differ.")
    return {
        "schema_version": DELTA_SCHEMA,
        "base": {"manifest_version": BASE_MANIFEST_VERSION, "effective_digest": BASE_EFFECTIVE_DIGEST,
                 "addendum_sha256": BASE_ADDENDUM_SHA256},
        "addendum": {"path": ADDENDUM, "sha256": ADDENDUM_SHA256},
        "result": dict(RESULT_VERSIONS),
        "operations": [{"op": "move_default_binding", "permission_code": code, "from_role": src, "to_role": dst}
                       for code, src, dst in moves],
        "independent_review": {"status": "OPEN", "note": "Independent approval or signing of the addendum pin not performed (D-101)."},
    }


def _apply(base, delta):
    data = deepcopy(base)
    for operation in delta["operations"]:
        source = {"role_name": operation["from_role"], "permission_code": operation["permission_code"]}
        index = [i for i, b in enumerate(data["default_bindings"]) if b == source]
        _require(len(index) == 1, "Binding to move is missing or duplicated in v2.1.")
        data["default_bindings"][index[0]] = {"role_name": operation["to_role"], "permission_code": operation["permission_code"]}
    data.update(RESULT_VERSIONS)
    data["revision"] = {
        "base_manifest_version": BASE_MANIFEST_VERSION, "base_effective_digest": BASE_EFFECTIVE_DIGEST,
        "addendum": {"path": ADDENDUM, "sha256": ADDENDUM_SHA256},
        "operations": deepcopy(delta["operations"]), "independent_review": "OPEN",
        "database_provisioning": "NOT_AUTHORIZED", "previous_revision": deepcopy(base["revision"]),
    }
    return data


def _check_guarantees(base, data):
    """Every authorization and governance guarantee, re-checked independently on the effective v2.2 data."""
    for key in UNCHANGED_KEYS:
        _require(v2._strict_equal(data[key], base[key]), f"v2.2 must not change {key}.")
    _require(data["planning_only"] is True, "Only static planning is authorized.")
    permissions = {p["permission_code"]: p for p in data["permissions"]}
    roles = {r["role_name"] for r in data["roles"]}
    before = [(b["role_name"], b["permission_code"]) for b in base["default_bindings"]]
    after = [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]
    moved = [(src, code) for code, src, _ in AUTHORIZED_MOVES]
    added = [(dst, code) for code, _, dst in AUTHORIZED_MOVES]
    _require(len(after) == len(before) == 106 and len(set(after)) == len(after), "Default binding count or uniqueness differs.")
    _require(tuple(before[i] for i in EXPECTED_INDICES) == tuple(moved)
             and tuple(after[i] for i in EXPECTED_INDICES) == tuple(added), "Moved bindings are not at the expected indices.")
    _require(set(after) == (set(before) - set(moved)) | set(added), "Default bindings differ from the authorized change.")
    _require([p for i, p in enumerate(after) if i not in EXPECTED_INDICES]
             == [p for i, p in enumerate(before) if i not in EXPECTED_INDICES], "Unchanged bindings were altered or reordered.")
    bound = {}
    for role, code in after:
        _require(role in roles and code in permissions, "Binding has invalid role/permission reference.")
        _require(permissions[code]["readiness"] != "B", "Blocked permissions cannot have defaults.")
        _require(not code.startswith("access_control.delegate."), "Delegation authority cannot have defaults.")
        _require(role != TECHNICAL or permissions[code]["service_code"] in {"accounts", "access_control"},
                 "Governance role cannot have business defaults.")
        bound.setdefault(code, set()).add(role)
    governance = data["composition"]["application_super_admin"]["required_effective_permissions"]
    _require(all(bound.get(code) == {TECHNICAL} for code in governance), "Governance codes must stay bound only to Technical Super Admin.")
    _require("access_control.governance_assignments.manage" not in bound, "Blocked governance assignment must stay unbound.")
    _require(not any(role == "Admin" and code.startswith("access_control.") for role, code in after),
             "School Admin must not hold any access_control default.")
    _require([p for p in after if p[1].startswith("accounts.")] == [p for p in before if p[1].startswith("accounts.")],
             "WF-01/WF-02 accounts bindings must be unchanged.")
    _require({code for role, code in after if role == "SSG Advisor"} == set(v2.ADVISOR_CODES), "Advisor defaults differ.")
    counts = Counter(role for role, _ in after)
    _require(all(counts[role] == total for role, total in EXPECTED_TOTALS.items()),
             "Role default totals differ from the authorized change.")
    return counts


@dataclass(frozen=True)
class ValidatedCatalogueV22:
    data: MappingProxyType
    counts: MappingProxyType
    base_counts: MappingProxyType
    base_digest: str
    digest: str


def validate_catalogue(delta=None, *, addendum_bytes=None, base_manifest_bytes=None, v21_delta=None, v21_addendum_bytes=None):
    """Validate v2.0 and v2.1 unchanged, the pinned v2.2 addendum and the exact delta; return the effective v2.2."""
    try:
        base_result = v21.validate_catalogue(v21_delta, base_manifest_bytes=base_manifest_bytes,
                                             addendum_bytes=v21_addendum_bytes)
    except v21.CatalogueV21ValidationError as exc:
        raise CatalogueV22ValidationError("The base v2.1 catalogue does not validate.") from exc
    _require(v21.ADDENDUM_SHA256 == BASE_ADDENDUM_SHA256, "The v2.1 addendum pin differs from the reviewed base.")
    _require(base_result.digest == BASE_EFFECTIVE_DIGEST, "Effective v2.1 digest mismatch; revision review required.")
    base = _thaw(base_result.data)
    try:
        text = (ROOT / ADDENDUM).read_bytes() if addendum_bytes is None else addendum_bytes
    except OSError as exc:
        raise CatalogueV22ValidationError("Pinned v2.2 addendum is unavailable.") from exc
    _require(sha256(text).hexdigest() == ADDENDUM_SHA256, "Pinned v2.2 addendum digest mismatch; revision review required.")
    try:
        addendum = text.decode("utf-8")
    except UnicodeError as exc:
        raise CatalogueV22ValidationError("Pinned v2.2 addendum is not UTF-8.") from exc
    delta = read_delta() if delta is None else delta
    expected = _expected_delta(addendum)
    _require(type(delta) is dict and set(delta) == set(expected), "v2.2 delta: invalid structure or unexpected fields.")
    _require(type(delta["operations"]) is list and all(type(o) is dict for o in delta["operations"]),
             "v2.2 delta operations are malformed.")
    _require(v2._strict_equal(delta, expected), "v2.2 delta differs from the exact pinned, owner-authorized change.")
    data = _apply(base, delta)
    role_counts = _check_guarantees(base, data)
    counts = dict(base_result.counts)
    counts.update(admin_defaults=role_counts["Admin"], technical_super_admin_defaults=role_counts[TECHNICAL],
                  moved_bindings=len(AUTHORIZED_MOVES), admin_access_control_defaults=0)
    counts.pop("restated_eligibility")  # a v2.1-only operation; still reported in base_counts
    return ValidatedCatalogueV22(v2._freeze(data), MappingProxyType(counts), base_result.counts, base_result.digest,
                                 v21.effective_digest(data))
