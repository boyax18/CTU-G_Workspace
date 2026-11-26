"""Execute the PREPARED validation SQL only on the runner's disposable MySQL schema."""
import json
from pathlib import Path
import re

from django.db import connection
from django.test import TransactionTestCase

HERE = Path(__file__).resolve().parent


class PreparedSchemaValidationTests(TransactionTestCase):
    def test_inventory_query_syntax_on_disposable_schema_only(self):
        import permission_inventory as inventory
        self.assertRegex(connection.settings_dict["NAME"], r"^test_ctug_registration_[0-9a-f]{16}$")
        with connection.cursor() as cursor:
            for query in inventory.QUERIES.values():
                self.assertTrue(query.startswith("SELECT "))
                count = query.count("%s") // len(inventory.CODES)
                cursor.execute(query, inventory.CODES * count if count else None)
                cursor.fetchall()

    def test_full_schema_and_read_only_validation_sql(self):
        self.assertRegex(connection.settings_dict["NAME"], r"^test_ctug_registration_[0-9a-f]{16}$")
        evidence = json.loads((HERE / "offline_repository_evidence.json").read_text(encoding="utf-8"))
        sql = (HERE / "schema_and_integrity_checks.sql").read_text(encoding="utf-8")
        sql = "\n".join(line for line in sql.splitlines() if not line.startswith("--"))
        with connection.cursor() as cursor:
            try:
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if not statement:
                        continue
                    self.assertTrue(statement.startswith(("SELECT ", "SHOW CREATE TABLE ", "SET SESSION TRANSACTION ", "START TRANSACTION ", "ROLLBACK")))
                    cursor.execute(statement)
                    if cursor.description:
                        names = [c[0] for c in cursor.description]
                        rows = cursor.fetchall()
                        if any(c in names for c in ("violation_count", "orphan_count", "duplicate_groups")):
                            self.assertTrue(all(row[-1] == 0 for row in rows), statement)
                for table in evidence["expected_schema"]:
                    columns = connection.introspection.get_table_description(cursor, table["table"])
                    self.assertEqual({c.name for c in columns}, {c["column"] for c in table["columns"]}, table["table"])
                    constraints = connection.introspection.get_constraints(cursor, table["table"])
                    self.assertTrue({c["name"] for c in table["constraints"]} <= set(constraints), table["table"])
                cursor.execute("SELECT DATABASE()")
                self.assertTrue(re.fullmatch(r"test_ctug_registration_[0-9a-f]{16}", cursor.fetchone()[0]))
            finally:
                connection.rollback()
                cursor.execute("SET SESSION TRANSACTION READ WRITE")
