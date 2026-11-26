"""WF-05.05 Student Semester Onboarding, WF-05.04 minimum verification, WF-06.01/06.02 clearance creation and
WF-07.02 fee obligation: eligibility, verification lanes, Steps 1-4, the atomic finalization, failure
injection, HDAC and multi-role isolation.

Run: python manage.py test apps.academic.test_student_onboarding --settings=config.test_settings --noinput
Disposable MySQL only (IsolatedMySQLRunner); synthetic accounts and records. Permissions mirror the pinned
catalogue defaults (Student -> academic.profile.self.read and clearance.requests.self.submit; Admin ->
academic.profiles.manage). The fee success path uses the throwaway-database-only Admin fee binding of
apps.finance.test_semester_fees.FeeWorld.grant_admin_fee (never an application grant). "CTU integration"
evidence rows are created directly in the throwaway database: no runtime writer for that lane exists.
"""

from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.access_control.models import AccountPermission, AccountRole, Permission, RolePermission, Service
from apps.accounts.active_role_context import bind_role_scope
from apps.clearance.models import ClearanceRequirement, SemesterClearance
from apps.finance import fees
from apps.finance.models import FeeObligation, FinanceAuditLog
from apps.finance.test_semester_fees import FEES, FeeWorld

from . import configuration as cfg
from . import dependencies, eligibility, onboarding, services, teaching, verification
from .models import (
    AcademicPeriodAuditLog, EnrollmentEvidence, EnrollmentEvidenceSubject, EnrollmentGapException, OnboardingStatus,
    ParticipationSubject, Semester, SemesterOnboarding, SemesterOnboardingSubject, SemesterParticipation, SemesterStatus,
)
from .test_wf1101_periods import activate, close

ONBOARD = dict(FEES, WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True, WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED=True,
               WORKSPACE_STUDENT_ONBOARDING_ENABLED=True, WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED=True,
               WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED=True, WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED=True)
READ, WRITE, VERIFY = onboarding.READ_CODE, onboarding.WRITE_CODE, verification.VERIFY_CODE
REFERENCE = "CTU-REG 2026-0001"


class OnboardingWorld(FeeWorld):
    """FeeWorld + the pinned Student self-service defaults and the Admin verification default."""

    def __init__(self):
        super().__init__()
        self.grant_admin_fee()
        self.read = self._perm(self.service, READ, "Student")
        self.write = self._perm(self.clearance, WRITE, "Student")
        self.verify = self._perm(self.service, VERIFY, "Admin")
        self.student = self.account("WF0505-STU1", "Student")
        self.student2 = self.account("WF0505-STU2", "Student")

    def _perm(self, service, code, role):
        perm = Permission.objects.create(service=service, permission_code=code, permission_name=code, module_name="m",
                                         action_name="a")
        RolePermission.objects.create(role=self.roles[role], permission=perm)
        self.perms[code] = perm
        return perm

    def deny(self, account, code):
        return AccountPermission.objects.create(account=account, permission=self.perms[code], effect="Deny")


def build_catalogue(w):
    """Course BSIT: year 1 has two First-term subjects and one Second-term subject; year 2 one First-term."""
    course = cfg.create_course(actor=w.admin, code="BSIT", name="Bachelor of Science in Information Technology")
    other = cfg.create_course(actor=w.admin, code="BSCS", name="Bachelor of Science in Computer Science")
    subjects = {code: cfg.create_subject(actor=w.admin, code=code, title=f"{code} title", lecture_units=3)["subject_id"]
                for code in ("MATH 101", "IT 101", "IT 102", "IT 201", "CS 101")}
    plan = {"BSIT": [("MATH 101", 1, "first"), ("IT 101", 1, "first"), ("IT 102", 1, "second"), ("IT 201", 2, "first")],
            "BSCS": [("CS 101", 1, "first")]}
    entries, courses = {}, {"BSIT": course["course_id"], "BSCS": other["course_id"]}
    for code, rows in plan.items():
        curriculum = cfg.create_curriculum(actor=w.admin, course_id=courses[code], label="2024", effective_start_year=2024)
        version = 1
        for subject, year, term in rows:
            curriculum = cfg.add_curriculum_entry(actor=w.admin, curriculum_id=curriculum["curriculum_id"],
                                                  subject_id=subjects[subject], year_level=year, term=term,
                                                  expected_version=version)
            version += 1
        curriculum = cfg.publish_curriculum(actor=w.admin, curriculum_id=curriculum["curriculum_id"],
                                            expected_version=version, confirmed=True)
        for e in curriculum["entries"]:
            entries[e["subject"]["code"]] = (e["curriculum_subject_id"], e["year_level"], e["term"])
    sections = {name: cfg.create_section(actor=w.admin, course_id=courses[code], year_level=year, name=name)["section_id"]
                for name, code, year in (("1-A", "BSIT", 1), ("1-B", "BSIT", 1), ("2-A", "BSIT", 2), ("CS1-A", "BSCS", 1))}
    section_course = {"1-A": ("BSIT", 1), "1-B": ("BSIT", 1), "2-A": ("BSIT", 2), "CS1-A": ("BSCS", 1)}
    return {"courses": courses, "subjects": subjects, "entries": entries, "sections": sections,
            "section_course": section_course, "years": {}}


def _year(w, cat, start):
    if start not in cat["years"]:
        year = services.create_school_year(actor=w.admin, start_year=start)
        cat["years"][start] = {1 if s["term"] == "first" else 2: s["semester_id"] for s in year["semesters"]}
    return cat["years"][start]


def prepare_semester(w, cat, start=2026, term=1, fee="1500.00", assign=True, approve=True, skip=()):
    """School Admin configuration through the real services: dates, offerings, instructors and fee."""
    semester_id = _year(w, cat, start)[term]
    dates = ((f"{start}-08-10", f"{start}-12-18") if term == 1 else (f"{start + 1}-01-12", f"{start + 1}-05-29"))
    semester = Semester.objects.get(pk=semester_id)
    services.update_semester_dates(actor=w.admin, semester_id=semester_id, start_date=dates[0], end_date=dates[1],
                                   expected_version=semester.version)
    term_name = "first" if term == 1 else "second"
    offerings = {}
    for section, (course, year) in cat["section_course"].items():
        for subject, (entry_id, entry_year, entry_term) in cat["entries"].items():
            course_of = "BSCS" if subject.startswith("CS") else "BSIT"
            if course_of != course or entry_year != year or entry_term != term_name or (section, subject) in skip:
                continue
            offering = cfg.create_offering(actor=w.admin, semester_id=semester_id, section_id=cat["sections"][section],
                                           curriculum_subject_id=entry_id)
            offerings[(section, subject)] = offering["offering_id"]
            if assign:
                instructor = w.instructor if section in ("1-A", "2-A", "CS1-A") else w.instructor2
                teaching.assign_instructor(actor=w.admin, offering_id=offering["offering_id"],
                                           instructor_account_id=instructor.pk, expected_assignment_id=None)
    if fee is not None:
        fees.save_draft(actor=w.admin, semester_id=semester_id, amount=fee, expected_draft_version=None)
        if approve:
            approve_fee(w, semester_id)
    return {"semester_id": semester_id, "offerings": offerings}


