# ratings/tests.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.models import GroupMembership
from ratings.models import RatingPeriod

PW = "StrongPass!123"


class GroupTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.outsider_prof = User.objects.create_user("prof2", password=PW, role=User.Role.INSTRUCTOR)
        self.students = [
            User.objects.create_user(f"s{i}", password=PW, role=User.Role.STUDENT) for i in range(4)
        ]
        self.not_enrolled = User.objects.create_user("ghost", password=PW, role=User.Role.STUDENT)

        self.cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create(
            [Enrollment(classroom=self.cls, student=s) for s in self.students]
        )
        self.period = RatingPeriod.objects.create(
            classroom=self.cls,
            title="Project 1 peer review",
            deadline=timezone.now() + timedelta(days=7),
        )
        self.url = f"/api/ratings/periods/{self.period.id}/groups/"
        self.s0, self.s1, self.s2, self.s3 = self.students

    def post_group(self, members, leader, name="G"):
        return self.client.post(
            self.url,
            {"name": name, "member_ids": [m.id for m in members], "leader_id": leader.id},
            format="json",
        )

    def test_create_group_with_one_leader(self):
        self.client.force_authenticate(self.instructor)
        r = self.post_group([self.s0, self.s1], self.s0)
        self.assertEqual(r.status_code, 201)
        leaders = GroupMembership.objects.filter(period=self.period, is_group_leader=True)
        self.assertEqual(leaders.count(), 1)
        self.assertEqual(leaders.get().student, self.s0)

    def test_student_cannot_be_in_two_groups_in_one_session(self):
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.post_group([self.s0, self.s1], self.s0).status_code, 201)
        r = self.post_group([self.s1, self.s2], self.s2, name="G2")
        self.assertEqual(r.status_code, 400)

    def test_leader_must_be_a_member(self):
        self.client.force_authenticate(self.instructor)
        r = self.post_group([self.s2, self.s3], self.s0)
        self.assertEqual(r.status_code, 400)

    def test_members_must_be_enrolled(self):
        self.client.force_authenticate(self.instructor)
        r = self.post_group([self.s2, self.not_enrolled], self.s2)
        self.assertEqual(r.status_code, 400)

    def test_student_cannot_create_groups(self):
        self.client.force_authenticate(self.s0)
        r = self.post_group([self.s0, self.s1], self.s0)
        self.assertEqual(r.status_code, 403)

    def test_other_instructor_cannot_see_the_session(self):
        self.client.force_authenticate(self.outsider_prof)
        r = self.post_group([self.s0, self.s1], self.s0)
        self.assertEqual(r.status_code, 404)

    def test_groups_locked_once_session_opens(self):
        self.period.status = RatingPeriod.Status.OPEN
        self.period.save(update_fields=["status"])
        self.client.force_authenticate(self.instructor)
        r = self.post_group([self.s0, self.s1], self.s0)
        self.assertEqual(r.status_code, 400)