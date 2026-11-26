"""WF-11.01 residual operations with real downstream records: closure/archive obligation counts,
controlled Active edits and historical date corrections with real impact, and the WF11-D14 evidenced
historical participation correction.

Run: python manage.py test apps.academic.test_wf1101_residual --settings=config.test_settings --noinput
Disposable MySQL only; every record is created by the real services (onboarding finalization or the
historical correction), never by a substitute bundle.
"""

from decimal import Decimal

from django.test import override_settings

from apps.clearance.models import ClearanceRequirement, SemesterClearance
from apps.finance.models import FeeObligation, FinanceAuditLog

from . import corrections, dependencies, historical_participation as hp, lifecycle, services, verification
from .models import AcademicPeriodAuditLog, Semester, SemesterParticipation
from .test_student_onboarding import (
    ONBOARD, OnboardingBase, finalize, open_semester, prepare_semester, record, record_counts, regular_steps,
)
from .test_wf1101_periods import close

NOTE = "Registrar list confirmed the official dates."


def records_snapshot():
    return (list(SemesterParticipation.objects.values().order_by("pk")),
            list(SemesterClearance.objects.values().order_by("pk")),
            list(ClearanceRequirement.objects.values().order_by("pk")),
            list(FeeObligation.objects.values().order_by("pk")))


@override_settings(**ONBOARD)
class RealObligationTests(OnboardingBase):
    def setUp(self):
        self.prepared = open_semester(self.w, self.cat)
        self.sem = self.prepared["semester_id"]
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student, self.cat)
        finalize(self.w.student)
        from . import onboarding
        onboarding.save_student_type(actor=self.w.student2, student_type="Irregular")  # an unfinished Draft

    def test_closure_reports_real_outstanding_records_and_preserves_them(self):
        preview = lifecycle.closure_preview(actor=self.w.admin, semester_id=self.sem)
        self.assertEqual({o["key"]: (o["status"], o["count"]) for o in preview["obligations"]}, {
            "outstanding_clearance_signatures": ("evaluated", 4), "unpaid_fee_obligations": ("evaluated", 1),
            "incomplete_onboarding": ("evaluated", 1)})
        self.assertTrue({"outstanding_clearance_signatures_outstanding", "unpaid_fee_obligations_outstanding",
                         "incomplete_onboarding_outstanding"} <= set(preview["warnings"]))
        before = records_snapshot()
        with self.assertRaises(lifecycle.TransitionRefused) as caught:
            with dependencies.isolated_bundle(dependencies.DEFAULT_BUNDLE):
                lifecycle.close_semester(actor=self.w.admin, semester_id=self.sem,
                                         expected_version=preview["semester"]["version"],
                                         acknowledged_warnings=["before_end_date"], confirmed=True)
        self.assertEqual(caught.exception.reason, "warnings_changed")  # the outstanding records must be reviewed
        close(self.w.admin, self.sem, source=dependencies.DEFAULT_BUNDLE)
        audit = AcademicPeriodAuditLog.objects.get(action=lifecycle.CLOSE_ACTION)
        self.assertEqual({o["key"]: o["count"] for o in audit.new_value["obligations"]},
                         {"outstanding_clearance_signatures": 4, "unpaid_fee_obligations": 1, "incomplete_onboarding": 1})
        self.assertEqual(records_snapshot(), before)  # closure settles, clears and deletes nothing
        close(self.w.admin, self.sem, source=dependencies.DEFAULT_BUNDLE, archive=True)
        self.assertEqual((Semester.objects.get(pk=self.sem).status, records_snapshot()), ("Archived", before))

    def test_active_edit_and_historical_correction_need_the_real_impact_acknowledged(self):
        semester = Semester.objects.get(pk=self.sem)
        preview = corrections.correction_preview(actor=self.w.admin, semester_id=self.sem)
        self.assertEqual({i["key"]: i["count"] for i in preview["impact"]},
                         {"student_participation": 1, "fee_obligations": 1, "clearance_records": 1})
        self.assertEqual(set(preview["affected"]), {"student_participation", "fee_obligations", "clearance_records"})
        kwargs = dict(actor=self.w.admin, semester_id=self.sem, start_date="2026-08-17", end_date="2026-12-18",
                      reason_code="calendar_change", reason_note=NOTE)
        before = records_snapshot()
        with self.assertRaises(services.AcademicPeriodConflict) as caught:
            corrections.correct_semester_dates(expected_version=semester.version, **kwargs)
        self.assertEqual(caught.exception.reason, "impact_review_required")
        corrections.correct_semester_dates(expected_version=semester.version, acknowledged_impacts=preview["affected"],
                                           **kwargs)
        audit = AcademicPeriodAuditLog.objects.get(action=corrections.ACTIVE_EDIT_ACTION)
        self.assertEqual({i["key"]: i["count"] for i in audit.new_value["impact"]},
                         {"student_participation": 1, "fee_obligations": 1, "clearance_records": 1})
        self.assertEqual(records_snapshot(), before)  # Student, clearance and fee records are never rewritten
        close(self.w.admin, self.sem, source=dependencies.DEFAULT_BUNDLE)
        semester.refresh_from_db()
        corrections.correct_semester_dates(
            actor=self.w.admin, semester_id=self.sem, start_date="2026-08-10", end_date="2026-12-18",
            expected_version=semester.version, reason_code="data_entry_correction", reason_note=NOTE,
            acknowledged_impacts=["student_participation", "fee_obligations", "clearance_records"])
        self.assertEqual(Semester.objects.get(pk=self.sem).status, "Closed")  # a correction never reopens
        self.assertEqual(records_snapshot(), before)


