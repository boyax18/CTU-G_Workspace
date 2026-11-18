"""WF-03.01 D-103 Option A: Permission Catalogue v2.2 overlay. Standard-library-only tests: no Django or database.

Run: python manage.py test apps.access_control.test_catalogue_v2_2 --settings=config.test_settings --noinput
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
from .catalogue import validation_v2_2 as v22
from .test_catalogue_v2_1 import TAMPERED_SECOND_READS, disk_sha256, manifest_on_disk, replace_with

TSA = "Technical Super Admin"
INSPECT = "access_control.school_access.inspect"
SCHOOL_AUDIT = "access_control.audit.school.read"
ORDINARY = "access_control.role_assignments.ordinary.manage"
# Recorded independently before D-103 (at 14125f9). v2_0.json is compared LF-normalized (= Git blob).
NORMALIZED = {
    "backend/apps/access_control/catalogue/v2_0.json": "a7e2705236a37522b77468fd4154113d19e7e64bc479cfa420c41d7744a2548b",
    "backend/apps/access_control/catalogue/validation_v2.py": "f6b83305db567dcafc57eba97011554587be4b65d6d3c7116dc6a80b9a756aa4",
    "backend/apps/access_control/catalogue/v2_1_delta.json": "b028a419bdc66a19a782f6a968464ffb2f4cec7e10630ec4c169e6cda549d3d8",
    # Revised by the D-101 F-1 correction (was 79e46cfc2790f4370f85c66aec12512102cb37e320cc9a5307181f88a036fa91 at
    # 14125f9): the v2 base is parsed only from the verified bytes; pins and effective digests are unchanged.
    "backend/apps/access_control/catalogue/validation_v2_1.py": "e176f9267b69baae7546d060064254d26a3e7df7a106b6505e941cb5b83d98b3",
}
RAW = {
    "docs/architecture/AR-3B2A-ADDENDUM-v2.1.md": "78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7",
    "backend/apps/access_control/catalogue/c1_v1.json": "86d72d82295cb358244145c6d24ebe8ba948f5211de298ebf897b5d3d83ed447",
    "docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md": "56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78",
    "docs/architecture/AR-2-revised-administrator-access-control.md": "b36c0dac6d18badc435cce242725d2d6424db9d7e12d6d4943f20c7eaaf8ce36",
    "docs/architecture/AR-3A-administrator-architecture-finalization.md": "464c0fec172ef5ba887dbc22ec5b09c3396ca1be53087d999bbf763966edded1",
    "docs/SRS/CTU-G_Workspace_SRS_v1.md": "af4ead4f88bdb0877ab6c3b8965bec5caf0f058d74ab0d878ec690379210346f",
    "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md":
        "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e",
}
V21_DIGEST = "1adb16465e9d32712f890a95ee13dd5f21f4441790715aeaf91aa10c53183362"
V22_DIGEST = "192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d"


def pairs(data):
    return [(b["role_name"], b["permission_code"]) for b in data["default_bindings"]]


class PreservedV2AndV21Tests(unittest.TestCase):
    def test_v2_and_v21_files_and_pins_are_unchanged(self):
        for path, digest in NORMALIZED.items():
            with self.subTest(path=path):
                self.assertEqual(sha256(v21.normalized_lf((v2.ROOT / path).read_bytes())).hexdigest(), digest)
        for path, digest in RAW.items():
            with self.subTest(path=path):
                self.assertEqual(sha256((v2.ROOT / path).read_bytes()).hexdigest(), digest)
        self.assertEqual(v21.ADDENDUM_SHA256, RAW["docs/architecture/AR-3B2A-ADDENDUM-v2.1.md"])
        self.assertEqual(v21.BASE_MANIFEST_SHA256, NORMALIZED["backend/apps/access_control/catalogue/v2_0.json"])

    def test_v2_and_v21_still_validate_with_their_own_expectations(self):
        self.assertEqual(dict(v2.validate_manifest().counts)["default_bindings"], 106)
        base = v21.validate_catalogue()
        self.assertEqual(base.digest, V21_DIGEST)
        self.assertEqual((base.counts["admin_defaults"], base.counts["technical_super_admin_defaults"]), (34, 11))
        self.assertIn(("Admin", INSPECT), pairs(base.data))  # v2.1 itself is not revised in place
        self.assertIn(("Admin", SCHOOL_AUDIT), pairs(base.data))


class CatalogueV22Tests(unittest.TestCase):
    def setUp(self):
        self.delta = v22.read_delta()
        self.addendum = (v22.ROOT / v22.ADDENDUM).read_bytes()
        self.base = v22._thaw(v21.validate_catalogue().data)

    def invalid(self, message=".", **kwargs):
        kwargs.setdefault("delta", self.delta)
        with self.assertRaisesRegex(v22.CatalogueV22ValidationError, message):
            v22.validate_catalogue(**kwargs)

    # -- valid overlay ------------------------------------------------------------------------
    def test_valid_addendum_counts_and_deterministic_digest(self):
        first, second = v22.validate_catalogue(), v22.validate_catalogue()
        self.assertEqual(dict(first.counts), dict(
            services=10, permissions=95, roles=6, default_bindings=106, retained=79, revised=2, added=14, retired=1,
            blocked=14, internal_contracts=9, planned=72, admin_defaults=32, technical_super_admin_defaults=13,
            moved_bindings=2, admin_access_control_defaults=0))
        self.assertEqual(first.base_digest, V21_DIGEST)
        self.assertEqual(first.digest, second.digest)
        self.assertRegex(first.digest, r"\A[0-9a-f]{64}\Z")
        self.assertNotEqual(first.digest, V21_DIGEST)
        self.assertEqual({k: first.data[k] for k in v22.RESULT_VERSIONS}, v22.RESULT_VERSIONS)
        revision = first.data["revision"]
        self.assertEqual((revision["independent_review"], revision["database_provisioning"]), ("OPEN", "NOT_AUTHORIZED"))
        self.assertEqual(revision["addendum"]["sha256"], sha256(self.addendum).hexdigest())
        self.assertEqual(revision["previous_revision"]["addendum"]["sha256"], v21.ADDENDUM_SHA256)
        self.assertTrue(first.data["planning_only"])
        with self.assertRaises(TypeError):
            first.data["default_bindings"][0] = None

    def test_exact_two_binding_moves_in_place(self):
        before, after = pairs(self.base), pairs(v22.validate_catalogue().data)
        self.assertEqual(before[97], ("Admin", INSPECT))
        self.assertEqual(before[102], ("Admin", SCHOOL_AUDIT))
        self.assertEqual(after[97], (TSA, INSPECT))
        self.assertEqual(after[102], (TSA, SCHOOL_AUDIT))
        self.assertEqual(set(before) - set(after), {("Admin", INSPECT), ("Admin", SCHOOL_AUDIT)})
        self.assertEqual(set(after) - set(before), {(TSA, INSPECT), (TSA, SCHOOL_AUDIT)})
        self.assertEqual([p for i, p in enumerate(after) if i not in (97, 102)],
                         [p for i, p in enumerate(before) if i not in (97, 102)])
        self.assertEqual(len(after), 106)

    def test_school_admin_holds_no_access_control_default_and_keeps_wf02(self):
        data = v22.validate_catalogue().data
        admin = {code for role, code in pairs(data) if role == "Admin"}
        self.assertEqual({c for c in admin if c.startswith("access_control.")}, set())
        self.assertEqual(len(admin), 32)
        for code in ("accounts.school_accounts.read", "accounts.school_accounts.suspend", "accounts.school_accounts.activate",
                     "accounts.registration_requests.read", "accounts.authentication_events.school.read"):
            self.assertIn(code, admin, code)
        self.assertEqual([p for p in pairs(data) if p[1].startswith("accounts.")],
                         [p for p in pairs(self.base) if p[1].startswith("accounts.")])

    def test_technical_super_admin_defaults_and_composition(self):
        data = v22.validate_catalogue().data
        technical = {code for role, code in pairs(data) if role == TSA}
        self.assertEqual(technical, {code for role, code in pairs(self.base) if role == TSA} | {INSPECT, SCHOOL_AUDIT})
        self.assertEqual(len(technical), 13)
        services = {p["permission_code"]: p["service_code"] for p in data["permissions"]}
        self.assertTrue(all(services[c] in {"accounts", "access_control"} for c in technical))
        composition = data["composition"]["application_super_admin"]
        self.assertEqual(list(composition["required_roles"]), ["Admin", TSA])
        self.assertNotIn(INSPECT, composition["required_effective_permissions"])  # not part of the governance profile
        self.assertNotIn(SCHOOL_AUDIT, composition["required_effective_permissions"])
        auth = data["composition"]["authorization"]
        self.assertTrue(auth["explicit_deny_precedence"])
        self.assertFalse(auth["role_names_are_bypass"] or auth["django_superuser_is_application_bypass"])

    def test_every_other_definition_is_preserved(self):
        data = v22.validate_catalogue().data
        for key in v22.UNCHANGED_KEYS:
            with self.subTest(key=key):
                self.assertEqual(json.dumps(v22._thaw(data[key]), sort_keys=True), json.dumps(self.base[key], sort_keys=True))
        definitions = {p["permission_code"]: p for p in data["permissions"]}
        self.assertEqual((definitions[INSPECT]["scope"], definitions[SCHOOL_AUDIT]["scope"]), ("SCHOOL", "SCHOOL_AUDIT"))
        self.assertEqual((definitions[INSPECT]["readiness"], definitions[SCHOOL_AUDIT]["readiness"]), ("P", "P"))

    def test_no_wf12_audit_widening(self):
        # The only audit defaults are unchanged except the narrow school projection moving to the role that
        # already holds the broader access_control.audit.read; nothing becomes ready, unblocked or ungated.
        data = v22.validate_catalogue().data
        audit = {code: sorted(r for r, c in pairs(data) if c == code)
                 for code in (p["permission_code"] for p in data["permissions"]) if ".audit" in code or "authentication_events" in code}
        self.assertEqual(audit, {"access_control.audit.read": [TSA], SCHOOL_AUDIT: [TSA],
                                 "accounts.authentication_events.school.read": ["Admin"],
                                 "accounts.authentication_events.governance.read": [TSA]})
        self.assertEqual(set(data["operational_gates"].values()), {"BLOCKED"})
        self.assertTrue(all(p["readiness"] != "F" for p in data["permissions"] if p["permission_code"] in audit))

    # -- unauthorized or tampered changes -------------------------------------------------------
    def op(self, index=0):
        return self.delta["operations"][index]

    def test_unauthorized_delta_changes_are_refused(self):
        cases = {
            "other permission": lambda: self.op().update(permission_code="accounts.school_accounts.read"),
            "governance code": lambda: self.op().update(permission_code="access_control.audit.read", from_role=TSA, to_role="Admin"),
            "ordinary code back to Admin": lambda: self.op().update(permission_code=ORDINARY, from_role=TSA, to_role="Admin"),
            "other target role": lambda: self.op(1).update(to_role="SSG Advisor"),
            "other source role": lambda: self.op().update(from_role="Instructor"),
            "third move": lambda: self.delta["operations"].append(
                {"op": "move_default_binding", "permission_code": "accounts.authentication_events.school.read",
                 "from_role": "Admin", "to_role": TSA}),
            "added permission": lambda: self.delta["operations"].append({"op": "add_permission", "permission_code": "access_control.x.read"}),
            "added role": lambda: self.delta["operations"].append({"op": "add_role", "role_name": "Owner"}),
            "added service": lambda: self.delta["operations"].append({"op": "add_service", "service_code": "extra"}),
            "duplicated move": lambda: self.delta["operations"].append(deepcopy(self.op())),
            "missing first move": lambda: self.delta["operations"].pop(0),
            "missing second move": lambda: self.delta["operations"].pop(),
            "reordered moves": lambda: self.delta["operations"].reverse(),
            "eligibility restatement": lambda: self.delta["operations"].append(
                {"op": "restate_role_eligibility", "role_name": "Admin", "old": "x", "new": "y"}),
            "extra attribute": lambda: self.op().update(scope="ALL"),
            "missing attribute": lambda: self.op().pop("to_role"),
            "malformed operation": lambda: self.delta["operations"].__setitem__(0, ["move", INSPECT]),
            "non-list operations": lambda: self.delta.__setitem__("operations", {}),
            "extra top-level field": lambda: self.delta.__setitem__("composition", {}),
            "missing top-level field": lambda: self.delta.pop("independent_review"),
            "review marked signed": lambda: self.delta["independent_review"].update(status="SIGNED"),
            "result version": lambda: self.delta["result"].update(manifest_version="catalogue-v3.0"),
            "base digest": lambda: self.delta["base"].update(effective_digest="0" * 64),
            "base addendum digest": lambda: self.delta["base"].update(addendum_sha256="0" * 64),
            "recorded addendum digest": lambda: self.delta["addendum"].update(sha256="0" * 64),
        }
        for name, tamper in cases.items():
            with self.subTest(name):
                self.delta = v22.read_delta()
                tamper()
                self.invalid()

    def test_tampered_addendum_is_refused_by_the_pin(self):
        for name, raw in {
            "edited move": self.addendum.replace(b"| access_control.audit.school.read | Admin |", b"| access_control.audit.read | Admin |"),
            "added row": self.addendum.replace(
                b"| access_control.audit.school.read | Admin | Technical Super Admin |",
                b"| access_control.audit.school.read | Admin | Technical Super Admin |\n"
                b"| accounts.school_accounts.read | Admin | Technical Super Admin |"),
            "CRLF conversion": self.addendum.replace(b"\n", b"\r\n"),
            "trailing whitespace": self.addendum + b" ",
        }.items():
            with self.subTest(name):
                self.assertNotEqual(raw, self.addendum)
                self.invalid("v2.2 addendum digest mismatch", addendum_bytes=raw)

    def test_a_self_consistent_but_unpinned_addendum_is_still_refused(self):
        raw = self.addendum.replace(b"Admin keeps 32 defaults", b"Admin keeps 31 defaults")
        self.delta["addendum"]["sha256"] = sha256(raw).hexdigest()
        self.invalid("v2.2 addendum digest mismatch", addendum_bytes=raw)

    def test_pinned_but_unauthorized_addendum_content_is_refused(self):
        variants = {
            "binding moves differ": self.addendum.replace(
                b"| access_control.school_access.inspect | Admin | Technical Super Admin |",
                b"| access_control.school_access.inspect | Admin | SSG Advisor |"),
            "result versions differ": self.addendum.replace(b"| manifest_version | catalogue-v2.2 |",
                                                            b"| manifest_version | catalogue-v9 |"),
            "base catalogue differs": self.addendum.replace(V21_DIGEST.encode(), b"0" * 64),
            "base table differs": self.addendum.replace(b"| base_effective_digest_rule |", b"| base_rule |"),
        }
        for message, raw in variants.items():
            with self.subTest(message), unittest.mock.patch.object(v22, "ADDENDUM_SHA256", sha256(raw).hexdigest()):
                self.assertNotEqual(raw, self.addendum)
                self.invalid(message, addendum_bytes=raw)

    def test_tampered_or_unpinned_base_chain_is_refused(self):
        v21_delta = v21.read_delta()
        v21_delta["operations"][0]["to_role"] = "SSG Advisor"
        self.invalid("base v2.1 catalogue does not validate", v21_delta=v21_delta)
        v21_addendum = (v2.ROOT / v21.ADDENDUM).read_bytes() + b" "
        self.invalid("base v2.1 catalogue does not validate", v21_addendum_bytes=v21_addendum)
        manifest = v21.normalized_lf((v2.ROOT / v21.BASE_MANIFEST).read_bytes())
        self.invalid("base v2.1 catalogue does not validate", base_manifest_bytes=manifest + b"\n")
        with unittest.mock.patch.object(v22, "BASE_EFFECTIVE_DIGEST", "0" * 64):
            self.invalid("Effective v2.1 digest mismatch")
        with unittest.mock.patch.object(v22, "BASE_ADDENDUM_SHA256", "0" * 64):
            self.invalid("v2.1 addendum pin differs")

    def test_invalid_compositions_and_guarantees_on_the_result_are_refused(self):
        mutations = {
            "composition roles": lambda d: d["composition"]["application_super_admin"]["required_roles"].remove("Admin"),
            "composition codes": lambda d: d["composition"]["application_super_admin"]["required_effective_permissions"].append(INSPECT),
            "framework privilege": lambda d: d["composition"]["application_super_admin"].update(framework_privilege_implied=True),
            "deny precedence": lambda d: d["composition"]["authorization"].update(explicit_deny_precedence=False),
            "superuser bypass": lambda d: d["composition"]["authorization"].update(django_superuser_is_application_bypass=True),
            "gate opened": lambda d: d["operational_gates"].update(grants="OPEN"),
            "permission attribute": lambda d: d["permissions"][0].update(description="Changed"),
            "audit readiness": lambda d: [p.update(readiness="F") for p in d["permissions"] if p["permission_code"] == SCHOOL_AUDIT],
            "eligibility": lambda d: d["role_eligibility"][3].update(requirement="Any account."),
            "planning flag": lambda d: d.update(planning_only=False),
            "duplicate binding": lambda d: d["default_bindings"].append(deepcopy(d["default_bindings"][0])),
            "missing binding": lambda d: d["default_bindings"].pop(0),
            "Admin keeps inspect": lambda d: d["default_bindings"].__setitem__(97, {"role_name": "Admin", "permission_code": INSPECT}),
            "Admin gains another access_control code": lambda d: d["default_bindings"].__setitem__(
                0, {"role_name": "Admin", "permission_code": "access_control.catalogue.read"}),
            "governance to Admin": lambda d: [b.update(role_name="Admin") for b in d["default_bindings"]
                                              if b["permission_code"] == "access_control.audit.read"],
            "business default for the technical role": lambda d: d["default_bindings"].__setitem__(
                0, {"role_name": TSA, "permission_code": "finance.monitoring.overview.read"}),
            "WF-02 binding moved": lambda d: [b.update(role_name=TSA) for b in d["default_bindings"]
                                              if b == {"role_name": "Admin", "permission_code": "accounts.school_accounts.read"}],
            "reordered": lambda d: d["default_bindings"].reverse(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                data = v22._apply(self.base, self.delta)
                mutate(data)
                with self.assertRaises(v22.CatalogueV22ValidationError):
                    v22._check_guarantees(self.base, data)

    def test_malformed_delta_json_is_refused(self):
        for raw in (b'{"a": 1, "a": 2}', b'{"x": NaN}', b"not json", b"\xff\xfe"):
            with self.subTest(raw=raw), unittest.mock.patch("pathlib.Path.read_bytes", return_value=raw):
                with self.assertRaises(v22.CatalogueV22ValidationError):
                    v22.read_delta()
        with unittest.mock.patch("pathlib.Path.read_bytes", side_effect=OSError):
            with self.assertRaisesRegex(v22.CatalogueV22ValidationError, "delta is unavailable"):
                v22.read_delta()

    def test_import_and_validation_work_with_django_imports_forbidden(self):
        code = """
import sys
class NoDjango:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'django' or fullname.startswith('django.'):
            raise AssertionError('Django import is forbidden for static v2.2 validation')
sys.meta_path.insert(0, NoDjango())
from apps.access_control.catalogue.validation_v2_2 import validate_catalogue
assert validate_catalogue().counts['admin_access_control_defaults'] == 0
print('stdlib-only v2.2 validation passed')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=v2.ROOT / "backend",
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "stdlib-only v2.2 validation passed")


class ChainSingleVerifiedReadTests(unittest.TestCase):
    """D-101 F-1 through the chain: a v2 manifest replaced on disk after its verified read never reaches v2.2."""

    def test_chain_ignores_a_manifest_replaced_after_its_verified_read(self):
        for label, change in TAMPERED_SECOND_READS.items():
            with self.subTest(label), manifest_on_disk(replace_with(change)) as reads:
                result = v22.validate_catalogue()
                self.assertNotEqual(disk_sha256(v2.MANIFEST_PATH), reads[0])  # really replaced (no false positive)
                self.assertEqual(len(reads), 1)
                self.assertEqual((result.base_digest, result.digest), (V21_DIGEST, V22_DIGEST))


if __name__ == "__main__":
    unittest.main()
