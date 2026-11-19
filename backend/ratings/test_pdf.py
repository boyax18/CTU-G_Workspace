# ratings/test_pdf.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.services import create_group
from ratings.models import RatingCriterion, RatingPeriod

PW = "StrongPass!123"


class ResultPdfTests(APITestCase):
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
        self.c1 = RatingCriterion.objects.create(period=self.period, name="Contribution", weight=1)
        self.c2 = RatingCriterion.objects.create(period=self.period, name="Reliability", weight=3)
        create_group(self.period, "G1", [self.s0.id, self.s1.id, self.s2.id], self.s0.id)

        self.client.force_authenticate(self.instructor)
        self.client.post(f"/api/ratings/periods/{self.period.id}/open/")

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

    # Student PDF

    def test_student_pdf_hidden_until_released(self):
        self.client.force_authenticate(self.s0)
        self.assertEqual(self.client.get(self.url("my-result/pdf/")).status_code, 404)

    def test_student_pdf_is_a_pdf(self):
        self.close_and_release()
        self.client.force_authenticate(self.s1)
        r = self.client.get(self.url("my-result/pdf/"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_student_pdf_shows_own_score_only(self):
        self.close_and_release()
        # s1's final score is 4.00; s0's is 3.25.
        self.client.force_authenticate(self.s1)
        content = self.client.get(self.url("my-result/pdf/")).content
        self.assertIn(b"4.00", content)
        self.assertNotIn(b"3.25", content)
        self.assertNotIn(b"s0", content)

    def test_student_pdf_has_no_rater_details(self):
        self.close_and_release()
        self.client.force_authenticate(self.s0)
        content = self.client.get(self.url("my-result/pdf/")).content
        self.assertNotIn(b"s1", content)
        self.assertNotIn(b"s2", content)

    def test_my_result_json_has_exactly_expected_keys(self):
        self.close_and_release()
        self.client.force_authenticate(self.s1)
        r = self.client.get(self.url("my-result/"))
        self.assertEqual(set(r.json().keys()), {"period_title", "final_score", "released_at"})

    # Instructor summary PDF

    def test_summary_blocked_while_open(self):
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.client.get(self.url("summary.pdf")).status_code, 400)

    def test_summary_pdf_for_instructor(self):
        self.close_and_release()
        self.client.force_authenticate(self.instructor)
        r = self.client.get(self.url("summary.pdf"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn(b"Project 1", r.content)

    def test_student_cannot_get_summary_pdf(self):
        self.close_and_release()
        self.client.force_authenticate(self.s0)
        self.assertEqual(self.client.get(self.url("summary.pdf")).status_code, 403)