"""G1D-P3C4: read-only MySQL writer-scope metadata visibility inventory.

This module is only a release-blocking diagnostic, NOT a privileged writer fence.
Database source queries are all fixed, single-statement SELECT COUNT queries.
Only anonymized counts and visibility indicators are returned. No usernames,
keys, SQL grant strings, raw process rows, or other account details are emitted.
"""

from dataclasses import dataclass


class InventoryUnavailable(Exception):
    """The source was not independently visible; fail closed."""


@dataclass(frozen=True)
class CounterSource:
    key: str
    scope: str
    query: str


# MySQL 8.4 local development. Counting catalogue rows is NOT equivalent to
# effective-grants enumeration, and PROCESSLIST visibility is privilege limited.
SOURCES = (
    CounterSource("accounts_visible", "PRINCIPALS", "SELECT COUNT(*) FROM mysql.user"),
    CounterSource("global_writer_account_rows", "PRINCIPALS", (
        "SELECT COUNT(*) FROM mysql.user WHERE Insert_priv='Y' OR Update_priv='Y' "
        "OR Delete_priv='Y' OR Create_priv='Y' OR Drop_priv='Y' OR Alter_priv='Y' "
        "OR Grant_priv='Y' OR Super_priv='Y' OR Create_user_priv='Y'"
    )),
    CounterSource("global_dynamic_grant_rows", "GRANTS", "SELECT COUNT(*) FROM mysql.global_grants"),
    CounterSource("database_grant_rows", "GRANTS", "SELECT COUNT(*) FROM mysql.db"),
    CounterSource("table_grant_rows", "GRANTS", "SELECT COUNT(*) FROM mysql.tables_priv"),
    CounterSource("column_grant_rows", "GRANTS", "SELECT COUNT(*) FROM mysql.columns_priv"),
    CounterSource("routine_grant_rows", "GRANTS", "SELECT COUNT(*) FROM mysql.procs_priv"),
    CounterSource("role_assignment_rows", "ROLES", "SELECT COUNT(*) FROM mysql.role_edges"),
    CounterSource("default_role_rows", "ROLES", "SELECT COUNT(*) FROM mysql.default_roles"),
    CounterSource("visible_session_rows", "SESSIONS", "SELECT COUNT(*) FROM information_schema.PROCESSLIST"),
    CounterSource("visible_workspace_routines", "DEFINERS", (
        "SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = 'ctug_workspace'"
    )),
    CounterSource("visible_workspace_triggers", "DEFINERS", (
        "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = 'ctug_workspace'"
    )),
    CounterSource("visible_workspace_events", "DEFINERS", (
        "SELECT COUNT(*) FROM information_schema.EVENTS WHERE EVENT_SCHEMA = 'ctug_workspace'"
    )),
)


SCOPES = frozenset({"PRINCIPALS", "GRANTS", "ROLES", "SESSIONS", "DEFINERS"})


def summarize_observations(fetch_count):
    """Fail-closed aggregate. Even complete DBA SELECT visibility != fencing.

    fetch_count receives an internally defined SELECT only, returns an int,
    or raises InventoryUnavailable for insufficient metadata privileges.
    Neither the SQL nor backend errors enter the output.
    """
    if not callable(fetch_count):
        raise TypeError("A read-only count reader is required")
    observations = {}
    for source in SOURCES:
        try:
            count = fetch_count(source.query)
        except InventoryUnavailable:
            observations[source.key] = {"scope": source.scope, "status": "UNAVAILABLE"}
            continue
        if type(count) is not int or count < 0 or count > 2**63 - 1:
            observations[source.key] = {"scope": source.scope, "status": "INVALID"}
            continue
        observations[source.key] = {
            "scope": source.scope, "status": "OBSERVED", "count": count,
        }

    unavailable = sorted(key for key, value in observations.items() if value["status"] != "OBSERVED")
    exposed = observations["global_writer_account_rows"]
    risk = (
        "VISIBLE_GLOBAL_WRITER_CAPABILITY"
        if exposed["status"] == "OBSERVED" and exposed["count"] > 0
        else "INCOMPLETE_METADATA_VISIBILITY"
        if unavailable else "GLOBAL_WRITER_ABSENCE_NOT_ESTABLISHED"
    )
    coverage = {
        scope: {
            "observed": sum(1 for v in observations.values() if v["scope"] == scope and v["status"] == "OBSERVED"),
            "expected": sum(1 for s in SOURCES if s.scope == scope),
        }
        for scope in sorted(SCOPES)
    }
    return {
        "checkpoint": "G1D-P3C4-DBA-METADATA-VISIBILITY-ONLY",
        "release_status": "BLOCKED",
        "writer_fence_verified": False,
        "triage": risk,
        "source_coverage": coverage,
        "unavailable_source_keys": unavailable,
        "aggregates": observations,
        "limitations": [
            "MySQL metadata visibility may be incomplete even when a query succeeds",
            "Visible global grants omit effective role, schema, table, routine and external process rights",
            "Session counts are a point-in-time partial view, not session draining or admission control",
            "No credentials, privileges, connections, roles, database schema, or official ERD are modified",
            "An independent DBA must enumerate and attest all writers and enforce a real fence",
            "This report never authorizes migrations, --apply, protected role creation or bootstrap",
        ],
    }
