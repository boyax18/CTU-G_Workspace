"""Run ONLY in the generated source copy via run_isolated_tests.py --candidate.

The app patch is applied to that copy, with real disposable MySQL and unmodified base helpers.
No production/dev binding, Deny or permission constant is changed by this module.
"""
from unittest.mock import patch
from django.db import DatabaseError
from django.test import override_settings

from apps.access_control.models import AccountPermission, Permission, RolePermission
from apps.access_control.services import get_effective_permissions, has_permission
from apps.accounts.active_role_context import bind_role_scope
from apps.academic import historical_participation as hp, onboarding, services, verification
from apps.academic.test_student_onboarding import (
    ONBOARD, OnboardingBase, finalize, open_semester, record, record_counts, regular_steps,
)

VERIFY = "academic.enrollment_verifications.record"
WRITE = "academic.semester_onboarding.self.submit"
HISTORY = "academic.historical_participation.correct"


def candidate_fixture(w):
    if onboarding.WRITE_CODE != WRITE or verification.VERIFY_CODE != VERIFY or getattr(hp, "CORRECTION_CODE", None) != HISTORY:
        raise RuntimeError("Run candidate tests only against the proposed source copy.")
    w.write.service = w.service
    w.write.save(update_fields=["service"])
    legacy = {}
    for code, service in (("academic.profiles.manage", w.service),
                          ("clearance.requests.self.submit", w.clearance),
                          ("academic.periods.manage", w.service)):
        legacy[code], _ = Permission.objects.get_or_create(permission_code=code, defaults={
            "service": service, "permission_name": code, "module_name": "m", "action_name": "manage"})
    return legacy, w._perm(w.service, HISTORY, "Admin")


