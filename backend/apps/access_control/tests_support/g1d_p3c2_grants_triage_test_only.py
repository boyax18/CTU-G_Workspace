"""G1D-P3C2: read-only, fail-closed SHOW GRANTS triage. TEST/REPORT ONLY.

Never treat a parsed grant as a full MySQL privilege audit or database fence.
Effective enabled roles, dynamic privilege aliases, DEFINER routines, external
principals and DBA capability are outside this single-session visibility.
No source here issues GRANT, REVOKE, CREATE USER, FLUSH, DDL, or data writes.
"""

from dataclasses import dataclass
import re


GRANT_ROW = re.compile(
    r"^GRANT\s+(?P<privileges>.*?)\s+ON\s+(?P<scope>.*?)\s+TO\s+(?P<principal>.*)$",
    re.IGNORECASE | re.DOTALL,
)
SAFE_OBSERVED_PRIVILEGES = frozenset({"USAGE", "SELECT", "SHOW VIEW"})
PRIVILEGED_OPERATIONS = frozenset({
    "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "INDEX",
    "REFERENCES", "TRIGGER", "EVENT", "EXECUTE", "LOCK TABLES",
    "CREATE ROUTINE", "ALTER ROUTINE", "CREATE TEMPORARY TABLES",
    "CREATE VIEW", "CREATE USER", "CREATE ROLE", "DROP ROLE",
    "GRANT OPTION", "PROXY", "FILE", "SUPER", "RELOAD", "SHUTDOWN",
    "SYSTEM_USER", "SYSTEM_VARIABLES_ADMIN", "SESSION_VARIABLES_ADMIN",
    "ROLE_ADMIN", "SET_USER_ID", "CONNECTION_ADMIN", "BACKUP_ADMIN",
    "BINLOG_ADMIN", "PERSIST_RO_VARIABLES_ADMIN", "SERVICE_CONNECTION_ADMIN",
    "AUTHENTICATION_POLICY_ADMIN", "FLUSH_PRIVILEGES", "APPLICATION_PASSWORD_ADMIN",
})


@dataclass(frozen=True)
class GrantObservation:
    classification: str
    scope: str
    privilege_names: tuple[str, ...]


def inspect_grant_line(value):
    """Return only names/scope/classification; never echo principal identifiers."""
    if type(value) is not str or not value.strip() or len(value) > 32_768:
        return GrantObservation("UNKNOWN", "UNKNOWN", ())
    line = value.strip()
    if any(ord(character) < 32 or ord(character) > 126 for character in line):
        return GrantObservation("UNKNOWN", "UNKNOWN", ())
    match = GRANT_ROW.fullmatch(line)
    if match is None:
        # A GRANT of roles has no ON, and the role may elevate the login.
        return GrantObservation("UNKNOWN_OR_ROLE", "UNKNOWN", ())
    raw_scope = match.group("scope").strip()
    raw_privileges = match.group("privileges").strip().upper()
    principal_clause = match.group("principal").strip().upper()
    if not raw_scope or not raw_privileges or not principal_clause:
        return GrantObservation("UNKNOWN", "UNKNOWN", ())
    # Parsing column-level grants, role grants, trailing clauses or unusual
    # SQL identifiers cannot be relied on as proof of least privilege.
    if "(" in raw_privileges or ")" in raw_privileges:
        return GrantObservation("UNKNOWN", "REDACTED", ())
    names = tuple(s.strip() for s in raw_privileges.split(","))
    if not names or any(not s or not re.fullmatch(r"[A-Z][A-Z0-9_ ]*", s) for s in names):
        return GrantObservation("UNKNOWN", "REDACTED", ())
    if any(s in {"ALL", "ALL PRIVILEGES"} for s in names):
        category = "PRIVILEGED_WRITE_OR_CONTROL"
    elif any(s in PRIVILEGED_OPERATIONS for s in names):
        category = "PRIVILEGED_WRITE_OR_CONTROL"
    elif not all(s in SAFE_OBSERVED_PRIVILEGES for s in names):
        category = "UNKNOWN_PRIVILEGE"
    else:
        category = "OBSERVED_READ_ONLY_KEYWORDS"
    if re.search(r"\bWITH\s+GRANT\s+OPTION\b", principal_clause):
        category = "PRIVILEGED_WRITE_OR_CONTROL"
    if "IDENTIFIED" in principal_clause or "WITH ADMIN OPTION" in principal_clause:
        category = "UNKNOWN"  # Do not print or parse trailing secret-bearing syntax.

    # Keep output scopes coarse; never expose full account or custom schema names.
    if raw_scope == "*.*":
        scope = "GLOBAL"
    elif raw_scope.lower() in {"`ctug_workspace`.*", "ctug_workspace.*"}:
        scope = "WORKSPACE_SCHEMA"
    elif re.fullmatch(r"`?ctug_workspace`?\.`?[A-Za-z_][A-Za-z0-9_]*`?", raw_scope, re.I):
        scope = "WORKSPACE_TABLE"
    else:
        scope = "OTHER_OR_UNRECOGNIZED"
        if category == "OBSERVED_READ_ONLY_KEYWORDS":
            category = "UNKNOWN_SCOPE"
    return GrantObservation(category, scope, tuple(names))


def summarize_grants(rows):
    """Triage a single CURRENT_USER grant result; deliberately BLOCKED always.

    Never returns principal strings, grant SQL, hashes of secrets or access
    credentials. Positive-looking results are not a writer fence.
    """
    if type(rows) not in (tuple, list) or not rows or len(rows) > 1_000:
        return {"checkpoint": "G1D-P3C2-ONE-PRINCIPAL-ONLY",
                "release_status": "BLOCKED", "triage": "MISSING_OR_INVALID_INPUT",
                "grant_rows": 0, "classifications": {}}
    observations = [inspect_grant_line(row) for row in rows]
    counts = {}
    for record in observations:
        counts[record.classification] = counts.get(record.classification, 0) + 1
    if any(o.classification == "PRIVILEGED_WRITE_OR_CONTROL" for o in observations):
        triage = "OBSERVED_PRIVILEGED_CAPABILITY"
    elif any(o.classification != "OBSERVED_READ_ONLY_KEYWORDS" for o in observations):
        triage = "UNKNOWN_EFFECTIVE_GRANTS"
    else:
        triage = "NO_WRITES_OBSERVED_BUT_UNVERIFIED"
    return {
        "checkpoint": "G1D-P3C2-ONE-PRINCIPAL-ONLY",
        "release_status": "BLOCKED",
        "triage": triage,
        "grant_rows": len(observations),
        "classifications": dict(sorted(counts.items())),
        "scope_counts": {
            scope: sum(o.scope == scope for o in observations)
            for scope in sorted({o.scope for o in observations})
        },
        "limitations": [
            "SHOW GRANTS for one connected account is not an inventory of other database users or active sessions",
            "Role grants, DEFINER routines, dynamic privileges, external writers and MySQL administrators require independent DBA review",
            "This command does not restrict privileges, close sessions, or establish a protected writer fence",
            "No output from this triage permits Technical Super Admin role creation or --apply",
        ],
    }
