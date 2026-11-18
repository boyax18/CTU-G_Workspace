"""WF-03.01 D-89: Permission Catalogue v2.1 overlay. Standard-library-only tests: no Django setup or database.

Run: python manage.py test apps.access_control.test_catalogue_v2_1 --settings=config.test_settings --noinput
"""

from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
import unittest
import unittest.mock

from .catalogue import validation_v2 as v2
from .catalogue import validation_v2_1 as v21

TSA = "Technical Super Admin"
ORDINARY = "access_control.role_assignments.ordinary.manage"
# Recorded independently before D-89 (baseline at 0da2182); the v2.1 work must leave every one unchanged.
# v2_0.json and validation_v2.py are compared as LF-normalized content (equal to their committed Git
# blobs, because autocrlf may convert them on checkout); the -text pinned sources as raw bytes.
NORMALIZED = {
    "backend/apps/access_control/catalogue/v2_0.json": "a7e2705236a37522b77468fd4154113d19e7e64bc479cfa420c41d7744a2548b",
    "backend/apps/access_control/catalogue/validation_v2.py": "f6b83305db567dcafc57eba97011554587be4b65d6d3c7116dc6a80b9a756aa4",
}
RAW = {
    "backend/apps/access_control/catalogue/c1_v1.json": "86d72d82295cb358244145c6d24ebe8ba948f5211de298ebf897b5d3d83ed447",
    "docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md": "56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78",
    "docs/architecture/AR-2-revised-administrator-access-control.md": "b36c0dac6d18badc435cce242725d2d6424db9d7e12d6d4943f20c7eaaf8ce36",
    "docs/architecture/AR-3A-administrator-architecture-finalization.md": "464c0fec172ef5ba887dbc22ec5b09c3396ca1be53087d999bbf763966edded1",
    "docs/SRS/CTU-G_Workspace_SRS_v1.md": "af4ead4f88bdb0877ab6c3b8965bec5caf0f058d74ab0d878ec690379210346f",
    "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md":
        "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e",
}


def pairs(data):
    return [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]


class OriginalV2IntegrityTests(unittest.TestCase):
    def test_v2_and_every_pinned_source_are_byte_identical(self):
        for path, digest in NORMALIZED.items():
            with self.subTest(path=path):
                self.assertEqual(sha256(v21.normalized_lf((v2.ROOT / path).read_bytes())).hexdigest(), digest)
        for path, digest in RAW.items():
            with self.subTest(path=path):
                self.assertEqual(sha256((v2.ROOT / path).read_bytes()).hexdigest(), digest)
        self.assertEqual(v21.BASE_MANIFEST_SHA256, NORMALIZED[v21.BASE_MANIFEST])
        self.assertEqual(dict(v2.PINS.values()), RAW)  # the v2 validator's own pins are unchanged too

    def test_v2_still_validates_with_its_original_expectations(self):
        result = v2.validate_manifest()
        self.assertEqual(result.data["manifest_version"], "catalogue-v2.0")
        self.assertEqual(dict(result.counts)["default_bindings"], 106)
        self.assertIn(("Admin", ORDINARY), pairs(result.data))  # v2 itself is not revised in place
        self.assertNotIn((TSA, ORDINARY), pairs(result.data))


