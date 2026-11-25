"""WF-11.01 lifecycle (activation/closure/archive), controlled edits, historical corrections, history.

Run: python manage.py test apps.academic.test_wf1101_lifecycle --settings=config.test_settings --noinput
Disposable MySQL only. Successful transitions use dependencies.isolated_bundle (fixed read-side
sources), which the module itself refuses outside the verified isolated database; no fee,
offering, participation, clearance or signature record is created.
"""

import threading
from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.access_control.models import AccountPermission
from apps.accounts.active_role_context import bind_role_scope

from . import corrections, dependencies, history, lifecycle, services
from .models import AcademicPeriodAuditLog, SchoolYear, Semester
from .test_wf1101_http import TOKEN, post, signed_in
from .test_wf1101_periods import GATE, READY_BUNDLE, World, activate, bundle, close, other_table_counts

TRANSITIONS = dict(GATE, WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=True)
CORRECTIONS = dict(TRANSITIONS, WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED=True)
NOTE = "Campus calendar revised by the registrar's memorandum."
ROOT = "/api/v1/academic/"


def year_with_dates(admin, start=2026):
    payload = services.create_school_year(actor=admin, start_year=start)
    first, second = (s["semester_id"] for s in payload["semesters"])
    services.update_semester_dates(actor=admin, semester_id=first, start_date=f"{start}-08-10",
                                   end_date=f"{start}-12-18", expected_version=1)
    services.update_semester_dates(actor=admin, semester_id=second, start_date=f"{start + 1}-01-11",
                                   end_date=f"{start + 1}-05-28", expected_version=1)
    return payload["school_year_id"], first, second


def rows():
    return list(Semester.objects.values().order_by("pk"))


def statuses():
    return dict(Semester.objects.values_list("pk", "status"))