@override_settings(**ONBOARD)
class CandidateRuntimeTests(OnboardingBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # The unchanged legacy helper associates WRITE with clearance; the new permission belongs
        # to academic. These explicit fixture updates occur ONLY in disposable MySQL.
        cls.legacy, cls.history = candidate_fixture(cls.w)

    def deny(self, actor, code, active=True):
        return AccountPermission.objects.update_or_create(
            account=actor, permission=Permission.objects.get(permission_code=code),
            defaults={"effect": "Deny", "is_active": active})[0]

    def test_narrow_codes_allow_own_onboarding_and_official_verification(self):
        sem = open_semester(self.w, self.cat)["semester_id"]
        record(self.w, self.w.student, sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        revision = onboarding.review(actor=self.w.student)["fee"]["revision_id"]
        self.assertEqual(finalize(self.w.student, version)["outcome"], "completed")
        counts = record_counts()
        self.assertEqual((counts["participations"], counts["clearances"], counts["obligations"]), (1, 1, 1))
        onboarding.finalize(actor=self.w.student, expected_version=version, expected_fee_revision_id=revision, confirmed=True)
        self.assertEqual(record_counts(), counts)

    def test_old_allow_never_substitutes_for_new_allow(self):
        for actor, new, old, role in ((self.w.student, WRITE, "clearance.requests.self.submit", "Student"),
                                      (self.w.admin, VERIFY, "academic.profiles.manage", "Admin"),
                                      (self.w.admin, HISTORY, "academic.periods.manage", "Admin")):
            with self.subTest(new=new):
                RolePermission.objects.filter(permission__permission_code=new).update(is_active=False)
                RolePermission.objects.get_or_create(role=self.w.roles[role], permission=self.legacy[old])
                self.assertTrue(has_permission(actor, old))
                self.assertFalse(has_permission(actor, new))

    def test_each_legacy_deny_blocks_replacement_and_session_hints(self):
        for actor, new, old in ((self.w.student, WRITE, "clearance.requests.self.submit"),
                                 (self.w.admin, VERIFY, "academic.profiles.manage"),
                                 (self.w.admin, HISTORY, "academic.profiles.manage"),
                                 (self.w.admin, HISTORY, "academic.periods.manage")):
            with self.subTest(new=new, old=old):
                self.assertTrue(has_permission(actor, new))
                row = self.deny(actor, old)
                self.assertFalse(has_permission(actor, new))
                self.assertNotIn(new, get_effective_permissions(actor))
                row.is_active = False
                row.save(update_fields=["is_active"])
                self.assertTrue(has_permission(actor, new))
                # Fixtures clean themselves by transaction rollback; old rows are retained here.
                self.assertTrue(AccountPermission.objects.filter(pk=row.pk, effect="Deny").exists())

    def test_new_deny_also_wins(self):
        for actor, code in ((self.w.student, WRITE), (self.w.admin, VERIFY), (self.w.admin, HISTORY)):
            self.deny(actor, code)
            self.assertFalse(has_permission(actor, code))

    def test_legacy_deny_does_not_depend_on_old_service_activation(self):
        self.deny(self.w.student, "clearance.requests.self.submit")
        self.w.clearance.is_active = False
        self.w.clearance.save(update_fields=["is_active"])
        self.assertFalse(has_permission(self.w.student, WRITE))

    def test_selected_student_and_admin_contexts_remain_separate(self):
        dual = self.w.account("V23-DUAL", "Student", "Admin")
        with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            with bind_role_scope(dual.pk, self.w.roles["Student"].pk):
                self.assertTrue(has_permission(dual, WRITE))
                self.assertFalse(has_permission(dual, VERIFY))
                self.assertFalse(has_permission(dual, HISTORY))
            with bind_role_scope(dual.pk, self.w.roles["Admin"].pk):
                self.assertFalse(has_permission(dual, WRITE))
                self.assertTrue(has_permission(dual, VERIFY))
                self.deny(dual, "academic.profiles.manage")
                self.assertFalse(has_permission(dual, VERIFY))
                self.assertFalse(has_permission(dual, HISTORY))

    def test_failure_in_transition_query_fails_closed(self):
        with patch("apps.access_control.services.preserve_transition_denies", side_effect=DatabaseError):
            self.assertFalse(has_permission(self.w.student, WRITE))

    def test_legacy_deny_arriving_between_precheck_and_finalization_is_rechecked(self):
        sem = open_semester(self.w, self.cat)["semester_id"]
        record(self.w, self.w.student, sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        revision = onboarding.review(actor=self.w.student)["fee"]["revision_id"]
        original = onboarding.authorize_student

        def revoke(*args, **kwargs):
            auth = original(*args, **kwargs)
            self.deny(self.w.student, "clearance.requests.self.submit")
            return auth

        before = record_counts()
        with patch.object(onboarding, "authorize_student", side_effect=revoke), self.assertRaises(services.AcademicPeriodDenied):
            onboarding.finalize(actor=self.w.student, expected_version=version,
                                expected_fee_revision_id=revision, confirmed=True)
        self.assertEqual(record_counts(), before)

    def test_historical_code_alone_reaches_preview_but_old_broad_codes_do_not(self):
        sem = open_semester(self.w, self.cat)["semester_id"]
        RolePermission.objects.filter(permission__permission_code__in=["academic.periods.manage", "academic.profiles.manage", VERIFY]).update(is_active=False)
        self.assertIn("period_not_historical", hp.preview(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=sem)["blockers"])
        RolePermission.objects.filter(permission=self.history).update(is_active=False)
        for code in ("academic.periods.manage", "academic.profiles.manage"):
            RolePermission.objects.update_or_create(role=self.w.roles["Admin"], permission=self.legacy[code], defaults={"is_active": True})
        with self.assertRaises(services.AcademicPeriodDenied):
            hp.preview(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=sem)


from apps.academic import test_student_onboarding as existing_onboarding
from apps.academic import test_wf1101_residual as existing_residual


class CandidateVerificationTests(existing_onboarding.VerificationTests):
    """Run all existing official-verification assertions unchanged against the new exact code."""
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        candidate_fixture(cls.w)


class CandidateHistoricalTests(existing_residual.HistoricalParticipationTests):
    """Run all existing historical success/refusal/original-fee assertions unchanged."""
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        candidate_fixture(cls.w)
