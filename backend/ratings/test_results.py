# ratings/test_results.py
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.services import create_group
from notifications.models import Notification
from ratings.models import RatingCriterion, RatingPeriod

PW = "StrongPass!123"


class ResultTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.s0 = User.objects.create_user("s0", password=PW, role=User.Role.STUDENT)
        self.s1 = User.objects.create_user("s1", password=PW, role=User.Role.STUDENT)
        self.s2 = User.objects.create_user("s2", password=PW, role=User.Role.STUDENT)

        cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create([
            Enrollment(classroom=cls, student=s) for s in [self.s0, self.s1, self.s2]
        ])
        self.period = RatingPeriod.objects.create(
            classroom=cls, title="Project 1", deadline=timezone.now() + timedelta(days=7)
        )
        # Weights 1 and 3 make the expected score non-trivial.
        self.c1 = RatingCriterion.objects.create(period=self.period, name="Contribution", weight=1)
        self.c2 = RatingCriterion.objects.create(period=self.period, name="Reliability", weight=3)
        create_group(self.period, "G1", [self.s0.id, self.s1.id, self.s2.id], self.s0.id)

        self.client.force_authenticate(self.instructor)
        self.client.post(f"/api/ratings/periods/{self.period.id}/open/")

        # s0 gives everyone 4s; s1 and s2 give s0 different values.
        self.submit(self.s0, {self.s1: (4, 4), self.s2: (4, 4)})
        self.submit(self.s1, {self.s0: (5, 3), self.s2: (4, 4)})
        self.submit(self.s2, {self.s0: (3, 3), self.s1: (4, 4)})

    def url(self, suffix):
        return f"/api/ratings/periods/{self.period.id}/{suffix}"

    def submit(self, rater, targets):
        scores = []
        for target, (v1, v2) in targets.items():
            scores.append({"target_id": target.id, "criterion_id": self.c1.id, "value": v1})
            scores.append({"target_id": target.id, "criterion_id": self.c2.id, "value": v2})
        self.client.force_authenticate(rater)
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def close_and_release(self):
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.client.post(self.url("close/")).status_code, 200)
        self.assertEqual(self.client.post(self.url("release/")).status_code, 200)

    # Release workflow

    def test_results_blocked_while_open(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.get(self.url("results/"))
        self.assertEqual(r.status_code, 400)

    def test_release_requires_closed_session(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.post(self.url("release/"))
        self.assertEqual(r.status_code, 400)

    def test_release_cannot_happen_twice(self):
        self.close_and_release()
        r = self.client.post(self.url("release/"))
        self.assertEqual(r.status_code, 400)

    def test_release_computes_weighted_average(self):
        self.close_and_release()
        # s0 criterion averages: c1 = (5+3)/2 = 4, c2 = (3+3)/2 = 3.
        # weighted: (4*1 + 3*3) / (1+3) = 3.25
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("my-result/"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.json()["final_score"]), Decimal("3.25"))

    def test_release_notifies_students(self):
        self.close_and_release()
        self.assertTrue(
            Notification.objects.filter(recipient=self.s0, message__contains="available").exists()
        )

    # Privacy

    def test_result_hidden_until_released(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("my-result/"))
        self.assertEqual(r.status_code, 404)

    def test_student_sees_only_own_result(self):
        self.close_and_release()
        self.client.force_authenticate(self.s1)
        r = self.client.get(self.url("my-result/"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.json()["final_score"]), Decimal("4.00"))
        # s1's response must not contain s0's score or any rater details.
        self.assertNotIn("3.25", r.content.decode())
        self.assertNotIn("rater_count", r.json())

    def test_student_cannot_list_all_results(self):
        self.close_and_release()
        self.client.force_authenticate(self.s0)
        self.assertEqual(self.client.get(self.url("results/")).status_code, 403)
        self.assertEqual(self.client.get(self.url("export/")).status_code, 403)

    def test_instructor_sees_all_results_after_release(self):
        self.close_and_release()
        self.client.force_authenticate(self.instructor)
        r = self.client.get(self.url("results/"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 3)

    def test_export_returns_xlsx(self):
        self.close_and_release()
        self.client.force_authenticate(self.instructor)
        r = self.client.get(self.url("export/"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        # XLSX files are zip archives, which start with the bytes "PK".
        self.assertTrue(r.content.startswith(b"PK"))