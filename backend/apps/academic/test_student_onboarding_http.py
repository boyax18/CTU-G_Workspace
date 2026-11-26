"""WF-05.05 / WF-05.04 / WF11-D14 HTTP contract and the full isolated end-to-end flow through config.urls.

Run: python manage.py test apps.academic.test_student_onboarding_http --settings=config.test_settings --noinput
Disposable MySQL only. Every request goes through the real routes, session, CSRF and HDAC.
"""

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.active_role_context import SESSION_ROLE_KEY
from apps.clearance.models import ClearanceRequirement, SemesterClearance
from apps.finance.models import FeeObligation

from .models import SemesterOnboarding, SemesterParticipation
from .test_student_onboarding import (
    ONBOARD, OnboardingBase, OnboardingWorld, build_catalogue, open_semester, prepare_semester, record, record_counts,
    ZERO,
)
from .test_wf1101_http import ROLE_CONTEXT, TOKEN, post, signed_in

ON = "/api/v1/academic/onboarding/"
VER = "/api/v1/academic/verification/"
ROOT = "/api/v1/academic/"


def steps_over_http(test, client, cat, section="1-A"):
    reply = post(client, ON + "type/", {"student_type": "Regular"})
    test.assertEqual(reply.status_code, 200, reply.content)
    bsit = cat["courses"]["BSIT"]
    options = client.get(ON + "subject-options/", {"course_id": bsit, "year_level": 1,
                                                    "section_id": cat["sections"][section]})
    test.assertEqual(options.status_code, 200, options.content)
    ids = [o["offering_id"] for o in options.json()["options"]]
    reply = post(client, ON + "subjects/", {"course_id": bsit, "year_level": 1, "offering_ids": ids,
                                            "expected_version": reply.json()["onboarding"]["version"]})
    test.assertEqual(reply.status_code, 200, reply.content)
    reply = post(client, ON + "course/", {"course_id": bsit, "year_level": 1,
                                          "expected_version": reply.json()["onboarding"]["version"]})
    test.assertEqual((reply.status_code, reply.json()["onboarding"]["next_step"]), (200, 4), reply.content)
    review = client.get(ON + "review/")
    test.assertEqual(review.status_code, 200, review.content)
    return review.json()


def confirm(client, review):
    return post(client, ON + "finalize/", {"expected_version": review["onboarding"]["version"],
                                           "expected_fee_revision_id": review["fee"]["revision_id"], "confirmed": True})


