"""Permission Catalogue v2.3 overlay validation (WF-11.01 Academic Settings), standard library only.

INSTALLED ONLY by the reviewed v2.3 runtime patch, after independent approval of v2.1, v2.2 and then
v2.3. Chain: the unchanged validation_v2_2.validate_catalogue() runs first and must produce the reviewed
v2.2 digest. The reviewed v2.3 delta and addendum (review_only/academic_settings_v2_3) must match their
pinned SHA-256 bytes. The strictly enumerated operations are applied in memory with exact preconditions,
and every governance guarantee is re-checked on the result. No Django setup, ORM or database.

INDEPENDENT_APPROVAL stays None until a separately authorized change records the independent reviewer's
completed sign-off for exactly these pins. Until then require_independent_approval() refuses, so the
v2.3 provisioning command writes nothing. Validation alone confers no authority.
"""

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from . import validation_v2 as v2
from . import validation_v2_1 as v21
from . import validation_v2_2 as v22

ROOT = v2.ROOT
DELTA = "review_only/academic_settings_v2_3/v2_3_delta.json"
ADDENDUM = "review_only/academic_settings_v2_3/ADDENDUM_PROPOSED.md"
# Reviewed pins (code constants; never read from the files they protect).
DELTA_SHA256 = "4aef40877a90c7e9b6ec8b2560402be0acf3435ff524881260100ecf98204640"
ADDENDUM_SHA256 = "e9c3d4f094a465cf946c7ab89167b84a367a9d122957c71a7f130914a315e552"
BASE_MANIFEST_VERSION = "catalogue-v2.2"
BASE_EFFECTIVE_DIGEST = "192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d"
BASE_ADDENDUM_SHA256 = "4285837e51f5331bb54fab50246c25d4efb0bbd65905a567368ba7e6681f8fdd"
DELTA_SCHEMA = "catalogue-delta-v2.3"
RESULT_VERSIONS = {"schema_version": "static-catalogue-v2.3", "manifest_version": "catalogue-v2.3",
                   "source_revision": "v2.3-candidate-1"}
TECHNICAL = "Technical Super Admin"
OPERATION_FIELDS = {
    "move_default_binding": {"op", "permission_code", "from_role", "to_role"},
    "add_permission": {"op", "permission"},
    "add_default_binding": {"op", "role_name", "permission_code"},
    "restate_permission_definition": {"op", "permission_code", "old", "new"},
}
EXPECTED_TOTALS = {"permissions": 98, "default_bindings": 109}
GOVERNANCE_SERVICES = frozenset({"accounts", "access_control"})
# The independent sign-off record: None until it genuinely exists (never pre-filled or fabricated).
# When set by a separately authorized change: {"delta_sha256": DELTA_SHA256, "addendum_sha256":
# ADDENDUM_SHA256, "sign_off": "docs/security/<completed sign-off record>.md"}.
INDEPENDENT_APPROVAL = None
SIGN_OFF_ROOT = ROOT
SIGN_OFF_DIRECTORY = "docs/security/"
SIGN_OFF_DECISIONS = ("v2.1 decision: APPROVED", "v2.2 decision: APPROVED", "v2.3 decision: APPROVED")


class CatalogueV23ValidationError(ValueError):
    """No data is substituted or repaired after a validation failure."""


def _require(condition, message):
    if not condition:
        raise CatalogueV23ValidationError(message)


def _read(relative):
    try:
        return (ROOT / relative).read_bytes()
    except OSError as exc:
        raise CatalogueV23ValidationError("A pinned v2.3 file is unavailable.") from exc


def _apply(before, operations):
    data = deepcopy(before)
    permission_fields = set(data["permissions"][0])
    roles = {role["role_name"] for role in data["roles"]}
    services = {service["service_code"] for service in data["services"]}
    scopes = {p["scope"] for p in data["permissions"]}
    _require(type(operations) is list and operations, "v2.3 operations are malformed.")
    for op in operations:
        _require(type(op) is dict and op.get("op") in OPERATION_FIELDS and set(op) == OPERATION_FIELDS[op["op"]],
                 "Unknown or malformed v2.3 operation.")
        _require(all(type(value) is str for key, value in op.items() if key != "permission"), "Operation fields must be strings.")
        bindings = data["default_bindings"]
        codes = {p["permission_code"] for p in data["permissions"]}
        if op["op"] == "move_default_binding":
            old = {"role_name": op["from_role"], "permission_code": op["permission_code"]}
            new = {"role_name": op["to_role"], "permission_code": op["permission_code"]}
            _require(bindings.count(old) == 1 and new not in bindings and op["to_role"] in roles, "Binding move precondition differs.")
            bindings[bindings.index(old)] = new
        elif op["op"] == "add_permission":
            permission = op["permission"]
            _require(type(permission) is dict and set(permission) == permission_fields
                     and all(type(value) is str for value in permission.values()), "Added definition is malformed.")
            _require(permission["permission_code"] not in codes and permission["service_code"] in services
                     and permission["permission_code"].startswith(permission["service_code"] + ".")
                     and permission["readiness"] == "P" and permission["origin"] == "ADD" and permission["scope"] in scopes
                     and permission["grant_protection"] == ("GOV" if permission["service_code"] in GOVERNANCE_SERVICES else "ORD")
                     and 0 < len(permission["description"]) <= 255, "Added definition violates the catalogue rules.")
            data["permissions"].append(deepcopy(permission))
        elif op["op"] == "add_default_binding":
            binding = {"role_name": op["role_name"], "permission_code": op["permission_code"]}
            _require(op["role_name"] in roles and op["permission_code"] in codes and binding not in bindings,
                     "Added binding precondition differs.")
            bindings.append(binding)
        else:
            rows = [p for p in data["permissions"] if p["permission_code"] == op["permission_code"]]
            _require(len(rows) == 1 and rows[0]["description"] == op["old"] and 0 < len(op["new"]) <= 255
                     and op["new"] != op["old"], "Definition restatement precondition differs.")
            rows[0]["description"] = op["new"]
    return data


