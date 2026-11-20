"""Offline-only G1D-P3C5 tests; do not touch MySQL, Docker or Django DB."""

import importlib
import re
import subprocess
import unittest
from unittest.mock import patch

m = importlib.import_module(
    "apps.access_control.tests_support.g1d_p3c5_docker_fence_test_only"
)


class DisposableSqlDesignTests(unittest.TestCase):
    def setUp(self):
        self.sql = m.sql_setup("a" * 48, "b" * 48)

    def test_only_disposable_schema_created(self):
        self.assertIn("CREATE DATABASE `ctug_p3c5_disposable`", self.sql)
        self.assertNotIn("CREATE DATABASE `ctug_workspace`", self.sql)

    def test_no_production_database_name_in_sql(self):
        self.assertNotIn("ctug_workspace", self.sql.lower())

    def test_disposable_test_table_contains_protected_fixture(self):
        self.assertIn("'Technical Super Admin', 0", self.sql)

    def test_admin_is_separate_from_protected_role(self):
        self.assertIn("'Admin', 1", self.sql)
        self.assertIn("'Technical Super Admin', 0", self.sql)

    def test_disposable_web_has_no_direct_mutation_grants(self):
        grants = re.findall(r"^GRANT\s+(SELECT|EXECUTE)\s+ON\s+[^;]+?\s+TO\s+'ctug_p3c5_web'@'localhost';", self.sql, re.I | re.M)
        # The captured prefix for EXECUTE is deliberately restricted to routine scope.
        self.assertEqual(3, len(grants))
        self.assertEqual(["SELECT", "SELECT", "EXECUTE"], [p.strip().upper() for p in grants])

    def test_executor_only_has_read_only_visibility(self):
        self.assertIn("GRANT SELECT ON `ctug_p3c5_disposable`.roles TO 'ctug_p3c5_executor'", self.sql)
        self.assertNotIn("GRANT EXECUTE ON PROCEDURE `ctug_p3c5_disposable`.p3c5_assign_base_demo\n  TO 'ctug_p3c5_executor'", self.sql)

    def test_stored_operation_is_definer_scoped(self):
        self.assertIn("CREATE PROCEDURE p3c5_assign_base_demo", self.sql)
        self.assertIn("SQL SECURITY DEFINER", self.sql)

    def test_stored_operation_only_allows_base_roles(self):
        self.assertIn("p_role NOT IN ('Student', 'Instructor')", self.sql)
        self.assertIn("p_role IS NULL", self.sql)

    def test_stored_operation_rejects_null_target(self):
        self.assertIn("p_target IS NULL", self.sql)

    def test_stored_operation_audit_and_assignment_transaction(self):
        self.assertIn("START TRANSACTION", self.sql)
        self.assertIn("INSERT INTO account_roles", self.sql)
        self.assertIn("INSERT INTO access_audit_logs", self.sql)
        self.assertIn("COMMIT;", self.sql)

    def test_stored_operation_rolls_back_on_sql_exception(self):
        self.assertIn("DECLARE EXIT HANDLER FOR SQLEXCEPTION", self.sql)
        self.assertIn("ROLLBACK;", self.sql)
        self.assertIn("RESIGNAL;", self.sql)

    def test_no_network_privilege_setup(self):
        self.assertNotIn("'%'", self.sql)
        self.assertIn("'ctug_p3c5_web'@'localhost'", self.sql)

    def test_generated_password_shape_required(self):
        with self.assertRaises(m.RehearsalError):
            m.sql_setup("foo", "b" * 48)

    def test_sql_special_char_password_rejected(self):
        with self.assertRaises(m.RehearsalError):
            m.sql_setup("a'" + "a" * 46, "b" * 48)

    def test_missing_password_rejected(self):
        with self.assertRaises(m.RehearsalError):
            m.sql_setup("a" * 48, "")

    def test_proof_manifest_has_unique_checks(self):
        names = m.expected_checks()
        self.assertEqual(21, len(names))
        self.assertEqual(len(names), len(set(names)))

    def test_manifest_checks_privileged_denials(self):
        names = m.expected_checks()
        for required in ("runtime_protected_assignment_denied", "runtime_role_permission_denied", "runtime_admin_via_routine_refused", "executor_role_insert_denied"):
            self.assertIn(required, names)


