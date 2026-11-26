"""Offline contract tests. No MySQL import or connection, including the inventory default path."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import permission_inventory as inventory
from prepare_runtime_patch import patch_text, proposed_files
from proposal import DENY_PREDECESSORS, NEW, expected_delta, validate_candidate


class CandidateTests(unittest.TestCase):
    def test_exact_scope_and_governance_boundaries(self):
        data = validate_candidate()
        self.assertEqual(len(data["permissions"]), 98)
        self.assertEqual(len(data["default_bindings"]), 109)
        bindings = {(b["role_name"], b["permission_code"]) for b in data["default_bindings"]}
        self.assertIn(("Admin", "finance.fee_schedule.manage"), bindings)
        self.assertNotIn(("Treasurer", "finance.fee_schedule.manage"), bindings)
        self.assertIn(("Student", "clearance.requests.self.submit"), bindings)
        for code, _, _, _, _, role, _ in NEW:
            self.assertEqual({r for r, c in bindings if c == code}, {role})
        self.assertFalse(any(r == "Admin" and c.startswith("access_control.") for r, c in bindings))

    def test_extra_binding_missing_operation_or_forged_approval_is_rejected(self):
        delta = expected_delta()
        for mutated in (dict(delta, independent_review={"status": "APPROVED"}),
                        dict(delta, operations=delta["operations"][:-1]),
                        dict(delta, operations=delta["operations"] + [{"op": "add_default_binding", "role_name": "Treasurer",
                                                                     "permission_code": NEW[0][0]}]),
                        dict(delta, base=dict(delta["base"], effective_digest="0" * 64))):
            with self.subTest(mutated=mutated), self.assertRaises(ValueError):
                validate_candidate(mutated)

    def test_duplicate_json_keys_and_wrong_types_are_refused(self):
        from apps.access_control.catalogue.validation_v2 import CatalogueV2ValidationError, _json
        with self.assertRaises(CatalogueV2ValidationError):
            _json(b'{"operations":[],"operations":[]}')
        bad = deepcopy(expected_delta())
        bad["operations"][1]["permission"]["readiness"] = True
        with self.assertRaises(ValueError):
            validate_candidate(bad)

    def test_changed_addendum_is_refused_without_claiming_independent_pin_approval(self):
        with self.assertRaises(ValueError):
            validate_candidate(addendum_bytes=b"Changed review scope")
        self.assertEqual(expected_delta()["independent_review"]["status"], "OPEN")

    def test_patch_is_reproducible_and_stays_unapplied(self):
        self.assertEqual((HERE / "runtime_changes_PROPOSED.patch").read_text(encoding="utf-8"), patch_text())
        from proposal import ROOT
        self.assertIn('WRITE_CODE = "clearance.requests.self.submit"',
                      (ROOT / "backend/apps/academic/onboarding.py").read_text())
        self.assertFalse((ROOT / "backend/apps/access_control/permission_transitions.py").exists())
        files = proposed_files()
        self.assertIn('WRITE_CODE = "academic.semester_onboarding.self.submit"', files["backend/apps/academic/onboarding.py"])
        self.assertIn("preserve_transition_denies(permissions, account_id)", files["backend/apps/access_control/services.py"])
        self.assertNotIn("has_permission(account, predecessor", files["backend/apps/access_control/permission_transitions.py"])
        self.assertEqual(set(DENY_PREDECESSORS), set(inventory.TRANSITIONS))


class InventoryTests(unittest.TestCase):
    def sample(self):
        return {"services": [("academic", 1), ("finance", 1), ("clearance", 1)],
                "permissions": [(1, "academic.profiles.manage", "academic", 1),
                                (2, "academic.periods.manage", "academic", 1),
                                (3, "clearance.requests.self.submit", "clearance", 1),
                                (4, "finance.fee_schedule.manage", "finance", 1)],
                "role_bindings": [("academic.profiles.manage", 1, "Admin", 1, 1, 1),
                                  ("academic.periods.manage", 1, "Admin", 1, 2, 1),
                                  ("clearance.requests.self.submit", 2, "Student", 1, 3, 1),
                                  ("finance.fee_schedule.manage", 3, "Treasurer", 1, 4, 1)],
                "scopes": [(10, 1)], "overrides": [("academic.profiles.manage", 123, 10, "Deny", 1),
                                                    ("clearance.requests.self.submit", 456, 11, "Grant", 1)],
                "assignments": [(123, 1, "Admin", 1), (456, 2, "Student", 1), (789, 3, "Treasurer", 1)],
                "accounts": [(123, 1, "Approved", 0, 0), (456, 1, "Approved", 0, 0), (789, 1, "Approved", 0, 0)]}

    def test_default_path_never_imports_driver(self):
        output = io.StringIO()
        with patch.dict(sys.modules, {"MySQLdb": None}), redirect_stdout(output):
            self.assertEqual(inventory.main([]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "NOT_EXECUTED")

    def test_only_literal_select_queries_and_no_personal_fields(self):
        for query in inventory.QUERIES.values():
            self.assertTrue(query.startswith("SELECT "), query)
            self.assertNotRegex(query, r"(?i)\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|CALL|INTO|FOR UPDATE)\b")
            self.assertNotRegex(query, r"(?i)\b(email|school_id|password|first_name|last_name|source_reference)\b")

    def test_deny_preservation_and_opaque_accounts(self):
        report = inventory.summarize(self.sample(), b"x" * 32)
        self.assertEqual(len(report["required_deny_review"]), 2)
        self.assertEqual({r["replacement"] for r in report["required_deny_review"]},
                         {"academic.enrollment_verifications.record", "academic.historical_participation.correct"})
        text = json.dumps(report)
        self.assertNotIn('"account_id"', text)
        self.assertNotIn('"123"', text)
        self.assertEqual(report["override_counts"], {"Deny:active": 1, "Grant:active": 1})
        affected = next(a for a in report["accounts"] if a["account_token"] == inventory.token(b"x" * 32, 123))
        self.assertFalse(any(i["replacement"].startswith("academic.") and i["potential"] == "expansion"
                             for i in affected["potential_transitions"]))

    def test_fee_move_shows_treasurer_source_loss_and_admin_operation_gain(self):
        report = inventory.summarize(self.sample(), b"x" * 32)
        impacts = [i for a in report["accounts"] for i in a["potential_transitions"]]
        self.assertTrue(any(i["potential"] == "loss_of_historical_hdac_code" for i in impacts))
        self.assertTrue(any(i["replacement"] == "finance.fee_schedule.manage" and i["potential"] == "expansion" for i in impacts))

    def test_inactive_legacy_deny_is_retained_in_inventory_without_blocking(self):
        data = self.sample()
        data["overrides"][0] = ("academic.profiles.manage", 123, 10, "Deny", 0)
        report = inventory.summarize(data, b"x" * 32)
        self.assertEqual(report["required_deny_review"], [])
        self.assertEqual(report["account_overrides"][0]["effect"], "Deny")
        self.assertFalse(report["account_overrides"][0]["active"])

    def test_scope_gates_are_enumerated_without_treating_scoped_grants_as_always_effective(self):
        report = inventory.summarize(self.sample(), b"x" * 32)
        contexts = {i["context"] for a in report["accounts"] for i in a["potential_transitions"]}
        self.assertTrue(any(c.endswith("scoped-grants-on") for c in contexts))
        self.assertTrue(any(c.endswith("scoped-grants-off") for c in contexts))

    def test_reduced_report_keeps_scope_unavailable_and_preserves_deny_findings(self):
        data = self.sample()
        original = inventory.summarize(data, b"x" * 32)
        data["scopes"] = None
        reduced = inventory.summarize(data, b"x" * 32)
        self.assertEqual(reduced["role_scope_inventory"]["status"], "unavailable")
        self.assertEqual(reduced["role_scope_inventory"]["scope_enabled_scenario"], "not_evaluated")
        self.assertEqual(reduced["required_deny_review"], original["required_deny_review"])
        self.assertTrue(reduced["account_overrides"])
        for entry in reduced["account_overrides"]:
            self.assertEqual(entry["role_scope_status"], "unavailable")
            self.assertNotIn("role_scope_id", entry)
        contexts = [i["context"] for a in reduced["accounts"] for i in a["potential_transitions"]]
        self.assertTrue(contexts)
        self.assertTrue(all(context.endswith("scoped-grants-off") for context in contexts))

    def test_reduced_grants_reject_broader_access_roles_and_missing_tables(self):
        grantee = "TO `ctug_wf11_inventory_ro`@`127.0.0.1`"
        grants = [f"GRANT USAGE ON *.* {grantee}", *[
            f"GRANT SELECT ON `ctug_workspace`.`{table}` {grantee}"
            for table in ("permissions", "services", "roles", "role_permissions", "account_permissions",
                          "account_roles", "accounts")]]
        inventory.verify_reduced_grants(grants)
        for invalid in (grants[:-1], grants + [f"GRANT SELECT ON `ctug_workspace`.* {grantee}"],
                        grants + [f"GRANT `unexpected_role`@`%` {grantee}"],
                        [*grants[:-1], grants[-1] + " WITH GRANT OPTION"]):
            with self.subTest(grants=invalid), self.assertRaises(ValueError):
                inventory.verify_reduced_grants(invalid)

    def test_reduced_plan_requires_explicit_execution_and_omits_scope_data_query(self):
        output = io.StringIO()
        with patch.dict(sys.modules, {"MySQLdb": None}), redirect_stdout(output):
            self.assertEqual(inventory.main(["--without-role-scopes"]), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["status"], "NOT_EXECUTED")
        self.assertNotIn("scopes", plan["queries"])

    def test_privileged_identity_and_wrong_database_are_refused_before_data_queries(self):
        class Cursor:
            def __init__(self, grant, database):
                self.grant, self.database, self.query = grant, database, ""
                self.executed = []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def execute(self, query, params=None):
                self.query = query
                self.executed.append(query)
            def fetchall(self):
                if self.query.startswith("SHOW GRANTS"):
                    return [(self.grant,)]
                if self.query == inventory.QUERIES["identity"]:
                    return [(self.database, "localhost", 3306, 1)]
                raise AssertionError("Must refuse before other data reads")

        for grant, database in (("GRANT ALL PRIVILEGES ON *.* TO 'writer'@'localhost'", "ctug_workspace"),
                                ("GRANT SELECT ON ctug_workspace.* TO 'reader'@'localhost' WITH GRANT OPTION", "ctug_workspace"),
                                ("GRANT SELECT ON ctug_workspace.* TO 'reader'@'localhost'", "wrong_schema")):
            cursor = Cursor(grant, database)
            connection = type("Connection", (), {"cursor": lambda self: cursor})()
            with self.subTest(grant=grant, database=database), self.assertRaises(ValueError):
                inventory.read_snapshot(connection)
            self.assertNotIn(inventory.QUERIES["overrides"], cursor.executed)


if __name__ == "__main__":
    unittest.main()
