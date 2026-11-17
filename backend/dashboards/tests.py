# dashboards/tests.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.services import create_group
from ratings.models import RatingCriterion, RatingPeriod

PW = "StrongPass!123"


class DashboardTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.other_prof = User.objects.create_user("prof2", password=PW, role=User.Role.INSTRUCTOR)
        self.admin = User.objects.create_user("admin", password=PW, role=User.Role.ADMIN)
        self.s0 = User.objects.create_user("s0", password=PW, role=User.Role.STUDENT)
        self.s1 = User.objects.create_user("s1", password=PW, role=User.Role.STUDENT)
        self.s2 = User.objects.create_user("s2", password=PW, role=User.Role.STUDENT)
        self.outsider = User.objects.create_user("out", password=PW, role=User.Role.STUDENT)

        self.cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create([
            Enrollment(classroom=self.cls, student=s) for s in [self.s0, self.s1, self.s2]
        ])
        self.period = RatingPeriod.objects.create(
            classroom=self.cls, title="Project 1", deadline=timezone.now() + timedelta(days=7)
        )
        self.c1 = RatingCriterion.objects.create(period=self.period, name="Contribution")
        create_group(self.period, "G1", [self.s0.id, self.s1.id, self.s2.id], self.s0.id)

        self.client.force_authenticate(self.instructor)
        self.client.post(f"/api/ratings/periods/{self.period.id}/open/")

        self.client.force_authenticate(self.s1)
        self.client.post(
            f"/api/ratings/periods/{self.period.id}/submit/",
            {"scores": [
                {"target_id": self.s0.id, "criterion_id": self.c1.id, "value": 4},
                {"target_id": self.s2.id, "criterion_id": self.c1.id, "value": 2},
            ]},
            format="json",
        )

    def test_student_dashboard_shows_own_submission_state(self):
        self.client.force_authenticate(self.s1)
        r = self.client.get("/api/dashboard/student/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)
        self.assertTrue(r.json()[0]["submitted"])
        self.assertFalse(r.json()[0]["is_leader"])

    def test_student_dashboard_has_no_scores(self):
        self.client.force_authenticate(self.s1)
        r = self.client.get("/api/dashboard/student/")
        self.assertNotIn('"value"', r.content.decode())

    def test_student_dashboard_marks_leader(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get("/api/dashboard/student/")
        self.assertTrue(r.json()[0]["is_leader"])
        self.assertFalse(r.json()[0]["submitted"])

    def test_unenrolled_student_sees_no_sessions(self):
        self.client.force_authenticate(self.outsider)
        r = self.client.get("/api/dashboard/student/")
        self.assertEqual(r.json(), [])

    def test_instructor_sees_submission_progress(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.get("/api/dashboard/instructor/")
        self.assertEqual(r.status_code, 200)
        session = r.json()[0]
        self.assertEqual(session["total_raters"], 3)
        self.assertEqual(session["submitted_count"], 1)
        by_id = {m["id"]: m for m in session["members"]}
        self.assertTrue(by_id[self.s1.id]["submitted"])
        self.assertFalse(by_id[self.s0.id]["submitted"])

    def test_instructor_dashboard_has_no_rating_values(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.get("/api/dashboard/instructor/")
        self.assertNotIn('"value"', r.content.decode())

    def test_other_instructor_sees_nothing(self):
        self.client.force_authenticate(self.other_prof)
        r = self.client.get("/api/dashboard/instructor/")
        self.assertEqual(r.json(), [])

    def test_admin_dashboard_counts(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/dashboard/admin/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["submissions"], 1)
        self.assertEqual(r.json()["sessions"]["open"], 1)

    def test_admin_dashboard_forbidden_to_instructor_and_student(self):
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.client.get("/api/dashboard/admin/").status_code, 403)
        self.client.force_authenticate(self.s1)
        self.assertEqual(self.client.get("/api/dashboard/admin/").status_code, 403)