"""Source-pinned v2 planning validation using only the standard library.

No Django setup, ORM, database, mutation, activation or runtime authorization API.
The accepted baseline authorizes static representation only.
"""

import ast
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from types import MappingProxyType
import unicodedata

ROOT = Path(__file__).resolve().parents[4]
MANIFEST_PATH = Path(__file__).with_name("v2_0.json")
MANIFEST_VERSION = "catalogue-v2.0"
SCHEMA_VERSION = "static-catalogue-v2.0"
SOURCE = "docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md"
SOURCE_SHA256 = "56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78"
PINS = {
    "proposal": (SOURCE, SOURCE_SHA256),
    "c1_manifest": (
        "backend/apps/access_control/catalogue/c1_v1.json",
        "86d72d82295cb358244145c6d24ebe8ba948f5211de298ebf897b5d3d83ed447",
    ),
    "c1_source": (
        "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md",
        "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e",
    ),
    "srs": (
        "docs/SRS/CTU-G_Workspace_SRS_v1.md",
        "af4ead4f88bdb0877ab6c3b8965bec5caf0f058d74ab0d878ec690379210346f",
    ),
    "ar2": (
        "docs/architecture/AR-2-revised-administrator-access-control.md",
        "b36c0dac6d18badc435cce242725d2d6424db9d7e12d6d4943f20c7eaaf8ce36",
    ),
    "ar3a": (
        "docs/architecture/AR-3A-administrator-architecture-finalization.md",
        "464c0fec172ef5ba887dbc22ec5b09c3396ca1be53087d999bbf763966edded1",
    ),
}
ROLE_KEYS = dict(S="Student", I="Instructor", T="Treasurer", A="Admin", G="Technical Super Admin", V="SSG Advisor")
CORE_FIELDS = ("service_code", "permission_code", "permission_name", "module_name", "action_name", "description", "readiness")
SERVICE_CODE = re.compile(r"[a-z][a-z0-9_]*\Z", re.ASCII)
PERMISSION_CODE = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+\Z", re.ASCII)
RETIRED_CODE = "access_control.role_assignments.manage"
DELEGATE_SERVICES = ("academic", "finance", "clearance", "group_rating", "announcements", "notifications", "reports")
ADVISOR_CODES = (
    "finance.monitoring.overview.read", "reports.monitoring.financial.read",
    "finance.monitoring.transactions.read",
)
CORE_GOVERNANCE_CODES = (
    "access_control.catalogue.read", "access_control.role_permissions.manage",
    "access_control.account_permissions.manage", "access_control.effective_permissions.inspect",
    "access_control.audit.read", "access_control.admin_assignments.manage",
)


class CatalogueV2ValidationError(ValueError):
    """No data is substituted or repaired after a validation failure."""


def _require(condition, message):
    if not condition:
        raise CatalogueV2ValidationError(message)


def _object(value, fields, label):
    _require(type(value) is dict and set(value) == set(fields), f"{label}: invalid structure or unexpected fields.")


def _text(value, limit, label):
    _require(type(value) is str and 0 < len(value) <= limit and value == value.strip()
             and not any(ord(c) < 32 or ord(c) == 127 for c in value), f"{label}: invalid text/field length.")


def _unique(values, label):
    def normalized(value):
        return "".join(c for c in unicodedata.normalize("NFKD", value).casefold() if not unicodedata.combining(c)).rstrip()
    _require(len(values) == len(set(values)), f"{label}: duplicate identifier.")
    _require(len(values) == len({normalized(v) for v in values}), f"{label}: equivalent identifier.")


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key.")
        result[key] = value
    return result


def _invalid_constant(value):
    raise CatalogueV2ValidationError("Non-finite JSON constants are forbidden.")


def _json(value):
    try:
        return json.loads(value, object_pairs_hook=_pairs_no_duplicates, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, CatalogueV2ValidationError):
            raise
        raise CatalogueV2ValidationError("Invalid JSON document.") from exc


def read_manifest():
    try:
        return _json(MANIFEST_PATH.read_bytes())
    except OSError as exc:
        raise CatalogueV2ValidationError("Versioned v2 manifest is unavailable.") from exc


def _read_provenance():
    documents = {}
    for name, (relative, expected_hash) in PINS.items():
        try:
            content = (ROOT / relative).read_bytes()
        except OSError as exc:
            raise CatalogueV2ValidationError(f"Pinned {name} is unavailable.") from exc
        _require(sha256(content).hexdigest() == expected_hash, f"Pinned {name} digest mismatch; revision review required.")
        try:
            documents[name] = content.decode("utf-8")
        except UnicodeError as exc:
            raise CatalogueV2ValidationError(f"Pinned {name} is not UTF-8.") from exc
    return documents


