"""AR-6C7D.5 offline-only contract/readiness reporting tests."""

import copy
import unittest

from scripts.report_registration_review_execution_readiness import (
    build_readiness_report,
)
from scripts.validate_registration_review_execution_contract import (
    ContractRejected,
    load_local,
)


class ReadinessReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_tuple = load_local()

    def check(self, mutate=None):
        contract, profile, source, source_raw = copy.deepcopy(self.source_tuple)
        if mutate:
            mutate(contract, profile, source)
        return build_readiness_report(contract, profile, source, source_raw)

    def test_exact_scope_is_reported(self):
        report = self.check()
        self.assertEqual(report["scope"]["role_name"], "Admin")
        self.assertEqual(report["scope"]["services"], ["accounts", "access_control"])
        self.assertEqual(len(report["scope"]["permission_definitions"]), 3)
        self.assertEqual(len(report["scope"]["role_bindings"]), 3)

    def test_all_execution_stages_remain_blocked(self):
        report = self.check()
        self.assertEqual([stage["id"] for stage in report["stages"]],
                         ["metadata", "role_grants", "service_activation", "api_activation"])
        self.assertTrue(all(stage["status"] == "BLOCKED" for stage in report["stages"]))
        self.assertFalse(report["live_execution_authorized"])
        self.assertFalse(report["release_ready"])

    def test_never_claims_runtime_or_database_verification(self):
        report = self.check()
        for name in ("live_database_checked", "route_and_runtime_gates_checked",
                     "database_writes_performed"):
            self.assertIs(report[name], False)

    def test_mutated_permissions_are_refused(self):
        def mutate(contract, *_):
            contract["intended_records"]["permissions"].append("accounts.secret.read")
        with self.assertRaises(ContractRejected):
            self.check(mutate)

    def test_unblocked_stage_is_refused(self):
        def mutate(contract, *_):
            contract["allowed_future_sequence"][0]["decision"] = "APPROVED"
        with self.assertRaises(ContractRejected):
            self.check(mutate)

    def test_forged_executor_approval_is_refused(self):
        def mutate(contract, *_):
            contract["authorization"]["executor_identity"] = "fictional-operator"
        with self.assertRaises(ContractRejected):
            self.check(mutate)

    def test_forged_database_authorization_is_refused(self):
        def mutate(contract, *_):
            contract["database_writes_authorized"] = True
        with self.assertRaises(ContractRejected):
            self.check(mutate)


if __name__ == "__main__":
    unittest.main()
