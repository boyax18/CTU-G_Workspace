# ratings/test_privacy.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.models import Group, GroupMembership
from ratings.models import RatingCriterion, RatingPeriod, RatingScore, RatingSubmission

PW = "StrongPass!123"


class PeerRatingTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.s0 = User.objects.create_user("s0", password=PW, role=User.Role.STUDENT)
        self.s1 = User.objects.create_user("s1", password=PW, role=User.Role.STUDENT)
        self.s2 = User.objects.create_user("s2", password=PW, role=User.Role.STUDENT)
        self.s3 = User.objects.create_user("s3", password=PW, role=User.Role.STUDENT)
        self.s4 = User.objects.create_user("s4", password=PW, role=User.Role.STUDENT)
        self.outsider = User.objects.create_user("outside", password=PW, role=User.Role.STUDENT)

        cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create([
            Enrollment(classroom=cls, student=s)
            for s in [self.s0, self.s1, self.s2, self.s3, self.s4]
        ])

        self.period = RatingPeriod.objects.create(
            classroom=cls, title="Project 1", deadline=timezone.now() + timedelta(days=7)
        )
        self.c1 = RatingCriterion.objects.create(period=self.period, name="Contribution")
        self.c2 = RatingCriterion.objects.create(period=self.period, name="Reliability")

        g1 = Group.objects.create(period=self.period, name="G1")
        g2 = Group.objects.create(period=self.period, name="G2")
        GroupMembership.objects.create(period=self.period, group=g1, student=self.s0, is_group_leader=True)
        GroupMembership.objects.create(period=self.period, group=g1, student=self.s1)
        GroupMembership.objects.create(period=self.period, group=g1, student=self.s2)
        GroupMembership.objects.create(period=self.period, group=g2, student=self.s3, is_group_leader=True)
        GroupMembership.objects.create(period=self.period, group=g2, student=self.s4)

        self.period.status = RatingPeriod.Status.OPEN
        self.period.save(update_fields=["status"])

    def url(self, suffix):
        return f"/api/ratings/periods/{self.period.id}/{suffix}"

    def full_scores(self, targets, value=4):
        return [
            {"target_id": t.id, "criterion_id": c.id, "value": value}
            for t in targets for c in (self.c1, self.c2)
        ]

    # Form and visibility

    def test_form_lists_only_own_teammates(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("form/"))
        self.assertEqual(r.status_code, 200)
        ids = {t["id"] for t in r.json()["teammates"]}
        self.assertEqual(ids, {self.s1.id, self.s2.id})

    def test_form_never_contains_scores(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("form/"))
        self.assertNotIn("scores", r.json())

    def test_unenrolled_student_gets_404(self):
        self.client.force_authenticate(self.outsider)
        r = self.client.get(self.url("form/"))
        self.assertEqual(r.status_code, 404)

    # Submission rules

    def test_submit_valid_form(self):
        self.client.force_authenticate(self.s1)
        r = self.client.post(
            self.url("submit/"), {"scores": self.full_scores([self.s0, self.s2])}, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(RatingScore.objects.count(), 4)

    def test_cannot_rate_self(self):
        self.client.force_authenticate(self.s1)
        scores = self.full_scores([self.s0, self.s2]) + [
            {"target_id": self.s1.id, "criterion_id": self.c1.id, "value": 5}
        ]
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_rate_student_from_another_group(self):
        self.client.force_authenticate(self.s1)
        scores = self.full_scores([self.s0, self.s3])  # s3 is in group G2
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_incomplete_form_is_rejected(self):
        self.client.force_authenticate(self.s1)
        scores = self.full_scores([self.s0])  # s2 missing
        r = self.client.post(self.url("submit/"), {"scores": scores}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_value_outside_scale_is_rejected(self):
        self.client.force_authenticate(self.s1)
        r = self.client.post(
            self.url("submit/"), {"scores": self.full_scores([self.s0, self.s2], value=6)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_cannot_submit_twice_and_submission_is_locked(self):
        self.client.force_authenticate(self.s1)
        payload = {"scores": self.full_scores([self.s0, self.s2])}
        self.assertEqual(self.client.post(self.url("submit/"), payload, format="json").status_code, 201)
        r = self.client.post(self.url("submit/"), payload, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(RatingScore.objects.count(), 4)
        self.assertTrue(RatingSubmission.objects.get(period=self.period, rater=self.s1).is_locked)

    def test_submission_rejected_after_deadline(self):
        self.period.deadline = timezone.now() - timedelta(minutes=1)
        self.period.save(update_fields=["deadline"])
        self.client.force_authenticate(self.s1)
        r = self.client.post(
            self.url("submit/"), {"scores": self.full_scores([self.s0, self.s2])}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_submission_rejected_when_closed(self):
        self.period.status = RatingPeriod.Status.CLOSED
        self.period.save(update_fields=["status"])
        self.client.force_authenticate(self.s1)
        r = self.client.post(
            self.url("submit/"), {"scores": self.full_scores([self.s0, self.s2])}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    # Leader status

    def test_leader_sees_submission_status_without_values(self):
        self.client.force_authenticate(self.s1)
        self.client.post(
            self.url("submit/"), {"scores": self.full_scores([self.s0, self.s2])}, format="json"
        )
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("group-status/"))
        self.assertEqual(r.status_code, 200)
        by_id = {m["id"]: m for m in r.json()}
        self.assertTrue(by_id[self.s1.id]["submitted"])
        self.assertFalse(by_id[self.s2.id]["submitted"])
        for member in r.json():
            self.assertEqual(set(member.keys()), {"id", "name", "submitted"})

    def test_non_leader_cannot_view_group_status(self):
        self.client.force_authenticate(self.s1)
        r = self.client.get(self.url("group-status/"))
        self.assertEqual(r.status_code, 403)

    def test_leader_status_covers_only_own_group(self):
        self.client.force_authenticate(self.s0)
        r = self.client.get(self.url("group-status/"))
        ids = {m["id"] for m in r.json()}
        self.assertEqual(ids, {self.s0.id, self.s1.id, self.s2.id})

    # Criteria

    def test_criteria_locked_once_open(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.post(
            self.url("criteria/"), {"name": "Late addition"}, format="json"
        )
        self.assertEqual(r.status_code, 400)