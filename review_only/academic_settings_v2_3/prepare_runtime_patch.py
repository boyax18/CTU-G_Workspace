"""Produce review text only; never replace application files. Used by isolated candidate tests too."""
from difflib import unified_diff
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def proposed_files():
    changes = {}

    def replace(path, replacements):
        text = (ROOT / path).read_text(encoding="utf-8")
        for old, new in replacements:
            if text.count(old) != 1:
                raise ValueError(f"Patch precondition differs in {path}: {old[:70]}")
            text = text.replace(old, new)
        changes[path] = text

    replace("backend/apps/access_control/services.py", [
        ("from .ordinary_role_runtime import (", "from .permission_transitions import preserve_transition_denies\nfrom .ordinary_role_runtime import ("),
        ("    return (\n        Permission.objects.using(DEFAULT_DB_ALIAS)",
         "    permissions = (\n        Permission.objects.using(DEFAULT_DB_ALIAS)"),
        ("        .filter(grant_source)\n    )", "        .filter(grant_source)\n    )\n    return preserve_transition_denies(permissions, account_id)"),
    ])
    changes["backend/apps/access_control/permission_transitions.py"] = (
        HERE / "proposed/permission_transitions.py").read_text(encoding="utf-8")
    replace("backend/apps/academic/onboarding.py", [
        ('WRITE_CODE = "clearance.requests.self.submit"', 'WRITE_CODE = "academic.semester_onboarding.self.submit"'),
        ('``clearance.requests.self.submit`` (WF-06.01 "Request clearance" now happens at finalization). The',
         '``academic.semester_onboarding.self.submit`` (clearance creation is an internal consequence). The'),
        ('Draft writes and finalization use the pinned Student default', 'Draft writes and finalization use the reviewed Student permission'),
    ])
    replace("backend/apps/academic/verification.py", [
        ('VERIFY_CODE = "academic.profiles.manage"  # PROPOSED mapping (governance pending)',
         'VERIFY_CODE = "academic.enrollment_verifications.record"'),
        ('with the PROPOSED ``academic.profiles.manage`` mapping\n(the readiness review: do not assume it authorizes CTU verification until the object policy is\naccepted)',
         'with the exact ``academic.enrollment_verifications.record`` code'),
    ])
    replace("backend/apps/academic/historical_participation.py", [
        ('School Admin only (Admin path of services.authorize) with BOTH\n``academic.periods.manage`` (WF-11.01 authority) and the proposed ``academic.profiles.manage``\n(verification records),',
         'School Admin only (Admin path of services.authorize) with\n``academic.historical_participation.correct``, '),
        ('PERIOD_CODE = "academic.periods.manage"\nPROFILE_CODE = "academic.profiles.manage"',
         'CORRECTION_CODE = "academic.historical_participation.correct"'),
        ('    services.authorize(actor, PROFILE_CODE, gate=correction_enabled)\n    return services.authorize(actor, PERIOD_CODE, gate=correction_enabled)',
         '    return services.authorize(actor, CORRECTION_CODE, gate=correction_enabled)'),
        ('            services.lock_and_authorize(actor, PROFILE_CODE, gate=correction_enabled)\n            auth = services.lock_and_authorize(actor, PERIOD_CODE, gate=correction_enabled)',
         '            auth = services.lock_and_authorize(actor, CORRECTION_CODE, gate=correction_enabled)'),
    ])
    replace("frontend/src/features/onboarding/onboardingConfig.ts", [
        ("ONBOARDING_WRITE_CODE = 'clearance.requests.self.submit'", "ONBOARDING_WRITE_CODE = 'academic.semester_onboarding.self.submit'"),
        ("VERIFICATION_CODE = 'academic.profiles.manage'", "VERIFICATION_CODE = 'academic.enrollment_verifications.record'"),
        ("export const VERIFICATION_CODE", "export const HISTORICAL_CORRECTION_CODE = 'academic.historical_participation.correct';\nexport const VERIFICATION_CODE"),
    ])
    replace("frontend/src/features/dashboard/navigation.ts", [
        ("requiredAny: ['academic.profiles.manage']", "requiredAny: ['academic.enrollment_verifications.record']"),
    ])
    replace("frontend/src/features/onboarding/EnrollmentVerificationPanel.tsx", [
        ("import { HISTORICAL_PARTICIPATION_CORRECTION_ENABLED }", "import { HISTORICAL_PARTICIPATION_CORRECTION_ENABLED, HISTORICAL_CORRECTION_CODE }"),
        ("import Modal from '../../components/common/Modal.tsx';",
         "import Modal from '../../components/common/Modal.tsx';\nimport { useDashboardContext } from '../../hooks/useDashboardContext';"),
        ("function StudentRecord({ student }: { student: StudentRef }) {",
         "function StudentRecord({ student }: { student: StudentRef }) {\n  const { session } = useDashboardContext();\n  const canCorrect = session.permissions.includes(HISTORICAL_CORRECTION_CODE);"),
        ("{HISTORICAL_PARTICIPATION_CORRECTION_ENABLED && historical", "{HISTORICAL_PARTICIPATION_CORRECTION_ENABLED && canCorrect && historical"),
        ("Django decides access on every request (proposed\n * academic.profiles.manage mapping,", "Django decides access on every request (exact\n * academic.enrollment_verifications.record code,"),
    ])
    replace("backend/apps/academic/dependencies.py", [
        ("Delegates to apps.academic.historical_participation.correct (School Admin, both\n"
         "    academic.periods.manage and academic.profiles.manage, its own default-off switch).",
         "Delegates to apps.academic.historical_participation.correct (School Admin with\n"
         "    academic.historical_participation.correct under dual control, its own default-off switch)."),
    ])
    replace("backend/apps/access_control/management/commands/provision_academic_settings_phase1_local_dev.py", [
        ("never installs v2.3; never runs in production settings.",
         "never installs v2.3 (its own reviewed command does; phase 1 accepts a restated v2.3 definition only\n"
         "with its exact receipt); never runs in production settings."),
        ("def _verify_metadata(services, permissions, service_defs, definitions, actor, active):\n"
         "    if set(services) != set(SERVICE_CODES) or set(permissions) != set(CODES):\n"
         "        raise AcademicPhase1Refused(\"Services or definitions are partial.\")\n",
         "def _restated(permissions, definitions):\n"
         "    \"\"\"Catalogue v2.3 restates two of these definitions; its text is accepted only with the exact receipt.\"\"\"\n"
         "    if not AccessAuditLog.objects.filter(action=\"workspace.academic_settings.v23.permission.restate\").exists():\n"
         "        return definitions\n"
         "    from apps.access_control.management.commands import provision_academic_settings_v2_3_local_dev as v23\n"
         "    try:\n"
         "        return v23.effective_definitions(permissions, definitions)\n"
         "    except Exception as exc:\n"
         "        raise AcademicPhase1Refused(\"Restated v2.3 definitions are not exactly receipted.\") from exc\n"
         "\n\n"
         "def _verify_metadata(services, permissions, service_defs, definitions, actor, active):\n"
         "    if set(services) != set(SERVICE_CODES) or set(permissions) != set(CODES):\n"
         "        raise AcademicPhase1Refused(\"Services or definitions are partial.\")\n"
         "    definitions = _restated(permissions, definitions)\n"),
    ])
    replace("backend/apps/academic/test_student_onboarding.py", [
        ("catalogue defaults (Student -> academic.profile.self.read and clearance.requests.self.submit; Admin ->\n"
         "academic.profiles.manage).",
         "catalogue v2.3 defaults (Student -> academic.profile.self.read and academic.semester_onboarding.self.submit;\n"
         "Admin -> academic.enrollment_verifications.record and academic.historical_participation.correct)."),
        ("from . import dependencies, eligibility, onboarding, services, teaching, verification\n",
         "from . import dependencies, eligibility, onboarding, services, teaching, verification\n"
         "from .historical_participation import CORRECTION_CODE as HISTORY\n"),
        ('        self.write = self._perm(self.clearance, WRITE, "Student")\n'
         '        self.verify = self._perm(self.service, VERIFY, "Admin")\n',
         '        self.write = self._perm(self.service, WRITE, "Student")  # v2.3: an academic-service code\n'
         '        self.verify = self._perm(self.service, VERIFY, "Admin")\n'
         '        self.history = self._perm(self.service, HISTORY, "Admin")  # v2.3: dual-controlled correction\n'),
        ("        # An inactive clearance service makes clearance.requests.self.submit ineffective (HDAC: Denied);\n"
         "        # an inactive academic or finance service makes the shared locks unavailable.\n"
         "        for code, expected in ((\"clearance\", services.AcademicPeriodDenied), (\"finance\", services.AcademicPeriodUnavailable),\n",
         "        # v2.3: the onboarding code belongs to the academic service, so an inactive clearance or finance\n"
         "        # service makes the shared locks unavailable; an inactive academic service refuses first.\n"
         "        for code, expected in ((\"clearance\", services.AcademicPeriodUnavailable), (\"finance\", services.AcademicPeriodUnavailable),\n"),
    ])
    boundary ="backend/apps/academic/test_student_dashboard_boundary.py"
    text = (ROOT / boundary).read_text(encoding="utf-8")
    start = text.index("    def test_proposed_governance_codes_stay_inactive(self):\n")
    end = text.index("\n\n\n", start) + 1
    replace(boundary, [
        ("PROPOSED governance codes stay inactive, and the fee-revision safeguard.",
         "legacy broad codes no longer authorize the narrow catalogue v2.3 operations, and the fee-revision safeguard."),
        (text[start:end],
         "    def test_legacy_broad_codes_no_longer_authorize_the_narrow_operations(self):\n"
         "        \"\"\"Catalogue v2.3: only the exact narrow codes authorize; the old broad codes never substitute.\"\"\"\n"
         "        for code, role in ((\"clearance.requests.self.submit\", \"Student\"), (\"academic.profiles.manage\", \"Admin\"),\n"
         "                           (\"academic.periods.manage\", \"Admin\")):\n"
         "            perm = Permission.objects.get_or_create(permission_code=code, defaults=dict(\n"
         "                service=self.w.service, permission_name=code, module_name=\"m\", action_name=\"a\"))[0]\n"
         "            RolePermission.objects.get_or_create(role=self.w.roles[role], permission=perm)\n"
         "        self.assertEqual((onboarding.WRITE_CODE, verification.VERIFY_CODE, hp.CORRECTION_CODE), tuple(PROPOSED.values()))\n"
         "        RolePermission.objects.filter(permission__permission_code__in=list(PROPOSED.values())).delete()\n"
         "        with self.assertRaises(services.AcademicPeriodDenied):\n"
         "            onboarding.save_student_type(actor=self.w.student, student_type=\"Regular\")\n"
         "        with self.assertRaises(services.AcademicPeriodDenied):\n"
         "            record(self.w, self.w.student, self.sem, self.cat, [\"MATH 101\"])\n"
         "        with self.assertRaises(services.AcademicPeriodDenied):\n"
         "            hp.preview(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.sem)\n"
         "        from pathlib import Path\n"
         "        catalogue = Path(__file__).resolve().parents[1] / \"access_control\" / \"catalogue\"\n"
         "        pinned = \"\".join((catalogue / name).read_text(encoding=\"utf-8\")\n"
         "                         for name in (\"v2_0.json\", \"v2_1_delta.json\", \"v2_2_delta.json\"))\n"
         "        for code in PROPOSED.values():\n"
         "            self.assertNotIn(code, pinned)  # the pinned v2.0-v2.2 files were never edited\n"),
    ])
    for name, target in (("validation_v2_3.py", "backend/apps/access_control/catalogue/validation_v2_3.py"),
                         ("provision_academic_settings_v2_3_local_dev.py",
                          "backend/apps/access_control/management/commands/provision_academic_settings_v2_3_local_dev.py"),
                         ("test_academic_v2_3_provisioning.py", "backend/apps/access_control/test_academic_v2_3_provisioning.py")):
        changes[target] = (HERE / "proposed" / name).read_text(encoding="utf-8")
    return changes


def patch_text():
    parts = []
    for path, after in proposed_files().items():
        exists = (ROOT / path).exists()
        before = (ROOT / path).read_text(encoding="utf-8") if exists else ""
        parts.append(f"diff --git a/{path} b/{path}\n")
        if not exists:
            parts.append("new file mode 100644\n")
        parts.extend(unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                  fromfile=f"a/{path}" if exists else "/dev/null", tofile=f"b/{path}"))
    # Git accepts an empty context line without its optional single-space marker. Preserve
    # application text while avoiding trailing whitespace in this committed review artifact.
    return "".join("\n" if line == " \n" else line for line in "".join(parts).splitlines(keepends=True))


if __name__ == "__main__":
    target = HERE / "runtime_changes_PROPOSED.patch"
    target.write_text(patch_text(), encoding="utf-8", newline="\n")
    print("Prepared review-only patch; application sources unchanged.")