@override_settings(**ONBOARD)
class HistoricalParticipationTests(OnboardingBase):
    """WF11-D14: a Student officially enrolled in a past semester without a Workspace participation."""

    def setUp(self):
        self.past = open_semester(self.w, self.cat, 2025, 2, fee="1400.00")
        self.past_id = self.past["semester_id"]
        self.current = open_semester(self.w, self.cat, 2026, 1)["semester_id"]  # closes 2025-2
        self.evidence = record(self.w, self.w.student, self.past_id, self.cat, ["IT 102"])
        self.offering = self.past["offerings"][("1-A", "IT 102")]

    def correct(self, **overrides):
        kwargs = dict(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.past_id,
                      expected_evidence_id=self.evidence["evidence_id"], student_type="Regular",
                      offering_ids=[self.offering], reason_note="Official CTU enrollment confirmed in person.",
                      confirmed=True)
        kwargs.update(overrides)
        return hp.correct(**kwargs)

    def refused(self, reason, **overrides):
        before = record_counts()
        with self.assertRaises(hp.HistoricalCorrectionRefused) as caught:
            self.correct(**overrides)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(record_counts(), before)

    def test_evidenced_correction_creates_the_full_record_set_without_reopening(self):
        preview = hp.preview(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.past_id)
        self.assertEqual((preview["blockers"], preview["fee"]["amount"]), ([], "1400.00"))
        self.assertEqual([o["offering_id"] for o in preview["options"]], [self.offering, self.past["offerings"][("1-B", "IT 102")]])
        result = self.correct()
        self.assertTrue(result["created"])
        participation = SemesterParticipation.objects.get()
        self.assertEqual((participation.source, participation.onboarding_id, participation.created_by_id),
                         ("historical_correction", None, self.w.admin.pk))
        self.assertEqual((SemesterClearance.objects.get().status, ClearanceRequirement.objects.count()), ("Uncleared", 3))
        obligation = FeeObligation.objects.get()
        self.assertEqual((obligation.amount, obligation.status), (Decimal("1400.00"), "Unpaid"))  # ORIGINAL rate
        semester = Semester.objects.get(pk=self.past_id)
        self.assertEqual((semester.status, semester.active_slot), ("Closed", None))  # never reopened
        audit = AcademicPeriodAuditLog.objects.get(action=hp.ACTION)
        self.assertEqual((audit.actor_account_id, audit.reason_note), (self.w.admin.pk, "Official CTU enrollment confirmed in person."))
        self.assertTrue(FinanceAuditLog.objects.get(action="finance.fee_obligation.create").new_value["historical"])
        self.refused("participation_exists")
        # The new period now sees the late-entered semester as the previous participation (Uncleared).
        from . import eligibility
        result = eligibility.evaluate(self.w.student, Semester.objects.get(pk=self.current))
        self.assertEqual(result["status"], "clearance_required")

    def test_refusals_never_invent_fee_signatory_or_enrollment(self):
        self.refused("period_not_historical", semester_id=self.current)
        self.refused("evidence_changed", expected_evidence_id=self.evidence["evidence_id"] + 99)
        self.refused("subjects_mismatch", offering_ids=[self.offering, self.past["offerings"][("1-B", "IT 102")]])
        self.refused("subjects_mismatch", offering_ids=[self.offering + 1000])
        self.refused("confirmation_required", confirmed=False)
        dual = self.w.account("WF0505-HADM", "Admin", "Student")
        dual_evidence = record(self.w, dual, self.past_id, self.cat, ["IT 102"])  # recorded by ANOTHER School Admin
        self.refused("self_verification", actor=dual, student_account_id=dual.pk,
                     expected_evidence_id=dual_evidence["evidence_id"])
        with self.assertRaises(services.AcademicPeriodInvalid):
            self.correct(reason_note="short")
        for actor in (self.w.student, self.w.instructor):
            with self.subTest(actor=actor.school_id), self.assertRaises(services.AcademicPeriodDenied):
                self.correct(actor=actor)
        with override_settings(WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED=False), \
                self.assertRaises(services.AcademicPeriodUnavailable):
            self.correct()

    def test_without_the_original_approved_fee_no_amount_is_invented(self):
        unpriced = prepare_semester(self.w, self.cat, 2027, 1, fee=None)
        past2 = unpriced["semester_id"]
        # Closed history without an approved fee: give it Closed status directly (TEST ONLY fixture; no
        # activation is possible without an approved fee, which is exactly the point being tested).
        from django.utils import timezone
        Semester.objects.filter(pk=past2).update(status="Closed", activated_at=timezone.now(),
                                                       closed_at=timezone.now(), active_slot=None)
        evidence = record(self.w, self.w.student2, past2, self.cat, ["MATH 101", "IT 101"])
        preview = hp.preview(actor=self.w.admin, student_account_id=self.w.student2.pk, semester_id=past2)
        self.assertIn("historical_fee_unavailable", preview["blockers"])
        before = record_counts()
        with self.assertRaises(hp.HistoricalCorrectionRefused) as caught:
            hp.correct(actor=self.w.admin, student_account_id=self.w.student2.pk, semester_id=past2,
                       expected_evidence_id=evidence["evidence_id"], student_type="Regular",
                       offering_ids=[unpriced["offerings"][("1-A", "MATH 101")], unpriced["offerings"][("1-A", "IT 101")]],
                       reason_note="Official CTU enrollment confirmed in person.", confirmed=True)
        self.assertEqual(caught.exception.reason, "historical_fee_unavailable")
        self.assertEqual(record_counts(), before)

    def test_a_verified_gap_or_unassigned_instructor_refuses(self):
        other = self.w.account("WF0505-GAP", "Student")
        verification.record_gap(actor=self.w.admin, student_account_id=other.pk, semester_id=self.past_id,
                                source_reference="CTU-LOA 2025-1")
        with self.assertRaises(hp.HistoricalCorrectionRefused) as caught:
            self.correct(student_account_id=other.pk)
        self.assertEqual(caught.exception.reason, "evidence_required")  # a gap is never enrollment evidence
        from apps.access_control.models import AccountRole
        AccountRole.objects.filter(account=self.w.instructor).delete()  # the 1-A instructor is no longer eligible
        self.refused("instructor_unassigned")  # nobody is substituted for the real assigned instructor

    def test_the_dependency_contract_delegates_to_the_real_correction(self):
        result = dependencies.request_historical_participation_correction(
            actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.past_id,
            expected_evidence_id=self.evidence["evidence_id"], student_type="Irregular", offering_ids=[self.offering],
            reason_note="Official CTU enrollment confirmed in person.", confirmed=True)
        self.assertTrue(result["created"])
        self.assertEqual(SemesterParticipation.objects.get().student_type, "Irregular")