def _rows(document, start, end):
    lines = document.splitlines()
    try:
        first = next(i for i, line in enumerate(lines) if line.startswith(start))
        last = next(i for i in range(first + 1, len(lines)) if lines[i].startswith(end))
    except StopIteration as exc:
        raise CatalogueV2ValidationError("Pinned proposal section is missing.") from exc
    return [[c.strip() for c in line.split("|")[1:-1]]
            for line in lines[first + 1:last] if line.startswith("| ")]


def _default_roles(cell):
    return [] if cell == "-" else [ROLE_KEYS[key] for key in cell.split(",")]


def _planning_contracts():
    return {
        "normal_admin": {"required_roles": ["Admin"], "effective_permission_required": True,
                         "object_authorization_required": True, "global_default_management": False},
        "application_super_admin": {
            "required_roles": ["Admin", "Technical Super Admin"],
            "required_effective_permissions": list(CORE_GOVERNANCE_CODES),
            "role_membership_sufficient": False, "direct_grants_replace_roles": False,
            "approved_active_account_required": True, "usable_approved_governance_workflow_required": True,
            "per_service_delegation_required": True, "object_authorization_required": True,
            "framework_privilege_implied": False, "policy_status": "BLOCKED_PENDING_GOVERNANCE_DECISIONS",
        },
        "ssg_advisor": {
            "required_roles": ["Instructor", "SSG Advisor"],
            "required_effective_permissions": list(ADVISOR_CODES),
            "role_membership_sufficient": False, "grants_alone_confer_eligibility": False,
            "approved_active_account_required": True, "valid_appointment_and_period_required": True,
            "read_only_projection_required": True, "other_role_writes_suppressed": False,
            "treasurer_coappointment": "BLOCKED_PENDING_REVIEWED_CONFLICT_EXCEPTION",
            "policy_status": "BLOCKED_PENDING_APPOINTMENT_AND_PRIVACY_DECISIONS",
        },
        "required_multi_role_combinations": [
            ["Student", "Treasurer"], ["Instructor", "Admin"],
            ["Instructor", "SSG Advisor"], ["Instructor", "Admin", "Technical Super Admin"],
        ],
        "authorization": {
            "explicit_deny_precedence": True, "requested_roles_are_authority": False,
            "role_names_are_bypass": False, "django_superuser_is_application_bypass": False,
            "object_ownership_checks_required": True, "financial_self_interest_checks_required": True,
            "direct_grants_are_account_wide": True, "dependent_grant_revocation_review_required": True,
            "self_and_assigned_role_ordinary_mutations_allowed": False,
            "effective_last_operator_protection_required": True,
            "runtime_enforcement_implemented_by_manifest": False,
        },
    }