@override_settings(**CORRECTIONS)
class ActivationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        self.year, self.first, self.second = year_with_dates(self.w.admin)

    def refused(self, reason, fn, *args, **kwargs):
        before, audits = rows(), AcademicPeriodAuditLog.objects.count()
        with self.assertRaises(lifecycle.TransitionRefused) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual((before, audits), (rows(), AcademicPeriodAuditLog.objects.count()))
        return caught.exception

    def confirm(self, semester_id, **overrides):
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=semester_id)
        current = preview["current_active"]
        kwargs = dict(actor=self.w.admin, semester_id=semester_id, expected_version=preview["semester"]["version"],
                      expected_active_semester_id=current["semester_id"] if current else None,
                      acknowledged_warnings=preview["warnings"], confirmed=True)
        kwargs.update(overrides)
        return lifecycle.activate_semester(**kwargs)

    def test_default_runtime_reports_precise_unavailable_prerequisites_and_refuses(self):
        preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)
        self.assertEqual(preview["prerequisites"], [
            {"key": "valid_dates", "status": "ready", "reason": ""},
            {"key": "approved_fee", "status": "unavailable", "reason": "fee_schedule_not_implemented"},
            {"key": "academic_offerings", "status": "unavailable", "reason": "curriculum_offerings_not_implemented"}])
        self.assertEqual((preview["can_confirm"], preview["blockers"]), (False, ["prerequisites_missing"]))
        error = self.refused("prerequisites_missing", self.confirm, self.first)
        self.assertEqual(error.missing, ("approved_fee", "academic_offerings"))

    def test_successful_activation_with_isolated_prerequisites(self):
        others = other_table_counts()
        with dependencies.isolated_bundle(READY_BUNDLE):
            preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)
            self.assertTrue(preview["can_confirm"], preview)
            result = self.confirm(self.first)
        self.assertEqual((result["status"], result["version"]), ("Active", 3))
        row = Semester.objects.get(pk=self.first)
        self.assertEqual((row.active_slot, row.closed_at is None), (1, True))
        audit = AcademicPeriodAuditLog.objects.get(action=lifecycle.ACTIVATE_ACTION)
        self.assertEqual((audit.actor_account_id, audit.old_value["status"], audit.new_value["status"]),
                         (self.w.admin.pk, "Draft", "Active"))
        self.assertEqual(other_table_counts(), others)  # no participation, fee or clearance created

    def test_missing_fee_or_offerings_prevent_activation(self):
        for source, expected in ((bundle(fee=dependencies.MISSING), ("approved_fee",)),
                                 (bundle(offerings=dependencies.MISSING), ("academic_offerings",)),
                                 (bundle(fee=dependencies.UNAVAILABLE), ("approved_fee",))):
            with self.subTest(expected=expected), dependencies.isolated_bundle(source):
                self.assertFalse(lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)["can_confirm"])
                self.assertEqual(self.refused("prerequisites_missing", self.confirm, self.first).missing, expected)
        Semester.objects.filter(pk=self.first).update(end_date=None)
        with dependencies.isolated_bundle(READY_BUNDLE):
            self.assertEqual(self.refused("prerequisites_missing", self.confirm, self.first).missing, ("valid_dates",))

    def test_a_substitute_that_omits_a_required_source_is_not_a_pass(self):
        partial = dependencies.DependencyBundle((), READY_BUNDLE.obligations, READY_BUNDLE.impact)
        with dependencies.isolated_bundle(partial):
            self.assertEqual(self.refused("prerequisites_missing", self.confirm, self.first).missing,
                             ("approved_fee", "academic_offerings"))

    def test_substitutes_are_refused_outside_the_isolated_database(self):
        with patch.object(dependencies, "isolated_test_database", return_value=False):
            with self.assertRaises(dependencies.DependencyUnavailable):
                with dependencies.isolated_bundle(READY_BUNDLE):
                    pass
        with dependencies.isolated_bundle(READY_BUNDLE), \
                patch.object(dependencies, "isolated_test_database", return_value=False):
            self.assertIs(dependencies.current_bundle(), dependencies.DEFAULT_BUNDLE)

    def test_atomic_transition_closes_the_previous_active_semester(self):
        with dependencies.isolated_bundle(READY_BUNDLE):
            self.confirm(self.first)
            preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.second)
            self.assertEqual(preview["current_active"]["semester_id"], self.first)
            self.assertIn("previous_active_will_close", preview["warnings"])
            self.refused("active_changed", self.confirm, self.second, expected_active_semester_id=None)
            self.confirm(self.second)
        self.assertEqual(statuses(), {self.first: "Closed", self.second: "Active"})
        actions = list(AcademicPeriodAuditLog.objects.filter(action__in=(lifecycle.ACTIVATE_ACTION, lifecycle.CLOSE_ACTION))
                       .order_by("pk").values_list("action", "semester_id"))
        self.assertEqual(actions, [(lifecycle.ACTIVATE_ACTION, self.first), (lifecycle.CLOSE_ACTION, self.first),
                                   (lifecycle.ACTIVATE_ACTION, self.second)])

    def test_failed_activation_rolls_back_both_state_changes_and_audit(self):
        real = services.write_audit

        def fail_on_activate(auth, **kwargs):
            if kwargs["action"] == lifecycle.ACTIVATE_ACTION:
                raise RuntimeError("audit down")
            return real(auth, **kwargs)

        with dependencies.isolated_bundle(READY_BUNDLE):
            self.confirm(self.first)
            before, audits = rows(), AcademicPeriodAuditLog.objects.count()
            with patch.object(services, "write_audit", side_effect=fail_on_activate), self.assertRaises(RuntimeError):
                self.confirm(self.second)
        self.assertEqual((rows(), AcademicPeriodAuditLog.objects.count()), (before, audits))  # nothing half-closed

    def test_confirmation_version_and_reviewed_warnings_are_required(self):
        with dependencies.isolated_bundle(READY_BUNDLE):
            self.refused("confirmation_required", self.confirm, self.first, confirmed="yes")
            self.refused("stale_version", self.confirm, self.first, expected_version=1)
            self.refused("warnings_changed", self.confirm, self.first, acknowledged_warnings=["something_else"])
            with patch.object(lifecycle, "campus_today", return_value=date(2026, 9, 1)):
                inside = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)["warnings"]
            with patch.object(lifecycle, "campus_today", return_value=date(2030, 1, 1)):
                self.refused("warnings_changed", self.confirm, self.first, acknowledged_warnings=inside)
        self.assertEqual(inside, [])
        with self.assertRaises(services.AcademicPeriodInvalid):
            self.confirm(self.first, acknowledged_warnings="none")

    def test_gates_permission_and_context_are_enforced(self):
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=False), \
                dependencies.isolated_bundle(READY_BUNDLE):
            preview = lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)
            self.assertEqual((preview["feature_enabled"], preview["can_confirm"]), (False, False))
            self.assertIn("feature_disabled", preview["blockers"])
            with self.assertRaises(services.AcademicPeriodFeatureDisabled):
                self.confirm(self.first)
        with override_settings(WORKSPACE_ACADEMIC_PERIODS_ENABLED=False), self.assertRaises(services.AcademicPeriodUnavailable):
            lifecycle.activation_preview(actor=self.w.admin, semester_id=self.first)
        student = self.w.account("WF1101-LSTU", "Student")
        with dependencies.isolated_bundle(READY_BUNDLE):
            with self.assertRaises(services.AcademicPeriodDenied):
                lifecycle.activation_preview(actor=student, semester_id=self.first)
            deny = self.w.deny(self.w.admin)
            with self.assertRaises(services.AcademicPeriodDenied):
                self.confirm(self.first, expected_version=2, expected_active_semester_id=None, acknowledged_warnings=[])
            AccountPermission.objects.filter(pk=deny.pk).delete()
            with override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True):
                with bind_role_scope(self.w.admin.pk, self.w.roles["Student"].pk), \
                        self.assertRaises(services.AcademicPeriodDenied):
                    lifecycle.activate_semester(actor=self.w.admin, semester_id=self.first, expected_version=2,
                                                expected_active_semester_id=None, acknowledged_warnings=[], confirmed=True)
        self.assertEqual(set(statuses().values()), {"Draft"})

    def test_a_deny_landing_during_the_transaction_is_honoured(self):
        real = services.authorize
        calls = []

        def deny_after_precheck(actor):
            result = real(actor)
            calls.append(1)
            if len(calls) == 2:  # preview, pre-check, then the locked re-check must see the Deny
                self.w.deny(self.w.admin)
            return result

        with dependencies.isolated_bundle(READY_BUNDLE), \
                patch.object(services, "authorize", side_effect=deny_after_precheck):
            with self.assertRaises(services.AcademicPeriodDenied):
                self.confirm(self.first)
        self.assertEqual(set(statuses().values()), {"Draft"})