class RehearsalDriverTests(unittest.TestCase):
    def setUp(self):
        self.driver = m.DockerRehearsal()

    def test_credentials_are_independently_generated(self):
        self.assertNotEqual(self.driver.web_password, self.driver.executor_password)
        self.assertNotEqual(self.driver.root_password, self.driver.web_password)
        self.assertRegex(self.driver.root_password, "^[a-f0-9]{48}$")

    def test_docker_not_installed_fails_closed(self):
        with patch.object(m.shutil, "which", return_value=None):
            with self.assertRaises(m.RehearsalError):
                self.driver._start()

    def test_unknown_principal_fails_closed(self):
        with self.assertRaises(m.RehearsalError):
            self.driver._mysql("production", "SELECT 1")

    def test_privilege_error_accepted(self):
        failed = subprocess.CompletedProcess([], 1, "", "ERROR 1142 (42000): INSERT denied")
        with patch.object(self.driver, "_mysql", return_value=failed):
            self.driver._denied("denial", "web", "INSERT ...")
        self.assertEqual([m.Proof("denial", "DENIED_AS_EXPECTED")], self.driver.proofs)

    def test_sql_syntax_error_not_treated_as_denial(self):
        failed = subprocess.CompletedProcess([], 1, "", "ERROR 1064 (42000): bad SQL")
        with patch.object(self.driver, "_mysql", return_value=failed):
            with self.assertRaises(m.RehearsalError):
                self.driver._denied("syntax", "web", "bad SQL")

    def test_credential_error_not_treated_as_privilege_proof(self):
        failed = subprocess.CompletedProcess([], 1, "", "ERROR 1045 (28000): bad credentials")
        with patch.object(self.driver, "_mysql", return_value=failed):
            with self.assertRaises(m.RehearsalError):
                self.driver._denied("auth", "web", "INSERT ...")

    def test_signal_requires_specific_mysql_error(self):
        denied = subprocess.CompletedProcess([], 1, "", "ERROR 1644 (45000): not allowed")
        with patch.object(self.driver, "_mysql", return_value=denied):
            self.driver._denied("role", "web", "CALL ...", {1644})
        self.assertEqual(1, len(self.driver.proofs))

    def test_unexpected_success_fails_denial(self):
        success = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(self.driver, "_mysql", return_value=success):
            with self.assertRaises(m.RehearsalError):
                self.driver._denied("unexpected", "web", "INSERT ...")

    def test_positive_requires_expected_query_result(self):
        result = subprocess.CompletedProcess([], 0, "2\n", "")
        with patch.object(self.driver, "_mysql", return_value=result):
            with self.assertRaises(m.RehearsalError):
                self.driver._good("mismatch", "root", "SELECT ...", expected="1")

    def test_positive_rejects_failed_query(self):
        result = subprocess.CompletedProcess([], 1, "", "ERROR 1146 (42S02)")
        with patch.object(self.driver, "_mysql", return_value=result):
            with self.assertRaises(m.RehearsalError):
                self.driver._good("failed", "root", "SELECT ...")

    def test_cleanup_runs_when_disposable_setup_fails(self):
        def fake_start():
            self.driver.created = True
        with (patch.object(self.driver, "_start", side_effect=fake_start),
              patch.object(self.driver, "_mysql", return_value=subprocess.CompletedProcess([], 1, "", "bad")),
              patch.object(self.driver, "_docker", return_value=subprocess.CompletedProcess([], 0, "", "")) as docker):
            with self.assertRaises(m.RehearsalError):
                self.driver.run()
            docker.assert_called_with(["rm", "--force", self.driver.container], timeout=35)

    def test_release_flag_permanently_blocked(self):
        self.assertEqual("BLOCKED", m.RELEASE_STATUS)
        self.assertNotIn("ctug_workspace", m.SCHEMA)

    def test_no_mysql_production_config_loaded(self):
        # The module is standalone and does not import Django settings or .env.
        with open(m.__file__, encoding="utf-8") as src:
            source = src.read()
        self.assertNotIn("from django", source)
        self.assertNotIn("load_dotenv", source)
        self.assertNotIn("config.settings", source)


if __name__ == "__main__":
    unittest.main()