def approve_fee(w, semester_id):
    preview = fees.approval_preview(actor=w.admin, semester_id=semester_id)
    current = preview["current_approved"]
    return fees.approve(actor=w.admin, semester_id=semester_id, revision_id=preview["proposed"]["revision_id"],
                        expected_version=preview["proposed"]["version"],
                        expected_current_approved_revision_id=current["revision_id"] if current else None,
                        acknowledged_warnings=preview["warnings"], confirmed=True,
                        confirm_zero_amount=preview["proposed"]["amount"] == "0.00")


def open_semester(w, cat, start=2026, term=1, **kwargs):
    """Prepare, then activate through the REAL prerequisites (approved fee + valid offerings)."""
    prepared = prepare_semester(w, cat, start, term, **kwargs)
    activate(w.admin, prepared["semester_id"], source=dependencies.DEFAULT_BUNDLE)
    return prepared


def record(w, student, semester_id, cat, subjects, classification="continuing", course="BSIT", year=1, expected=None,
           actor=None):
    return verification.record_evidence(
        actor=actor or w.admin, student_account_id=student.pk, semester_id=semester_id,
        entry_classification=classification, course_id=cat["courses"][course], year_level=year,
        subject_ids=[cat["subjects"][s] for s in subjects], source_reference=REFERENCE, expected_evidence_id=expected)


def regular_steps(student, cat, section="1-A", course="BSIT", year=1):
    """Steps 1-3 for a Regular Student through the real service; returns the Draft version."""
    state = onboarding.save_student_type(actor=student, student_type="Regular")
    options = onboarding.subject_options(actor=student, course_id=cat["courses"][course], year_level=year,
                                         section_id=cat["sections"][section])
    state = onboarding.confirm_subjects(actor=student, course_id=cat["courses"][course], year_level=year,
                                        offering_ids=[o["offering_id"] for o in options["options"]],
                                        expected_version=state["onboarding"]["version"])
    state = onboarding.confirm_course(actor=student, course_id=cat["courses"][course], year_level=year,
                                      expected_version=state["onboarding"]["version"])
    return state["onboarding"]["version"]


def finalize(student, version=None):
    review = onboarding.review(actor=student)
    return onboarding.finalize(actor=student, expected_version=version or review["onboarding"]["version"],
                               expected_fee_revision_id=review["fee"]["revision_id"], confirmed=True)


def record_counts():
    return {"participations": SemesterParticipation.objects.count(), "subjects": ParticipationSubject.objects.count(),
            "clearances": SemesterClearance.objects.count(), "requirements": ClearanceRequirement.objects.count(),
            "obligations": FeeObligation.objects.count()}


ZERO = {"participations": 0, "subjects": 0, "clearances": 0, "requirements": 0, "obligations": 0}


class OnboardingBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = OnboardingWorld()
        cls.cat = build_catalogue(cls.w)

    def conflict(self, reason, fn, *args, **kwargs):
        before = record_counts()
        with self.assertRaises(onboarding.OnboardingConflict) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(record_counts(), before)
        return caught.exception

    def invalid(self, field, fn, *args, **kwargs):
        with self.assertRaises(services.AcademicPeriodInvalid) as caught:
            fn(*args, **kwargs)
        self.assertIn(field, caught.exception.fields)


# ---- Eligibility (WF11-D15/16, WF-06.02 steps 1-3, WF-07.08) -----------------------------------------

