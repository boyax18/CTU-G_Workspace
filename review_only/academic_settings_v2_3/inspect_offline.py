"""Prove migration graph/model and feature registry facts with ALL DB connections forbidden."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

from run_isolated_tests import ROOT, test_environment

TARGETS = (
    ("academic", "0001_initial"), ("academic", "0002_audit_reason_note"),
    ("academic", "0003_academic_configuration"), ("finance", "0001_semester_fee_configuration"),
    ("academic", "0004_student_semester_onboarding"), ("clearance", "0001_semester_clearance"),
    ("finance", "0002_fee_obligation"),
)


def inspect():
    test_environment()
    from django.db.backends.base.base import BaseDatabaseWrapper
    with patch.object(BaseDatabaseWrapper, "ensure_connection", side_effect=AssertionError("Offline inspection forbids every database connection")):
        import django
        django.setup()
        from django.apps import apps
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.state import ProjectState
        from config.dev_features import FEATURES
        loader = MigrationLoader(None)
        closure = set()
        for target in TARGETS:
            closure.update(loader.graph.forwards_plan(target))
        drift = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps)).changes(graph=loader.graph)
        if drift:
            raise ValueError("Model/migration drift requires review: " + ",".join(sorted(drift)))
        order = list(dict.fromkeys(node for target in TARGETS for node in loader.graph.forwards_plan(target)))
        graph = [{"migration": ".".join(node),
                  "parents": sorted(".".join(p.key) for p in loader.graph.node_map[node].parents)} for node in order]
        schema = []
        for model in loader.project_state().apps.get_models():
            if model._meta.app_label not in {"academic", "clearance", "finance"}:
                continue
            schema.append({"table": model._meta.db_table,
                           "columns": [{"field": f.name, "column": f.column, "type": f.get_internal_type(), "null": f.null,
                                        "primary_key": f.primary_key, "unique": f.unique,
                                        "max_length": f.max_length, "max_digits": getattr(f, "max_digits", None),
                                        "decimal_places": getattr(f, "decimal_places", None),
                                        "choices": list(f.flatchoices) if f.choices else [],
                                        "foreign_key": (f.remote_field.model._meta.db_table + "." + f.target_field.column)
                                        if f.is_relation and f.remote_field else None}
                                       for f in model._meta.local_fields],
                           "constraints": [{"name": c.name, "kind": type(c).__name__,
                                            "fields": list(getattr(c, "fields", ())),
                                            "condition": str(getattr(c, "condition", ""))}
                                           for c in model._meta.constraints]})
        features = [{"key": f.key, "backend_env": f.backend_env, "frontend_flags": f.frontend_flags,
                     "registry_dependencies": f.requires, "approved_modes": sorted(f.modes)}
                    for f in FEATURES if f.key.startswith(("wf11.", "wf05."))]
        if any(f["approved_modes"] for f in features):
            raise ValueError("An Academic Settings launcher mode was activated; review required.")
        return {"status": "OFFLINE_NO_DATABASE_CONNECTION", "model_drift": False,
                "valid_topological_order": [".".join(n) for n in order], "complete_dependency_graph": graph,
                "expected_schema": sorted(schema, key=lambda r: r["table"]), "feature_registry": features}


def integrity_sql(evidence):
    lines = ["-- PREPARED ONLY. Execute only under a separate schema/data-inspection authorization.",
             "-- Select ctug_workspace explicitly in the client; verify the identity before continuing.",
             "SELECT DATABASE() AS expected_ctug_workspace, VERSION() AS server_version;",
             "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;",
             "SET SESSION TRANSACTION READ ONLY;",
             "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;",
             "SELECT app,name,COUNT(*) AS ledger_rows FROM django_migrations WHERE app IN ('academic','clearance','finance') GROUP BY app,name ORDER BY app,name;"]
    for table in evidence["expected_schema"]:
        name = table["table"]
        lines += [f"SHOW CREATE TABLE `{name}`;", f"SELECT '{name}' AS table_name,COUNT(*) AS row_count FROM `{name}`;"]
        for column in table["columns"]:
            field = column["column"]
            if column["foreign_key"]:
                parent, key = column["foreign_key"].split(".")
                lines.append(f"SELECT '{name}.{field}' AS foreign_key_check,COUNT(*) AS orphan_count FROM `{name}` t LEFT JOIN `{parent}` p ON t.`{field}`=p.`{key}` WHERE t.`{field}` IS NOT NULL AND p.`{key}` IS NULL;")
        # Every explicit UNIQUE constraint (including nullable lifecycle slots). MySQL permits
        # repeated NULL slots; only all-non-NULL keys should participate in duplicate detection.
        columns = {c["column"] for c in table["columns"]}
        for constraint in table["constraints"]:
            if constraint["kind"] != "UniqueConstraint":
                continue
            by_field = {c["field"]: c["column"] for c in table["columns"]}
            fields = [by_field[f] for f in constraint["fields"]]
            if not fields or not set(fields) <= columns:
                raise ValueError("Unsupported constraint field mapping; inspect before preparing SQL.")
            group = ",".join(f"`{f}`" for f in fields)
            present = " AND ".join(f"`{f}` IS NOT NULL" for f in fields)
            lines.append(f"SELECT '{constraint['name']}' AS uniqueness_check,COUNT(*) AS duplicate_groups FROM (SELECT {group} FROM `{name}` WHERE {present} GROUP BY {group} HAVING COUNT(*)>1) duplicates;")
    lines.extend([
        "SELECT 'atomic_participation_bundle' AS integrity_check,COUNT(*) AS violation_count FROM academic_semester_participations p LEFT JOIN clearance_semester_clearances c ON c.participation_id=p.participation_id LEFT JOIN finance_fee_obligations o ON o.participation_id=p.participation_id WHERE c.clearance_id IS NULL OR o.obligation_id IS NULL OR c.student_account_id<>p.student_account_id OR c.semester_id<>p.semester_id OR o.student_account_id<>p.student_account_id OR o.semester_id<>p.semester_id;",
        "SELECT 'completed_onboarding' AS integrity_check,COUNT(*) AS violation_count FROM academic_semester_onboardings b LEFT JOIN academic_semester_participations p ON p.onboarding_id=b.onboarding_id WHERE b.status='Completed' AND (p.participation_id IS NULL OR p.student_account_id<>b.student_account_id OR p.semester_id<>b.semester_id);",
        "SELECT 'fee_snapshot' AS integrity_check,COUNT(*) AS violation_count FROM finance_fee_obligations o JOIN finance_semester_fee_revisions r ON r.revision_id=o.fee_revision_id JOIN finance_semester_fee_schedules s ON s.schedule_id=r.schedule_id WHERE o.amount<>r.amount OR o.currency<>r.currency OR o.semester_id<>s.semester_id;",
        "SELECT 'subject_signatory' AS integrity_check,COUNT(*) AS violation_count FROM clearance_requirements r JOIN clearance_semester_clearances c ON c.clearance_id=r.clearance_id LEFT JOIN academic_participation_subjects p ON p.participation_id=c.participation_id AND p.subject_id=r.subject_id AND p.offering_id=r.offering_id WHERE r.kind='subject_instructor' AND (p.id IS NULL OR p.instructor_account_id<>r.signatory_account_id OR c.student_account_id=r.signatory_account_id);",
        "SELECT 'requirement_count' AS integrity_check,COUNT(*) AS violation_count FROM clearance_semester_clearances c WHERE (SELECT COUNT(*) FROM clearance_requirements r WHERE r.clearance_id=c.clearance_id)<>(SELECT COUNT(*)+2 FROM academic_participation_subjects p WHERE p.participation_id=c.participation_id);",
        "ROLLBACK;",
    ])
    return "\n\n".join(lines) + "\n"


if __name__ == "__main__":
    result = inspect()
    if sys.argv[1:] == ["--write"]:
        here = Path(__file__).resolve().parent
        (here / "offline_repository_evidence.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        (here / "schema_and_integrity_checks.sql").write_text(integrity_sql(result), encoding="utf-8", newline="\n")
        print("Prepared graph, expected schema and read-only validation SQL; no database connection.")
    else:
        print(json.dumps(result, indent=2))