def _expected_manifest(documents):
    """Derive the accepted static data in memory. Never generates/writes files."""
    document = documents["proposal"]
    baseline = _json(documents["c1_manifest"])
    by_code = {p["permission_code"]: p for p in baseline["permissions"]}
    inventory = [r for r in _rows(document, "### 2.2", "### 2.3") if len(r) == 7 and r[1] in by_code]
    revisions = {r[0]: r for r in _rows(document, "### 2.3", "### 2.4") if len(r) == 3 and r[0] in by_code}
    additions = [r for r in _rows(document, "### 2.4", "## 3.") if len(r) == 9 and PERMISSION_CODE.fullmatch(r[1])]
    role_rows = [r for r in _rows(document, "### 3.1", "### 3.2") if len(r) == 5 and r[0] in ROLE_KEYS]
    _require((len(inventory), len(revisions), len(additions), len(role_rows)) == (82, 2, 14, 6), "Incomplete pinned proposal tables.")
    permissions, bindings, tombstones = [], [], []
    delta = {"retained_codes": [], "revisions": [], "added_codes": [], "retired_codes": []}
    for row in inventory:
        service, code, disposition, readiness, defaults, protection, scope = row
        old = by_code[code]
        if disposition == "RETIRE":
            tombstones.append({
                "permission_code": code, "service_code": service, "lifecycle": "RETIRED_FOR_V2_SELECTION",
                "original_definition": old,
                "replacement_codes": ["access_control.role_assignments.ordinary.manage",
                                      "access_control.admin_assignments.manage", "access_control.governance_assignments.manage"],
                "default_roles": [], "existing_record_policy": "preserve_and_report",
                "automatic_grant_remapping": False, "execution_allowed": False,
            })
            delta["retired_codes"].append(code)
            continue
        entry = {field: old[field] for field in CORE_FIELDS}
        if disposition == "REVISE":
            revision = revisions[code]
            changes = {}
            for field, replacement in zip(("permission_name", "description"), revision[1:], strict=True):
                changes[field] = {"old": old[field], "new": replacement}
                entry[field] = replacement
            delta["revisions"].append({"permission_code": code, "changes": changes})
        else:
            _require(disposition == "KEEP", "Unknown pinned disposition.")
            delta["retained_codes"].append(code)
        entry.update(origin=disposition, scope=scope, grant_protection=protection)
        permissions.append(entry)
        bindings.extend({"role_name": role, "permission_code": code} for role in _default_roles(defaults))
    for row in additions:
        service, code, name, module, action, description, defaults, readiness, scope = row
        permissions.append(dict(service_code=service, permission_code=code, permission_name=name,
                                module_name=module, action_name=action, description=description,
                                readiness=readiness, origin="ADD", scope=scope,
                                grant_protection="GOV" if service in {"accounts", "access_control"} else "ORD"))
        bindings.extend({"role_name": role, "permission_code": code} for role in _default_roles(defaults))
        delta["added_codes"].append(code)
    role_map = {r[1]: r for r in role_rows}
    roles = [dict(role) for role in baseline["roles"]]
    roles.append(dict(role_name="SSG Advisor", description=role_map["SSG Advisor"][2], provisioning="proposed_optional"))
    scopes = [dict(scope_id=r[0], description=r[1]) for r in _rows(document, "### 4.3", "## 5.")
              if len(r) == 2 and re.fullmatch(r"[A-Z][A-Z_]*", r[0])]
    blockers = [dict(id=r[0].split(" ", 1)[0], status="OPEN", decision=r[1], references=r[2])
                for r in _rows(document, "### 7.2", "## 8.") if len(r) == 3 and r[0].startswith("V2-")]
    unsupported = [dict(configuration=r[0], current_result=r[1], proposed_treatment=r[2], status="BLOCKED")
                   for r in _rows(document, "## 6.", "## 7.") if len(r) == 3 and r[0] not in {"Configuration/use case", "---"}]
    blocked = [dict(permission_code=r[0], status="BLOCKED", required_decisions=r[3])
               for r in _rows(document, "### 7.1", "### 7.2") if len(r) == 4 and r[1] == "B"]
    return {
        "schema_version": SCHEMA_VERSION, "manifest_version": MANIFEST_VERSION,
        "source_revision": "v2.0-review-1", "planning_only": True,
        "acceptance_scope": "owner-accepted static planning baseline only; no live grant or security-policy approval",
        "provenance": {key: dict(path=relative, sha256=digest) for key, (relative, digest) in PINS.items()},
        "services": baseline["services"], "roles": roles, "role_keys": ROLE_KEYS,
        "role_eligibility": [dict(role_name=r[1], requirement=r[4]) for r in role_rows],
        "permissions": permissions, "default_bindings": bindings,
        "historical_retirements": tombstones, "delta": delta, "scope_definitions": scopes,
        "composition": _planning_contracts(),
        "delegation": {
            "status": "OFF", "enabled_scopes": [], "wildcards_allowed": False,
            "legacy_cartesian_widening_allowed": False, "ordinary_reserved_target_mutations_allowed": False,
            "service_authority_codes": [f"access_control.delegate.{s}" for s in DELEGATE_SERVICES],
            "unsupported_configurations": unsupported,
        },
        "policy_blockers": blockers, "blocked_permissions": blocked,
        "operational_gates": {key: "BLOCKED" for key in (
            "initialization", "grants", "service_activation", "live_mutations", "administrator_provisioning",
            "first_operator_attribution", "independent_review_evidence", "effective_last_operator",
            "object_authorization", "session_revocation", "authentication_events", "django_superuser_changes",
        )},
    }


def _field_limits():
    """Read declared model limits with AST, without importing Django/models."""
    try:
        module = ast.parse((ROOT / "backend/apps/access_control/models.py").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise CatalogueV2ValidationError("Model field-limit prerequisite is unavailable.") from exc
    limits = {}
    required = {"Role": {"role_name", "description"},
                "Service": {"service_code", "service_name", "description"},
                "Permission": set(CORE_FIELDS) - {"service_code", "readiness"}}
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name in required:
            fields = {}
            for statement in node.body:
                if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name) and isinstance(statement.value, ast.Call)):
                    name = statement.targets[0].id
                    if name in required[node.name]:
                        for keyword in statement.value.keywords:
                            if keyword.arg == "max_length" and isinstance(keyword.value, ast.Constant):
                                fields[name] = keyword.value.value
            _require(set(fields) == required[node.name] and all(type(n) is int and n > 0 for n in fields.values()),
                     "Model field limits cannot be determined statically.")
            limits[node.name] = fields
    _require(set(limits) == set(required), "Required model definitions are missing.")
    return limits


