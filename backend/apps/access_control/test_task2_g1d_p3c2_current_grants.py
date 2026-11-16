"""Offline pure-unit tests; no Django settings, connection or MySQL needed."""

from unittest import TestCase

from apps.access_control.tests_support.g1d_p3c2_grants_triage_test_only import (
    inspect_grant_line, summarize_grants,
)


class GrantInspectorContractTests(TestCase):
    PRINCIPAL = "'workspace_service'@'localhost'"

    def obs(self, privilege, object_name="`ctug_workspace`.*", extra=""):
        return inspect_grant_line(f"GRANT {privilege} ON {object_name} TO {self.PRINCIPAL}{extra}")

    def test_usage_is_only_observed_nonwriter(self):
        self.assertEqual(self.obs("USAGE", "*.*").classification, "OBSERVED_READ_ONLY_KEYWORDS")

    def test_select_is_only_observed_nonwriter(self):
        self.assertEqual(self.obs("SELECT").classification, "OBSERVED_READ_ONLY_KEYWORDS")

    def test_show_view_observed_nonwriter(self):
        self.assertEqual(self.obs("SHOW VIEW").classification, "OBSERVED_READ_ONLY_KEYWORDS")

    def test_mixed_select_and_insert_is_privileged(self):
        self.assertEqual(self.obs("SELECT, INSERT").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_update_is_privileged(self):
        self.assertEqual(self.obs("UPDATE").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_delete_is_privileged(self):
        self.assertEqual(self.obs("DELETE").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_all_privileges_is_privileged(self):
        self.assertEqual(self.obs("ALL PRIVILEGES", "*.*").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_create_role_is_privileged(self):
        self.assertEqual(self.obs("CREATE ROLE", "*.*").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_system_user_is_privileged(self):
        self.assertEqual(self.obs("SYSTEM_USER", "*.*").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_execute_is_privileged_due_to_definer_routines(self):
        self.assertEqual(self.obs("EXECUTE").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_grant_option_is_privileged(self):
        self.assertEqual(self.obs("SELECT", extra=" WITH GRANT OPTION").classification, "PRIVILEGED_WRITE_OR_CONTROL")

    def test_roles_without_on_are_unknown(self):
        line = "GRANT `powerful_role`@`%` TO 'user'@'localhost'"
        self.assertEqual(inspect_grant_line(line).classification, "UNKNOWN_OR_ROLE")

    def test_unrecognized_grant_is_unknown(self):
        self.assertEqual(inspect_grant_line("GRANT MAGIC ON *.* TO 'user'@'localhost'").classification, "UNKNOWN_PRIVILEGE")

    def test_newline_is_unknown(self):
        self.assertEqual(inspect_grant_line("GRANT SELECT ON *.* TO 'x'@'localhost'\nDROP TABLE roles").classification, "UNKNOWN")

    def test_excessive_length_is_unknown(self):
        self.assertEqual(inspect_grant_line("A" * 32769).classification, "UNKNOWN")

    def test_nonstring_input_is_unknown(self):
        self.assertEqual(inspect_grant_line(None).classification, "UNKNOWN")

    def test_empty_input_is_unknown(self):
        self.assertEqual(inspect_grant_line(" ").classification, "UNKNOWN")

    def test_unknown_scope_is_unknown(self):
        self.assertEqual(self.obs("SELECT", "other_database.*").classification, "UNKNOWN_SCOPE")

    def test_column_scoped_grant_is_unknown(self):
        self.assertEqual(self.obs("SELECT (school_id)").classification, "UNKNOWN")

    def test_schema_scope_is_redacted(self):
        self.assertEqual(self.obs("SELECT").scope, "WORKSPACE_SCHEMA")

    def test_table_scope_is_redacted(self):
        self.assertEqual(self.obs("SELECT", "`ctug_workspace`.`roles`").scope, "WORKSPACE_TABLE")

    def test_unusual_identified_clause_is_not_echoed(self):
        record = inspect_grant_line("GRANT SELECT ON *.* TO 'user'@'host' IDENTIFIED BY 'secret123'")
        self.assertEqual(record.classification, "UNKNOWN")
        self.assertNotIn("secret", repr(record))

    def test_privileged_report_always_blocked(self):
        report = summarize_grants(["GRANT UPDATE ON `ctug_workspace`.* TO 'user'@'localhost'"])
        self.assertEqual(report["release_status"], "BLOCKED")
        self.assertEqual(report["triage"], "OBSERVED_PRIVILEGED_CAPABILITY")

    def test_read_only_looking_report_still_blocked(self):
        report = summarize_grants(["GRANT SELECT ON `ctug_workspace`.* TO 'user'@'localhost'"])
        self.assertEqual(report["release_status"], "BLOCKED")
        self.assertEqual(report["triage"], "NO_WRITES_OBSERVED_BUT_UNVERIFIED")

    def test_roles_unknown_report_still_blocked(self):
        report = summarize_grants(["GRANT `admin_role`@`%` TO 'user'@'localhost'"])
        self.assertEqual(report["triage"], "UNKNOWN_EFFECTIVE_GRANTS")

    def test_empty_grants_fail_closed(self):
        self.assertEqual(summarize_grants([])["triage"], "MISSING_OR_INVALID_INPUT")

    def test_wrong_grants_shape_fail_closed(self):
        self.assertEqual(summarize_grants("GRANT SELECT ON *.* TO x")["triage"], "MISSING_OR_INVALID_INPUT")

    def test_nonstring_row_does_not_raise_or_authorize(self):
        self.assertEqual(summarize_grants([42])["release_status"], "BLOCKED")

    def test_metadata_does_not_contain_principal(self):
        report = summarize_grants(["GRANT SELECT ON *.* TO 'do-not-log-me'@'private-host'"])
        self.assertNotIn("do-not-log-me", str(report))
        self.assertNotIn("private-host", str(report))

    def test_raw_grant_sql_is_not_echoed(self):
        report = summarize_grants(["GRANT INSERT ON `ctug_workspace`.* TO 'secret_login'@'host'"])
        self.assertNotIn("GRANT INSERT ON", str(report))
        self.assertNotIn("secret_login", str(report))

    def test_global_select_is_not_writer_fence(self):
        report = summarize_grants(["GRANT SELECT ON *.* TO 'reader'@'localhost'"])
        self.assertEqual(report["scope_counts"], {"GLOBAL": 1})
        self.assertEqual(report["release_status"], "BLOCKED")
