"""Read-only comparison, never an initialization or authority-granting service."""

from collections import Counter
from contextlib import contextmanager
import re

from django.db import DEFAULT_DB_ALIAS, connection
from django.db.models import Count, Q

from ..models import AccountPermission, Permission, Role, RolePermission, Service
from .validation import normalized, validate_manifest


class CataloguePlanningError(RuntimeError):
    pass


def select_only(execute, sql, params, many, context):
    # Only our fixed SELECT statements are accepted inside the comparison body.
    # Parameter values are never interpolated or inspected as SQL.
    if (many or not re.match(r"\ASELECT\s", sql, re.I)
            or re.search(r";|\bINTO\b|\bFOR\s+UPDATE\b|\bLOCK\s+IN\b", sql, re.I)):
        raise CataloguePlanningError("Read-only planner refused a non-SELECT statement.")
    return execute(sql, params, many, context)


@contextmanager
def readonly_snapshot():
    if connection.vendor != "mysql" or connection.alias != DEFAULT_DB_ALIAS:
        raise CataloguePlanningError("Planner requires the default MySQL database.")
    if connection.in_atomic_block or not connection.get_autocommit():
        raise CataloguePlanningError("Planner requires its own read-only transaction; caller transaction refused.")
    # Initialize Django/MySQL session before applying the statement guard. These
    # connection/session controls do not change database records or schema.
    connection.ensure_connection()
    started = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
            started = True
        with connection.execute_wrapper(select_only):
            yield
    finally:
        if started:
            connection.rollback()


def build_plan():
    # Always validate before establishing a database connection. No externally
    # supplied manifest path, database IDs, apply flag, or activation mode exists.
    catalogue = validate_manifest().data
    with readonly_snapshot():
        return _compare(catalogue)


