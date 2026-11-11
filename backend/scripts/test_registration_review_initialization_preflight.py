"""Pure unit tests: no Django, database, environment files or writes."""

import copy
import unittest

from scripts.plan_registration_review_profile import load_local
from scripts.registration_review_initialization_preflight import (
    InitializationPreflightError, build_preflight,
)


class RegistrationReviewInitializationPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile, cls.source, cls.digest = load_local()

    def setUp(self):
        self.report = {
            "mode": "READ-ONLY V2 PLANNING",
            "database_vendor": "mysql",
            "application_approved": False,
            "database_modifications": 0,
            "guarantee": "MySQL READ ONLY consistent snapshot with SELECT-only guard; rolled back.",
            "manifest": self.source["manifest_version"],
            "source_revision": self.source["source_revision"],
            "provenance": copy.deepcopy(self.source["provenance"]["proposal"]),
            "proposed": {
                "services": len(self.source["services"]),
                "permissions": len(self.source["permissions"]),
                "roles": len(self.source["roles"]),
                "role_bindings": len(self.source["default_bindings"]),
                "retired_tombstones": len(self.source["historical_retirements"]),
            },
            "totals": {"CREATE": 105, "MATCH": 4, "DEFER": 108, "CONFLICT": 0},
            "review_totals": {"CREATE": 0, "MATCH": 0, "DEFER": 0, "CONFLICT": 0},
            "unexpected": [],
            "retirement_review": [],
            "account_override_review": [],
            "blocked_dependencies": [{"id": "initialization", "status": "BLOCKED"}],
            "records": ([
                {"kind": "service", "key": code, "classification": "CREATE"}
                for code in ("accounts", "access_control")
            ] + [
                {"kind": "permission", "key": code, "classification": "CREATE"}
                for code in (
                    "accounts.registration_requests.read",
                    "accounts.registration_requests.approve",
                    "accounts.registration_requests.reject",
                )
            ] + [{"kind": "role", "key": "Admin", "classification": "MATCH"}] + [
                {"kind": "role_binding", "key": "Admin -> " + code,
                 "classification": "DEFER"}
                for code in (
                    "accounts.registration_requests.read",
                    "accounts.registration_requests.approve",
                    "accounts.registration_requests.reject",
                )
            ]),
        }

    def plan(self, *, report=None, profile=None, source=None, digest=None):
        return build_preflight(
            profile=self.profile if profile is None else profile,
            source=self.source if source is None else source,
            source_sha256=self.digest if digest is None else digest,
            database_report=self.report if report is None else report,
        )

    def refuse(self, mutate):
        report = copy.deepcopy(self.report)
        mutate(report)
        with self.assertRaises(InitializationPreflightError):
            self.plan(report=report)

    def test_exact_expected_missing_rows_are_only_proposed(self):
        result = self.plan()
        self.assertEqual(len(result["metadata_proposals"]), 5)
        self.assertEqual(len(result["deferred_role_grants"]), 3)
        self.assertTrue(all(g["state"] == "DEFER" for g in result["deferred_role_grants"]))
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["release_ready"])
        self.assertEqual(set(result["activation_gates"].values()), {"BLOCKED"})

    def test_metadata_matches_are_allowed_only_for_inactive_existing_definitions(self):
        self.report["records"][0]["classification"] = "MATCH"
        self.report["records"][2]["classification"] = "MATCH"
        result = self.plan()
        self.assertEqual(result["metadata_proposals"][0]["state"], "MATCH")
        self.assertFalse(result["execution_authorized"])

    def test_refuses_active_service(self):
        self.refuse(lambda r: r["records"][0].update(classification="CONFLICT"))

    def test_refuses_already_active_role_grant(self):
        self.refuse(lambda r: r["records"][-1].update(classification="MATCH"))

    def test_refuses_missing_record(self):
        self.refuse(lambda r: r["records"].pop())

    def test_refuses_duplicate_record(self):
        self.refuse(lambda r: r["records"].append(copy.deepcopy(r["records"][0])))

    def test_refuses_conflicts_anywhere_in_catalogue(self):
        self.refuse(lambda r: r["totals"].update(CONFLICT=1))

    def test_refuses_unexpected_record(self):
        self.refuse(lambda r: r["unexpected"].append({"kind": "role_binding"}))

    def test_refuses_unreviewed_override(self):
        self.refuse(lambda r: r["account_override_review"].append({"count": 1}))

    def test_refuses_retired_definition_review(self):
        self.refuse(lambda r: r["retirement_review"].append({"kind": "retired_permission"}))

    def test_refuses_non_mysql_planner(self):
        self.refuse(lambda r: r.update(database_vendor="sqlite"))

    def test_refuses_report_claiming_any_write(self):
        self.refuse(lambda r: r.update(database_modifications=1))

    def test_refuses_report_claiming_approval(self):
        self.refuse(lambda r: r.update(application_approved=True))

    def test_refuses_missing_readonly_guarantee(self):
        self.refuse(lambda r: r.update(guarantee="Database read successful"))

    def test_refuses_unpinned_v2_provenance(self):
        self.refuse(lambda r: r["provenance"].update(sha256="0" * 64))

    def test_refuses_tampered_source(self):
        self.refuse(lambda r: r.update(manifest="catalogue-v3"))

    def test_refuses_changed_static_profile(self):
        profile = copy.deepcopy(self.profile)
        profile["gates"]["role_grants"] = "ENABLED"
        with self.assertRaises(InitializationPreflightError):
            self.plan(profile=profile)

    def test_refuses_source_unblocked_operational_gate(self):
        source = copy.deepcopy(self.source)
        source["operational_gates"]["grants"] = "ENABLED"
        with self.assertRaises(InitializationPreflightError):
            self.plan(source=source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
