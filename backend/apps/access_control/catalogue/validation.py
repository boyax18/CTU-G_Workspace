"""Strict, source-pinned C1 v1 validation. No database access or activation."""

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from types import MappingProxyType
import unicodedata

from ..delegation import ACCOUNT_PERMISSION_MANAGE, ROLE_PERMISSION_MANAGE, is_reserved_role
from ..management.commands.init_system_roles import SYSTEM_ROLES
from ..models import Permission, Role, Service

ROOT = Path(__file__).resolve().parents[4]
SOURCE = "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md"
SOURCE_SHA256 = "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e"
MANIFEST_PATH = Path(__file__).with_name("c1_v1.json")
ROLE_KEYS = dict(S="Student", I="Instructor", T="Treasurer", A="Admin", X="Technical Super Admin")
DELEGATED_SERVICES = frozenset(("academic", "finance", "clearance", "group_rating", "announcements", "notifications", "reports"))
SERVICE_CODE = re.compile(r"[a-z][a-z0-9_]*\Z", re.ASCII)
PERMISSION_CODE = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+\Z", re.ASCII)
DECISIONS = frozenset(f"D{number:02}" for number in range(1, 19))


class CatalogueValidationError(ValueError):
    """A baseline mismatch; never repair or substitute entries."""


def require(condition, message):
    if not condition:
        raise CatalogueValidationError(message)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected.split()), f"{label}: unexpected structure/privilege fields.")


def text(value, limit, label):
    require(type(value) is str and 0 < len(value) <= limit and value == value.strip()
            and not any(ord(char) < 32 or ord(char) == 127 for char in value), f"{label}: invalid text or field length.")


def normalized(value):
    # Static conservative collision check. The planner additionally queries actual
    # MySQL column collations; this is deliberately not a MySQL collation emulator.
    return "".join(c for c in unicodedata.normalize("NFKD", value).casefold() if not unicodedata.combining(c)).rstrip()


def unique(values, label):
    require(len(values) == len(set(values)), f"{label}: duplicate identifier.")
    require(len(values) == len({normalized(v) for v in values}), f"{label}: equivalent identifier.")


def refs(value):
    require(type(value) is list and value and all(type(v) is str and v in DECISIONS for v in value)
            and len(value) == len(set(value)), "Invalid/missing governance decision references.")


def table_rows(document, start, end):
    try:
        section = document.split(start, 1)[1].split(end, 1)[0]
    except IndexError as exc:
        raise CatalogueValidationError("Source proposal sections are missing.") from exc
    return [[cell.strip() for cell in line.split("|")[1:-1]]
            for line in section.splitlines() if line.startswith("| ")]


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Manifest contains duplicate JSON keys.")
        result[key] = value
    return result


def read_manifest():
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogueValidationError("Versioned manifest cannot be read.") from exc


def freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ValidatedCatalogue:
    data: MappingProxyType