def _compare(data):
    records, unexpected, overrides = [], [], []
    found = {"service": set(), "permission": set(), "role": set(), "role_binding": set()}
    canonical = {"service": {}, "permission": {}, "role": {}}
    states = {"service": {}, "permission": {}, "role": {}}

    def entry(kind, key, classification, detail, existing_id=None, **extra):
        record = dict(kind=kind, key=key, classification=classification, detail=detail, **extra)
        if existing_id is not None:
            record["existing_id"] = existing_id
        records.append(record)
        return record

    # Lookups deliberately execute against the actual unique-column collations.
    # A Python normalization approximation alone misses MySQL equivalences.
    for proposed in data["services"]:
        code = proposed["service_code"]
        matches = list(Service.objects.filter(Q(service_code=code) | Q(service_name=proposed["service_name"])).values())
        found["service"].update(row["service_id"] for row in matches)
        state, detail = "CREATE", "Metadata candidate only; future creation must be inactive."
        row = matches[0] if len(matches) == 1 else None
        if matches:
            if row is None or any(row[field] != proposed[field] for field in ("service_code", "service_name", "description")):
                state, detail = "CONFLICT", "Unique code/name, collation-equivalent identifier, or metadata differs; preserve existing rows."
            elif row["is_active"]:
                state, detail = "CONFLICT", "Existing active service requires separate activation/provenance review; never toggle it."
            else:
                state, detail = "MATCH", "Exact metadata; existing inactive state preserved."
        states["service"][code] = state
        if row and row["service_code"] == code:
            canonical["service"][code] = row
        entry("service", code, state, detail, row["service_id"] if row else None,
              decision_refs=list(proposed["decision_refs"]))

    for proposed in data["permissions"]:
        code = proposed["permission_code"]
        matches = list(Permission.objects.filter(permission_code=code).values())
        found["permission"].update(row["permission_id"] for row in matches)
        row = matches[0] if len(matches) == 1 else None
        parent = canonical["service"].get(proposed["service_code"])
        state, detail = "CREATE", "Metadata candidate only; no permission grant or feature activation."
        if matches:
            if (row is None or parent is None or row["service_id"] != parent["service_id"]
                    or any(row[field] != proposed[field] for field in ("permission_code", "permission_name", "module_name", "action_name", "description"))):
                state, detail = "CONFLICT", "Code/collation, service relationship, or metadata differs; no repair."
            else:
                state, detail = "MATCH", "Exact existing definition; catalogue presence does not authorize use."
        if states["service"][proposed["service_code"]] == "CONFLICT":
            state, detail = "CONFLICT", "Parent service conflict blocks this permission plan."
        states["permission"][code] = state
        if row and row["permission_code"] == code:
            canonical["permission"][code] = row
        entry("permission", code, state, detail, row["permission_id"] if row else None,
              readiness=proposed["readiness"], policy_markers=list(proposed["policy_markers"]),
              decision_refs=list(proposed["decision_refs"]))

    existing_roles = list(Role.objects.order_by("role_id").values())
    for proposed in data["roles"]:
        name = proposed["role_name"]
        matches = list(Role.objects.filter(role_name=name).values())
        # B2 also reserves formatting variants that need not be SQL-equivalent.
        compact = lambda value: re.sub(r"[\W_]+", "", normalized(value))
        aliases = [r for r in existing_roles if compact(r["role_name"]) == compact(name) and r not in matches]
        matches += aliases
        found["role"].update(row["role_id"] for row in matches)
        row = matches[0] if len(matches) == 1 else None
        state, detail = "CREATE", "Missing canonical role; proposal only, never initialized here."
        if matches:
            if row is None or row["role_name"] != name or row["description"] != proposed["description"] or not row["is_active"]:
                state, detail = "CONFLICT", "Role identifier/metadata/inactive state differs; preserve it."
            else:
                state, detail = "MATCH", "Exact existing active role; no assignments implied."
        elif name == "Technical Super Admin":
            state, detail = "DEFER", "Missing fifth role: separately authorized human provisioning, actor attribution, governance, bootstrap and recovery required."
        states["role"][name] = state
        if row and row["role_name"] == name:
            canonical["role"][name] = row
        entry("role", name, state, detail, row["role_id"] if row else None)

    grants = list(RolePermission.objects.order_by("role_permission_id").values())
    grant_pairs = {(row["role_id"], row["permission_id"]): row for row in grants}
    for proposed in data["default_bindings"]:
        name, code = proposed["role_name"], proposed["permission_code"]
        role, permission = canonical["role"].get(name), canonical["permission"].get(code)
        row = grant_pairs.get((role["role_id"], permission["permission_id"])) if role and permission else None
        state, detail = "DEFER", "Proposed default only: explicit per-binding approval, implementation/object scopes, attributable initializer and activation review remain required."
        if row:
            found["role_binding"].add(row["role_permission_id"])
            if row["is_active"]:
                state, detail = "MATCH", "Existing active binding matches proposed pair; approval/provenance not inferred."
            else:
                state, detail = "CONFLICT", "Existing inactive grant is protected; never reactivate or refresh attribution."
        if states["role"][name] == "CONFLICT" or states["permission"][code] == "CONFLICT":
            state, detail = "CONFLICT", "Parent role/permission conflict blocks this proposed binding."
        entry("role_binding", f"{name} -> {code}", state, detail,
              row["role_permission_id"] if row else None, proposed_delta="EXISTS" if row else "CREATE",
              application_approved=False)

    for kind, rows, id_field, label_field in (
        ("service", Service.objects.order_by("service_id").values(), "service_id", "service_code"),
        ("permission", Permission.objects.order_by("permission_id").values(), "permission_id", "permission_code"),
        ("role", existing_roles, "role_id", "role_name"),
        ("role_binding", grants, "role_permission_id", None),
    ):
        for row in rows:
            if row[id_field] not in found[kind]:
                unexpected.append(dict(kind=kind, existing_id=row[id_field],
                    key=row[label_field] if label_field else f"role_id={row['role_id']}, permission_id={row['permission_id']}",
                    classification="DEFER", detail="Unexpected existing record; preserve unchanged and review separately."))

    # Overrides are never folded into defaults, removed, replaced or reattributed.
    # Aggregate only security state; no account identities/credential/profile data.
    for group in AccountPermission.objects.values("permission_id", "effect", "is_active").annotate(count=Count("pk")).order_by("permission_id", "effect", "is_active"):
        overrides.append(dict(group, classification="DEFER", detail="Existing account overrides preserved; separate conflict/effective-access review required."))

    blockers = [dict(gap) | {"decision_refs": list(gap["decision_refs"])} for gap in data["blocked_contracts"]]
    blockers.extend([
        dict(id="APPLY", status="BLOCKED", description="C2A authorizes planning only; D01-D18 remain OPEN. No apply/seed mode exists."),
        dict(id="FIRST_OPERATOR", status="BLOCKED", description="No trusted initial actor, first-init lock, bootstrap authority or initialization audit event contract is established by this tool."),
        dict(id="ACTIVATION", status="BLOCKED", description="All feature/object-scope, explicit grant, service activation and delegation approvals remain separate."),
    ])
    totals = Counter(record["classification"] for record in records)
    unexpected_totals = Counter(record["classification"] for record in unexpected)
    return dict(mode="READ-ONLY PLANNING", manifest=data["manifest_version"], source=dict(data["source"]),
        proposed=dict(services=len(data["services"]), permissions=len(data["permissions"]), role_bindings=len(data["default_bindings"])),
        database_vendor=connection.vendor, existing_roles=[r["role_name"] for r in existing_roles],
        records=records, totals={name: totals[name] for name in ("CREATE", "MATCH", "CONFLICT", "DEFER")},
        unexpected=unexpected, unexpected_totals=dict(unexpected_totals), account_override_review=overrides,
        pending_decisions=[dict(d) for d in data["decisions"]], blocked_dependencies=blockers,
        delegation_candidates=[dict(service_code=s["service_code"], status=s["status"],
            permission_codes=list(s["permission_codes"]), role_names=list(s["role_names"])) for s in data["delegation_candidates"]],
        database_modifications=0,
        guarantee="Comparison used a MySQL READ ONLY consistent snapshot and SELECT-only statement guard; transaction rolled back. No DML, DDL or audit writes. Session/transaction controls only.")
