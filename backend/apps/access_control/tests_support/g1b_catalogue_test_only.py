"""G1B static planning contract and fictional bootstrap checks; NEVER an authorizer.

This module has no Django imports, database calls, writes, routing or provisioning.
Its outputs validate a pinned PROPOSAL; they do not approve metadata seeding or grants.
Production endpoints and mutation services must NEVER import this module.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import unicodedata


# G1B-D1: exact planning-only subset of the existing v2.0 proposal.
# Do NOT derive authority/default grants from these constants.
CORE_K_DEFINITIONS = (
    (
        "access_control.catalogue.read", "Read permission catalogue",
        "catalogue", "read",
        "Read service/permission definitions and readiness metadata without exposing business records or secrets.",
        "P", "KEEP",
    ),
    (
        "access_control.role_permissions.manage", "Manage ordinary role permissions",
        "role_permissions", "manage",
        "Invoke trusted role-grant/revoke services only with separate approved service delegation and eligible targets.",
        "F", "KEEP",
    ),
    (
        "access_control.account_permissions.manage", "Manage ordinary account overrides",
        "account_permissions", "manage",
        "Invoke trusted Grant/Deny/deactivation services only with separate approved service delegation and eligible targets.",
        "F", "KEEP",
    ),
    (
        "access_control.effective_permissions.inspect", "Inspect effective permissions",
        "effective_permissions", "inspect",
        "Inspect attributable account/role/permission identifiers and outcomes; exclude profile, finance and assessment bodies.",
        "P", "KEEP",
    ),
    (
        "access_control.audit.read", "Read access-control audit",
        "audit", "read",
        "Read security-change attribution and allowlisted snapshots; do not treat this as business-ledger or credential access.",
        "P", "KEEP",
    ),
    (
        "access_control.admin_assignments.manage", "Manage school Admin assignments",
        "admin_assignments", "manage",
        "Promote or remove another eligible Normal Admin through protected review, actor-impact and last-effective-operator safeguards.",
        "P", "ADD",
    ),
)
CORE_K_CODES = tuple(item[0] for item in CORE_K_DEFINITIONS)
EXPECTED_ROLE = "Technical Super Admin"
NORMAL_ROLE = "Admin"
RETIRED_CODE = "access_control.role_assignments.manage"
EXCLUDED_CORE_CODES = frozenset({
    "access_control.diagnostics.read",
    "access_control.role_assignments.ordinary.manage",
    "access_control.role_assignments.manage",
    "access_control.governance_grants.manage",
    "access_control.technical_accounts.provision",
    "access_control.technical_accounts.recover",
    "access_control.services.activation.manage",
    "access_control.catalogue.initialize",
})
SOURCE_MANIFEST = Path(__file__).resolve().parents[1] / "catalogue" / "v2_0.json"


def _compact(text):
    if type(text) is not str:
        return ""
    normalized = "".join(
        ch for ch in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(ch)
    )
    return re.sub(r"[\W_]+", "", normalized)


def load_pinned_proposal_test_only():
    """Reads the existing v2 proposal without altering it; never accesses MySQL."""
    with SOURCE_MANIFEST.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_catalogue_subset_test_only(data):
    """Return a tuple of static drift codes. Empty tuple means paper subset matches.

    Validity is *not* authorization to initialize, assign, grant or activate rows.
    The remainder of v2's 95 definitions and 106 bindings is not approved here.
    """
    if type(data) is not dict:
        return ("invalid-manifest",)
    errors = set()
    for key, expected in (
        ("schema_version", "static-catalogue-v2.0"),
        ("manifest_version", "catalogue-v2.0"),
        ("source_revision", "v2.0-review-1"),
        ("planning_only", True),
    ):
        if type(data.get(key)) is not type(expected) or data.get(key) != expected:
            errors.add("manifest-header-mismatch")

    sections = ("services", "roles", "permissions", "default_bindings", "historical_retirements", "blocked_permissions")
    if any(type(data.get(s)) is not list or any(type(x) is not dict for x in data[s]) for s in sections):
        return tuple(sorted(errors | {"invalid-sections"}))

    services = [s.get("service_code") for s in data["services"]]
    if services.count("access_control") != 1 or sum(_compact(s) == "accesscontrol" for s in services) != 1:
        errors.add("governance-service-mismatch")

    roles = [r.get("role_name") for r in data["roles"]]
    for canonical in (NORMAL_ROLE, EXPECTED_ROLE):
        if roles.count(canonical) != 1 or sum(_compact(r) == _compact(canonical) for r in roles) != 1:
            errors.add("protected-role-name-mismatch")
    if data.get("role_keys") != {"S": "Student", "I": "Instructor", "T": "Treasurer", "A": "Admin", "G": EXPECTED_ROLE, "V": "SSG Advisor"}:
        errors.add("role-key-mismatch")

    entries = data["permissions"]
    codes = [p.get("permission_code") for p in entries]
    for entry in CORE_K_DEFINITIONS:
        code, name, module, action, description, readiness, origin = entry
        canonical = [p for p in entries if p.get("permission_code") == code]
        near = [p for p in entries if _compact(p.get("permission_code")) == _compact(code)]
        if len(canonical) != 1 or len(near) != 1:
            errors.add("core-code-collision-or-missing")
            continue
        actual = canonical[0]
        expected = {
            "service_code": "access_control", "permission_code": code,
            "permission_name": name, "module_name": module, "action_name": action,
            "description": description, "readiness": readiness, "origin": origin,
            "scope": "GOV", "grant_protection": "GOV",
        }
        if any(actual.get(k) != v or type(actual.get(k)) is not str for k, v in expected.items()):
            errors.add("core-metadata-mismatch")

    if RETIRED_CODE in codes or any(_compact(x) == _compact(RETIRED_CODE) for x in codes):
        errors.add("retired-code-selectable")
    retired = [p.get("permission_code") for p in data["historical_retirements"]]
    if retired.count(RETIRED_CODE) != 1:
        errors.add("retirement-tombstone-mismatch")

    bindings = [(b.get("role_name"), b.get("permission_code")) for b in data["default_bindings"]]
    for code in CORE_K_CODES:
        candidates = [(role, c) for role, c in bindings if _compact(c) == _compact(code)]
        if len(candidates) != 1 or candidates[0] != (EXPECTED_ROLE, code):
            errors.add("core-default-binding-mismatch")
    if any(c == RETIRED_CODE or _compact(c) == _compact(RETIRED_CODE) for _, c in bindings):
        errors.add("retired-binding")

    blocked = {_compact(item.get("permission_code")) for item in data["blocked_permissions"]}
    if any(_compact(c) in blocked for c in CORE_K_CODES):
        errors.add("core-code-blocked")
    if any(_compact(c) in blocked for _, c in bindings):
        errors.add("blocked-default-binding")
    if not EXCLUDED_CORE_CODES.isdisjoint(CORE_K_CODES):
        errors.add("excluded-core-code")
    return tuple(sorted(errors))


@dataclass(frozen=True)
class SimulatedBootstrapBlueprint:
    """Fictional input only. Numeric IDs are NOT verified real-world identities."""

    beneficiary_id: int
    beneficiary_approved_active_admin: bool
    institutional_approver_id: int
    technical_custodian_id: int
    executor_id: int
    target_database: str
    policy_version: str
    proposed_roles: tuple[str, ...]
    proposed_governance_codes: tuple[str, ...]
    before_digest: str
    request_id: str
    issued_at: datetime
    expires_at: datetime
    existing_technical_operator_count: int
    consumed: bool = False


def bootstrap_blueprint_matches_test_only(blueprint, *, now, test_database, before_digest, policy_version):
    """Illustrate refusal rules only; deliberately never checks or writes live state.

    No assurance of identity, authentic reviewer signatures, replay protection,
    locks, sessions or ledger persistence is provided by this simulated predicate.
    """
    if type(blueprint) is not SimulatedBootstrapBlueprint:
        return False
    if type(test_database) is not str or not test_database.startswith("test_ctug_registration_"):
        return False
    if blueprint.target_database != test_database or blueprint.target_database == "ctug_workspace":
        return False
    if type(now) is not datetime or now.tzinfo is None:
        return False
    if any(type(v) is not int or v <= 0 for v in (
        blueprint.beneficiary_id, blueprint.institutional_approver_id,
        blueprint.technical_custodian_id, blueprint.executor_id,
    )):
        return False
    if len({blueprint.beneficiary_id, blueprint.institutional_approver_id,
            blueprint.technical_custodian_id, blueprint.executor_id}) != 4:
        return False
    if blueprint.beneficiary_approved_active_admin is not True:
        return False
    if type(blueprint.consumed) is not bool or blueprint.consumed:
        return False
    if type(blueprint.existing_technical_operator_count) is not int or blueprint.existing_technical_operator_count != 0:
        return False
    if blueprint.proposed_roles != (NORMAL_ROLE, EXPECTED_ROLE):
        return False
    if blueprint.proposed_governance_codes != CORE_K_CODES:
        return False
    if type(blueprint.policy_version) is not str or blueprint.policy_version != policy_version or not policy_version:
        return False
    if type(blueprint.request_id) is not str or not 1 <= len(blueprint.request_id.strip()) <= 80:
        return False
    if (
        type(blueprint.before_digest) is not str
        or blueprint.before_digest != before_digest
        or re.fullmatch(r"[0-9a-f]{64}", before_digest or "") is None
    ):
        return False
    start, end = blueprint.issued_at, blueprint.expires_at
    if type(start) is not datetime or type(end) is not datetime or start.tzinfo is None or end.tzinfo is None:
        return False
    return start <= now < end and timedelta(0) < end - start <= timedelta(minutes=15)
