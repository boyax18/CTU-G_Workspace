"""Standard-library-only tests: no Django setup or database is needed."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from .catalogue import validation_v2 as v2


class CatalogueV2Tests(unittest.TestCase):
    def setUp(self):
        self.data = v2.read_manifest()

    def invalid(self, message="."):
        with self.assertRaisesRegex(v2.CatalogueV2ValidationError, message):
            v2.validate_manifest(self.data)

    def test_exact_validated_counts(self):
        self.assertEqual(dict(v2.validate_manifest().counts), dict(
            services=10, permissions=95, roles=6, default_bindings=106,
            retained=79, revised=2, added=14, retired=1, blocked=14,
            internal_contracts=9, planned=72,
        ))

    def test_exact_role_totals_and_advisor_reads(self):
        expected = dict(Student=18, Instructor=17, Treasurer=23, Admin=35,
                        **{"Technical Super Admin": 10, "SSG Advisor": 3})
        for role, total in expected.items():
            self.assertEqual(sum(b["role_name"] == role for b in self.data["default_bindings"]), total)
        self.assertEqual({b["permission_code"] for b in self.data["default_bindings"] if b["role_name"] == "SSG Advisor"}, {
            "finance.monitoring.overview.read", "reports.monitoring.financial.read", "finance.monitoring.transactions.read",
        })

    def test_79_unchanged_and_two_name_description_revisions(self):
        baseline = json.loads((v2.ROOT / v2.PINS["c1_manifest"][0]).read_bytes())
        old = {p["permission_code"]: p for p in baseline["permissions"]}
        for permission in self.data["permissions"]:
            if permission["origin"] == "KEEP":
                self.assertEqual({f: permission[f] for f in v2.CORE_FIELDS}, {f: old[permission["permission_code"]][f] for f in v2.CORE_FIELDS})
            elif permission["origin"] == "REVISE":
                changed = {f for f in v2.CORE_FIELDS if permission[f] != old[permission["permission_code"]][f]}
                self.assertEqual(changed, {"permission_name", "description"})
        self.assertEqual(len(self.data["delta"]["retained_codes"]), 79)
        self.assertEqual(len(self.data["delta"]["revisions"]), 2)
        self.assertEqual(len(self.data["delta"]["added_codes"]), 14)

    def test_all_existing_proposed_pairs_are_retained(self):
        baseline = json.loads((v2.ROOT / v2.PINS["c1_manifest"][0]).read_bytes())
        pairs = {(b["role_name"], b["permission_code"]) for b in self.data["default_bindings"]}
        self.assertTrue({(b["role_name"], b["permission_code"]) for b in baseline["default_bindings"]} <= pairs)

    def test_tombstone_preserves_original_definition_without_remapping(self):
        tombstone, = self.data["historical_retirements"]
        baseline = json.loads((v2.ROOT / v2.PINS["c1_manifest"][0]).read_bytes())
        self.assertEqual(tombstone["original_definition"], next(p for p in baseline["permissions"] if p["permission_code"] == v2.RETIRED_CODE))
        self.assertEqual(len(tombstone["replacement_codes"]), 3)
        self.assertFalse(tombstone["automatic_grant_remapping"])
        self.assertFalse(tombstone["execution_allowed"])

    def test_deep_immutable_result_is_detached(self):
        result = v2.validate_manifest(self.data)
        self.data["permissions"][0]["description"] = "caller edit"
        self.assertNotEqual(result.data["permissions"][0]["description"], "caller edit")
        for target, key in ((result.data, "planning_only"), (result.data["roles"][0], "role_name"),
                            (result.data["composition"]["authorization"], "explicit_deny_precedence"), (result.counts, "permissions")):
            with self.assertRaises(TypeError):
                target[key] = None
        with self.assertRaises(TypeError):
            result.data["default_bindings"][0] = None

    def test_duplicate_service_code(self):
        self.data["services"].append(deepcopy(self.data["services"][0]))
        self.invalid("duplicate")

    def test_equivalent_service_name(self):
        self.data["services"][1]["service_name"] = "Accóunts and Profiles"
        self.invalid("equivalent")

    def test_duplicate_permission_code(self):
        self.data["permissions"].append(deepcopy(self.data["permissions"][0]))
        self.invalid("duplicate")

    def test_duplicate_role(self):
        self.data["roles"].append(deepcopy(self.data["roles"][0]))
        self.invalid("duplicate")

    def test_invalid_service_reference(self):
        self.data["permissions"][0]["service_code"] = "missing"
        self.invalid("service relationship")

    def test_noncanonical_codes_and_wildcards(self):
        original = deepcopy(self.data)
        for code in ("Accounts.profile.self.read", "accounts.*", "accounts.profile.self.read "):
            with self.subTest(code=code):
                self.data = deepcopy(original)
                self.data["permissions"][0]["permission_code"] = code
                self.invalid()

    def test_all_database_text_field_limits(self):
        original = deepcopy(self.data)
        cases = (("services", {"service_code": 100, "service_name": 100, "description": 255}),
                 ("roles", {"role_name": 50, "description": 255}),
                 ("permissions", {"permission_code": 150, "permission_name": 100, "module_name": 100, "action_name": 50, "description": 255}))
        for group, fields in cases:
            for field, limit in fields.items():
                with self.subTest(group=group, field=field):
                    self.data = deepcopy(original)
                    self.data[group][0][field] = "x" * (limit + 1)
                    self.invalid("field length")

    def test_field_limit_prerequisite_missing(self):
        with patch("pathlib.Path.read_text", side_effect=OSError):
            self.invalid("field-limit prerequisite")

    def test_invalid_readiness(self):
        self.data["permissions"][0]["readiness"] = "READY"
        self.invalid("readiness")

    def test_invalid_role_or_permission_binding(self):
        for field, value in (("role_name", "Finance Monitor"), ("permission_code", "missing.permission")):
            with self.subTest(field=field):
                original = self.data["default_bindings"][0][field]
                self.data["default_bindings"][0][field] = value
                self.invalid("invalid role/permission")
                self.data["default_bindings"][0][field] = original

    def test_duplicate_binding(self):
        self.data["default_bindings"].append(deepcopy(self.data["default_bindings"][0]))
        self.invalid("Duplicate proposed binding")

    def test_blocked_permissions_have_no_defaults(self):
        original = deepcopy(self.data)
        blocked = [p["permission_code"] for p in self.data["permissions"] if p["readiness"] == "B"]
        self.assertEqual(len(blocked), 14)
        for code in blocked:
            with self.subTest(code=code):
                self.data = deepcopy(original)
                self.data["default_bindings"].append(dict(role_name="Admin", permission_code=code))
                self.invalid("Blocked permissions")

    def test_delegation_has_no_default_authority(self):
        self.data["default_bindings"].append(dict(role_name="Technical Super Admin", permission_code="access_control.delegate.finance"))
        self.invalid("Delegation authority")

    def test_governance_has_no_business_defaults(self):
        self.data["default_bindings"].append(dict(role_name="Technical Super Admin", permission_code="finance.summary.read"))
        self.invalid("Governance role")

    def test_advisor_has_no_write_default(self):
        self.data["default_bindings"].append(dict(role_name="SSG Advisor", permission_code="finance.payments.record"))
        self.invalid("Advisor must")

    def test_advisor_cannot_lose_one_required_view(self):
        self.data["default_bindings"] = [b for b in self.data["default_bindings"] if not (b["role_name"] == "SSG Advisor" and b["permission_code"] == "finance.monitoring.transactions.read")]
        self.invalid("Advisor must")

    def test_same_count_changed_matrix_is_rejected(self):
        binding = next(b for b in self.data["default_bindings"] if b["permission_code"] == "academic.profile.self.read")
        binding["role_name"] = "Instructor"
        self.invalid("exact pinned")

    def test_retired_code_cannot_be_selected(self):
        permission = {k: self.data["historical_retirements"][0]["original_definition"][k] for k in v2.CORE_FIELDS}
        permission.update(origin="KEEP", scope="GOV", grant_protection="GOV")
        self.data["permissions"].append(permission)
        self.invalid("Retired code")

    def test_retired_code_cannot_have_default(self):
        self.data["default_bindings"].append(dict(role_name="Admin", permission_code=v2.RETIRED_CODE))
        self.invalid("invalid role/permission")

    def test_tombstone_cannot_automatically_remap_grants(self):
        self.data["historical_retirements"][0]["automatic_grant_remapping"] = True
        self.invalid("exact pinned")

    def test_missing_definition_or_changed_metadata(self):
        original = deepcopy(self.data)
        self.data["permissions"] = [p for p in self.data["permissions"] if p["permission_code"] != "access_control.delegate.academic"]
        self.invalid("exact pinned")
        self.data = original
        self.data["permissions"][0]["description"] = "Different scope"
        self.invalid("exact pinned")

    def test_super_admin_requires_admin_and_governance(self):
        self.data["composition"]["application_super_admin"]["required_roles"] = ["Technical Super Admin"]
        self.invalid("composition/eligibility")

    def test_roles_or_grants_cannot_replace_full_super_admin_eligibility(self):
        original = deepcopy(self.data)
        for field, value in (("role_membership_sufficient", True), ("direct_grants_replace_roles", True),
                             ("usable_approved_governance_workflow_required", False), ("per_service_delegation_required", False)):
            with self.subTest(field=field):
                self.data = deepcopy(original)
                self.data["composition"]["application_super_admin"][field] = value
                self.invalid("composition/eligibility")

    def test_advisor_requires_instructor_and_appointment_not_just_grants(self):
        original = deepcopy(self.data)
        for field, value in (("required_roles", ["SSG Advisor"]), ("role_membership_sufficient", True),
                             ("valid_appointment_and_period_required", False), ("grants_alone_confer_eligibility", True),
                             ("read_only_projection_required", False), ("other_role_writes_suppressed", True)):
            with self.subTest(field=field):
                self.data = deepcopy(original)
                self.data["composition"]["ssg_advisor"][field] = value
                self.invalid("composition/eligibility")

    def test_normal_admin_cannot_edit_global_defaults(self):
        self.data["composition"]["normal_admin"]["global_default_management"] = True
        self.invalid("composition/eligibility")

    def test_deny_object_self_interest_last_operator_and_framework_guards(self):
        original = deepcopy(self.data)
        fields = ("explicit_deny_precedence", "object_ownership_checks_required", "financial_self_interest_checks_required",
                  "django_superuser_is_application_bypass", "self_and_assigned_role_ordinary_mutations_allowed",
                  "effective_last_operator_protection_required", "runtime_enforcement_implemented_by_manifest")
        for field in fields:
            with self.subTest(field=field):
                self.data = deepcopy(original)
                contract = self.data["composition"]["authorization"]
                contract[field] = not contract[field]
                self.invalid("composition/eligibility")

    def test_role_combinations_are_preserved(self):
        self.data["composition"]["required_multi_role_combinations"].remove(["Student", "Treasurer"])
        self.invalid("composition/eligibility")

    def test_delegation_cannot_be_enabled_or_widened(self):
        original = deepcopy(self.data)
        for field, value in (("status", "ON"), ("enabled_scopes", [{"service": "finance"}]),
                             ("wildcards_allowed", True), ("legacy_cartesian_widening_allowed", True),
                             ("ordinary_reserved_target_mutations_allowed", True)):
            with self.subTest(field=field):
                self.data = deepcopy(original)
                self.data["delegation"][field] = value
                self.invalid("Delegation must remain OFF")

    def test_policy_and_bootstrap_blockers_cannot_be_marked_approved(self):
        self.assertEqual(len(self.data["policy_blockers"]), 10)
        for index in range(10):
            with self.subTest(index=index):
                self.data["policy_blockers"][index]["status"] = "APPROVED"
                self.invalid("blockers must remain explicit")
                self.data["policy_blockers"][index]["status"] = "OPEN"
        self.data["operational_gates"]["first_operator_attribution"] = "READY"
        self.invalid("blockers must remain explicit")

    def test_missing_or_altered_blocker_and_readiness_marker(self):
        original = deepcopy(self.data)
        self.data["policy_blockers"].pop()
        self.invalid("blockers must remain explicit")
        self.data = original
        self.data["blocked_permissions"].pop()
        self.invalid("exact pinned")

    def test_version_and_source_revision_are_immutable(self):
        original = deepcopy(self.data)
        for field in ("schema_version", "manifest_version", "source_revision"):
            with self.subTest(field=field):
                self.data = deepcopy(original)
                self.data[field] = "another-version"
                self.invalid("Immutable")

    def test_planning_only_is_strict_boolean(self):
        for value in (False, 1, "true"):
            with self.subTest(value=value):
                self.data["planning_only"] = value
                self.invalid("static planning")

    def test_no_database_ids_or_implicit_privilege_fields(self):
        self.data["permissions"][0]["permission_id"] = 1
        self.invalid("unexpected fields")
        del self.data["permissions"][0]["permission_id"]
        self.data["roles"][0]["is_superuser"] = True
        self.invalid("exact pinned")

    def test_unknown_manifest_fields_and_invalid_shapes(self):
        self.data["apply"] = True
        self.invalid("unexpected fields")
        del self.data["apply"]
        for group in ("services", "roles", "permissions", "default_bindings"):
            original = self.data[group]
            self.data[group] = None
            self.invalid()
            self.data[group] = original

    def test_strict_nested_boolean_types(self):
        self.data["composition"]["authorization"]["explicit_deny_precedence"] = 1
        self.invalid("composition/eligibility")

    def test_provenance_hash_missing_or_tampered_file_fails_closed(self):
        original_read = Path.read_bytes
        for key, (relative, _digest) in v2.PINS.items():
            for corrupt in (False, True):
                def read(location, *, selected=v2.ROOT / relative, corrupt=corrupt):
                    if location == selected:
                        if corrupt:
                            return b"changed pinned content"
                        raise OSError("missing")
                    return original_read(location)
                with self.subTest(source=key, corrupt=corrupt), patch("pathlib.Path.read_bytes", autospec=True, side_effect=read):
                    self.invalid("Pinned")

    def test_manifest_cannot_redirect_provenance_reads(self):
        self.data["provenance"]["proposal"]["path"] = "../../untrusted"
        with patch("pathlib.Path.read_bytes", autospec=True, side_effect=Path.read_bytes) as read:
            self.invalid("Pinned provenance differs")
        self.assertEqual([call.args[0] for call in read.call_args_list], [v2.ROOT / relative for relative, _ in v2.PINS.values()])

    def test_c1_pinned_bytes_and_hashes_remain_exact(self):
        self.assertEqual(sha256((v2.ROOT / v2.PINS["c1_manifest"][0]).read_bytes()).hexdigest(), "86d72d82295cb358244145c6d24ebe8ba948f5211de298ebf897b5d3d83ed447")
        self.assertEqual(sha256((v2.ROOT / v2.PINS["c1_source"][0]).read_bytes()).hexdigest(), "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e")

    def test_duplicate_json_keys_nonfinite_values_and_unreadable_manifest(self):
        for raw in (b'{"planning_only":true,"planning_only":false}', b'{"invalid":NaN}', b'{', b'\xff'):
            with self.subTest(raw=raw), patch("pathlib.Path.read_bytes", return_value=raw):
                with self.assertRaises(v2.CatalogueV2ValidationError):
                    v2.read_manifest()
        with patch("pathlib.Path.read_bytes", side_effect=OSError):
            with self.assertRaisesRegex(v2.CatalogueV2ValidationError, "manifest is unavailable"):
                v2.read_manifest()

    def test_import_and_validation_work_with_django_imports_forbidden(self):
        code = """
import sys
class NoDjango:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'django' or fullname.startswith('django.'):
            raise AssertionError('Django import is forbidden for static v2 validation')
sys.meta_path.insert(0, NoDjango())
from apps.access_control.catalogue.validation_v2 import validate_manifest
assert validate_manifest().counts['permissions'] == 95
print('stdlib-only validation passed')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=v2.ROOT / "backend",
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "stdlib-only validation passed")


if __name__ == "__main__":
    unittest.main()
