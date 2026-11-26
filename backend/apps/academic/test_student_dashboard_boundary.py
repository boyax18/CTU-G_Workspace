"""WF11-D17 Student dashboard boundary, route classification, signatory and governance safeguards.

Run: python manage.py test apps.academic.test_student_dashboard_boundary --settings=config.test_settings --noinput
Disposable MySQL only. Covers the server side of the dashboard boundary (every API route classified;
semester-dependent operations refused with the structured ``onboarding_required`` answer until the
CURRENT Active semester is finalized; account, period, onboarding and historical operations never
gated), Student self-signatory refusal, authorization revalidation during finalization, that the
legacy broad codes no longer authorize the narrow catalogue v2.3 operations, and the fee-revision safeguard.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver

from apps.access_control.models import Permission, RolePermission
from apps.accounts.active_role_context import SESSION_ROLE_KEY
from apps.clearance.models import ClearanceRequirement
from apps.clearance.services import ClearanceCreationRefused, create_semester_clearance
from apps.finance import fees
from apps.finance.models import FeeObligation, SemesterFeeRevision

from . import historical_participation as hp
from . import onboarding, services, student_gate, teaching, verification
from .models import ParticipationSubject, SemesterOnboarding, SemesterParticipation, SubjectOffering
from .test_student_onboarding import (
    ONBOARD, ZERO, OnboardingBase, approve_fee, finalize, open_semester, record, record_counts, regular_steps,
)
from .test_wf1101_http import ROLE_CONTEXT, post, signed_in

ON = "/api/v1/academic/onboarding/"
PROPOSED = {"student_onboarding": "academic.semester_onboarding.self.submit",
            "enrollment_verification": "academic.enrollment_verifications.record",
            "historical_correction": "academic.historical_participation.correct"}


def api_routes(urlconf):
    def walk(patterns, prefix=""):
        for entry in patterns:
            if isinstance(entry, URLResolver):
                yield from walk(entry.url_patterns, prefix + str(entry.pattern))
            elif isinstance(entry, URLPattern) and (prefix + str(entry.pattern)).startswith("api/"):
                yield prefix + str(entry.pattern), entry.name
    return list(walk(get_resolver(urlconf).url_patterns))


class RouteClassificationTests(SimpleTestCase):
    def test_every_api_route_is_classified_and_only_my_semester_is_semester_dependent(self):
        for urlconf in ("config.urls", "config.review_decision_local_urls"):
            for route, name in api_routes(urlconf):
                with self.subTest(urlconf=urlconf, route=route):
                    self.assertIn(student_gate.route_class(name), student_gate.CLASSES, f"unclassified route {route}")
        dependent = sorted(n for n, c in student_gate.ROUTE_POLICY.items() if c == student_gate.SEMESTER_DEPENDENT)
        self.assertEqual(dependent, ["academic-onboarding-my-semester"])
        self.assertEqual(student_gate.route_class("academic-onboarding-my-history"), student_gate.HISTORICAL)
        for name in ("workspace-session", "workspace-logout", "workspace-role-context-switch-normal",
                     "academic-catalogue-current-period", "academic-onboarding-status", "academic-onboarding-finalize"):
            self.assertNotEqual(student_gate.route_class(name), student_gate.SEMESTER_DEPENDENT, name)
        self.assertIsNone(student_gate.route_class("some-future-route"))  # a new route must be classified explicitly

    def test_dashboard_routes_follow_the_state(self):
        self.assertEqual({state: onboarding.dashboard_route(state) for state in (
            "completed", "no_active_semester", "clearance_required", "onboarding", "pending_verification",
            "gap_verification_required", "history_unverified", "evidence_conflict")}, {
            "completed": "dashboard", "no_active_semester": "period_unavailable", "clearance_required": "clearance_required",
            "onboarding": "onboarding", "pending_verification": "onboarding", "gap_verification_required": "verification_required",
            "history_unverified": "verification_required", "evidence_conflict": "verification_required"})


@override_settings(**ONBOARD)
class DashboardBoundaryTests(OnboardingBase):
    def setUp(self):
        cache.clear()

    def blocked(self, client, state, route):
        reply = client.get(ON + "my-semester/")
        self.assertEqual((reply.status_code, reply.json()["error"]["code"], reply.json()["error"]["state"],
                          reply.json()["error"]["route"]), (409, "onboarding_required", state, route), reply.content)

    def test_scenario_a_no_active_semester_keeps_account_and_history_functions(self):
        client = signed_in(self.w.student)
        status = client.get(ON + "status/").json()
        self.assertEqual((status["state"], status["dashboard_route"]), ("no_active_semester", "period_unavailable"))
        self.blocked(client, "no_active_semester", "period_unavailable")
        for path in ("/api/v1/auth/session/", ON + "my-history/"):
            self.assertEqual(client.get(path).status_code, 200, path)
        self.assertEqual(record_counts(), ZERO)

    def test_scenarios_b_d_e_onboarding_pending_and_completion_over_http(self):
        sem = open_semester(self.w, self.cat)["semester_id"]
        client = signed_in(self.w.student)
        status = client.get(ON + "status/").json()
        self.assertEqual((status["state"], status["dashboard_route"]), ("onboarding", "onboarding"))
        self.blocked(client, "onboarding", "onboarding")
        version = regular_steps(self.w.student, self.cat)
        self.assertEqual(finalize(self.w.student, version)["outcome"], "pending_verification")
        status = client.get(ON + "status/").json()
        self.assertEqual((status["state"], status["dashboard_route"], status["onboarding"]["next_step"]),
                         ("pending_verification", "onboarding", 4))  # the Draft is preserved and recoverable
        self.blocked(client, "pending_verification", "onboarding")
        record(self.w, self.w.student, sem, self.cat, ["MATH 101", "IT 101"])
        done = finalize(self.w.student)
        self.assertEqual((done["outcome"], done["dashboard_route"]), ("completed", "dashboard"))
        self.assertEqual(client.get(ON + "my-semester/").status_code, 200)
        self.assertEqual(client.get(ON + "status/").json()["dashboard_route"], "dashboard")

    def test_scenarios_c_and_f_a_newly_activated_semester_needs_its_own_onboarding(self):
        first = open_semester(self.w, self.cat)["semester_id"]
        record(self.w, self.w.student, first, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student, self.cat)
        finalize(self.w.student)
        client = signed_in(self.w.student)
        self.assertEqual(client.get(ON + "my-semester/").status_code, 200)
        open_semester(self.w, self.cat, 2026, 2, fee="1500.00")  # activation closes the completed semester
        status = client.get(ON + "status/").json()
        self.assertEqual((status["state"], status["dashboard_route"]), ("clearance_required", "clearance_required"))
        self.assertEqual(status["previous_clearance"]["clearance"]["status"], "Uncleared")
        self.blocked(client, "clearance_required", "clearance_required")
        history = client.get(ON + "my-history/").json()["results"]
        self.assertEqual([(r["clearance"]["status"], r["fee"]["status"]) for r in history], [("Uncleared", "Unpaid")])
        self.assertEqual(post(client, ON + "type/", {"student_type": "Regular"}).json()["error"]["reason"], "eligibility_blocked")
        self.assertEqual(SemesterParticipation.objects.count(), 1)  # nothing created for the new semester

    def test_other_role_contexts_are_never_gated(self):
        open_semester(self.w, self.cat)
        dual = self.w.account("WF0505-BDUAL", "Student", "Admin")
        with override_settings(**ROLE_CONTEXT):
            client = signed_in(dual)
            session = client.session
            session[SESSION_ROLE_KEY] = self.w.roles["Admin"].pk
            session.save()
            refused = client.get(ON + "status/")
            self.assertEqual((refused.status_code, refused.json()["error"]["reason"]), (403, "student_context_required"))
            self.assertEqual(client.get("/api/v1/academic/school-years/").status_code, 200)  # Admin work is unaffected
            session[SESSION_ROLE_KEY] = self.w.roles["Student"].pk
            session.save()
            self.assertEqual(client.get(ON + "status/").json()["dashboard_route"], "onboarding")
            self.assertEqual(client.get(ON + "my-semester/").status_code, 409)

    def test_default_off_preserves_the_release_behaviour(self):
        open_semester(self.w, self.cat)
        client = signed_in(self.w.student)
        with override_settings(WORKSPACE_STUDENT_ONBOARDING_ENABLED=False):
            for path in (ON + "status/", ON + "my-semester/", ON + "my-history/"):
                self.assertEqual(client.get(path).status_code, 503, path)
            self.assertEqual(client.get("/api/v1/auth/session/").status_code, 200)


@override_settings(**ONBOARD)
class SignatoryAndSecurityTests(OnboardingBase):
    def setUp(self):
        self.prepared = open_semester(self.w, self.cat)
        self.sem = self.prepared["semester_id"]

    def test_a_student_who_is_the_assigned_instructor_is_refused_everywhere(self):
        teacher_student = self.w.account("WF0505-TSTU", "Student", "Instructor")
        offering = self.prepared["offerings"][("1-B", "MATH 101")]
        current = teaching.current_assignment(SubjectOffering.objects.get(pk=offering))
        teaching.assign_instructor(actor=self.w.admin, offering_id=offering, instructor_account_id=teacher_student.pk,
                                   expected_assignment_id=current.pk)
        state = onboarding.save_student_type(actor=teacher_student, student_type="Regular")
        options = onboarding.subject_options(actor=teacher_student, course_id=self.cat["courses"]["BSIT"], year_level=1,
                                             section_id=self.cat["sections"]["1-B"])
        exc = self.conflict("instructor_conflict", onboarding.confirm_subjects, actor=teacher_student,
                            course_id=self.cat["courses"]["BSIT"], year_level=1,
                            offering_ids=[o["offering_id"] for o in options["options"]],
                            expected_version=state["onboarding"]["version"])
        self.assertEqual(exc.details, ("MATH 101",))
        # Defence in depth: the clearance service refuses a self-signatory even if called directly.
        participation = SemesterParticipation(pk=1, student_id=teacher_student.pk, semester_id=self.sem)
        row = ParticipationSubject(participation_id=1, subject_id=self.cat["subjects"]["MATH 101"], offering_id=offering,
                                   instructor_id=teacher_student.pk)
        from django.db import transaction
        with self.assertRaises(ClearanceCreationRefused) as caught, transaction.atomic():
            create_semester_clearance(participation, [row])
        self.assertEqual(caught.exception.reason, "signatory_conflict")
        self.assertEqual(ClearanceRequirement.objects.count(), 0)

    def test_authorization_is_revalidated_inside_the_finalization(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        version = regular_steps(self.w.student, self.cat)
        revision = onboarding.review(actor=self.w.student)["fee"]["revision_id"]
        precheck = onboarding.authorize_student

        def deny_after_precheck(*args, **kwargs):
            result = precheck(*args, **kwargs)
            self.w.deny(self.w.student, onboarding.WRITE_CODE)  # arrives between the pre-check and the locks
            return result
        with patch.object(onboarding, "authorize_student", side_effect=deny_after_precheck), \
                self.assertRaises(services.AcademicPeriodDenied):
            onboarding.finalize(actor=self.w.student, expected_version=version, expected_fee_revision_id=revision,
                                confirmed=True)
        self.assertEqual(record_counts(), ZERO)
        self.assertEqual(SemesterOnboarding.objects.get().status, "Draft")

    def test_cross_account_and_ineligible_access_is_refused(self):
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        other = signed_in(self.w.student2)
        self.assertEqual(other.get(f"/api/v1/academic/verification/students/{self.w.student.pk}/").status_code, 403)
        self.assertEqual(post(other, ON + "finalize/", {"expected_version": 1, "expected_fee_revision_id": 1, "confirmed": True,
                                                        "student_account_id": self.w.student.pk}).status_code, 400)
        inactive = self.w.account("WF0505-INACT", "Student", active=False)
        with self.assertRaises(services.AcademicPeriodDenied):
            onboarding.status(actor=inactive)

    def test_legacy_broad_codes_no_longer_authorize_the_narrow_operations(self):
        """Catalogue v2.3: only the exact narrow codes authorize; the old broad codes never substitute."""
        for code, role in (("clearance.requests.self.submit", "Student"), ("academic.profiles.manage", "Admin"),
                           ("academic.periods.manage", "Admin")):
            perm = Permission.objects.get_or_create(permission_code=code, defaults=dict(
                service=self.w.service, permission_name=code, module_name="m", action_name="a"))[0]
            RolePermission.objects.get_or_create(role=self.w.roles[role], permission=perm)
        self.assertEqual((onboarding.WRITE_CODE, verification.VERIFY_CODE, hp.CORRECTION_CODE), tuple(PROPOSED.values()))
        RolePermission.objects.filter(permission__permission_code__in=list(PROPOSED.values())).delete()
        with self.assertRaises(services.AcademicPeriodDenied):
            onboarding.save_student_type(actor=self.w.student, student_type="Regular")
        with self.assertRaises(services.AcademicPeriodDenied):
            record(self.w, self.w.student, self.sem, self.cat, ["MATH 101"])
        with self.assertRaises(services.AcademicPeriodDenied):
            hp.preview(actor=self.w.admin, student_account_id=self.w.student.pk, semester_id=self.sem)
        from pathlib import Path
        catalogue = Path(__file__).resolve().parents[1] / "access_control" / "catalogue"
        pinned = "".join((catalogue / name).read_text(encoding="utf-8")
                         for name in ("v2_0.json", "v2_1_delta.json", "v2_2_delta.json"))
        for code in PROPOSED.values():
            self.assertNotIn(code, pinned)  # the pinned v2.0-v2.2 files were never edited


@override_settings(**ONBOARD)
class FeeRevisionSafeguardTests(OnboardingBase):
    def setUp(self):
        self.sem = open_semester(self.w, self.cat)["semester_id"]

    def revise(self, amount):
        current = SemesterFeeRevision.objects.filter(schedule__semester_id=self.sem, status="Draft").first()
        fees.save_draft(actor=self.w.admin, semester_id=self.sem, amount=amount,
                        expected_draft_version=current.version if current else None,
                        change_reason="Student council resolution revised the semester fee.")
        return approve_fee(self.w, self.sem)

    def test_revision_before_any_obligation_then_refused_without_touching_snapshots(self):
        self.assertEqual(self.revise("1600.00")["current_approved"]["amount"], "1600.00")  # no obligation yet: allowed
        record(self.w, self.w.student, self.sem, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student, self.cat)
        finalize(self.w.student)
        snapshot = list(FeeObligation.objects.values().order_by("pk"))
        self.assertEqual(snapshot[0]["amount"], Decimal("1600.00"))
        with self.assertRaises(fees.FeeConflict) as caught:
            self.revise("1700.00")
        self.assertEqual(caught.exception.reason, "obligations_assessed")
        self.assertEqual(list(FeeObligation.objects.values().order_by("pk")), snapshot)  # never rewritten or deleted
        self.assertEqual(SemesterFeeRevision.objects.get(status="Approved").amount, Decimal("1600.00"))
        self.assertEqual(SemesterFeeRevision.objects.filter(status="Draft").count(), 1)  # the Draft is kept, not applied
        # A later Student is snapshotted at the SAME approved rate: no silent split between Students.
        record(self.w, self.w.student2, self.sem, self.cat, ["MATH 101", "IT 101"])
        regular_steps(self.w.student2, self.cat)
        finalize(self.w.student2)
        self.assertEqual(set(FeeObligation.objects.values_list("amount", flat=True)), {Decimal("1600.00")})
