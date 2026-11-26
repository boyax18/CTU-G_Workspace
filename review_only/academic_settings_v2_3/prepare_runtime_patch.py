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
