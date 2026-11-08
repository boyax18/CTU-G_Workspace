"""C2A local integrity evidence. Reads only; never repairs or drops databases.

Run from backend: .venv/Scripts/python.exe -B scripts/verify_catalogue_plan.py
Only the intended loopback ctug_workspace development target is accepted.
"""

from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from apps.access_control.catalogue.planner import readonly_snapshot  # noqa: E402

EXPECTED_ERDS = {
    "docs/database/full_schema.dbml": "e9235a87555ffcd50ecb6ab6c1a45f9c7c54e344ff8f269ecc890579f633e4b2",
    "docs/database/schema.dbml": "f050f7b910038532ca8e73b283f16a57dedd6b738fdc74d293e64d539a4afac4",
}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def snapshot():
    metadata = []
    tables, counts, row_digests = [], {}, {}
    with readonly_snapshot():
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE(), VERSION()")
            database, version = cursor.fetchone()
            if database != "ctug_workspace":
                raise RuntimeError("Unexpected connected database; stopping read-only verification.")
            queries = (
                "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME",
                "SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, CHARACTER_SET_NAME, COLLATION_NAME, GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION",
                "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART, INDEX_TYPE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX",
                "SELECT TABLE_NAME, CONSTRAINT_NAME, COLUMN_NAME, ORDINAL_POSITION, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION",
                "SELECT TABLE_NAME, CONSTRAINT_NAME, UNIQUE_CONSTRAINT_NAME, MATCH_OPTION, UPDATE_RULE, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() ORDER BY TABLE_NAME, CONSTRAINT_NAME",
                "SELECT CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() ORDER BY CONSTRAINT_NAME",
            )
            for query in queries:
                cursor.execute(query)
                metadata.append(cursor.fetchall())
            tables = [row[0] for row in metadata[0]]
            for table in tables:
                # Names originate only in the current MySQL schema and are quoted.
                cursor.execute("SELECT * FROM " + connection.ops.quote_name(table))
                rows = cursor.fetchall()
                counts[table] = len(rows)
                row_digests[table] = digest(sorted(json.dumps(row, default=str, separators=(",", ":")) for row in rows))
            cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY app, name")
            migrations = cursor.fetchall()
            cursor.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME")
            disposable = [row[0] for row in cursor.fetchall() if re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", row[0])]
    return dict(database=database, mysql_version=version, table_count=len(tables), counts=counts,
        row_digests=row_digests, all_data_sha256=digest(row_digests), schema_sha256=digest(metadata),
        migration_count=len(migrations), migrations_sha256=digest(migrations), disposable_databases=disposable)


def verify():
    config = settings.DATABASES["default"]
    if (config["ENGINE"] != "django.db.backends.mysql" or config["NAME"] != "ctug_workspace"
            or config["HOST"] not in {"127.0.0.1", "localhost", "::1"} or str(config["PORT"]) != "3306"):
        raise RuntimeError("Verifier accepts only the intended local development target.")
    erds_before = {name: sha256((BACKEND.parent / name).read_bytes()).hexdigest() for name in EXPECTED_ERDS}
    if erds_before != EXPECTED_ERDS:
        raise RuntimeError("Protected ERD fingerprint mismatch.")
    before = snapshot()
    outputs = []
    with CaptureQueriesContext(connection) as queries:
        for _ in range(2):
            out = StringIO()
            call_command("plan_permission_catalogue", format="json", stdout=out)
            outputs.append(json.loads(out.getvalue()))
    after = snapshot()
    erds_after = {name: sha256((BACKEND.parent / name).read_bytes()).hexdigest() for name in EXPECTED_ERDS}
    if before != after or erds_before != erds_after or outputs[0] != outputs[1]:
        raise RuntimeError("Integrity/replay comparison failed; investigate without automatic repair.")
    if any(not re.match(r"\A(?:SELECT|SET TRANSACTION|START TRANSACTION|ROLLBACK)\b", q["sql"]) for q in queries.captured_queries):
        raise RuntimeError("Unexpected planner statement category.")
    report = outputs[0]
    print(json.dumps(dict(integrity="PASS", before=before, after=after,
        protected_erd_sha256=erds_after, manifest=report["manifest"], proposed=report["proposed"],
        planner_totals=report["totals"], existing_roles=report["existing_roles"],
        technical_role=next(r for r in report["records"] if r["kind"] == "role" and r["key"] == "Technical Super Admin"),
        unexpected_records=len(report["unexpected"]), override_groups=len(report["account_override_review"]),
        open_decisions=[d["id"] for d in report["pending_decisions"]], repeated_reports_identical=True,
        planner_statement_count=len(queries.captured_queries), database_modifications=0), indent=2))


if __name__ == "__main__":
    try:
        verify()
    finally:
        connection.close()