def _strict_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(_strict_equal(actual[k], value) for k, value in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(_strict_equal(a, b) for a, b in zip(actual, expected, strict=True))
    return actual == expected


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ValidatedCatalogueV2:
    data: MappingProxyType
    counts: MappingProxyType


def validate_manifest(manifest=None):
    data = read_manifest() if manifest is None else manifest
    expected = _expected_manifest(_read_provenance())
    _object(data, expected, "Manifest")
    _require(data["schema_version"] == SCHEMA_VERSION and data["manifest_version"] == MANIFEST_VERSION
             and data["source_revision"] == "v2.0-review-1", "Immutable v2 version identifiers differ.")
    _require(data["planning_only"] is True, "Only static planning is authorized.")
    _require(_strict_equal(data["provenance"], expected["provenance"]), "Pinned provenance differs.")
    limits = _field_limits()
    for group, model in (("services", "Service"), ("roles", "Role")):
        _require(type(data[group]) is list, f"{group}: list required.")
        for row in data[group]:
            _require(type(row) is dict and set(limits[model]) <= row.keys(), f"{group}: fields missing.")
            for field, limit in limits[model].items():
                _text(row[field], limit, f"{model}.{field}")
    _unique([s["service_code"] for s in data["services"]], "Service codes")
    _unique([s["service_name"] for s in data["services"]], "Service names")
    _unique([r["role_name"] for r in data["roles"]], "Roles")
    services = {s["service_code"] for s in data["services"]}
    roles = {r["role_name"] for r in data["roles"]}
    _require(all(SERVICE_CODE.fullmatch(code) for code in services), "Noncanonical service code.")
    _require(type(data["permissions"]) is list, "Permissions must be a list.")
    for permission in data["permissions"]:
        _object(permission, (*CORE_FIELDS, "origin", "scope", "grant_protection"), "Permission")
        for field, limit in limits["Permission"].items():
            _text(permission[field], limit, f"Permission.{field}")
        code = permission["permission_code"]
        _require(PERMISSION_CODE.fullmatch(code), "Noncanonical/wildcard permission code.")
        _require(type(permission["service_code"]) is str and permission["service_code"] in services
                 and code.split(".")[0] == permission["service_code"], "Invalid permission service relationship.")
        _require(type(permission["readiness"]) is str and permission["readiness"] in {"F", "P", "B"}, "Invalid readiness state.")
    _unique([p["permission_code"] for p in data["permissions"]], "Permissions")
    permissions = {p["permission_code"]: p for p in data["permissions"]}
    _require(RETIRED_CODE not in permissions, "Retired code cannot be selectable.")
    _require(type(data["default_bindings"]) is list, "Default bindings must be a list.")
    pairs = []
    for binding in data["default_bindings"]:
        _object(binding, ("role_name", "permission_code"), "Binding")
        role, code = binding["role_name"], binding["permission_code"]
        _require(type(role) is str and role in roles and type(code) is str and code in permissions,
                 "Binding has invalid role/permission reference.")
        permission = permissions[code]
        _require(permission["readiness"] != "B", "Blocked permissions cannot have defaults.")
        _require(not code.startswith("access_control.delegate."), "Delegation authority cannot have defaults.")
        _require(role != "Technical Super Admin" or permission["service_code"] in {"accounts", "access_control"},
                 "Governance role cannot have business defaults.")
        pairs.append((role, code))
    _require(len(pairs) == len(set(pairs)), "Duplicate proposed binding.")
    _require({code for role, code in pairs if role == "SSG Advisor"} == set(ADVISOR_CODES),
             "Advisor must have exactly three scoped read-only defaults.")
    _require(_strict_equal(data["composition"], expected["composition"]),
             "Role composition/eligibility/Deny/framework contract differs; grants or role membership are not sufficient.")
    _require(_strict_equal(data["delegation"], expected["delegation"]), "Delegation must remain OFF with unsupported configurations blocked.")
    _require(_strict_equal(data["policy_blockers"], expected["policy_blockers"])
             and _strict_equal(data["operational_gates"], expected["operational_gates"]),
             "Unresolved governance/bootstrap/operational blockers must remain explicit.")
    _require(_strict_equal(data, expected), "Manifest differs from the exact pinned v2 planning baseline.")
    _require((len(services), len(permissions), len(roles), len(pairs)) == (10, 95, 6, 106), "Incomplete v2 baseline.")
    _require(Counter(p["origin"] for p in data["permissions"]) == Counter(KEEP=79, REVISE=2, ADD=14), "Invalid change counts.")
    _require(Counter(p["readiness"] for p in data["permissions"]) == Counter(F=9, P=72, B=14), "Invalid readiness counts.")
    counts = dict(services=10, permissions=95, roles=6, default_bindings=106, retained=79,
                  revised=2, added=14, retired=1, blocked=14, internal_contracts=9, planned=72)
    return ValidatedCatalogueV2(_freeze(data), MappingProxyType(counts))