@override_settings(**ONBOARD)
class EligibilityTests(OnboardingBase):
    """Read-only evaluator over real activated periods; participations are created by the real finalization."""

    def onboard(self, student, semester_id, subjects=("MATH 101", "IT 101"), classification="continuing"):
        record(self.w, student, semester_id, self.cat, subjects, classification=classification)
        regular_steps(student, self.cat)
        return finalize(student)

    def evaluate(self, student, semester_id):
        semester = Semester.objects.get(pk=semester_id)
        return eligibility.evaluate(student, semester, verification.current_evidence(student.pk, semester_id))

    def sign_all(self, student, semester_id):
        """TEST ONLY: mark a clearance Cleared directly (no signing workflow exists yet)."""
        from django.utils import timezone
        clearance = SemesterClearance.objects.get(student=student, semester_id=semester_id)
        ClearanceRequirement.objects.filter(clearance=clearance).update(status="Signed", signed_at=timezone.now())
        SemesterClearance.objects.filter(pk=clearance.pk).update(status="Cleared", cleared_at=timezone.now())

    def test_first_workspace_period_is_eligible_and_draft_semesters_never_count(self):
        first = open_semester(self.w, self.cat, 2026, 1)["semester_id"]
        _year(self.w, self.cat, 2025)  # S.Y. 2025 semesters exist but were never Active
        result = self.evaluate(self.w.student, first)
        self.assertEqual((result["status"], result["basis"], result["previous_semester"]), ("eligible", "no_prior_period", None))

    def test_previous_clearance_must_be_cleared_and_payment_alone_is_not_clearance(self):
        first = open_semester(self.w, self.cat, 2026, 1)["semester_id"]
        self.onboard(self.w.student, first)
        second = open_semester(self.w, self.cat, 2026, 2, fee="1600.00")["semester_id"]
        result = self.evaluate(self.w.student, second)
        self.assertEqual((result["status"], result["basis"], result["previous_semester"]["semester_id"]),
                         ("clearance_required", "previous_uncleared", first))
        state = onboarding.status(actor=self.w.student)
        self.assertEqual(state["state"], "clearance_required")
        self.assertEqual(state["previous_clearance"]["clearance"]["status"], "Uncleared")
        self.assertEqual(state["previous_clearance"]["clearance"]["pending_count"], 4)  # 2 subjects + Treasurer + final
        self.assertEqual(state["previous_clearance"]["fee"]["status"], "Unpaid")
        self.conflict("eligibility_blocked", onboarding.save_student_type, actor=self.w.student, student_type="Regular")
        self.sign_all(self.w.student, first)
        self.assertEqual(self.evaluate(self.w.student, second)["basis"], "previous_cleared")

    def test_verified_gap_lets_a_returning_student_proceed_and_preserves_old_records(self):
        first = open_semester(self.w, self.cat, 2025, 1)["semester_id"]
        self.onboard(self.w.student, first)
        skipped = open_semester(self.w, self.cat, 2025, 2)["semester_id"]
        target = open_semester(self.w, self.cat, 2026, 1)["semester_id"]
        result = self.evaluate(self.w.student, target)
        self.assertEqual((result["status"], [g["semester_id"] for g in result["missing_gaps"]]),
                         ("gap_verification_required", [skipped]))
        self.assertEqual(onboarding.status(actor=self.w.student)["state"], "gap_verification_required")
        gap = verification.record_gap(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=skipped,
                                      source_reference="CTU-LOA 2025-77")
        result = self.evaluate(self.w.student, target)
        self.assertEqual((result["status"], result["basis"], [s["semester_id"] for s in result["older_uncleared"]]),
                         ("eligible", "verified_gap", [first]))
        old = SemesterClearance.objects.get(student=self.w.student, semester_id=first)
        self.assertEqual(old.status, "Uncleared")  # never cleared or waived by the exception
        self.assertEqual(FeeObligation.objects.get(student=self.w.student, semester_id=first).status, "Unpaid")
        self.assertFalse(SemesterClearance.objects.filter(semester_id=skipped).exists())  # no clearance for the gap
        verification.revoke_gap(actor=self.w.admin, gap_id=gap["gap_id"], expected_version=gap["version"])
        self.assertEqual(self.evaluate(self.w.student, target)["status"], "gap_verification_required")

    def test_missing_records_never_prove_first_time_or_non_enrollment(self):
        open_semester(self.w, self.cat, 2025, 2)
        target = open_semester(self.w, self.cat, 2026, 1)["semester_id"]
        result = self.evaluate(self.w.student, target)
        self.assertEqual((result["status"], result["basis"]), ("verification_required", "no_workspace_history"))
        record(self.w, self.w.student, target, self.cat, ["MATH 101", "IT 101"], classification="continuing")
        result = self.evaluate(self.w.student, target)
        self.assertEqual(result["status"], "history_unverified")
        for kind in ("newcomer", "transferee"):
            with self.subTest(kind=kind):
                current = verification.current_evidence(self.w.student.pk, target)
                record(self.w, self.w.student, target, self.cat, ["MATH 101", "IT 101"], classification=kind,
                       expected=current.pk)
                self.assertEqual(self.evaluate(self.w.student, target)["basis"], "first_time_evidence")

    def test_first_time_evidence_contradicted_by_history_is_a_conflict(self):
        first = open_semester(self.w, self.cat, 2026, 1)["semester_id"]
        self.onboard(self.w.student, first)
        self.sign_all(self.w.student, first)
        second = open_semester(self.w, self.cat, 2026, 2)["semester_id"]
        record(self.w, self.w.student, second, self.cat, ["IT 102"], classification="newcomer")
        self.assertEqual(self.evaluate(self.w.student, second)["status"], "evidence_conflict")


# ---- Official verification (R-02 lanes; WF-05.04 minimum) ---------------------------------------------

