"""WF-05.05 finalization under real concurrency (committed transactions, separate connections).

Run: python manage.py test apps.academic.test_student_onboarding_concurrency --settings=config.test_settings --noinput
Disposable MySQL only. Every race asserts the invariants of the shared lock order: at most one
participation / clearance / obligation per Student and semester, never a partial set, and every
competing operation either serialized after the finalization or refused cleanly.
"""

import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase, override_settings

from apps.clearance.models import ClearanceRequirement, SemesterClearance
from apps.finance import fees
from apps.finance.models import FeeObligation, SemesterFeeRevision

from . import dependencies, lifecycle, onboarding, verification
from .models import Semester, SemesterParticipation
from .test_student_onboarding import (
    ONBOARD, OnboardingWorld, approve_fee, build_catalogue, open_semester, record, record_counts, regular_steps,
)


@override_settings(**ONBOARD)
class FinalizationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.w = OnboardingWorld()
        self.cat = build_catalogue(self.w)
        self.sem = open_semester(self.w, self.cat)["semester_id"]

    def tearDown(self):
        connections.close_all()

    def race(self, *calls):
        barrier = threading.Barrier(len(calls))
        results = [None] * len(calls)

        def run(index, fn):
            try:
                barrier.wait(5)
                results[index] = ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - reported to the test
                results[index] = ("error", exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(calls)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
        self.assertTrue(all(r is not None for r in results), results)
        return results

    def ready(self, student):
        record(self.w, student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(student, self.cat)
        revision = onboarding.review(actor=student)["fee"]["revision_id"]
        return lambda: onboarding.finalize(actor=student, expected_version=version, expected_fee_revision_id=revision,
                                           confirmed=True)

    def assert_consistent(self):
        participations = SemesterParticipation.objects.count()
        self.assertEqual(SemesterClearance.objects.count(), participations)
        self.assertEqual(FeeObligation.objects.count(), participations)
        for clearance in SemesterClearance.objects.all():
            self.assertEqual(ClearanceRequirement.objects.filter(clearance=clearance).count(),
                             SemesterParticipation.objects.get(pk=clearance.participation_id).subjects.count() + 2)
        for obligation in FeeObligation.objects.select_related("fee_revision"):
            self.assertEqual(obligation.amount, obligation.fee_revision.amount)

    def test_double_submission_from_two_sessions_creates_one_record_set(self):
        attempt = self.ready(self.w.student)
        results = self.race(attempt, attempt, attempt)
        self.assertTrue(all(r[0] == "ok" and r[1]["outcome"] == "completed" for r in results), results)
        self.assertEqual(len({r[1]["result"]["participation_id"] for r in results}), 1)
        self.assertEqual(record_counts(), {"participations": 1, "subjects": 2, "clearances": 1, "requirements": 4,
                                           "obligations": 1})

    def test_two_students_finalize_concurrently(self):
        results = self.race(self.ready(self.w.student), self.ready(self.w.student2))
        self.assertTrue(all(r[0] == "ok" and r[1]["outcome"] == "completed" for r in results), results)
        self.assertEqual(SemesterParticipation.objects.count(), 2)
        self.assert_consistent()

    def test_finalization_racing_closure_is_serialized(self):
        attempt = self.ready(self.w.student)
        preview = lifecycle.closure_preview(actor=self.w.admin, semester_id=self.sem)

        def closure():
            with dependencies.isolated_bundle(dependencies.DEFAULT_BUNDLE):
                return lifecycle.close_semester(actor=self.w.admin, semester_id=self.sem,
                                                expected_version=preview["semester"]["version"],
                                                acknowledged_warnings=preview["warnings"], confirmed=True)
        results = self.race(attempt, closure)
        finalized, closed = results
        semester = Semester.objects.get(pk=self.sem)
        if finalized[0] == "ok" and finalized[1]["outcome"] == "completed":
            # Finalization committed first: the closure saw new outstanding records and was refused
            # because its reviewed warnings changed - or it committed after with no participation lost.
            self.assertEqual(SemesterParticipation.objects.count(), 1)
            if closed[0] == "error":
                self.assertEqual(getattr(closed[1], "reason", None), "warnings_changed")
                self.assertEqual(semester.status, "Active")
        else:
            self.assertEqual(closed[0], "ok", results)
            self.assertEqual(getattr(finalized[1], "reason", None), "no_active_semester")
            self.assertEqual((semester.status, SemesterParticipation.objects.count()), ("Closed", 0))
        self.assert_consistent()

    def test_finalization_racing_a_fee_revision_uses_one_consistent_rate(self):
        attempt = self.ready(self.w.student)
        fees.save_draft(actor=self.w.admin, semester_id=self.sem, amount="1750.00", expected_draft_version=None,
                        change_reason="Student council resolution revised the semester fee.")
        results = self.race(attempt, lambda: approve_fee(self.w, self.sem))
        finalized, approved = results
        if finalized[0] == "ok":
            self.assertEqual(FeeObligation.objects.get().amount, Decimal("1500.00"))  # the rate the Student confirmed
            self.assertEqual(approved[0], "error", results)
            self.assertEqual(approved[1].reason, "obligations_assessed")
        else:
            self.assertEqual(approved[0], "ok", results)
            self.assertEqual(finalized[1].reason, "fee_changed")  # the reviewed rate is no longer current
            self.assertEqual(FeeObligation.objects.count(), 0)
        self.assertEqual(SemesterFeeRevision.objects.filter(status="Approved").count(), 1)
        self.assert_consistent()

    def test_finalization_racing_evidence_revocation(self):
        attempt = self.ready(self.w.student)
        evidence = verification.current_evidence(self.w.student.pk, self.sem)
        results = self.race(attempt, lambda: verification.revoke_evidence(
            actor=self.w.admin, evidence_id=evidence.pk, expected_version=evidence.version, reason_code="recorded_in_error"))
        finalized, revoked = results
        if finalized[0] == "ok" and finalized[1]["outcome"] == "completed":
            self.assertEqual((revoked[0], revoked[1].reason), ("error", "evidence_in_use"))
        else:
            self.assertEqual(revoked[0], "ok", results)
            self.assertEqual(finalized[1]["outcome"], "pending_verification")
            self.assertEqual(SemesterParticipation.objects.count(), 0)
        self.assert_consistent()

    def test_finalization_racing_activation_of_the_next_semester(self):
        attempt = self.ready(self.w.student)
        from .test_student_onboarding import prepare_semester
        next_id = prepare_semester(self.w, self.cat, 2026, 2)["semester_id"]
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=next_id)

        def activation():
            with dependencies.isolated_bundle(dependencies.DEFAULT_BUNDLE):
                return lifecycle.activate_semester(
                    actor=self.w.admin, semester_id=next_id, expected_version=preview["semester"]["version"],
                    expected_active_semester_id=self.sem, acknowledged_warnings=preview["warnings"], confirmed=True)
        finalized, activated = self.race(attempt, activation)
        self.assertEqual(activated[0], "ok", activated)
        if finalized[0] == "ok":
            self.assertEqual(SemesterParticipation.objects.get().semester_id, self.sem)  # never the new semester
        else:
            self.assertIn(finalized[1].reason, ("semester_changed", "no_active_semester"))
            self.assertEqual(SemesterParticipation.objects.count(), 0)
        self.assert_consistent()
