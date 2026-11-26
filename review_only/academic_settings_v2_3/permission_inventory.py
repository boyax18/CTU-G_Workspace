"""Explicitly authorized, SELECT-only permission inventory. Default invocation never connects.

No Django setup, application credentials, SQL input, ORM, writes, stored procedures or DDL.
Use a pre-existing SELECT-only MySQL identity. See the controlled-activation runbook first.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import hmac
import json
import os
import re
import sys

AUTHORIZATION = "OWNER_AUTHORIZED_CTUG_WORKSPACE_PERMISSION_SELECT_ONLY"
REDUCED_READER = "ctug_wf11_inventory_ro"
REDUCED_HOST = "127.0.0.1"
REDUCED_PORT = 3306
REDUCED_TABLES = frozenset({"permissions", "services", "roles", "role_permissions", "account_permissions",
                            "account_roles", "accounts"})
REDUCED_IDENTITY = "SELECT DATABASE(), CURRENT_USER(), @@port, CURRENT_ROLE(), @@GLOBAL.mandatory_roles"
TRANSITIONS = {
    "academic.enrollment_verifications.record": ("academic.profiles.manage",),
    "academic.semester_onboarding.self.submit": ("clearance.requests.self.submit",),
    "academic.historical_participation.correct": ("academic.periods.manage", "academic.profiles.manage"),
}
UNCHANGED = ("finance.fee_schedule.manage", "academic.courses.manage", "academic.periods.manage",
             "academic.sections.manage", "academic.profile.self.read", "academic.catalogue.read",
             "clearance.subjects.manage", "clearance.teaching_assignments.manage")
CODES = tuple(sorted(set(UNCHANGED) | set(TRANSITIONS) | {c for old in TRANSITIONS.values() for c in old}))
MARKS = ",".join(["%s"] * len(CODES))
QUERIES = {
    "identity": "SELECT DATABASE(), @@hostname, @@port, @@transaction_read_only",
    "engines": "SELECT table_name, engine FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name IN ('permissions','services','roles','role_permissions','account_permissions','account_roles','accounts','account_permission_role_scopes') ORDER BY table_name",
    "services": "SELECT service_code,is_active FROM services WHERE service_code IN ('academic','finance','clearance') ORDER BY service_code",
    "permissions": f"SELECT p.permission_id, p.permission_code, s.service_code, s.is_active FROM permissions p JOIN services s ON s.service_id=p.service_id WHERE p.permission_code IN ({MARKS}) ORDER BY p.permission_id",
    "role_bindings": f"SELECT p.permission_code, r.role_id, r.role_name, r.is_active, rp.role_permission_id, rp.is_active FROM role_permissions rp JOIN permissions p ON p.permission_id=rp.permission_id JOIN roles r ON r.role_id=rp.role_id WHERE p.permission_code IN ({MARKS}) ORDER BY p.permission_code,r.role_id",
    "overrides": f"SELECT p.permission_code, ap.account_id, ap.account_permission_id, ap.effect, ap.is_active FROM account_permissions ap JOIN permissions p ON p.permission_id=ap.permission_id WHERE p.permission_code IN ({MARKS}) ORDER BY p.permission_code,ap.account_id",
    "scopes": f"SELECT ap.account_permission_id, rs.role_id FROM account_permission_role_scopes rs JOIN account_permissions ap ON ap.account_permission_id=rs.account_permission_id JOIN permissions p ON p.permission_id=ap.permission_id WHERE p.permission_code IN ({MARKS}) ORDER BY ap.account_permission_id",
    # Only accounts that could gain new defaults or hold any old/new affected code. No names/IDs/emails.
    "accounts": f"SELECT DISTINCT a.account_id,a.is_active,a.request_status,a.is_staff,a.is_superuser FROM accounts a WHERE EXISTS (SELECT 1 FROM account_roles ar JOIN roles r ON r.role_id=ar.role_id WHERE ar.account_id=a.account_id AND r.role_name IN ('Admin','Student','Treasurer','Technical Super Admin')) OR EXISTS (SELECT 1 FROM account_permissions ap JOIN permissions p ON p.permission_id=ap.permission_id WHERE ap.account_id=a.account_id AND p.permission_code IN ({MARKS})) OR EXISTS (SELECT 1 FROM account_roles ar JOIN role_permissions rp ON rp.role_id=ar.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE ar.account_id=a.account_id AND p.permission_code IN ({MARKS})) ORDER BY a.account_id",
    "assignments": f"SELECT ar.account_id,r.role_id,r.role_name,r.is_active FROM account_roles ar JOIN roles r ON r.role_id=ar.role_id WHERE EXISTS (SELECT 1 FROM account_roles ar2 JOIN roles r2 ON r2.role_id=ar2.role_id WHERE ar2.account_id=ar.account_id AND r2.role_name IN ('Admin','Student','Treasurer','Technical Super Admin')) OR EXISTS (SELECT 1 FROM account_permissions ap JOIN permissions p ON p.permission_id=ap.permission_id WHERE ap.account_id=ar.account_id AND p.permission_code IN ({MARKS})) OR EXISTS (SELECT 1 FROM account_roles ar3 JOIN role_permissions rp ON rp.role_id=ar3.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE ar3.account_id=ar.account_id AND p.permission_code IN ({MARKS})) ORDER BY ar.account_id,r.role_id",
}


def token(key, account_id):
    return hmac.new(key, str(account_id).encode("ascii"), hashlib.sha256).hexdigest()[:24]


def summarize(data, key):
    permissions = {r[1]: {"service": r[2], "active": bool(r[3])} for r in data["permissions"]}
    service_states = {code: bool(active) for code, active in data["services"]}
    scopes_available = data["scopes"] is not None
    scope = dict(data["scopes"]) if scopes_available else None
    scoped_scenarios = (False, True) if scopes_available else (False,)
    assignments = defaultdict(list)
    for account_id, role_id, name, active in data["assignments"]:
        assignments[account_id].append((role_id, name, bool(active)))
    overrides = defaultdict(list)
    output_overrides = []
    for code, account_id, row_id, effect, active in data["overrides"]:
        role_scope_id = scope.get(row_id) if scopes_available else None
        overrides[account_id].append((code, effect, bool(active), role_scope_id))
        scope_evidence = {"role_scope_id": role_scope_id} if scopes_available else {"role_scope_status": "unavailable"}
        output_overrides.append({"code": code, "account_token": token(key, account_id), "effect": effect,
                                 "active": bool(active), **scope_evidence})
    old_bindings = {(r[1], r[0]) for r in data["role_bindings"] if r[3] and r[5]}
    new_bindings = old_bindings - {(r[1], "finance.fee_schedule.manage") for r in data["role_bindings"] if r[2] == "Treasurer"}
    for _, rows in assignments.items():
        for role_id, name, active in rows:
            if active and name == "Admin":
                new_bindings.update((role_id, c) for c in ("finance.fee_schedule.manage", "academic.enrollment_verifications.record", "academic.historical_participation.correct"))
            if active and name == "Student":
                new_bindings.add((role_id, "academic.semester_onboarding.self.submit"))
    accounts, mirrors, holders = [], [], defaultdict(set)
    eligible_accounts = {r[0] for r in data["accounts"] if r[1] and r[2] == "Approved" and not r[3] and not r[4]}
    for account_id, _, _, _, _ in data["accounts"]:
        roles = assignments[account_id]
        entries = overrides[account_id]
        denies = {c for c, effect, active, _ in entries if effect == "Deny" and active}
        all_grants = {c for c, effect, active, _ in entries if effect == "Grant" and active}
        sources = {c for role_id, _, active in roles if active for rid, c in old_bindings if role_id == rid}
        for code in sources | all_grants:
            holders[code].add(token(key, account_id))
        for new, old in TRANSITIONS.items():
            blocking = sorted(denies.intersection(old))
            if blocking:
                mirrors.append({"account_token": token(key, account_id), "replacement": new, "legacy_denies": blocking,
                                "new_deny_exists": new in denies, "new_grant_conflict": new in all_grants})
        contexts = [(f"union:scoped-grants-{'on' if scoped else 'off'}", {r[0] for r in roles if r[2]}, None, scoped)
                    for scoped in scoped_scenarios]
        contexts.extend((f"{name}:scoped-grants-{'on' if scoped else 'off'}",
                         {role_id} | ({r[0] for r in roles if r[1] == "Admin" and r[2]} if name == "Technical Super Admin" else set()),
                         role_id, scoped)
                        for role_id, name, active in roles if active for scoped in scoped_scenarios)
        impacts = []
        for context, ids, selected_id, scoped in contexts:
            # Only model scoped evaluation when the role-scope table was read. Off: union ignores role-scope rows, while
            # selected contexts ignore direct Grants. On: union uses unscoped Grants and a
            # selected context uses only its matching scoped Grants. Appointment gates still
            # require a separate contextual review; these are potential source-based impacts.
            grants = {c for c, effect, active, rid in entries if effect == "Grant" and active
                      and ((selected_id is None and (not scoped or rid is None))
                           or (selected_id is not None and scoped and rid == selected_id))}

            def effective(codes, bindings, legacy_denies=False):
                result = {c for rid, c in bindings if rid in ids} | grants
                return {c for c in codes if c in result and c not in denies and account_id in eligible_accounts and ids
                        and permissions.get(c, {"active": service_states.get("academic", False) if c in TRANSITIONS else False})["active"]
                        and not (legacy_denies and denies.intersection(TRANSITIONS.get(c, ())))}

            for new, old in TRANSITIONS.items():
                before = set(old) <= effective(old, old_bindings)
                after = new in effective((new,), new_bindings, True)
                expected_role = "Student" if new.endswith("self.submit") else "Admin"
                role_eligible = any(rid in ids and name == expected_role and active for rid, name, active in roles)
                after = after and role_eligible
                before = before and role_eligible
                if before != after:
                    impacts.append({"context": context, "replacement": new,
                                    "potential": "expansion" if after else "loss",
                                    "old_operation_candidate": before, "new_operation_candidate": after})
            fee = "finance.fee_schedule.manage"
            # Mirror the application's genuine Admin ROLE grant restriction, not just HDAC union.
            admin_ids = {rid for rid, name, active in roles if active and name == "Admin" and rid in ids}
            fee_before = bool(admin_ids) and fee in effective((fee,), old_bindings) and any((rid, fee) in old_bindings for rid in admin_ids)
            fee_after = bool(admin_ids) and fee in effective((fee,), new_bindings) and any((rid, fee) in new_bindings for rid in admin_ids)
            if fee_before != fee_after:
                impacts.append({"context": context, "replacement": fee, "potential": "expansion" if fee_after else "loss"})
            if any(name == "Treasurer" and active and rid in ids for rid, name, active in roles):
                if fee in effective((fee,), old_bindings) and fee not in effective((fee,), new_bindings):
                    impacts.append({"context": context, "replacement": fee, "potential": "loss_of_historical_hdac_code",
                                    "fee_runtime_already_requires_admin_role_grant": True})
        if impacts or entries or sources:
            accounts.append({"account_token": token(key, account_id), "roles": sorted({r[1] for r in roles if r[2]}),
                             "eligible": account_id in eligible_accounts, "potential_transitions": impacts})
    scope_limit = ("Both scoped-grant evaluation states are modeled; actual switches, appointment receipts and live request context must be reviewed separately."
                   if scopes_available else "Role scope is unavailable. Only the hypothetical scoped-Grant-evaluation-off scenario was modeled. Live switches, role context and appointments were not verified.")
    return {"status": "READ_ONLY_INVENTORY_NOT_AUTHORIZATION", "database": "ctug_workspace",
            "role_scope_inventory": {"table": "account_permission_role_scopes",
                                     "status": "available" if scopes_available else "unavailable",
                                     "scope_enabled_scenario": "modeled" if scopes_available else "not_evaluated"},
            "permission_definitions": permissions, "service_states": service_states,
            "role_bindings": [{"code": r[0], "role_id": r[1], "role": r[2], "role_active": bool(r[3]),
                               "binding_id": r[4], "binding_active": bool(r[5])} for r in data["role_bindings"]],
            "account_overrides": output_overrides,
            "override_counts": dict(Counter(f"{r['effect']}:{'active' if r['active'] else 'inactive'}" for r in output_overrides)),
            "existing_code_holders_potential": {c: sorted(v) for c, v in sorted(holders.items())},
            "required_deny_review": mirrors, "accounts": accounts,
            "limitations": ["Potential source-based impacts, not an effective-permission attestation.",
                            scope_limit,
                            "No broad account Grants copied; no provisioning, writes or record deletion performed.",
                            "Report and HMAC key are restricted owner evidence; do not commit either."]}


def verify_reduced_grants(grants):
    """Refuse a missing, additional, scoped differently, or grantable privilege."""
    grantee = f"TO `{REDUCED_READER}`@`{REDUCED_HOST}`"
    expected = {f"GRANT USAGE ON *.* {grantee}"}
    expected.update(f"GRANT SELECT ON `ctug_workspace`.`{table}` {grantee}" for table in REDUCED_TABLES)
    if len(grants) != len(expected) or set(grants) != expected:
        raise ValueError("Reduced reader grants must be USAGE and SELECT on exactly the seven approved tables.")


def read_snapshot(connection, *, without_role_scopes=False):
    with connection.cursor() as cursor:
        if without_role_scopes:
            cursor.execute(REDUCED_IDENTITY)
            schema, account, port, roles, mandatory = cursor.fetchone()
            if (schema, account, port, roles, mandatory) != (
                "ctug_workspace", f"{REDUCED_READER}@{REDUCED_HOST}", REDUCED_PORT, "NONE", ""
            ):
                raise ValueError("Reduced reader requires the approved account, local schema, and no inherited roles.")
            cursor.execute("SHOW GRANTS")  # Includes mandatory roles for the current user.
            verify_reduced_grants([row[0] for row in cursor.fetchall()])
        else:
            cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
            for (grant,) in cursor.fetchall():
                match = re.match(r"^GRANT (.+?) ON .+ TO .+$", grant)
                if not match or "WITH GRANT OPTION" in grant or set(match[1].split(", ")) - {"USAGE", "SELECT", "SHOW VIEW"}:
                    raise ValueError("Use an existing SELECT-only identity without roles, writes or GRANT OPTION.")
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        data = {}
        for name, query in QUERIES.items():
            if without_role_scopes and name == "scopes":
                data[name] = None  # Unavailable evidence is distinct from a successfully read empty table.
                continue
            if "%s" in query:
                count = query.count("%s") // len(CODES)
                cursor.execute(query, CODES * count)
            else:
                cursor.execute(query)
            data[name] = cursor.fetchall()
            if name == "identity" and (data[name][0][0] != "ctug_workspace" or not data[name][0][3]):
                raise ValueError("Wrong database or read-only transaction unavailable.")
            if name == "engines":
                tables = REDUCED_TABLES if without_role_scopes else REDUCED_TABLES | {"account_permission_role_scopes"}
                if {table for table, _ in data[name]} != tables or any(engine != "InnoDB" for _, engine in data[name]):
                    raise ValueError("Expected permission schema or consistent InnoDB storage unavailable.")
        return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorize-read-only", choices=[AUTHORIZATION])
    parser.add_argument("--without-role-scopes", action="store_true",
                        help="Use only the verified seven-table inventory reader. Report role scopes as unavailable.")
    args = parser.parse_args(argv)
    if not args.authorize_read_only:
        queries = {name: sql for name, sql in QUERIES.items() if not args.without_role_scopes or name != "scopes"}
        print(json.dumps({"status": "NOT_EXECUTED", "required_authorization": AUTHORIZATION,
                          "database": "ctug_workspace", "queries": queries}, indent=2))
        return 0
    # Do not import a driver, load application .env or open a socket before the explicit guard.
    import MySQLdb
    key = os.environ.get("WF11_INVENTORY_HMAC_KEY", "").encode("utf-8")
    if len(key) < 32:
        raise ValueError("An owner-held WF11_INVENTORY_HMAC_KEY of at least 32 bytes is required.")
    host = os.environ.get("WF11_INVENTORY_DB_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only an explicitly authorized local database host is supported.")
    port = int(os.environ.get("WF11_INVENTORY_DB_PORT", "3306"))
    user = os.environ["WF11_INVENTORY_DB_USER"]
    if args.without_role_scopes and (host, port, user) != (REDUCED_HOST, REDUCED_PORT, REDUCED_READER):
        raise ValueError("Use the dedicated reader on local TCP for the reduced inventory.")
    transport = {"ssl_mode": "REQUIRED"} if args.without_role_scopes else {}
    connection = MySQLdb.connect(host=host, port=port, user=user, passwd=os.environ["WF11_INVENTORY_DB_PASSWORD"],
                                db="ctug_workspace", charset="utf8mb4", connect_timeout=5, **transport)
    try:
        report = summarize(read_snapshot(connection, without_role_scopes=args.without_role_scopes), key)
        print(json.dumps(report, indent=2))
    finally:
        connection.rollback()
        connection.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Never echo credentials, connection strings, SQL errors or personal information.
        print(f"Inventory refused ({type(exc).__name__}); no report accepted.", file=sys.stderr)
        sys.exit(1)