@override_settings(**ONBOARD)
class OnboardingHTTPTests(OnboardingBase):
    def setUp(self):
        cache.clear()
        self.sem = open_semester(self.w, self.cat)["semester_id"]
        self.student = signed_in(self.w.student)

    def test_gates_session_csrf_and_strict_bodies(self):
        with override_settings(WORKSPACE_STUDENT_ONBOARDING_ENABLED=False):
            reply = self.student.get(ON + "status/")
            self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "student_onboarding_unavailable"))
        with override_settings(WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED=False):
            self.assertEqual(signed_in(self.w.admin).get(VER + "students/").status_code, 503)
        with override_settings(WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED=False):
            self.assertEqual(signed_in(self.w.admin).get(VER + "historical-participation/").status_code, 503)
        anonymous = signed_in(self.w.student)
        anonymous.logout()
        self.assertEqual(anonymous.get(ON + "status/").status_code, 401)
        reply = self.student.get(ON + "status/")
        self.assertEqual((reply.status_code, reply.json()["state"]), (200, "onboarding"))
        self.assertIn("no-store", reply["Cache-Control"])
        missing_csrf = post(self.student, ON + "type/", {"student_type": "Regular"}, csrf=False)
        self.assertEqual((missing_csrf.status_code, missing_csrf.json()["error"]["code"]), (403, "csrf_failed"))
        for body in ({"student_type": "Regular", "student_account_id": self.w.student2.pk}, {}, ["Regular"]):
            with self.subTest(body=body):
                self.assertEqual(post(self.student, ON + "type/", body).status_code, 400)
        bad = post(self.student, ON + "type/", {"student_type": "regular"})
        self.assertEqual(bad.json()["error"]["fields"], {"student_type": ["Choose Regular or Irregular."]})
        self.assertEqual(self.student.get(ON + "subject-options/", {"course_id": "x"}).status_code, 400)
        self.assertEqual(self.student.delete(ON + "status/", HTTP_X_CSRFTOKEN=TOKEN).status_code, 405)
        self.assertEqual(SemesterOnboarding.objects.count(), 0)

    def test_backend_dashboard_gate_and_error_mapping(self):
        reply = self.student.get(ON + "my-semester/")
        self.assertEqual((reply.status_code, reply.json()["error"]["code"], reply.json()["error"]["state"]),
                         (409, "onboarding_required", "onboarding"))
        self.assertEqual(self.student.get(ON + "my-history/").json(), {"results": []})
        reply = self.student.get(ON + "review/")
        self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (409, "type_required"))
        reply = signed_in(self.w.instructor).get(ON + "status/")
        self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (403, "access_denied"))

    def test_pending_then_verified_then_completed_over_http(self):
        review = steps_over_http(self, self.student, self.cat)
        self.assertEqual(review["verification"], "not_recorded")
        reply = confirm(self.student, review)
        self.assertEqual((reply.status_code, reply.json()["outcome"], reply.json()["state"]),
                         (200, "pending_verification", "pending_verification"))
        self.assertEqual(record_counts(), ZERO)
        admin = signed_in(self.w.admin)
        found = admin.get(VER + "students/", {"q": "WF0505-STU1"}).json()["results"]
        self.assertEqual([r["account_id"] for r in found], [self.w.student.pk])
        body = {"student_account_id": self.w.student.pk, "semester_id": self.sem, "entry_classification": "continuing",
                "course_id": self.cat["courses"]["BSIT"], "year_level": 1,
                "subject_ids": [self.cat["subjects"]["MATH 101"], self.cat["subjects"]["IT 101"]],
                "source_reference": "CTU-REG 2026-0042", "expected_evidence_id": None}
        reply = post(admin, VER + "evidence/", body)
        self.assertEqual((reply.status_code, reply.json()["status"]), (200, "Verified"), reply.content)
        self.assertNotIn("CTU-REG 2026-0042", reply.content.decode())
        review = self.student.get(ON + "review/").json()
        self.assertEqual(review["verification"], "verified")
        reply = confirm(self.student, review)
        self.assertEqual((reply.status_code, reply.json()["outcome"]), (200, "completed"), reply.content)
        mine = self.student.get(ON + "my-semester/")
        self.assertEqual((mine.status_code, mine.json()["result"]["fee"]["amount"]), (200, "1500.00"))
        record_view = admin.get(f"{VER}students/{self.w.student.pk}/").json()
        self.assertEqual(record_view["periods"][0]["clearance_status"], "Uncleared")
        self.assertEqual(set(record_view["periods"][0]["fee"]), {"obligation_id", "amount", "currency", "status"})
        evidence_id = record_view["periods"][0]["evidence"]["evidence_id"]
        revoke = post(admin, f"{VER}evidence/{evidence_id}/revoke/", {"expected_version": 1, "reason_code": "recorded_in_error"})
        self.assertEqual((revoke.status_code, revoke.json()["error"]["reason"]), (409, "evidence_in_use"))

    def test_conflicts_map_to_messages(self):
        steps = post(self.student, ON + "type/", {"student_type": "Regular"})
        reply = post(self.student, ON + "subjects/", {"course_id": self.cat["courses"]["BSIT"], "year_level": 1,
                                                       "offering_ids": [999_999],
                                                       "expected_version": steps.json()["onboarding"]["version"]})
        self.assertEqual((reply.status_code, reply.json()["error"]["code"], reply.json()["error"]["reason"]),
                         (409, "onboarding_conflict", "subject_unavailable"))
        reply = post(self.student, ON + "finalize/", {"expected_version": 1, "expected_fee_revision_id": 1,
                                                       "confirmed": False})
        self.assertEqual(reply.json()["error"]["reason"], "confirmation_required")
        with override_settings(WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED=False):
            reply = post(self.student, ON + "finalize/", {"expected_version": 1, "expected_fee_revision_id": 1,
                                                           "confirmed": True})
            self.assertEqual((reply.status_code, reply.json()["error"]["code"]), (503, "feature_disabled"))


@override_settings(**ONBOARD)
class OnboardingRoleContextHTTPTests(OnboardingBase):
    def setUp(self):
        cache.clear()
        open_semester(self.w, self.cat)
        self.dual = self.w.account("WF0505-HDUAL", "Student", "Treasurer")

    def client_for(self, role_name):
        client = signed_in(self.dual)
        session = client.session
        session[SESSION_ROLE_KEY] = self.w.roles[role_name].pk
        session.save()
        return client

    @override_settings(**ROLE_CONTEXT)
    def test_treasurer_context_of_the_same_account_cannot_reach_student_onboarding(self):
        treasurer = self.client_for("Treasurer")
        for reply in (treasurer.get(ON + "status/"), post(treasurer, ON + "type/", {"student_type": "Regular"})):
            self.assertEqual((reply.status_code, reply.json()["error"]["reason"]), (403, "student_context_required"))
        student = self.client_for("Student")
        self.assertEqual(student.get(ON + "status/").json()["state"], "onboarding")
        self.assertEqual(post(student, ON + "type/", {"student_type": "Regular"}).status_code, 200)
        self.assertEqual(SemesterOnboarding.objects.get().student_id, self.dual.pk)


