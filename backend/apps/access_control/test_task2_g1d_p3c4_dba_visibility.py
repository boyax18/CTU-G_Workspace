"""G1D-P3C4 read-only DBA visibility contract tests; offline and deterministic."""

import ast
from pathlib import Path
from unittest import TestCase

from apps.access_control.tests_support.g1d_p3c4_dba_visibility_test_only import (
    SOURCES, SCOPES, InventoryUnavailable, summarize_observations,
)


class DBAVisibilityContracts(TestCase):
    def report(self, overrides=None):
        overrides = overrides or {}
        return summarize_observations(lambda sql: overrides.get(sql, 0))

    def test_fixed_query_inventory_nonempty(self):
        self.assertGreaterEqual(len(SOURCES), 10)

    def test_query_keys_unique(self):
        self.assertEqual(len({source.key for source in SOURCES}), len(SOURCES))

    def test_query_strings_unique(self):
        self.assertEqual(len({source.query for source in SOURCES}), len(SOURCES))

    def test_all_queries_are_select_only(self):
        for source in SOURCES:
            self.assertTrue(source.query.startswith("SELECT COUNT(*) FROM "))
            self.assertNotIn(";", source.query)

    def test_no_literal_multi_statement_delimiter(self):
        for source in SOURCES:
            self.assertNotIn("--", source.query)
            self.assertNotIn("/*", source.query)

    def test_scopes_exact(self):
        self.assertEqual({source.scope for source in SOURCES}, SCOPES)

    def test_no_external_query_parameters(self):
        self.assertFalse(any("{" in source.query or "%" in source.query for source in SOURCES))

    def test_complete_zero_counts_remain_blocked(self):
        report = self.report()
        self.assertEqual(report["release_status"], "BLOCKED")
        self.assertFalse(report["writer_fence_verified"])

    def test_no_visible_globals_still_unproven(self):
        self.assertEqual(self.report()["triage"], "GLOBAL_WRITER_ABSENCE_NOT_ESTABLISHED")

    def test_visible_global_writers_trigger_triage(self):
        q = next(s.query for s in SOURCES if s.key == "global_writer_account_rows")
        self.assertEqual(self.report({q: 2})["triage"], "VISIBLE_GLOBAL_WRITER_CAPABILITY")

    def test_missing_source_is_explicit(self):
        def read(sql):
            raise InventoryUnavailable()
        report = summarize_observations(read)
        self.assertEqual(len(report["unavailable_source_keys"]), len(SOURCES))
        self.assertEqual(report["release_status"], "BLOCKED")

    def test_missing_source_coverage_is_zero(self):
        report = summarize_observations(lambda sql: (_ for _ in ()).throw(InventoryUnavailable()))
        self.assertTrue(all(x["observed"] == 0 for x in report["source_coverage"].values()))

    def test_invalid_negative_count_is_not_observed(self):
        report = summarize_observations(lambda sql: -1)
        self.assertTrue(all(v["status"] == "INVALID" for v in report["aggregates"].values()))

    def test_invalid_noninteger_count_is_not_observed(self):
        report = summarize_observations(lambda sql: "3")
        self.assertTrue(all(v["status"] == "INVALID" for v in report["aggregates"].values()))

    def test_boolean_count_is_not_accepted_as_integer(self):
        report = summarize_observations(lambda sql: True)
        self.assertTrue(all(v["status"] == "INVALID" for v in report["aggregates"].values()))

    def test_huge_count_is_not_accepted(self):
        report = summarize_observations(lambda sql: 2**64)
        self.assertTrue(all(v["status"] == "INVALID" for v in report["aggregates"].values()))

    def test_no_fetcher_refused(self):
        with self.assertRaises(TypeError):
            summarize_observations(None)

    def test_zero_count_is_exactly_preserved(self):
        self.assertTrue(all(v["count"] == 0 for v in self.report()["aggregates"].values()))

    def test_permission_denial_is_not_disclosed(self):
        marker = "PRIVATE_USER_credential_please_do_not_log"
        def read(sql):
            try:
                raise RuntimeError(marker)
            except RuntimeError:
                raise InventoryUnavailable()
        report = summarize_observations(read)
        self.assertNotIn(marker, str(report))

    def test_report_never_returns_sql_text(self):
        report = self.report()
        self.assertNotIn("SELECT COUNT(*)", str(report))

    def test_report_never_prints_raw_grant_sql(self):
        report = self.report()
        self.assertNotIn("GRANT INSERT", str(report))

    def test_every_expected_source_is_reported(self):
        self.assertEqual({s.key for s in SOURCES}, set(self.report()["aggregates"]))

    def test_coverage_sums_correctly(self):
        report = self.report()
        self.assertEqual(sum(x["observed"] for x in report["source_coverage"].values()), len(SOURCES))

    def test_multi_principal_visibility_is_not_attestation(self):
        counts = {s.query: 300 for s in SOURCES}
        self.assertEqual(self.report(counts)["release_status"], "BLOCKED")

    def test_point_in_time_session_count_not_fence(self):
        q = next(s.query for s in SOURCES if s.key == "visible_session_rows")
        self.assertFalse(self.report({q: 1})["writer_fence_verified"])

    def test_role_edges_do_not_prove_privilege(self):
        q = next(s.query for s in SOURCES if s.key == "role_assignment_rows")
        self.assertEqual(self.report({q: 20})["release_status"], "BLOCKED")

    def test_partial_metadata_not_upgraded(self):
        def partial(sql):
            if "mysql.user" in sql:
                raise InventoryUnavailable()
            return 0
        report = summarize_observations(partial)
        self.assertEqual(report["triage"], "INCOMPLETE_METADATA_VISIBILITY")

    def test_global_writer_count_positive_with_other_missing_remains_risk(self):
        q = next(s.query for s in SOURCES if s.key == "global_writer_account_rows")
        def partial(sql):
            if sql == q:
                return 1
            raise InventoryUnavailable()
        self.assertEqual(summarize_observations(partial)["triage"], "VISIBLE_GLOBAL_WRITER_CAPABILITY")

    def test_report_limitations_mention_independent_dba(self):
        self.assertTrue(any("independent DBA" in x for x in self.report()["limitations"]))

    def test_command_has_no_db_mutation_sql_literals(self):
        # Check the local source AST literals, not a substitute for code review.
        command_path = Path(__file__).parent / "management" / "commands" / "report_g1d_p3c4_dba_visibility.py"
        tree = ast.parse(command_path.read_text(encoding="utf-8"))
        sql_strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertIn("SELECT DATABASE()", sql_strings)
        self.assertNotIn("DELETE FROM", sql_strings)
        self.assertNotIn("GRANT ALL", sql_strings)

    def test_outputs_are_json_serializable(self):
        import json
        json.dumps(self.report())

    def test_deprecated_processlist_not_treated_as_complete(self):
        q = next(s.query for s in SOURCES if s.key == "visible_session_rows")
        self.assertTrue(q.endswith("information_schema.PROCESSLIST"))
        self.assertFalse(self.report()["writer_fence_verified"])