def _check_guarantees(before, data):
    codes = [p["permission_code"] for p in data["permissions"]]
    pairs = [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]
    old_pairs = [(b["role_name"], b["permission_code"]) for b in before["default_bindings"]]
    _require(len(codes) == len(set(codes)) == EXPECTED_TOTALS["permissions"]
             and len(pairs) == len(set(pairs)) == EXPECTED_TOTALS["default_bindings"], "v2.3 counts or uniqueness differ.")
    for key in before.keys() - {"permissions", "default_bindings"}:
        _require(data[key] == before[key], f"Unexpected v2.3 change: {key}")
    _require(not any(role == "Admin" and code.startswith("access_control.") for role, code in pairs),
             "School Admin governance expansion is prohibited.")
    for prefix_role in (TECHNICAL, "SSG Advisor"):
        _require([p for p in pairs if p[0] == prefix_role] == [p for p in old_pairs if p[0] == prefix_role],
                 "Technical Super Admin and SSG Advisor defaults must be unchanged.")
    _require([p for p in pairs if p[1].startswith(("accounts.", "access_control."))]
             == [p for p in old_pairs if p[1].startswith(("accounts.", "access_control."))], "Governance namespace defaults changed.")
    _require(not any(code.startswith("access_control.delegate.") for _, code in pairs), "Delegation authority cannot have defaults.")
    blocked = {b["permission_code"] for b in data["blocked_permissions"]}
    _require(not blocked & (set(codes) - {p["permission_code"] for p in before["permissions"]}), "A new code is blocked.")
    return Counter(role for role, _ in pairs)


@dataclass(frozen=True)
class ValidatedCatalogueV23:
    data: MappingProxyType
    counts: MappingProxyType
    base_digest: str
    digest: str


def validate_catalogue(*, delta_bytes=None, addendum_bytes=None):
    """Validate the unchanged v2.2 chain and the exact pinned v2.3 delta; return the effective v2.3."""
    try:
        base_result = v22.validate_catalogue()
    except v22.CatalogueV22ValidationError as exc:
        raise CatalogueV23ValidationError("The base v2.2 catalogue does not validate.") from exc
    _require(v22.ADDENDUM_SHA256 == BASE_ADDENDUM_SHA256 and base_result.digest == BASE_EFFECTIVE_DIGEST,
             "The v2.2 base differs from the reviewed base.")
    addendum = _read(ADDENDUM) if addendum_bytes is None else addendum_bytes
    _require(sha256(addendum).hexdigest() == ADDENDUM_SHA256, "Pinned v2.3 addendum digest mismatch; revision review required.")
    raw = _read(DELTA) if delta_bytes is None else delta_bytes
    _require(sha256(raw).hexdigest() == DELTA_SHA256, "Pinned v2.3 delta digest mismatch; revision review required.")
    try:
        delta = v2._json(raw)
    except v2.CatalogueV2ValidationError as exc:
        raise CatalogueV23ValidationError("Invalid v2.3 delta JSON.") from exc
    _require(type(delta) is dict and set(delta) == {"schema_version", "base", "addendum", "result", "operations",
                                                     "independent_review"}, "v2.3 delta: invalid structure.")
    _require(delta["schema_version"] == DELTA_SCHEMA and delta["result"] == RESULT_VERSIONS
             and delta["base"] == {"manifest_version": BASE_MANIFEST_VERSION, "effective_digest": BASE_EFFECTIVE_DIGEST,
                                   "addendum_sha256": BASE_ADDENDUM_SHA256}
             and delta["addendum"] == {"path": ADDENDUM, "sha256": ADDENDUM_SHA256}, "v2.3 delta envelope differs.")
    before = v22._thaw(base_result.data)
    data = _apply(before, delta["operations"])
    counts = _check_guarantees(before, data)
    data.update(RESULT_VERSIONS)
    data["revision"] = {"base_manifest_version": BASE_MANIFEST_VERSION, "base_effective_digest": BASE_EFFECTIVE_DIGEST,
                        "addendum": deepcopy(delta["addendum"]), "operations": deepcopy(delta["operations"]),
                        "previous_revision": deepcopy(before["revision"])}
    return ValidatedCatalogueV23(v2._freeze(data), MappingProxyType(dict(counts)), base_result.digest,
                                 v21.effective_digest(data))


def require_independent_approval():
    """Refuse unless the completed independent sign-off (v2.1, v2.2, then v2.3) is recorded for these pins."""
    record = INDEPENDENT_APPROVAL
    _require(type(record) is dict and set(record) == {"delta_sha256", "addendum_sha256", "sign_off"},
             "Catalogue v2.3 independent approval has not been recorded.")
    _require(record["delta_sha256"] == DELTA_SHA256 and record["addendum_sha256"] == ADDENDUM_SHA256,
             "The recorded approval does not cover the pinned v2.3 bytes.")
    path = record["sign_off"]
    _require(type(path) is str and path.startswith(SIGN_OFF_DIRECTORY) and path.endswith(".md")
             and ".." not in path and "\\" not in path, "The sign-off record path is invalid.")
    try:
        text = (SIGN_OFF_ROOT / path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CatalogueV23ValidationError("The sign-off record is unavailable.") from exc
    lines = {line.strip() for line in text.splitlines()}
    _require(DELTA_SHA256 in text and ADDENDUM_SHA256 in text and all(d in lines for d in SIGN_OFF_DECISIONS),
             "The sign-off record does not approve v2.1, v2.2 and v2.3 for these pins.")
    return record
