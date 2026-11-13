"""AR-3B2B2: read-only v2 proposal comparison; never initialize or grant.

Reuses v1's MySQL READ ONLY snapshot and SELECT-only execution wrapper.
No runtime permission decision, approval, or write operation is exposed here.
"""

from collections import Counter
import re

from django.db import connection
from django.db.models import Count, Q

from ..models import AccountPermission, Permission, Role, RolePermission, Service
from .planner import readonly_snapshot
from .validation import normalized
from .validation_v2 import RETIRED_CODE, validate_manifest


KINDS = ("service", "permission", "role", "role_binding")
STATES = ("CREATE", "MATCH", "CONFLICT", "DEFER")


def build_plan_v2():
    # Pin and validate every source before opening a database connection.
    # The manifest is static review metadata, NOT an authorization policy.
    catalogue = validate_manifest().data
    with readonly_snapshot():
        return _compare_v2(catalogue)


def _compare_v2(data):
    records = []
    unexpected = []
    found = {kind: set() for kind in KINDS}
    canonical = {kind: {} for kind in ("service", "permission", "role")}
    states = {kind: {} for kind in ("service", "permission", "role")}
    blocked_codes = {p["permission_code"] for p in data["permissions"] if p["readiness"] == "B"}
    delegation_codes = {p["permission_code"] for p in data["permissions"]
                        if p["permission_code"].startswith("access_control.delegate.")}

    def entry(kind, key, classification, detail, existing_id=None, **extra):
        result = {"kind": kind, "key": key, "classification": classification,
                  "detail": detail, **extra}
        if existing_id is not None:
            result["existing_id"] = existing_id
        records.append(result)
        return result

    for proposal in data["services"]:
        code = proposal["service_code"]
        matches = list(Service.objects.filter(
            Q(service_code=code) | Q(service_name=proposal["service_name"])
        ).values())
        found["service"].update(row["service_id"] for row in matches)
        row = matches[0] if len(matches) == 1 else None
        state, detail = "CREATE", "Missing service; proposed inactive creation only."
        if matches:
            if (row is None or any(row[field] != proposal[field]
                                   for field in ("service_code", "service_name", "description"))):
                state, detail = "CONFLICT", "Service code/name/collation or metadata differs; preserve existing rows."
            elif row["is_active"]:
                state, detail = "CONFLICT", "Already active service requires separate activation/provenance review."
            else:
                state, detail = "MATCH", "Exact existing inactive service; preserve current state."
        states["service"][code] = state
        if row and row["service_code"] == code:
            canonical["service"][code] = row
        entry("service", code, state, detail, row["service_id"] if row else None)

    for proposal in data["permissions"]:
        code = proposal["permission_code"]
        matches = list(Permission.objects.filter(permission_code=code).values())
        found["permission"].update(row["permission_id"] for row in matches)
        row = matches[0] if len(matches) == 1 else None
        parent = canonical["service"].get(proposal["service_code"])
        state, detail = "CREATE", "Missing selectable definition; metadata proposal only, not authorized use."
        if matches:
            if (row is None or parent is None or row["service_id"] != parent["service_id"]
                    or any(row[field] != proposal[field] for field in (
                        "permission_code", "permission_name", "module_name", "action_name", "description"
                    ))):
                state = "CONFLICT"
                detail = ("Metadata revision requires explicit approved transition; do not overwrite."
                          if proposal["origin"] == "REVISE" and row and row["permission_code"] == code
                          else "Code/collation, parent service, or metadata differs; no repair.")
            else:
                state, detail = "MATCH", "Exact existing definition; no approval or activation inferred."
        if states["service"][proposal["service_code"]] == "CONFLICT":
            state, detail = "CONFLICT", "Parent service conflict blocks this permission proposal."
        states["permission"][code] = state
        if row and row["permission_code"] == code:
            canonical["permission"][code] = row
        entry("permission", code, state, detail, row["permission_id"] if row else None,
              origin=proposal["origin"], readiness=proposal["readiness"],
              scope=proposal["scope"], grant_protection=proposal["grant_protection"],
              application_approved=False)

    existing_roles = list(Role.objects.order_by("role_id").values())

    def compact(value):
        return re.sub(r"[\W_]+", "", normalized(value))

    for proposal in data["roles"]:
        name = proposal["role_name"]
        matches = list(Role.objects.filter(role_name=name).values())
        aliases = [r for r in existing_roles if compact(r["role_name"]) == compact(name)
                   and r not in matches]
        matches += aliases
        found["role"].update(row["role_id"] for row in matches)
        row = matches[0] if len(matches) == 1 else None
        state, detail = "CREATE", "Missing ordinary role; separate audited initializer approval required."
        if matches:
            if (row is None or row["role_name"] != name
                    or row["description"] != proposal["description"] or not row["is_active"]):
                state, detail = "CONFLICT", "Role name/alias, metadata, or active status differs; preserve existing record."
            else:
                state, detail = "MATCH", "Existing active role matches; no assignment implied."
        elif name in {"Technical Super Admin", "SSG Advisor"}:
            state, detail = "DEFER", "Protected/optional role absent; eligibility, appointment, or bootstrap approval required."
        states["role"][name] = state
        if row and row["role_name"] == name:
            canonical["role"][name] = row
        entry("role", name, state, detail, row["role_id"] if row else None)

    grants = list(RolePermission.objects.order_by("role_permission_id").values())
    grant_pairs = {(row["role_id"], row["permission_id"]): row for row in grants}
    for proposal in data["default_bindings"]:
        name, code = proposal["role_name"], proposal["permission_code"]
        role, permission = canonical["role"].get(name), canonical["permission"].get(code)
        row = grant_pairs.get((role["role_id"], permission["permission_id"])) if role and permission else None
        state, detail = "DEFER", "Proposed default only; no grant, eligibility, object policy, or activation approval."
        if row:
            found["role_binding"].add(row["role_permission_id"])
            if row["is_active"]:
                state, detail = "MATCH", "Existing active pair; approval/provenance NOT inferred."
            else:
                state, detail = "CONFLICT", "Existing inactive grant must not be silently reactivated."
        if states["role"][name] == "CONFLICT" or states["permission"][code] == "CONFLICT":
            state, detail = "CONFLICT", "Parent role/permission conflict blocks proposed binding."
        entry("role_binding", f"{name} -> {code}", state, detail,
              row["role_permission_id"] if row else None,
              proposed_delta="EXISTS" if row else "CREATE", application_approved=False)

    # Retired C1 code is not a selectable v2 definition. An existing row is
    # retained; active role grants / account overrides need urgent conflict review.
    retired_rows = list(Permission.objects.filter(permission_code=RETIRED_CODE).values())
    found["permission"].update(row["permission_id"] for row in retired_rows)
    retired_ids = {row["permission_id"] for row in retired_rows}
    retired_grants = [g for g in grants if g["permission_id"] in retired_ids]
    found["role_binding"].update(g["role_permission_id"] for g in retired_grants)
    retired_active_grants = sum(bool(g["is_active"]) for g in retired_grants)

    # Aggregate override counts only. Never select account_id, email, credentials,
    # reason, or any other account-level identifying data into the report.
    overrides = []
    retired_active_overrides = 0
    # Ask MySQL for code equivalence, not Python casefold alone: an existing
    # permission with a collating/formatting variant must still be reviewed.
    restricted_ids = {row["permission_id"] for row in
                      Permission.objects.filter(permission_code__in=blocked_codes | delegation_codes)
                      .values("permission_id")}
    for group in (AccountPermission.objects.values("permission_id", "effect", "is_active")
                  .annotate(count=Count("pk"))
                  .order_by("permission_id", "effect", "is_active")):
        retired = group["permission_id"] in retired_ids
        restricted = group["permission_id"] in restricted_ids
        active = bool(group["is_active"])
        if retired and active:
            retired_active_overrides += group["count"]
        state = "CONFLICT" if active and (retired or (restricted and group["effect"] == "Grant")) else "DEFER"
        overrides.append(dict(permission_id=group["permission_id"], effect=group["effect"],
                              is_active=active, count=group["count"], classification=state,
                              retired=retired, restricted=restricted,
                              detail="Preserve override; independently review any active restricted/retired authority."))

    retirement_review = []
    for row in retired_rows:
        state = "CONFLICT" if (retired_active_grants or retired_active_overrides
                               or row["permission_code"] != RETIRED_CODE) else "DEFER"
        retirement_review.append(dict(kind="retired_permission", key=RETIRED_CODE,
                                      existing_id=row["permission_id"], classification=state,
                                      active_role_grants=retired_active_grants,
                                      active_account_overrides=retired_active_overrides,
                                      detail="Preserve historical row and all overrides; no remap, deletion, or activation."))

    for kind, rows, id_field, key_field in (
        ("service", Service.objects.order_by("service_id").values(), "service_id", "service_code"),
        ("permission", Permission.objects.order_by("permission_id").values(), "permission_id", "permission_code"),
        ("role", existing_roles, "role_id", "role_name"),
        ("role_binding", grants, "role_permission_id", None),
    ):
        for row in rows:
            if row[id_field] in found[kind]:
                continue
            unapproved_active_grant = kind == "role_binding" and bool(row["is_active"])
            state = "CONFLICT" if unapproved_active_grant else "DEFER"
            key = row[key_field] if key_field else f"role_id={row['role_id']}, permission_id={row['permission_id']}"
            unexpected.append(dict(kind=kind, existing_id=row[id_field], key=key,
                                   classification=state,
                                   detail="Preserve unexpected active role grant; explicit security review required."
                                   if unapproved_active_grant else "Preserve unexpected existing record for explicit review."))

    blockers = [{"id": p["id"], "status": p["status"], "description": p["decision"]}
                for p in data["policy_blockers"]]
    blockers += [{"id": name, "status": gate, "description": "Unapproved operational gate; no enablement."}
                 for name, gate in data["operational_gates"].items()]
    totals = Counter(r["classification"] for r in records)
    risk_totals = Counter(r["classification"] for r in unexpected + retirement_review + overrides)
    return {
        "mode": "READ-ONLY V2 PLANNING", "manifest": data["manifest_version"],
        "source_revision": data["source_revision"], "provenance": dict(data["provenance"]["proposal"]),
        "proposed": dict(services=len(data["services"]), permissions=len(data["permissions"]),
                         roles=len(data["roles"]), role_bindings=len(data["default_bindings"]),
                         retired_tombstones=len(data["historical_retirements"])),
        "database_vendor": connection.vendor,
        "existing_roles": [r["role_name"] for r in existing_roles],
        "records": records, "totals": {state: totals[state] for state in STATES},
        "unexpected": unexpected, "retirement_review": retirement_review,
        "account_override_review": overrides,
        "review_totals": {state: risk_totals[state] for state in STATES},
        "blocked_dependencies": blockers,
        "delegation_status": data["delegation"]["status"],
        "application_approved": False, "database_modifications": 0,
        "guarantee": ("MySQL READ ONLY consistent snapshot with SELECT-only guard; rolled back. "
                      "No DML, DDL, audit writes, grants, service activation, or repairs."),
    }