def validate_manifest(manifest=None):
    data = read_manifest() if manifest is None else manifest
    keys(data, "manifest_version planning_only source roles services permissions default_bindings delegation_candidates decisions blocked_contracts", "Manifest")
    require(data["manifest_version"] == "c1-v1" and data["planning_only"] is True, "Only the C1 v1 planning baseline is supported.")
    keys(data["source"], "path sha256", "Source")
    require(data["source"] == {"path": SOURCE, "sha256": SOURCE_SHA256}, "Source revision is not the pinned C1 proposal.")
    try:
        source_bytes = (ROOT / SOURCE).read_bytes()
    except OSError as exc:
        raise CatalogueValidationError("Pinned source proposal is unavailable.") from exc
    require(sha256(source_bytes).hexdigest() == SOURCE_SHA256, "Source content digest mismatch; explicit revision review required.")
    document = source_bytes.decode("utf-8")
    for name in ("roles", "services", "permissions", "default_bindings", "delegation_candidates", "decisions", "blocked_contracts"):
        require(type(data[name]) is list and data[name], f"{name}: nonempty list required.")
    require(len(data["roles"]) == 5, "Exactly five proposed role definitions required.")
    expected_roles = dict(SYSTEM_ROLES)
    expected_roles["Technical Super Admin"] = "Proposed technical governance operator; no automatic academic or financial access."
    for role in data["roles"]:
        keys(role, "role_name description provisioning", "Role")
        for field in ("role_name", "description"):
            text(role[field], Role._meta.get_field(field).max_length, f"Role.{field}")
        require(role["role_name"] in expected_roles and role["description"] == expected_roles[role["role_name"]], "Role metadata differs from versioned planning definition.")
        require(role["provisioning"] == ("separate_future_provisioning" if role["role_name"] == "Technical Super Admin" else "existing"), "Role provisioning boundary changed.")
    unique([r["role_name"] for r in data["roles"]], "Roles")
    for service in data["services"]:
        keys(service, "service_code service_name description decision_refs", "Service")
        for field in ("service_code", "service_name", "description"):
            text(service[field], Service._meta.get_field(field).max_length, f"Service.{field}")
        require(SERVICE_CODE.fullmatch(service["service_code"]), "Noncanonical service code.")
        refs(service["decision_refs"])
    for field in ("service_code", "service_name"):
        unique([s[field] for s in data["services"]], field)
    services = {s["service_code"]: s for s in data["services"]}
    for permission in data["permissions"]:
        keys(permission, "service_code permission_code permission_name module_name action_name description readiness decision_refs policy_markers", "Permission")
        for field in ("permission_code", "permission_name", "module_name", "action_name", "description"):
            text(permission[field], Permission._meta.get_field(field).max_length, f"Permission.{field}")
        require(PERMISSION_CODE.fullmatch(permission["permission_code"]), "Noncanonical/wildcard permission code.")
        require(type(permission["service_code"]) is str and permission["service_code"] in services and permission["permission_code"].split(".")[0] == permission["service_code"], "Permission references invalid service/namespace.")
        require(type(permission["readiness"]) is str and permission["readiness"] in {"F", "P", "B"}, "Invalid readiness state.")
        expected_marker = {"F": "internal_contract_only", "P": "implementation_required", "B": "policy_blocked"}[permission["readiness"]]
        require(permission["policy_markers"] == [expected_marker], "Missing/invalid blocked-policy marker.")
        refs(permission["decision_refs"])
    unique([p["permission_code"] for p in data["permissions"]], "Permissions")
    permissions = {p["permission_code"]: p for p in data["permissions"]}
    binding_pairs = []
    for binding in data["default_bindings"]:
        keys(binding, "role_name permission_code", "Binding")
        require(type(binding["role_name"]) is str and binding["role_name"] in expected_roles
                and type(binding["permission_code"]) is str and binding["permission_code"] in permissions, "Binding references invalid role/permission.")
        p = permissions[binding["permission_code"]]
        require(p["readiness"] != "B", "Blocked permissions cannot have defaults.")
        require(not p["permission_code"].startswith("access_control.delegate."), "Delegation permissions cannot have defaults.")
        require(binding["role_name"] != "Technical Super Admin" or p["service_code"] in {"accounts", "access_control"}, "Technical Super Admin business default forbidden.")
        binding_pairs.append((binding["role_name"], binding["permission_code"]))
    require(len(binding_pairs) == len(set(binding_pairs)), "Duplicate role binding.")
    for code in (ROLE_PERMISSION_MANAGE, ACCOUNT_PERMISSION_MANAGE):
        require(code in permissions and permissions[code]["service_code"] == "access_control"
                and permissions[code]["readiness"] == "F", "B2 management authority contract mismatch.")
    delegate_codes = {f"access_control.delegate.{s}" for s in DELEGATED_SERVICES}
    require({c for c in permissions if c.startswith("access_control.delegate.")} == delegate_codes, "B2 delegation family contract mismatch.")
    for scope in data["delegation_candidates"]:
        keys(scope, "service_code authority_permission permission_codes role_names status decision_refs restriction", "Delegation")
        require(type(scope["service_code"]) is str and scope["service_code"] in services, "Invalid delegation service.")
        require(scope["status"] == "OFF", "Planning scopes must remain OFF.")
        require(scope["authority_permission"] == (f"access_control.delegate.{scope['service_code']}" if scope["service_code"] in DELEGATED_SERVICES else None), "Delegation authority mismatch.")
        for field in ("permission_codes", "role_names"):
            require(type(scope[field]) is list and all(type(item) is str for item in scope[field]), "Invalid delegation list.")
            unique(scope[field], f"Delegation {field}")
        require(bool(scope["permission_codes"]) == bool(scope["role_names"]), "Incomplete delegation candidate.")
        for code in scope["permission_codes"]:
            require(code in permissions and permissions[code]["service_code"] == scope["service_code"]
                    and permissions[code]["readiness"] != "B" and scope["service_code"] not in {"accounts", "access_control", "support"}, "Invalid/protected delegation permission.")
            for role in scope["role_names"]:
                require(role in expected_roles and not is_reserved_role(role) and (role, code) in binding_pairs, "Unsafe delegation recipient Cartesian product.")
        refs(scope["decision_refs"])
        text(scope["restriction"], 1024, "Delegation restriction")
    unique([s["service_code"] for s in data["delegation_candidates"]], "Delegation services")
    require({s["service_code"] for s in data["delegation_candidates"]} == set(services), "Every service must have an explicit candidate/disabled scope.")
    for decision in data["decisions"]:
        keys(decision, "id state description", "Decision")
        require(decision["state"] == "OPEN" and type(decision["id"]) is str and decision["id"] in DECISIONS, "Unapproved governance decision state.")
        text(decision["description"], 2048, "Decision description")
    require(Counter(d["id"] for d in data["decisions"]) == Counter(DECISIONS), "All D01-D18 must remain explicitly OPEN.")
    for gap in data["blocked_contracts"]:
        keys(gap, "id status decision_refs description", "Blocked contract")
        require(type(gap["id"]) is str and gap["status"] == "BLOCKED", "Unsupported governance must remain blocked.")
        refs(gap["decision_refs"])
        text(gap["description"], 1024, "Blocked contract")
    require(Counter(g["id"] for g in data["blocked_contracts"]) == Counter(f"G{n}" for n in range(1, 9)), "All G1-G8 compatibility blockers required.")

    # The pinned document, not mutable counts in JSON, defines the exact matrix.
    source_services = [r[:3] for r in table_rows(document, "## 2.", "## 3.") if len(r) == 4 and SERVICE_CODE.fullmatch(r[0])]
    require(sorted(source_services) == sorted([s[k] for k in ("service_code", "service_name", "description")] for s in data["services"]), "Service metadata differs from C1.")
    source_permissions = [r for r in table_rows(document, "## 3.", "## 4.") if len(r) == 8 and PERMISSION_CODE.fullmatch(r[1])]
    expected_permissions = {r[1]: r[:6] + [r[7]] for r in source_permissions}
    actual_permissions = {p["permission_code"]: [p[k] for k in ("service_code", "permission_code", "permission_name", "module_name", "action_name", "description", "readiness")] for p in data["permissions"]}
    require(actual_permissions == expected_permissions, "Permission metadata/readiness differs from C1.")
    expected_bindings = {(ROLE_KEYS[key], r[1]) for r in source_permissions if r[6] != "-" for key in r[6].split(",")}
    require(set(binding_pairs) == expected_bindings, "Default role matrix differs from C1.")
    matrix = [r for r in table_rows(document, "## 4.", "## 5.") if len(r) == 6 and r[0] in services]
    for row in matrix:
        for role, count in zip(ROLE_KEYS.values(), row[1:], strict=True):
            require(sum(r == role and permissions[c]["service_code"] == row[0] for r, c in binding_pairs) == int(count), "Source role count matrix mismatch.")
    source_scopes = {r[0]: r for r in table_rows(document, "### 6.1", "### 6.2") if len(r) == 4 and r[0] in services}
    for scope in data["delegation_candidates"]:
        row = source_scopes[scope["service_code"]]
        require(scope["permission_codes"] == ([] if row[1].startswith("None") else row[1].split(", "))
                and scope["role_names"] == ([] if row[2] == "None" else row[2].split(", "))
                and scope["restriction"] == row[3], "Delegation candidate differs from narrow C1 scope.")
    source_decisions = {r[0][:3]: ": ".join(r) for r in table_rows(document, "## 9.", "## 10.") if re.match(r"D\d\d ", r[0])}
    require({d["id"]: d["description"] for d in data["decisions"]} == source_decisions, "Governance decision text differs from C1.")
    require((len(services), len(permissions), len(binding_pairs), len(matrix)) == (10, 82, 96, 10), "Incomplete C1 planning baseline.")
    return ValidatedCatalogue(freeze(data))