@override_settings(**CORRECTIONS)
class ClosureAndArchiveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        self.year, self.first, self.second = year_with_dates(self.w.admin)
        activate(self.w.admin, self.first)

    def test_closure_preview_reports_unavailable_obligations_never_zero(self):
        preview = lifecycle.closure_preview(actor=self.w.admin, semester_id=self.first)
        self.assertEqual([(o["key"], o["status"], o["count"]) for o in preview["obligations"]], [
            ("outstanding_clearance_signatures", "unavailable", None), ("unpaid_fee_obligations", "unavailable", None),
            ("incomplete_onboarding", "unavailable", None)])
        self.assertTrue({"outstanding_clearance_signatures_unavailable", "unpaid_fee_obligations_unavailable",
                         "incomplete_onboarding_unavailable"} <= set(preview["warnings"]))
        self.assertTrue(preview["can_confirm"])  # warned closure is allowed (WF11-D11)

    def test_closure_requires_explicit_confirmation_of_the_reviewed_warnings(self):
        preview = lifecycle.closure_preview(actor=self.w.admin, semester_id=self.first)
        version = preview["semester"]["version"]
        for kwargs, reason in ((dict(confirmed=False, acknowledged_warnings=preview["warnings"]), "confirmation_required"),
                               (dict(confirmed=True, acknowledged_warnings=[]), "warnings_changed")):
            with self.subTest(reason=reason), self.assertRaises(lifecycle.TransitionRefused) as caught:
                lifecycle.close_semester(actor=self.w.admin, semester_id=self.first, expected_version=version, **kwargs)
            self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(statuses()[self.first], "Active")
        lifecycle.close_semester(actor=self.w.admin, semester_id=self.first, expected_version=version,
                                 acknowledged_warnings=preview["warnings"], confirmed=True)
        self.assertEqual(statuses()[self.first], "Closed")
        audit = AcademicPeriodAuditLog.objects.filter(action=lifecycle.CLOSE_ACTION).get()
        self.assertEqual(sorted(audit.new_value["acknowledged_warnings"]), sorted(preview["warnings"]))

    def test_closure_preserves_outstanding_obligations_and_every_other_record(self):
        others = other_table_counts()
        outstanding = bundle(obligations=3)
        with dependencies.isolated_bundle(outstanding):
            preview = lifecycle.closure_preview(actor=self.w.admin, semester_id=self.first)
            self.assertIn("unpaid_fee_obligations_outstanding", preview["warnings"])
            close(self.w.admin, self.first, source=outstanding)
        audit = AcademicPeriodAuditLog.objects.filter(action=lifecycle.CLOSE_ACTION).get()
        self.assertEqual({o["key"]: o["count"] for o in audit.new_value["obligations"]},
                         {"outstanding_clearance_signatures": 3, "unpaid_fee_obligations": 3, "incomplete_onboarding": 3})
        self.assertEqual(other_table_counts(), others)  # nothing settled, cleared or deleted
        self.assertFalse(dependencies.accepts_new_onboarding(Semester.objects.get(pk=self.first)))
        with self.assertRaises(dependencies.DependencyUnavailable):
            dependencies.request_historical_participation_correction(semester_id=self.first)

    def test_archive_only_from_closed_and_archived_periods_stay_immutable(self):
        with self.assertRaises(lifecycle.TransitionRefused) as caught:
            close(self.w.admin, self.first, archive=True)
        self.assertEqual(caught.exception.reason, "not_closed")
        self.assertFalse(lifecycle.archive_preview(actor=self.w.admin, semester_id=self.first)["can_confirm"])
        close(self.w.admin, self.first)
        preview = lifecycle.archive_preview(actor=self.w.admin, semester_id=self.first)
        self.assertTrue(preview["can_confirm"])
        close(self.w.admin, self.first, archive=True)  # obligations need not be settled first
        row = Semester.objects.get(pk=self.first)
        self.assertEqual((row.status, row.active_slot), ("Archived", None))
        self.assertTrue(row.activated_at and row.closed_at and row.archived_at)
        for fn, reason in ((lambda: activate(self.w.admin, self.first), "not_draft"),
                           (lambda: close(self.w.admin, self.first), "not_active"),
                           (lambda: close(self.w.admin, self.first, archive=True), "not_closed")):
            with self.subTest(reason=reason), self.assertRaises(lifecycle.TransitionRefused) as caught:
                fn()
            self.assertEqual(caught.exception.reason, reason)
        with self.assertRaises(services.AcademicPeriodConflict):
            services.update_semester_dates(actor=self.w.admin, semester_id=self.first, start_date="2026-08-11",
                                           end_date="2026-12-18", expected_version=row.version)
        with self.assertRaises(services.AcademicPeriodConflict):
            services.delete_school_year(actor=self.w.admin, school_year_id=self.year, expected_start_year=2026)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(pk=self.first).update(status="Draft")
        self.assertEqual(Semester.objects.get(pk=self.first).status, "Archived")

    def test_database_backstop_forbids_two_active_semesters(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(pk=self.second).update(status="Active", active_slot=1, activated_at=timezone.now())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Semester.objects.filter(pk=self.second).update(status="Active", activated_at=timezone.now())


@override_settings(**CORRECTIONS)
class CorrectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        self.year, self.first, self.second = year_with_dates(self.w.admin)
        activate(self.w.admin, self.first)

    def version(self, semester_id):
        return Semester.objects.get(pk=semester_id).version

    def correct(self, semester_id, start="2026-08-17", end="2026-12-18", source=bundle(), **overrides):
        kwargs = dict(actor=self.w.admin, semester_id=semester_id, start_date=start, end_date=end,
                      expected_version=self.version(semester_id), reason_code="calendar_change", reason_note=NOTE)
        kwargs.update(overrides)
        with dependencies.isolated_bundle(source):
            return corrections.correct_semester_dates(**kwargs)

    def conflict(self, reason, *args, **kwargs):
        before, audits = rows(), AcademicPeriodAuditLog.objects.count()
        with self.assertRaises(services.AcademicPeriodConflict) as caught:
            self.correct(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual((before, audits), (rows(), AcademicPeriodAuditLog.objects.count()))
        return caught.exception

    def test_valid_active_edit_is_audited_with_old_value_new_value_and_reason(self):
        before_version = self.version(self.first)
        payload = self.correct(self.first)
        semester = next(s for s in payload["semesters"] if s["semester_id"] == self.first)
        self.assertEqual((semester["status"], semester["start_date"], semester["version"]),
                         ("Active", "2026-08-17", before_version + 1))
        audit = AcademicPeriodAuditLog.objects.get(action=corrections.ACTIVE_EDIT_ACTION)
        self.assertEqual((audit.old_value["start_date"], audit.new_value["start_date"], audit.reason, audit.reason_note,
                          audit.actor_account_id), ("2026-08-10", "2026-08-17", "calendar_change", NOTE, self.w.admin.pk))
        self.assertEqual(Semester.objects.get(pk=self.first).active_slot, 1)

    def test_default_runtime_refuses_because_impact_cannot_be_evaluated(self):
        preview = corrections.correction_preview(actor=self.w.admin, semester_id=self.first)
        self.assertEqual((preview["kind"], preview["can_confirm"]), ("active_edit", False))
        self.assertIn("impact_unavailable", preview["blockers"])
        before = rows()
        with self.assertRaises(services.AcademicPeriodConflict) as caught:
            corrections.correct_semester_dates(actor=self.w.admin, semester_id=self.first, start_date="2026-08-17",
                                               end_date="2026-12-18", expected_version=self.version(self.first),
                                               reason_code="calendar_change", reason_note=NOTE)
        self.assertEqual((caught.exception.reason, caught.exception.details),
                         ("impact_unavailable", ("student_participation", "fee_obligations", "clearance_records")))
        self.assertEqual(before, rows())

    def test_affected_records_require_acknowledgment_and_are_never_rewritten(self):
        others = other_table_counts()
        affected = bundle(impact=4)
        error = self.conflict("impact_review_required", self.first, source=affected)
        self.assertEqual(set(error.details), set(dependencies.IMPACT_RECORDS))
        self.correct(self.first, source=affected, acknowledged_impacts=list(dependencies.IMPACT_RECORDS))
        self.assertEqual(other_table_counts(), others)
        self.conflict("impact_unavailable", self.first, start="2026-08-18", source=bundle(impact=None))

    def test_invalid_input_dates_and_reasons_are_refused(self):
        cases = [dict(start="2026-12-18", end="2026-08-10"), dict(start=None), dict(end="2028-01-01"),
                 dict(reason_code="because"), dict(reason_note="short"), dict(reason_note="x" * 501),
                 dict(reason_note="Bad\x00note text here"), dict(expected_version=True), dict(acknowledged_impacts="all")]
        for overrides in cases:
            with self.subTest(**{k: str(v)[:20] for k, v in overrides.items()}):
                with self.assertRaises(services.AcademicPeriodInvalid):
                    self.correct(self.first, **overrides)
        self.conflict("semesters_overlap", self.first, end="2027-01-11")
        self.conflict("no_change", self.first, start="2026-08-10")
        self.conflict("stale_version", self.first, expected_version=1)
        self.conflict("period_is_draft", self.second, start="2027-01-12", end="2027-05-28")

    def test_historical_corrections_never_reopen_and_are_traceable(self):
        close(self.w.admin, self.first)
        self.correct(self.first, reason_code="data_entry_correction")
        close(self.w.admin, self.first, archive=True)
        self.correct(self.first, start="2026-08-18", reason_code="institutional_directive")
        self.assertEqual(Semester.objects.get(pk=self.first).status, "Archived")
        self.assertEqual(AcademicPeriodAuditLog.objects.filter(action=corrections.HISTORICAL_CORRECTION_ACTION).count(), 2)
        page = history.school_year_history(actor=self.w.admin, school_year_id=self.year)
        self.assertEqual([e["event"] for e in page["results"][:4]], [
            corrections.HISTORICAL_CORRECTION_ACTION, lifecycle.ARCHIVE_ACTION, corrections.HISTORICAL_CORRECTION_ACTION,
            lifecycle.CLOSE_ACTION])
        latest = page["results"][0]
        self.assertEqual((latest["actor"], latest["semester"], latest["reason"], latest["note"]),
                         ("You", "first", "institutional_directive", NOTE))
        self.assertEqual(latest["changes"], {"start_date": {"before": "2026-08-17", "after": "2026-08-18"}})
        text = repr(page)
        for hidden in ("actor_account", "acting_role", self.w.admin.school_id, "old_value"):
            self.assertNotIn(hidden, text)
        other_admin = self.w.account("WF1101-ADM2", "Admin")
        self.assertEqual(history.school_year_history(actor=other_admin, school_year_id=self.year)["results"][0]["actor"],
                         "An administrator")

    def test_gate_and_authorization(self):
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED=False):
            with self.assertRaises(services.AcademicPeriodFeatureDisabled):
                self.correct(self.first)
            self.assertIn("feature_disabled", corrections.correction_preview(actor=self.w.admin,
                                                                              semester_id=self.first)["blockers"])
        for role in ("Student", "Instructor", "Treasurer"):
            with self.subTest(role=role), self.assertRaises(services.AcademicPeriodDenied):
                self.correct(self.first, actor=self.w.account(f"WF1101-C{role[:3].upper()}", role))
        self.w.deny(self.w.admin)
        with self.assertRaises(services.AcademicPeriodDenied):
            self.correct(self.first)
        with self.assertRaises(services.AcademicPeriodDenied):
            history.school_year_history(actor=self.w.admin, school_year_id=self.year)


class LifecycleConcurrencyTests(TransactionTestCase):
    def tearDown(self):
        connections.close_all()

    def race(self, *calls):
        barrier = threading.Barrier(len(calls))
        results = [None] * len(calls)

        def run(index, fn):
            try:
                barrier.wait(5)
                with dependencies.isolated_bundle(READY_BUNDLE):  # ContextVars are per thread
                    results[index] = ("ok", fn())
            except Exception as exc:  # noqa: BLE001 - reported to the test
                results[index] = ("error", exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(calls)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        return results

    @override_settings(**CORRECTIONS)
    def test_concurrent_activations_never_produce_two_active_semesters(self):
        w = World()
        ids = [year_with_dates(w.admin, start)[1] for start in (2026, 2027)]
        previews = {}
        with dependencies.isolated_bundle(READY_BUNDLE):
            for sid in ids:
                previews[sid] = lifecycle.activation_preview(actor=w.admin, semester_id=sid)
        results = self.race(*[
            (lambda sid=sid: lifecycle.activate_semester(
                actor=w.admin, semester_id=sid, expected_version=previews[sid]["semester"]["version"],
                expected_active_semester_id=None, acknowledged_warnings=previews[sid]["warnings"], confirmed=True))
            for sid in ids])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        refused = [r[1] for r in results if r[0] == "error"]
        self.assertTrue(all(isinstance(e, lifecycle.TransitionRefused) and e.reason == "active_changed" for e in refused),
                        refused)
        self.assertEqual(Semester.objects.filter(status="Active").count(), 1)
        self.assertEqual(AcademicPeriodAuditLog.objects.filter(action=lifecycle.ACTIVATE_ACTION).count(), 1)

    @override_settings(**CORRECTIONS)
    def test_concurrent_corrections_with_one_version_apply_once(self):
        w = World()
        _, first, _ = year_with_dates(w.admin)
        with dependencies.isolated_bundle(READY_BUNDLE):
            activate(w.admin, first)
        version = Semester.objects.get(pk=first).version
        results = self.race(*[
            (lambda day=day: corrections.correct_semester_dates(
                actor=w.admin, semester_id=first, start_date=f"2026-08-{day}", end_date="2026-12-18",
                expected_version=version, reason_code="calendar_change", reason_note=NOTE)) for day in ("11", "12")])
        self.assertEqual(sum(r[0] == "ok" for r in results), 1, results)
        self.assertTrue(all(isinstance(r[1], services.AcademicPeriodConflict) and r[1].reason == "stale_version"
                            for r in results if r[0] == "error"))
        self.assertEqual(AcademicPeriodAuditLog.objects.filter(action=corrections.ACTIVE_EDIT_ACTION).count(), 1)


@override_settings(**CORRECTIONS)
class LifecycleHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.admin)
        self.year, self.first, self.second = year_with_dates(self.w.admin)

    def test_activation_preview_and_confirmation_over_http(self):
        reply = self.client.get(f"{ROOT}semesters/{self.first}/activation/")
        self.assertEqual(reply.status_code, 200, reply.content)
        self.assertEqual(set(reply.json()), {"semester", "current_active", "prerequisites", "warnings", "blockers",
                                             "feature_enabled", "can_confirm"})
        body = {"confirmed": True, "expected_version": 2, "expected_active_semester_id": None,
                "acknowledged_warnings": reply.json()["warnings"]}
        refused = post(self.client, f"{ROOT}semesters/{self.first}/activation/", body)
        self.assertEqual((refused.status_code, refused.json()["error"]["reason"], refused.json()["error"]["details"]),
                         (409, "prerequisites_missing", ["approved_fee", "academic_offerings"]))
        with dependencies.isolated_bundle(READY_BUNDLE):
            reply = post(self.client, f"{ROOT}semesters/{self.first}/activation/", body)
        self.assertEqual((reply.status_code, reply.json()["status"]), (200, "Active"), reply.content)
        listing = self.client.get(f"{ROOT}school-years/").json()
        self.assertEqual(listing["features"], {"transitions": True, "corrections": True})
        self.assertEqual(listing["results"][0]["status"], "Active")

    def test_closure_archive_correction_and_history_routes(self):
        activate(self.w.admin, self.first)
        preview = self.client.get(f"{ROOT}semesters/{self.first}/closure/").json()
        reply = post(self.client, f"{ROOT}semesters/{self.first}/closure/",
                     {"confirmed": True, "expected_version": preview["semester"]["version"],
                      "acknowledged_warnings": preview["warnings"]})
        self.assertEqual((reply.status_code, reply.json()["status"]), (200, "Closed"), reply.content)
        preview = self.client.get(f"{ROOT}semesters/{self.first}/archive/").json()
        reply = post(self.client, f"{ROOT}semesters/{self.first}/archive/",
                     {"confirmed": True, "expected_version": preview["semester"]["version"],
                      "acknowledged_warnings": preview["warnings"]})
        self.assertEqual(reply.json()["status"], "Archived")
        impact = self.client.get(f"{ROOT}semesters/{self.first}/corrections/").json()
        self.assertEqual((impact["kind"], impact["can_confirm"]), ("historical_correction", False))
        body = {"start_date": "2026-08-17", "end_date": "2026-12-18", "expected_version": reply.json()["version"],
                "reason_code": "data_entry_correction", "reason_note": NOTE}
        refused = post(self.client, f"{ROOT}semesters/{self.first}/corrections/", body)
        self.assertEqual((refused.status_code, refused.json()["error"]["reason"]), (409, "impact_unavailable"))
        with dependencies.isolated_bundle(bundle()):
            reply = post(self.client, f"{ROOT}semesters/{self.first}/corrections/", body)
        self.assertEqual(reply.status_code, 200, reply.content)
        bad = post(self.client, f"{ROOT}semesters/{self.first}/corrections/", {**body, "reason_note": "no"})
        self.assertEqual(bad.json()["error"]["fields"], {"reason_note": ["Explain the change in 10 to 500 characters."]})
        events = self.client.get(f"{ROOT}school-years/{self.year}/history/").json()["results"]
        self.assertEqual(events[0]["event"], corrections.HISTORICAL_CORRECTION_ACTION)
        self.assertEqual(self.client.get(f"{ROOT}school-years/999999/history/").status_code, 404)

    def test_disabled_lifecycle_gates_answer_feature_disabled(self):
        with override_settings(WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED=False,
                               WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED=False):
            preview = self.client.get(f"{ROOT}semesters/{self.first}/activation/")
            self.assertEqual((preview.status_code, preview.json()["feature_enabled"]), (200, False))
            for path, body in ((f"semesters/{self.first}/activation/", {"confirmed": True, "expected_version": 3,
                                "expected_active_semester_id": None, "acknowledged_warnings": []}),
                               (f"semesters/{self.first}/closure/", {"confirmed": True, "expected_version": 3,
                                "acknowledged_warnings": []}),
                               (f"semesters/{self.first}/corrections/", {"start_date": "2026-08-17",
                                "end_date": "2026-12-18", "expected_version": 3, "reason_code": "calendar_change",
                                "reason_note": NOTE})):
                reply = post(self.client, ROOT + path, body)
                self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "feature_disabled"), path)
        student = signed_in(self.w.account("WF1101-HLST", "Student"))
        self.assertEqual(student.get(f"{ROOT}semesters/{self.first}/activation/").status_code, 403)
        self.assertEqual(post(self.client, f"{ROOT}semesters/{self.first}/activation/", {"confirmed": True}).status_code, 400)
        self.assertEqual(self.client.post(f"{ROOT}semesters/{self.first}/closure/", data="{}",
                                          content_type="application/json").status_code, 403)  # no CSRF token
        self.assertEqual(set(statuses().values()), {"Draft"})
        self.assertTrue(TOKEN)
