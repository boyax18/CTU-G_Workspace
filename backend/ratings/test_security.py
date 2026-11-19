# ratings/test_security.py
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from classes.models import Class, Enrollment
from groups.services import create_group
from ratings.models import RatingCriterion, RatingPeriod, RatingResult, RatingScore, RatingSubmission

PW = "StrongPass!123"


class SecurityBase(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.other_prof = User.objects.create_user("prof2", password=PW, role=User.Role.INSTRUCTOR)
        self.admin = User.objects.create_user("admin", password=PW, role=User.Role.ADMIN)
        self.s0 = User.objects.create_user("s0", password=PW, role=User.Role.STUDENT)
        self.s1 = User.objects.create_user("s1", password=PW, role=User.Role.STUDENT)
        self.s2 = User.objects.create_user("s2", password=PW, role=User.Role.STUDENT)
        self.s3 = User.objects.create_user("s3", password=PW, role=User.Role.STUDENT)
        self.outsider = User.objects.create_user("out", password=PW, role=User.Role.STUDENT)

        self.cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create([
            Enrollment(classroom=self.cls, student=s) for s in [self.s0, self.s1, self.s2, self.s3]
        ])
        self.period = RatingPeriod.objects.create(
            classroom=self.cls, title="Project 1", deadline=timezone.now() + timedelta(days=7)
        )
        self.c1 = RatingCriterion.objects.create(period=self.period, name="Contribution", weight=1)
        self.c2 = RatingCriterion.objects.create(period=self.period, name="Reliability", weight=3)
        create_group(self.period, "G1", [self.s0.id, self.s1.id, self.s2.id], self.s0.id)

        # A second class and session that the first instructor does not own.
        self.other_cls = Class.objects.create(code="CS999", name="Other", instructor=self.other_prof)
        self.other_period = RatingPeriod.objects.create(
            classroom=self.other_cls, title="Other project",
            deadline=timezone.now() + timedelta(days=7),
        )

        self.client.force_authenticate(self.instructor)
        self.client.post(self.url("open/"))

    def url(self, suffix):
        return f"/api/ratings/periods/{self.period.id}/{suffix}"

    def submit(self, rater, targets):
        scores = []
        for target, (v1, v2) in targets.items():
            scores.append({"target_id": target.id, "criterion_id": self.c1.id, "value": v1})
            scores.append({"target_id": target.id, "criterion_id": self.c2.id, "value": v2})
        self.client.force_authenticate(rater)
        return self.client.post(self.url("submit/"), {"scores": scores}, format="json")

    def submit_all_and_release(self):
        self.submit(self.s0, {self.s1: (4, 4), self.s2: (4, 4)})
        self.submit(self.s1, {self.s0: (5, 3), self.s2: (4, 4)})
        self.submit(self.s2, {self.s0: (3, 3), self.s1: (4, 4)})
        self.client.force_authenticate(self.instructor)
        self.client.post(self.url("close/"))
        self.client.post(self.url("release/"))


class TamperedIdTests(SecurityBase):
    def test_student_cannot_read_another_students_result(self):
        self.submit_all_and_release()

        # s1 gets their own score (4.00), never s0's (3.25).
        self.client.force_authenticate(self.s1)
        r = self.client.get(self.url("my-result/"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.json()["final_score"]), Decimal("4.00"))
        self.assertNotIn("3.25", r.content.decode())

    def test_student_cannot_open_another_class_session_form(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get(f"/api/ratings/periods/{self.other_period.id}/form/")
        self.assertEqual(r.status_code, 404)

    def test_student_cannot_submit_to_another_class_session(self):
        self.client.force_authenticate(self.s0)
        r = self.client.post(
            f"/api/ratings/periods/{self.other_period.id}/submit/",
            {"scores": []}, format="json",
        )
        self.assertEqual(r.status_code, 404)

    def test_instructor_cannot_close_another_instructors_session(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.post(f"/api/ratings/periods/{self.other_period.id}/close/")
        self.assertEqual(r.status_code, 404)

    def test_instructor_cannot_export_another_instructors_results(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.get(f"/api/ratings/periods/{self.other_period.id}/export/")
        self.assertEqual(r.status_code, 404)

    def test_leader_cannot_submit_scores_for_non_teammate(self):
        r = self.submit(self.s0, {self.s3: (5, 5), self.s1: (4, 4)})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(RatingScore.objects.filter(target=self.s3).exists())


class MassAssignmentTests(SecurityBase):
    def test_student_cannot_escalate_role_through_profile_fields(self):
        self.client.force_authenticate(self.s0)
        self.client.patch("/api/auth/me/", {"role": "admin"}, format="json")
        self.s0.refresh_from_db()
        self.assertEqual(self.s0.role, User.Role.STUDENT)

    def test_class_creation_ignores_client_supplied_instructor(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.post(
            "/api/classes/",
            {"code": "X1", "name": "Injected", "instructor": self.other_prof.id},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Class.objects.get(pk=r.json()["id"]).instructor, self.instructor)

    def test_submission_ignores_client_supplied_rater(self):
        scores = [
            {"target_id": self.s1.id, "criterion_id": self.c1.id, "value": 4},
            {"target_id": self.s1.id, "criterion_id": self.c2.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c1.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c2.id, "value": 4},
        ]
        self.client.force_authenticate(self.s0)
        r = self.client.post(self.url("submit/"), {"scores": scores, "rater": self.s2.id},
                             format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(RatingSubmission.objects.filter(period=self.period, rater=self.s0).exists())
        self.assertFalse(RatingSubmission.objects.filter(period=self.period, rater=self.s2).exists())

    def test_student_cannot_set_final_score_directly(self):
        self.submit_all_and_release()
        self.client.force_authenticate(self.s0)
        self.client.patch(self.url("my-result/"), {"final_score": "5.00"}, format="json")
        stored = RatingResult.objects.get(period=self.period, student=self.s0)
        self.assertNotEqual(stored.final_score, Decimal("5.00"))


class TokenAbuseTests(SecurityBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(None)  # clear the forced login from SecurityBase

    def test_forged_token_is_rejected(self):
        token = str(AccessToken.for_user(self.s0)) + "tampered"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_token_for_deleted_user_is_rejected(self):
        token = str(AccessToken.for_user(self.outsider))
        self.outsider.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_protected_routes_reject_anonymous(self):
        for path in [
            self.url("form/"),
            self.url("my-result/"),
            self.url("group-status/"),
            "/api/dashboard/student/",
            "/api/notifications/",
        ]:
            self.assertEqual(self.client.get(path).status_code, 401, path)


class SubmissionEdgeTests(SecurityBase):
    def test_duplicate_scores_in_one_request_are_rejected(self):
        scores = [
            {"target_id": self.s1.id, "criterion_id": self.c1.id, "value": 4},
            {"target_id": self.s1.id, "criterion_id": self.c1.id, "value": 5},
            {"target_id": self.s1.id, "criterion_id": self.c2.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c1.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c2.id, "value": 4},
        ]
        self.client.force_authenticate(self.s0)
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(RatingScore.objects.count(), 0)

    def test_submission_rejected_when_deadline_passed_even_if_open(self):
        self.period.deadline = timezone.now() - timedelta(seconds=1)
        self.period.save(update_fields=["deadline"])
        r = self.submit(self.s0, {self.s1: (4, 4), self.s2: (4, 4)})
        self.assertEqual(r.status_code, 400)

    def test_non_integer_score_is_rejected(self):
        scores = [
            {"target_id": self.s1.id, "criterion_id": self.c1.id, "value": "high"},
            {"target_id": self.s1.id, "criterion_id": self.c2.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c1.id, "value": 4},
            {"target_id": self.s2.id, "criterion_id": self.c2.id, "value": 4},
        ]
        self.client.force_authenticate(self.s0)
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_concurrent_resubmission_stores_one_submission(self):
        # Sequential stand-in for a race: the locked row must prevent a second submission.
        first = self.submit(self.s0, {self.s1: (4, 4), self.s2: (4, 4)})
        second = self.submit(self.s0, {self.s1: (4, 4), self.s2: (4, 4)})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(RatingScore.objects.filter(submission__rater=self.s0).count(), 4)