@override_settings(**ONBOARD)
class VerificationTests(OnboardingBase):
    def setUp(self):
        self.sem = open_semester(self.w, self.cat)["semester_id"]

    def verification_conflict(self, reason, fn, **kwargs):
        before = (EnrollmentEvidence.objects.count(), EnrollmentGapException.objects.count(),
                  AcademicPeriodAuditLog.objects.count())
        with self.assertRaises(verification.VerificationConflict) as caught:
            fn(**kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(before, (EnrollmentEvidence.objects.count(), EnrollmentGapException.objects.count(),
                                  AcademicPeriodAuditLog.objects.count()))

    def test_in_person_evidence_is_attributed_audited_and_minimized(self):
        payload = record(self.w, self.w.student, self.sem, self.cat, ["IT 101", "MATH 101"])
        self.assertEqual((payload["source_type"], payload["status"], payload["year_level"], payload["verified_by"]),
                         ("in_person", "Verified", 1, "A School Admin"))
        self.assertEqual([s["code"] for s in payload["subjects"]], ["IT 101", "MATH 101"])
        self.assertNotIn("source_reference", payload)
        evidence = EnrollmentEvidence.objects.get()
        self.assertEqual((evidence.verified_by_id, evidence.source_reference), (self.w.admin.pk, REFERENCE))
        audit = AcademicPeriodAuditLog.objects.filter(action="academic.enrollment_evidence.record").get()
        self.assertEqual((audit.actor_account_id, audit.semester_id), (self.w.admin.pk, self.sem))
        self.assertTrue(audit.new_value["source_reference_recorded"])
        self.assertNotIn(REFERENCE, str(audit.new_value))  # the reference itself never reaches the audit
        self.assertEqual(record_counts(), ZERO)  # verification alone creates no participation, clearance or fee

    def test_superseding_needs_the_reviewed_record_and_keeps_history(self):
        first = record(self.w, self.w.student, self.sem, self.cat, ["MATH 101"])
        self.verification_conflict("evidence_changed", record, w=self.w, student=self.w.student, semester_id=self.sem,
                                   cat=self.cat, subjects=["IT 101"])
        second = record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"], expected=first["evidence_id"])
        old = EnrollmentEvidence.objects.get(pk=first["evidence_id"])
        self.assertEqual((old.status, old.revoke_reason, old.active_slot), ("Revoked", "superseded", None))
        self.assertEqual(verification.current_evidence(self.w.student.pk, self.sem).pk, second["evidence_id"])
        with self.assertRaises(IntegrityError), transaction.atomic():
            EnrollmentEvidence.objects.create(student=self.w.student, semester_id=self.sem, source_type="in_person",
                                              source_reference="X-1", entry_classification="continuing",
                                              course_id=self.cat["courses"]["BSIT"], year_level=1, active_slot=1,
                                              verified_by=self.w.admin)  # one Verified record per Student + semester

    def test_validation_and_period_rules(self):
        base = dict(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.sem,
                    entry_classification="continuing", course_id=self.cat["courses"]["BSIT"], year_level=1,
                    subject_ids=[self.cat["subjects"]["MATH 101"]], source_reference=REFERENCE)
        for field, bad in (("source_reference", "x"), ("source_reference", "<script>"), ("source_reference", "a" * 81),
                           ("entry_classification", "irregular"), ("year_level", 7), ("subject_ids", []),
                           ("subject_ids", [1, 1]), ("source_as_of", "2999-01-01"), ("course_id", "1")):
            with self.subTest(field=field, bad=bad):
                self.invalid(field, verification.record_evidence, **{**base, field: bad})
        draft = _year(self.w, self.cat, 2027)[1]
        self.verification_conflict("period_not_open", verification.record_evidence, **{**base, "semester_id": draft})
        with self.assertRaises(services.AcademicPeriodNotFound):
            verification.record_evidence(**{**base, "student_account_id": self.w.instructor.pk})  # not a Student
        self.verification_conflict("period_not_historical", verification.record_gap, actor=self.w.admin,
                                   student_account_id=self.w.student.pk, semester_id=self.sem, source_reference=REFERENCE)

    def test_gap_and_evidence_are_mutually_exclusive_and_revocation_is_guarded(self):
        close(self.w.admin, self.sem, source=dependencies.DEFAULT_BUNDLE)
        evidence = record(self.w, self.w.student, self.sem, self.cat, ["MATH 101"])
        self.verification_conflict("evidence_conflict", verification.record_gap, actor=self.w.admin,
                                   student_account_id=self.w.student.pk, semester_id=self.sem, source_reference=REFERENCE)
        verification.revoke_evidence(actor=self.w.admin, evidence_id=evidence["evidence_id"], expected_version=1,
                                     reason_code="recorded_in_error")
        self.verification_conflict("already_revoked", verification.revoke_evidence, actor=self.w.admin,
                                   evidence_id=evidence["evidence_id"], expected_version=2, reason_code="recorded_in_error")
        gap = verification.record_gap(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.sem,
                                      source_reference=REFERENCE)
        self.verification_conflict("gap_conflict", record, w=self.w, student=self.w.student, semester_id=self.sem,
                                   cat=self.cat, subjects=["MATH 101"])
        self.verification_conflict("stale_version", verification.revoke_gap, actor=self.w.admin, gap_id=gap["gap_id"],
                                   expected_version=9)
        for code in ("bogus", None):
            with self.subTest(code=code):
                self.invalid("reason_code", verification.revoke_evidence, actor=self.w.admin, evidence_id=1,
                             expected_version=1, reason_code=code)

    def test_evidence_supporting_a_participation_cannot_be_revoked_or_rewritten(self):
        evidence = record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student, self.cat)
        finalize(self.w.student)
        self.verification_conflict("evidence_in_use", verification.revoke_evidence, actor=self.w.admin,
                                   evidence_id=evidence["evidence_id"], expected_version=1, reason_code="recorded_in_error")
        self.verification_conflict("participation_exists", record, w=self.w, student=self.w.student, semester_id=self.sem,
                                   cat=self.cat, subjects=["MATH 101"], expected=evidence["evidence_id"])

    def test_school_admin_hdac_self_dealing_and_switches(self):
        for actor in (self.w.student, self.w.instructor, self.w.treasurer):
            with self.subTest(actor=actor.school_id), self.assertRaises(services.AcademicPeriodDenied):
                record(self.w, self.w.student2, self.sem, self.cat, ["MATH 101"], actor=actor)
        dual = self.w.account("WF0505-ADMSTU", "Admin", "Student")
        self.verification_conflict("self_verification", record, w=self.w, student=dual, semester_id=self.sem,
                                   cat=self.cat, subjects=["MATH 101"], actor=dual)
        self.w.deny(self.w.admin, VERIFY)
        with self.assertRaises(services.AcademicPeriodDenied):
            verification.search_students(actor=self.w.admin)
        AccountPermission.objects.filter(account=self.w.admin).delete()
        with override_settings(WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED=False), \
                self.assertRaises(services.AcademicPeriodUnavailable):
            record(self.w, self.w.student, self.sem, self.cat, ["MATH 101"])
        with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            with bind_role_scope(dual.pk, self.w.roles["Student"].pk), self.assertRaises(services.AcademicPeriodDenied):
                verification.search_students(actor=dual)
            with bind_role_scope(dual.pk, self.w.roles["Admin"].pk):
                found = verification.search_students(actor=dual, q="WF0505-STU")
        self.assertEqual({r["ctug_id"] for r in found["results"]}, {"WF0505-STU1", "WF0505-STU2"})
        self.assertEqual(set(found["results"][0]), {"account_id", "ctug_id", "full_name"})

    def test_student_record_lists_each_period_for_the_counter(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        row = verification.student_record(actor=self.w.admin, student_account_id=self.w.student.pk)["periods"][0]
        self.assertEqual((row["semester"]["semester_id"], row["evidence"]["status"], row["participation"], row["fee"]),
                         (self.sem, "Verified", None, None))


# ---- Steps 1-4 ---------------------------------------------------------------------------------------------

@override_settings(**ONBOARD)
class OnboardingStepTests(OnboardingBase):
    def setUp(self):
        self.prepared = open_semester(self.w, self.cat)
        self.sem = self.prepared["semester_id"]
        self.off = self.prepared["offerings"]

    def test_status_reports_read_only_period_and_account_and_creates_nothing(self):
        state = onboarding.status(actor=self.w.student)
        self.assertEqual((state["state"], state["semester"]["semester_id"], state["semester"]["status"],
                          state["student"]["ctug_id"], state["dashboard_unlocked"], state["onboarding"]["next_step"]),
                         ("onboarding", self.sem, "Active", "WF0505-STU1", False, 1))
        self.assertIn("in person", state["correction_instructions"])
        self.assertEqual(SemesterOnboarding.objects.count(), 0)  # a status read never writes
        with self.assertRaises(onboarding.OnboardingRequired) as caught:
            onboarding.my_semester(actor=self.w.student)
        self.assertEqual(caught.exception.state, "onboarding")
        self.assertEqual(onboarding.my_history(actor=self.w.student), {"results": []})  # always available
        courses = onboarding.context_options(actor=self.w.student)["courses"]
        self.assertEqual({c["code"]: c["year_levels"] for c in courses}, {"BSCS": [1], "BSIT": [1, 2]})

    def test_regular_flow_confirms_the_full_prepared_section(self):
        state = onboarding.save_student_type(actor=self.w.student, student_type="Regular")
        self.assertEqual((state["onboarding"]["status"], state["onboarding"]["next_step"]), ("Draft", 2))
        bsit = self.cat["courses"]["BSIT"]
        options = onboarding.subject_options(actor=self.w.student, course_id=bsit, year_level=1,
                                             section_id=self.cat["sections"]["1-A"])
        self.assertEqual([o["subject"]["code"] for o in options["options"]], ["IT 101", "MATH 101"])
        self.assertTrue(options["complete"])
        version = state["onboarding"]["version"]
        self.conflict("incomplete_section", onboarding.confirm_subjects, actor=self.w.student, course_id=bsit,
                      year_level=1, offering_ids=[self.off[("1-A", "MATH 101")]], expected_version=version)
        self.conflict("section_mismatch", onboarding.confirm_subjects, actor=self.w.student, course_id=bsit,
                      year_level=1, offering_ids=[self.off[("1-A", "MATH 101")], self.off[("1-B", "IT 101")]],
                      expected_version=version)
        self.conflict("section_mismatch", onboarding.confirm_subjects, actor=self.w.student, course_id=bsit,
                      year_level=1, offering_ids=[self.off[("CS1-A", "CS 101")]], expected_version=version)
        self.conflict("stale_version", onboarding.confirm_subjects, actor=self.w.student, course_id=bsit, year_level=1,
                      offering_ids=[o["offering_id"] for o in options["options"]], expected_version=version + 5)
        state = onboarding.confirm_subjects(actor=self.w.student, course_id=bsit, year_level=1,
                                            offering_ids=[o["offering_id"] for o in options["options"]],
                                            expected_version=version)
        self.assertEqual((state["onboarding"]["subjects_confirmed"], state["onboarding"]["next_step"]), (True, 3))
        state = onboarding.confirm_course(actor=self.w.student, course_id=bsit, year_level=1,
                                          expected_version=state["onboarding"]["version"])
        self.assertEqual(state["onboarding"]["next_step"], 4)
        review = onboarding.review(actor=self.w.student)
        self.assertEqual((review["fee"]["amount"], review["verification"], review["blockers"], review["can_confirm"]),
                         ("1500.00", "not_recorded", [], True))
        self.assertEqual(review["student"]["ctug_id"], "WF0505-STU1")
        self.assertEqual(record_counts(), ZERO)  # Draft steps and review never create records

    def test_course_or_year_change_requires_subject_reconfirmation(self):
        version = regular_steps(self.w.student, self.cat)
        state = onboarding.confirm_course(actor=self.w.student, course_id=self.cat["courses"]["BSIT"], year_level=2,
                                          expected_version=version)
        self.assertEqual((state["onboarding"]["subjects_confirmed"], state["onboarding"]["next_step"]), (False, 2))
        self.conflict("subjects_required", onboarding.review, actor=self.w.student)
        options = onboarding.subject_options(actor=self.w.student, course_id=self.cat["courses"]["BSIT"], year_level=2,
                                             section_id=self.cat["sections"]["2-A"])
        state = onboarding.confirm_subjects(actor=self.w.student, course_id=self.cat["courses"]["BSIT"], year_level=2,
                                            offering_ids=[o["offering_id"] for o in options["options"]],
                                            expected_version=state["onboarding"]["version"])
        self.assertEqual(state["onboarding"]["next_step"], 4)  # same course/year as confirmed in Step 3
        self.assertEqual([s["subject"]["code"] for s in state["onboarding"]["subjects"]], ["IT 201"])

    def test_irregular_selects_offerings_of_the_course_once_each(self):
        state = onboarding.save_student_type(actor=self.w.student, student_type="Irregular")
        options = onboarding.subject_options(actor=self.w.student, course_id=self.cat["courses"]["BSIT"])
        self.assertEqual(len(options["options"]), 5)  # 1-A x2, 1-B x2, 2-A x1; never BSCS
        bsit, version = self.cat["courses"]["BSIT"], state["onboarding"]["version"]
        self.conflict("duplicate_subject", onboarding.confirm_subjects, actor=self.w.student, course_id=bsit,
                      year_level=2, offering_ids=[self.off[("1-A", "MATH 101")], self.off[("1-B", "MATH 101")]],
                      expected_version=version)
        state = onboarding.confirm_subjects(actor=self.w.student, course_id=bsit, year_level=2,
                                            offering_ids=[self.off[("1-B", "MATH 101")], self.off[("2-A", "IT 201")]],
                                            expected_version=version)
        self.assertEqual(state["onboarding"]["next_step"], 3)
        state = onboarding.confirm_course(actor=self.w.student, course_id=self.cat["courses"]["BSCS"], year_level=2,
                                          expected_version=state["onboarding"]["version"])
        self.assertFalse(state["onboarding"]["subjects_confirmed"])  # other course: subjects inconsistent
        state = onboarding.save_student_type(actor=self.w.student, student_type="Regular",
                                             expected_version=state["onboarding"]["version"])
        self.assertEqual((state["onboarding"]["subjects"], state["onboarding"]["student_type"]), ([], "Regular"))

    def test_unassigned_or_ineligible_instructors_hold_confirmation(self):
        assignment = teaching.current_assignment(cfg._offerings_qs().get(pk=self.off[("1-A", "IT 101")]))
        teaching.end_assignment(actor=self.w.admin, offering_id=self.off[("1-A", "IT 101")],
                                expected_assignment_id=assignment.pk, reason_code="instructor_unavailable")
        state = onboarding.save_student_type(actor=self.w.student, student_type="Regular")
        options = onboarding.subject_options(actor=self.w.student, course_id=self.cat["courses"]["BSIT"], year_level=1,
                                             section_id=self.cat["sections"]["1-A"])
        self.assertFalse(options["complete"])
        self.assertEqual({o["subject"]["code"]: o["instructor_assigned"] for o in options["options"]},
                         {"IT 101": False, "MATH 101": True})
        exc = self.conflict("instructor_unassigned", onboarding.confirm_subjects, actor=self.w.student,
                            course_id=self.cat["courses"]["BSIT"], year_level=1,
                            offering_ids=[o["offering_id"] for o in options["options"]],
                            expected_version=state["onboarding"]["version"])
        self.assertEqual(exc.details, ("IT 101",))
        AccountRole.objects.filter(account=self.w.instructor2).delete()  # 1-B instructor loses the Instructor role
        options = onboarding.subject_options(actor=self.w.student, course_id=self.cat["courses"]["BSIT"], year_level=1,
                                             section_id=self.cat["sections"]["1-B"])
        self.assertFalse(any(o["ready_for_confirmation"] for o in options["options"]))

    def test_input_validation(self):
        for bad in ("regular", "", None, 1):
            with self.subTest(student_type=bad):
                self.invalid("student_type", onboarding.save_student_type, actor=self.w.student, student_type=bad)
        onboarding.save_student_type(actor=self.w.student, student_type="Irregular")
        for bad in ([], [1, 1], ["1"], list(range(1, 22)), None):
            with self.subTest(offering_ids=bad):
                self.invalid("offering_ids", onboarding.confirm_subjects, actor=self.w.student, course_id=1, year_level=1,
                             offering_ids=bad, expected_version=1)
        self.invalid("year_level", onboarding.confirm_course, actor=self.w.student, course_id=1, year_level=0,
                     expected_version=1)
        self.conflict("course_unavailable", onboarding.confirm_course, actor=self.w.student, course_id=999_999,
                      year_level=1, expected_version=1)

    def test_no_active_semester_holds_safely(self):
        close(self.w.admin, self.sem, source=dependencies.DEFAULT_BUNDLE)
        self.assertEqual(onboarding.status(actor=self.w.student)["state"], "no_active_semester")
        self.conflict("no_active_semester", onboarding.save_student_type, actor=self.w.student, student_type="Regular")
        with self.assertRaises(onboarding.OnboardingRequired):
            onboarding.my_semester(actor=self.w.student)


# ---- Finalization (WF11-D23/D24) ---------------------------------------------------------------------------

@override_settings(**ONBOARD)
class FinalizationTests(OnboardingBase):
    def setUp(self):
        self.prepared = open_semester(self.w, self.cat)
        self.sem = self.prepared["semester_id"]

    def test_without_evidence_the_confirmation_is_pending_verification_only(self):
        version = regular_steps(self.w.student, self.cat)
        result = finalize(self.w.student, version)
        self.assertEqual((result["outcome"], result["state"]), ("pending_verification", "pending_verification"))
        self.assertEqual(SemesterOnboarding.objects.get().status, OnboardingStatus.PENDING_VERIFICATION)
        self.assertEqual(record_counts(), ZERO)  # self-confirmation never infers official enrollment
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        result = finalize(self.w.student)
        self.assertEqual(result["outcome"], "completed")

    def test_mismatching_evidence_names_the_differences_and_holds(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101"], year=2)
        regular_steps(self.w.student, self.cat)
        review = onboarding.review(actor=self.w.student)
        self.assertEqual((review["verification"], review["mismatched"]), ("mismatch", ["year_level", "subjects"]))
        self.assertEqual(finalize(self.w.student)["outcome"], "pending_verification")
        self.assertEqual(record_counts(), ZERO)

    def test_completed_finalization_creates_every_record_once_atomically(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        result = finalize(self.w.student, version)
        self.assertEqual((result["outcome"], result["dashboard_unlocked"]), ("completed", True))
        self.assertEqual(record_counts(), {"participations": 1, "subjects": 2, "clearances": 1, "requirements": 4,
                                           "obligations": 1})
        participation = SemesterParticipation.objects.get()
        self.assertEqual((participation.source, participation.student_type, participation.year_level,
                          participation.created_by_id), ("onboarding", "Regular", 1, self.w.student.pk))
        clearance = SemesterClearance.objects.get()
        self.assertEqual((clearance.status, clearance.cleared_at), ("Uncleared", None))
        requirements = {r.requirement_key: r for r in ClearanceRequirement.objects.all()}
        self.assertTrue(all(r.status == "Pending" and r.signed_at is None for r in requirements.values()))
        subject = requirements[f"subject:{self.cat['subjects']['MATH 101']}"]
        self.assertEqual(subject.signatory_id, self.w.instructor.pk)  # the REAL assigned instructor
        self.assertEqual((requirements["treasurer_fee"].signatory_id, requirements["school_admin_final"].signatory_id),
                         (None, None))  # role requirements: no person invented
        obligation = FeeObligation.objects.get()
        self.assertEqual((obligation.amount, obligation.currency, obligation.status),
                         (Decimal("1500.00"), "PHP", "Unpaid"))
        onboarding_row = SemesterOnboarding.objects.get()
        self.assertEqual((onboarding_row.status, onboarding_row.version), (OnboardingStatus.COMPLETED, version + 1))
        audit = AcademicPeriodAuditLog.objects.get(action=onboarding.FINALIZE_ACTION)
        self.assertEqual((audit.actor_account_id, audit.new_value["participation_id"], audit.new_value["evidence_source"]),
                         (self.w.student.pk, participation.pk, "in_person"))
        self.assertEqual(FinanceAuditLog.objects.get(action="finance.fee_obligation.create").new_value["amount"], "1500.00")
        mine = onboarding.my_semester(actor=self.w.student)
        self.assertEqual((mine["result"]["clearance"]["status"], mine["result"]["fee"]["status"],
                          mine["result"]["clearance"]["pending_count"]), ("Uncleared", "Unpaid", 4))
        self.assertEqual(onboarding.status(actor=self.w.student)["state"], "completed")

    def test_repeated_confirmation_returns_the_existing_records(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        review = onboarding.review(actor=self.w.student)
        first = onboarding.finalize(actor=self.w.student, expected_version=version,
                                    expected_fee_revision_id=review["fee"]["revision_id"], confirmed=True)
        counts, audits = record_counts(), AcademicPeriodAuditLog.objects.count()
        again = onboarding.finalize(actor=self.w.student, expected_version=version,
                                    expected_fee_revision_id=review["fee"]["revision_id"], confirmed=True)
        self.assertEqual(again["result"]["participation_id"], first["result"]["participation_id"])
        self.assertEqual((record_counts(), AcademicPeriodAuditLog.objects.count()), (counts, audits))
        self.conflict("already_completed", onboarding.save_student_type, actor=self.w.student, student_type="Irregular")

    def test_the_confirmed_fee_must_be_the_current_approved_rate_and_is_snapshotted(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        review = onboarding.review(actor=self.w.student)
        self.conflict("fee_changed", onboarding.finalize, actor=self.w.student, expected_version=version,
                      expected_fee_revision_id=review["fee"]["revision_id"] + 50, confirmed=True)
        self.conflict("confirmation_required", onboarding.finalize, actor=self.w.student, expected_version=version,
                      expected_fee_revision_id=review["fee"]["revision_id"], confirmed="yes")
        finalize(self.w.student, version)
        fees.save_draft(actor=self.w.admin, semester_id=self.sem, amount="1800.00", expected_draft_version=None,
                        change_reason="Student council resolution revised the semester fee.")
        preview = fees.approval_preview(actor=self.w.admin, semester_id=self.sem)
        self.assertEqual((preview["impact"]["status"], preview["impact"]["count"]), ("evaluated", 1))
        self.assertIn("obligations_assessed", preview["blockers"])
        with self.assertRaises(fees.FeeConflict) as caught:
            approve_fee(self.w, self.sem)
        self.assertEqual(caught.exception.reason, "obligations_assessed")
        self.assertEqual(FeeObligation.objects.get().amount, Decimal("1500.00"))  # snapshot unchanged

    def test_lane_one_ctu_integration_evidence_finalizes_without_admin_action(self):
        evidence = EnrollmentEvidence.objects.create(  # TEST ONLY: no runtime writer for this lane exists
            student=self.w.student, semester_id=self.sem, source_type="ctu_integration", source_reference="FIXTURE-1",
            entry_classification="newcomer", course_id=self.cat["courses"]["BSIT"], year_level=1, active_slot=1)
        for code in ("MATH 101", "IT 101"):
            EnrollmentEvidenceSubject.objects.create(evidence=evidence, subject_id=self.cat["subjects"][code])
        regular_steps(self.w.student, self.cat)
        result = finalize(self.w.student)
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(SemesterParticipation.objects.get().evidence_id, evidence.pk)

    def test_everything_is_revalidated_at_the_transaction_boundary(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        offering = self.prepared["offerings"][("1-A", "IT 101")]
        assignment = teaching.current_assignment(cfg._offerings_qs().get(pk=offering))
        teaching.end_assignment(actor=self.w.admin, offering_id=offering, expected_assignment_id=assignment.pk,
                                reason_code="instructor_unavailable")
        self.conflict("instructor_unassigned", finalize, self.w.student, version)
        teaching.assign_instructor(actor=self.w.admin, offering_id=offering, instructor_account_id=self.w.instructor2.pk,
                                   expected_assignment_id=None)
        result = finalize(self.w.student, version)
        requirement = ClearanceRequirement.objects.get(requirement_key=f"subject:{self.cat['subjects']['IT 101']}")
        self.assertEqual((result["outcome"], requirement.signatory_id), ("completed", self.w.instructor2.pk))

    def test_no_records_from_activation_login_draft_selection_or_verification_alone(self):
        self.assertEqual(record_counts(), ZERO)  # activation
        onboarding.status(actor=self.w.student)  # "login"
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        self.assertEqual(record_counts(), ZERO)  # verification
        with override_settings(WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED=False):
            regular_steps(self.w.student, self.cat)  # Draft, subject selection, course confirmation
            self.assertEqual(record_counts(), ZERO)
            review = onboarding.review(actor=self.w.student)
            self.assertIn("feature_disabled", review["blockers"])
            with self.assertRaises(services.AcademicPeriodFeatureDisabled):
                finalize(self.w.student)
        self.assertEqual(record_counts(), ZERO)

    def test_an_unapproved_or_unavailable_fee_holds_finalization(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        review = onboarding.review(actor=self.w.student)
        with override_settings(WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED=False):
            self.assertEqual(onboarding.review(actor=self.w.student)["blockers"], ["fee_unavailable"])
            self.conflict("fee_unavailable", onboarding.finalize, actor=self.w.student, expected_version=version,
                          expected_fee_revision_id=review["fee"]["revision_id"], confirmed=True)

    def test_the_active_semester_switch_is_detected(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        review = onboarding.review(actor=self.w.student)
        open_semester(self.w, self.cat, 2026, 2)  # activation closes the semester being onboarded
        self.conflict("semester_changed", onboarding.finalize, actor=self.w.student, expected_version=version,
                      expected_fee_revision_id=review["fee"]["revision_id"], confirmed=True)


# ---- Failure injection: every creation step rolls the whole finalization back ----------------------------

@override_settings(**ONBOARD)
class FailureInjectionTests(OnboardingBase):
    def setUp(self):
        self.sem = open_semester(self.w, self.cat)["semester_id"]
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        self.version = regular_steps(self.w.student, self.cat)
        self.revision = onboarding.review(actor=self.w.student)["fee"]["revision_id"]

    def snapshot(self):
        row = SemesterOnboarding.objects.get()
        return (record_counts(), (row.status, row.version, row.completed_at),
                AcademicPeriodAuditLog.objects.filter(action=onboarding.FINALIZE_ACTION).count(),
                FinanceAuditLog.objects.filter(action="finance.fee_obligation.create").count())

    def attempt(self):
        return onboarding.finalize(actor=self.w.student, expected_version=self.version,
                                   expected_fee_revision_id=self.revision, confirmed=True)

    def test_failure_at_each_step_leaves_nothing_behind_and_a_retry_succeeds(self):
        before = self.snapshot()
        for step in ("participation", "subjects", "clearance", "obligation", "audit", "completion"):
            def fail(name, step=step):
                if name == step:
                    raise RuntimeError(f"injected failure at {step}")
            with self.subTest(step=step), patch.object(onboarding, "_fail", side_effect=fail), \
                    self.assertRaises(RuntimeError):
                self.attempt()
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.attempt()["outcome"], "completed")

    def test_requirement_obligation_and_audit_write_failures_roll_back(self):
        before = self.snapshot()
        calls = {"n": 0}
        original = ClearanceRequirement.save

        def second_requirement_fails(instance, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise IntegrityError("injected requirement failure")
            return original(instance, *args, **kwargs)
        cases = (
            patch.object(ClearanceRequirement, "save", second_requirement_fails),
            patch.object(FeeObligation, "save", side_effect=IntegrityError("injected obligation failure")),
            patch.object(services, "write_audit", side_effect=RuntimeError("injected audit failure")),
            patch("apps.finance.fees._audit", side_effect=RuntimeError("injected finance audit failure")),
        )
        for case in cases:
            with self.subTest(case=str(case)), case, self.assertRaises((IntegrityError, RuntimeError,
                                                                         onboarding.OnboardingConflict)):
                self.attempt()
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.attempt()["outcome"], "completed")

    def test_database_constraints_back_the_uniqueness_rules(self):
        self.attempt()
        participation = SemesterParticipation.objects.get()
        clearance = SemesterClearance.objects.get(participation=participation)
        revision = FeeObligation.objects.get().fee_revision
        for create in (
            lambda: SemesterParticipation.objects.create(
                student=self.w.student, semester_id=self.sem, evidence=participation.evidence, source="historical_correction",
                student_type="Regular", course_id=participation.course_id, year_level=1, created_by=self.w.admin),
            lambda: SemesterClearance.objects.create(participation=participation, student=self.w.student,
                                                     semester_id=self.sem),
            lambda: FeeObligation.objects.create(participation=participation, student=self.w.student, semester_id=self.sem,
                                                 fee_revision=revision, amount=Decimal("1.00")),
            lambda: ClearanceRequirement.objects.create(clearance=clearance, requirement_key="treasurer_fee",
                                                        kind="treasurer_fee"),
            lambda: ClearanceRequirement.objects.create(clearance=clearance, requirement_key="subject:x",
                                                        kind="subject_instructor"),  # subject kind needs its signatory
            lambda: SemesterClearance.objects.filter(pk=clearance.pk).update(status="Cleared"),
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                create()


# ---- HDAC and multi-role isolation -------------------------------------------------------------------------

@override_settings(**ONBOARD)
class StudentAuthorizationTests(OnboardingBase):
    def setUp(self):
        self.sem = open_semester(self.w, self.cat)["semester_id"]

    def denied(self, actor, fn=onboarding.status, reason="access_denied", **kwargs):
        with self.assertRaises(services.AcademicPeriodDenied) as caught:
            fn(actor=actor, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def test_only_genuine_eligible_students_with_the_exact_permission(self):
        for actor in (self.w.admin, self.w.instructor, self.w.treasurer):
            with self.subTest(actor=actor.school_id):
                self.denied(actor)
        for n, flags in enumerate(({"is_staff": True}, {"status": "Pending"}, {"active": False}, {"is_superuser": True})):
            with self.subTest(flags=list(flags)):
                self.denied(self.w.account(f"WF0505-X{n}", "Student", **flags))
        self.w.deny(self.w.student, READ)
        self.denied(self.w.student)
        self.w.deny(self.w.student2, WRITE)
        self.assertEqual(onboarding.status(actor=self.w.student2)["state"], "onboarding")
        self.denied(self.w.student2, onboarding.save_student_type, student_type="Regular")
        RolePermission.objects.filter(permission=self.w.write).delete()
        self.denied(self.w.account("WF0505-NOGRANT", "Student"), onboarding.save_student_type, student_type="Regular")

    def test_selected_student_context_is_required_and_other_roles_cannot_bypass_it(self):
        dual = self.w.account("WF0505-DUAL", "Student", "Instructor")
        with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
            for role_id in (self.w.roles["Instructor"].pk, None, 999_999, self.w.roles["Admin"].pk):
                with self.subTest(role_id=role_id), bind_role_scope(dual.pk, role_id):
                    self.denied(dual, reason="student_context_required")
            with bind_role_scope(self.w.student.pk, self.w.roles["Student"].pk):
                self.denied(dual, reason="student_context_required")  # another account's scope
            self.denied(dual, reason="student_context_required")  # no scope at all
            with bind_role_scope(dual.pk, self.w.roles["Student"].pk):
                self.assertEqual(onboarding.status(actor=dual)["state"], "onboarding")
                onboarding.save_student_type(actor=dual, student_type="Regular")
            with bind_role_scope(dual.pk, self.w.roles["Instructor"].pk):
                self.denied(dual, onboarding.save_student_type, reason="student_context_required", student_type="Irregular")
        self.assertEqual(SemesterOnboarding.objects.get(student=dual).student_type, "Regular")

    def test_switches_services_and_protected_writer_fail_closed(self):
        with override_settings(WORKSPACE_STUDENT_ONBOARDING_ENABLED=False), \
                self.assertRaises(services.AcademicPeriodUnavailable):
            onboarding.status(actor=self.w.student)
        with override_settings(WORKSPACE_ACADEMIC_PERIODS_ENABLED=False), \
                self.assertRaises(services.AcademicPeriodUnavailable):
            onboarding.status(actor=self.w.student)
        with patch.object(services, "_executor_enabled", return_value=True), \
                self.assertRaises(services.AcademicPeriodUnavailable):
            onboarding.status(actor=self.w.student)
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        revision = onboarding.review(actor=self.w.student)["fee"]["revision_id"]
        # An inactive clearance service makes clearance.requests.self.submit ineffective (HDAC: Denied);
        # an inactive academic or finance service makes the shared locks unavailable.
        for code, expected in (("clearance", services.AcademicPeriodDenied), ("finance", services.AcademicPeriodUnavailable),
                               ("academic", services.AcademicPeriodUnavailable)):
            with self.subTest(service=code):
                Service.objects.filter(service_code=code).update(is_active=False)
                with self.assertRaises(expected):
                    onboarding.finalize(actor=self.w.student, expected_version=version,
                                        expected_fee_revision_id=revision, confirmed=True)
                Service.objects.filter(service_code=code).update(is_active=True)
        self.assertEqual(record_counts(), ZERO)
        import config.settings as base
        for name in (onboarding.ONBOARDING_SETTING, onboarding.FINALIZATION_SETTING, verification.VERIFY_SETTING,
                     "WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED"):
            self.assertIs(getattr(base, name), False, name)

    def test_objects_are_always_the_actors_own(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student, self.cat)
        finalize(self.w.student)
        self.assertEqual(onboarding.status(actor=self.w.student2)["state"], "onboarding")
        with self.assertRaises(onboarding.OnboardingRequired):
            onboarding.my_semester(actor=self.w.student2)
        self.assertEqual(onboarding.my_history(actor=self.w.student2), {"results": []})
        self.assertEqual(len(onboarding.my_history(actor=self.w.student)["results"]), 1)