class CatalogueV21Tests(unittest.TestCase):
    def setUp(self):
        self.delta = v21.read_delta()
        self.base = v2.read_manifest()
        self.addendum = (v21.ROOT / v21.ADDENDUM).read_bytes()

    def invalid(self, message=".", **kwargs):
        kwargs.setdefault("delta", self.delta)
        with self.assertRaisesRegex(v21.CatalogueV21ValidationError, message):
            v21.validate_catalogue(**kwargs)

    # -- valid overlay ------------------------------------------------------------------------
    def test_valid_addendum_and_exact_counts(self):
        result = v21.validate_catalogue()
        self.assertEqual(dict(result.counts), dict(
            services=10, permissions=95, roles=6, default_bindings=106, retained=79, revised=2, added=14, retired=1,
            blocked=14, internal_contracts=9, planned=72, admin_defaults=34, technical_super_admin_defaults=11,
            moved_bindings=1, restated_eligibility=2))
        self.assertEqual(dict(result.base_counts), dict(v2.validate_manifest().counts))
        self.assertEqual({k: result.data[k] for k in v21.RESULT_VERSIONS}, v21.RESULT_VERSIONS)
        self.assertTrue(result.data["planning_only"])
        self.assertEqual(result.data["revision"]["independent_review"], "OPEN")
        self.assertEqual(result.data["revision"]["database_provisioning"], "NOT_AUTHORIZED")
        self.assertEqual(result.data["revision"]["addendum"]["sha256"], sha256(self.addendum).hexdigest())

    def test_effective_catalogue_is_deterministic_and_immutable(self):
        first, second = v21.validate_catalogue(), v21.validate_catalogue()
        self.assertEqual(first.digest, second.digest)
        self.assertRegex(first.digest, r"\A[0-9a-f]{64}\Z")
        with self.assertRaises(TypeError):
            first.data["default_bindings"][0] = None
        with self.assertRaises(TypeError):
            first.data["revision"]["independent_review"] = "SIGNED"

    def test_exact_permission_binding_change(self):
        before, after = pairs(self.base), pairs(v21.validate_catalogue().data)
        self.assertEqual(set(before) - set(after), {("Admin", ORDINARY)})
        self.assertEqual(set(after) - set(before), {(TSA, ORDINARY)})
        index = before.index(("Admin", ORDINARY))
        self.assertEqual(after[index], (TSA, ORDINARY))  # moved in place; nothing else reordered
        self.assertEqual(after[:index] + after[index + 1:], before[:index] + before[index + 1:])

    def test_school_admin_holds_no_access_control_management_default(self):
        after = pairs(v21.validate_catalogue().data)
        admin = {code for role, code in after if role == "Admin"}
        self.assertNotIn(ORDINARY, admin)
        self.assertEqual({c for c in admin if c.startswith("access_control.") and c.endswith(".manage")}, set())
        # Admin keeps its two read-only access_control defaults unchanged (not part of this decision).
        self.assertEqual({c for c in admin if c.startswith("access_control.")},
                         {"access_control.school_access.inspect", "access_control.audit.school.read"})

    def test_technical_super_admin_binding_and_composition(self):
        data = v21.validate_catalogue().data
        technical = {code for role, code in pairs(data) if role == TSA}
        governance = set(data["composition"]["application_super_admin"]["required_effective_permissions"])
        v2_technical = {code for role, code in pairs(self.base) if role == TSA}
        self.assertEqual(technical, v2_technical | {ORDINARY})  # exactly one new default
        self.assertIn(ORDINARY, technical)
        self.assertTrue(governance <= technical)
        self.assertEqual(len(technical), 11)
        services = {p["permission_code"]: p["service_code"] for p in data["permissions"]}
        self.assertTrue(all(services[c] in {"accounts", "access_control"} for c in technical))
        self.assertEqual(list(data["composition"]["application_super_admin"]["required_roles"]), ["Admin", TSA])
        self.assertFalse(data["composition"]["application_super_admin"]["framework_privilege_implied"])
        auth = data["composition"]["authorization"]
        self.assertTrue(auth["explicit_deny_precedence"])
        self.assertFalse(auth["role_names_are_bypass"])
        self.assertFalse(auth["django_superuser_is_application_bypass"])
        self.assertIn(("Instructor", "Admin", TSA), data["composition"]["required_multi_role_combinations"])

    def test_wf01_wf02_and_every_other_definition_is_preserved(self):
        data = v21.validate_catalogue().data
        for key in v21.UNCHANGED_KEYS:
            with self.subTest(key=key):
                self.assertEqual(json.dumps(_thaw(data[key]), sort_keys=True), json.dumps(self.base[key], sort_keys=True))
        accounts = [(r, c) for r, c in pairs(self.base) if c.startswith("accounts.")]
        self.assertEqual([(r, c) for r, c in pairs(data) if c.startswith("accounts.")], accounts)
        self.assertGreater(len(accounts), 0)
        eligibility = {r["role_name"]: r["requirement"] for r in data["role_eligibility"]}
        old = {r["role_name"]: r["requirement"] for r in self.base["role_eligibility"]}
        self.assertEqual({r for r in old if old[r] != eligibility[r]}, {"Admin", TSA})
        self.assertIn("retains Instructor", eligibility["Admin"])
        self.assertIn("only by the Django Superuser", eligibility[TSA])

    def test_existing_governance_restrictions_hold(self):
        data = v21.validate_catalogue().data
        bound = {}
        for role, code in pairs(data):
            bound.setdefault(code, set()).add(role)
        for code in data["composition"]["application_super_admin"]["required_effective_permissions"]:
            self.assertEqual(bound[code], {TSA}, code)
        self.assertNotIn("access_control.governance_assignments.manage", bound)
        blocked = {p["permission_code"] for p in data["permissions"] if p["readiness"] == "B"}
        self.assertFalse(blocked & set(bound))
        self.assertEqual(data["delegation"]["status"], "OFF")
        self.assertEqual(set(data["operational_gates"].values()), {"BLOCKED"})

    # -- tampered or unauthorized changes -------------------------------------------------------
    def op(self, index=0):
        return self.delta["operations"][index]

    def test_unauthorized_binding_changes_are_refused(self):
        cases = {
            "other permission": lambda: self.op().update(permission_code="access_control.school_access.inspect"),
            "other target role": lambda: self.op().update(to_role="SSG Advisor"),
            "other source role": lambda: self.op().update(from_role="Instructor"),
            "governance code": lambda: self.op().update(permission_code="access_control.audit.read", from_role=TSA, to_role="Admin"),
            "blocked governance code": lambda: self.op().update(permission_code="access_control.governance_assignments.manage"),
            "added binding op": lambda: self.delta["operations"].append(
                {"op": "add_default_binding", "permission_code": ORDINARY, "role_name": "Admin"}),
            "added permission op": lambda: self.delta["operations"].append(
                {"op": "add_permission", "permission_code": "access_control.extra.manage"}),
            "added role op": lambda: self.delta["operations"].append({"op": "add_role", "role_name": "Owner"}),
            "added service op": lambda: self.delta["operations"].append({"op": "add_service", "service_code": "extra"}),
            "duplicated move": lambda: self.delta["operations"].insert(1, deepcopy(self.op())),
            "missing move": lambda: self.delta["operations"].pop(0),
            "missing eligibility": lambda: self.delta["operations"].pop(),
            "eligibility for another role": lambda: self.op(1).update(role_name="Treasurer"),
            "altered eligibility text": lambda: self.op(1).update(new="Any account."),
            "reordered operations": lambda: self.delta["operations"].reverse(),
            "extra attribute": lambda: self.op().update(scope="ALL"),
            "missing attribute": lambda: self.op().pop("from_role"),
            "malformed operation": lambda: self.delta["operations"].__setitem__(0, ["move", ORDINARY]),
            "non-list operations": lambda: self.delta.__setitem__("operations", {}),
            "extra top-level field": lambda: self.delta.__setitem__("composition", {}),
            "missing top-level field": lambda: self.delta.pop("independent_review"),
            "review marked signed": lambda: self.delta["independent_review"].update(status="SIGNED"),
            "result version": lambda: self.delta["result"].update(manifest_version="catalogue-v3.0"),
            "base digest": lambda: self.delta["base"].update(sha256="0" * 64),
            "recorded addendum digest": lambda: self.delta["addendum"].update(sha256="0" * 64),
        }
        for name, tamper in cases.items():
            with self.subTest(name):
                self.delta = v21.read_delta()
                tamper()
                self.invalid()

    def test_tampered_addendum_is_refused_by_the_pin(self):
        for name, raw in {
            "edited delta row": self.addendum.replace(b"| Admin | Technical Super Admin |", b"| Admin | SSG Advisor |"),
            "added row": self.addendum.replace(
                b"| access_control.role_assignments.ordinary.manage | Admin | Technical Super Admin |",
                b"| access_control.role_assignments.ordinary.manage | Admin | Technical Super Admin |\n"
                b"| access_control.school_access.inspect | Admin | Technical Super Admin |"),
            "CRLF conversion": self.addendum.replace(b"\n", b"\r\n"),
            "trailing whitespace": self.addendum + b" ",
        }.items():
            with self.subTest(name):
                self.assertNotEqual(raw, self.addendum)
                self.invalid("addendum digest mismatch", addendum_bytes=raw)

    def test_a_self_consistent_but_unpinned_addendum_is_still_refused(self):
        # Re-pinning the delta's own record is not enough: only the validator's constant is trusted.
        raw = self.addendum.replace(b"retains Instructor.", b"retains Instructor and Treasurer.")
        self.delta["addendum"]["sha256"] = sha256(raw).hexdigest()
        self.invalid("addendum digest mismatch", addendum_bytes=raw)

    def test_addendum_content_is_checked_against_the_authorized_change(self):
        # Even with a matching pin the parsed tables must equal the authorized constants.
        raw = self.addendum.replace(b"| Admin | Technical Super Admin |", b"| Admin | SSG Advisor |")
        with unittest.mock.patch.object(v21, "ADDENDUM_SHA256", sha256(raw).hexdigest()):
            self.invalid("binding moves differ", addendum_bytes=raw)
        raw = self.addendum.replace(b"| manifest_version | catalogue-v2.1 |", b"| manifest_version | catalogue-v9 |")
        with unittest.mock.patch.object(v21, "ADDENDUM_SHA256", sha256(raw).hexdigest()):
            self.invalid("result versions differ", addendum_bytes=raw)
        raw = self.addendum.replace(b"| Technical Super Admin | Granted", b"| Treasurer | Granted")
        with unittest.mock.patch.object(v21, "ADDENDUM_SHA256", sha256(raw).hexdigest()):
            self.invalid("eligibility scope differs", addendum_bytes=raw)

    def test_tampered_base_manifest_is_refused(self):
        raw = v21.normalized_lf((v21.ROOT / v21.BASE_MANIFEST).read_bytes())
        for variant in (raw, raw.replace(b"\n", b"\r\n")):  # LF and CRLF checkouts are the same content
            self.assertEqual(v21.validate_catalogue(base_manifest_bytes=variant).digest, v21.validate_catalogue().digest)
        changed = raw.replace(b'"role_name": "Admin",\n      "permission_code": "access_control.role_assignments.ordinary.manage"',
                              b'"role_name": "Technical Super Admin",\n      "permission_code": "access_control.role_assignments.ordinary.manage"')
        self.assertNotEqual(changed, raw)
        self.invalid("v2 manifest digest mismatch", base_manifest_bytes=changed)
        self.invalid("v2 manifest digest mismatch", base_manifest_bytes=raw + b"\n")
        # A base that matches the pin but fails the original validator is refused by it (pin patched for the test).
        data = json.loads(raw)
        data["composition"]["application_super_admin"]["framework_privilege_implied"] = True
        bad = json.dumps(data, indent=2).encode()
        with unittest.mock.patch.object(v21, "BASE_MANIFEST_SHA256", sha256(bad).hexdigest()):
            self.invalid("base v2 catalogue does not validate", base_manifest_bytes=bad)

    def test_invalid_administrator_composition_or_guarantee_on_the_result_is_refused(self):
        base = v2.read_manifest()
        mutations = {
            "composition": lambda d: d["composition"]["application_super_admin"]["required_roles"].remove("Admin"),
            "deny precedence": lambda d: d["composition"]["authorization"].update(explicit_deny_precedence=False),
            "superuser bypass": lambda d: d["composition"]["authorization"].update(django_superuser_is_application_bypass=True),
            "gate opened": lambda d: d["operational_gates"].update(grants="OPEN"),
            "permission attribute": lambda d: d["permissions"][0].update(description="Changed"),
            "extra permission": lambda d: d["permissions"].append(deepcopy(d["permissions"][0])),
            "extra service": lambda d: d["services"].append({"service_code": "extra", "service_name": "Extra"}),
            "extra role": lambda d: d["roles"].append({"role_name": "Owner", "description": "x", "provisioning": "x"}),
            "planning flag": lambda d: d.update(planning_only=False),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                data = v21._apply(base, self.delta)
                mutate(data)
                with self.assertRaises(v21.CatalogueV21ValidationError):
                    v21._check_guarantees(base, data)
        binding_mutations = {
            "duplicate binding": lambda d: d["default_bindings"].append(deepcopy(d["default_bindings"][0])),
            "missing binding": lambda d: d["default_bindings"].pop(0),
            "governance to Admin": lambda d: d["default_bindings"].__setitem__(
                0, {"role_name": "Admin", "permission_code": "access_control.audit.read"}),
            "business default for the technical role": lambda d: d["default_bindings"].__setitem__(
                0, {"role_name": TSA, "permission_code": "finance.monitoring.overview.read"}),
            "reordered": lambda d: d["default_bindings"].reverse(),
            "ordinary code back to Admin": lambda d: [b.update(role_name="Admin") for b in d["default_bindings"]
                                                      if b["permission_code"] == ORDINARY],
        }
        for name, mutate in binding_mutations.items():
            with self.subTest(name):
                data = v21._apply(base, self.delta)
                mutate(data)
                with self.assertRaises(v21.CatalogueV21ValidationError):
                    v21._check_guarantees(base, data)

    def test_malformed_delta_json_is_refused(self):
        for raw in (b'{"a": 1, "a": 2}', b'{"x": NaN}', b"not json", b"\xff\xfe"):
            with self.subTest(raw=raw), unittest.mock.patch("pathlib.Path.read_bytes", return_value=raw):
                with self.assertRaises(v21.CatalogueV21ValidationError):
                    v21.read_delta()
        with unittest.mock.patch("pathlib.Path.read_bytes", side_effect=OSError):
            with self.assertRaisesRegex(v21.CatalogueV21ValidationError, "delta is unavailable"):
                v21.read_delta()

    def test_import_and_validation_work_with_django_imports_forbidden(self):
        code = """
import sys
class NoDjango:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'django' or fullname.startswith('django.'):
            raise AssertionError('Django import is forbidden for static v2.1 validation')
sys.meta_path.insert(0, NoDjango())
from apps.access_control.catalogue.validation_v2_1 import validate_catalogue
assert validate_catalogue().counts['technical_super_admin_defaults'] == 11
print('stdlib-only v2.1 validation passed')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=v2.ROOT / "backend",
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "stdlib-only v2.1 validation passed")


def _thaw(value):
    if isinstance(value, dict) or type(value).__name__ == "mappingproxy":
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


if __name__ == "__main__":
    unittest.main()