@override_settings(**ONBOARD)
class EndToEndOnboardingTests(TestCase):
    """The complete isolated flow (18 steps), School Admin and Student over HTTP, real services only."""

    def test_full_semester_onboarding_flow(self):
        cache.clear()
        w = OnboardingWorld()
        admin, student = signed_in(w.admin), signed_in(w.student)
        # 1-5. School Admin: school year, course/subjects/curriculum/sections, dates, offerings, instructors.
        cat = build_catalogue(w)
        prepared = prepare_semester(w, cat, 2026, 1, fee="1500.00", approve=False)
        sem = prepared["semester_id"]
        # 6. Before the fee is approved the semester cannot be activated (real prerequisite).
        preview = admin.get(f"{ROOT}semesters/{sem}/activation/").json()
        self.assertIn("prerequisites_missing", preview["blockers"])
        # 7. Approve the semester fee over HTTP.
        fee = admin.get(f"/api/v1/finance/semester-fees/{sem}/approval/").json()
        reply = post(admin, f"/api/v1/finance/semester-fees/{sem}/approval/",
                     {"revision_id": fee["proposed"]["revision_id"], "expected_version": fee["proposed"]["version"],
                      "expected_current_approved_revision_id": None, "acknowledged_warnings": fee["warnings"],
                      "confirmed": True, "confirm_zero_amount": False})
        self.assertEqual(reply.status_code, 200, reply.content)
        # 8. Before activation: no Active semester for the Student.
        self.assertEqual(student.get(ON + "status/").json()["state"], "no_active_semester")
        # 9. Explicit activation with the real prerequisites. No participation, clearance or fee is created.
        preview = admin.get(f"{ROOT}semesters/{sem}/activation/").json()
        self.assertEqual(preview["blockers"], [])
        reply = post(admin, f"{ROOT}semesters/{sem}/activation/",
                     {"confirmed": True, "expected_version": preview["semester"]["version"],
                      "expected_active_semester_id": None, "acknowledged_warnings": preview["warnings"]})
        self.assertEqual((reply.status_code, reply.json()["status"]), (200, "Active"), reply.content)
        self.assertEqual(record_counts(), ZERO)
        # 10. Student login: onboarding is required and the dashboard data is gated on the backend.
        status = student.get(ON + "status/").json()
        self.assertEqual((status["state"], status["dashboard_unlocked"], status["student"]["ctug_id"]),
                         ("onboarding", False, "WF0505-STU1"))
        self.assertEqual(student.get(ON + "my-semester/").status_code, 409)
        # 11-14. Steps 1-4 (type, subjects, course/year, review with the approved fee).
        review = steps_over_http(self, student, cat)
        self.assertEqual((review["fee"]["amount"], review["can_confirm"]), ("1500.00", True))
        self.assertEqual(record_counts(), ZERO)
        # 15. Confirmation without official evidence: Pending Verification only.
        self.assertEqual(confirm(student, review).json()["outcome"], "pending_verification")
        self.assertEqual(record_counts(), ZERO)
        # 16. School Admin records the in-person CTU verification.
        record(w, w.student, sem, cat, ["MATH 101", "IT 101"])
        # 17. Student confirms again: one atomic set of records; the dashboard unlocks.
        review = student.get(ON + "review/").json()
        done = confirm(student, review).json()
        self.assertEqual(done["outcome"], "completed")
        self.assertEqual(record_counts(), {"participations": 1, "subjects": 2, "clearances": 1, "requirements": 4,
                                           "obligations": 1})
        mine = student.get(ON + "my-semester/").json()["result"]
        self.assertEqual((mine["clearance"]["status"], mine["fee"]["status"], len(mine["subjects"])),
                         ("Uncleared", "Unpaid", 2))
        self.assertEqual(confirm(student, review).json()["result"]["participation_id"], done["result"]["participation_id"])
        self.assertEqual(SemesterParticipation.objects.count(), 1)
        # 18. Closure shows the real outstanding records; the next semester requires the old clearance.
        closure = admin.get(f"{ROOT}semesters/{sem}/closure/").json()
        self.assertEqual({o["key"]: o["count"] for o in closure["obligations"]},
                         {"outstanding_clearance_signatures": 4, "unpaid_fee_obligations": 1, "incomplete_onboarding": 0})
        reply = post(admin, f"{ROOT}semesters/{sem}/closure/", {"confirmed": True, "expected_version":
                                                                 closure["semester"]["version"],
                                                                 "acknowledged_warnings": closure["warnings"]})
        self.assertEqual(reply.status_code, 200, reply.content)
        self.assertEqual((SemesterClearance.objects.get().status, FeeObligation.objects.get().status,
                          ClearanceRequirement.objects.filter(status="Pending").count()), ("Uncleared", "Unpaid", 4))
        open_semester(w, cat, 2026, 2, fee="1500.00")
        status = student.get(ON + "status/").json()
        self.assertEqual((status["state"], status["previous_clearance"]["clearance"]["status"]),
                         ("clearance_required", "Uncleared"))
        self.assertEqual(len(student.get(ON + "my-history/").json()["results"]), 1)
        self.assertTrue(TOKEN)
