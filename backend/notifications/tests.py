# notifications/tests.py
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from classes.models import Class, Enrollment
from groups.services import create_group
from ratings.models import RatingCriterion, RatingPeriod

from .models import Notification

PW = "StrongPass!123"


class NotificationTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof", password=PW, role=User.Role.INSTRUCTOR)
        self.s0 = User.objects.create_user("s0", password=PW, role=User.Role.STUDENT)
        self.s1 = User.objects.create_user("s1", password=PW, role=User.Role.STUDENT)
        self.outsider = User.objects.create_user("out", password=PW, role=User.Role.STUDENT)

        self.cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        Enrollment.objects.bulk_create([
            Enrollment(classroom=self.cls, student=self.s0),
            Enrollment(classroom=self.cls, student=self.s1),
        ])
        self.period = RatingPeriod.objects.create(
            classroom=self.cls, title="Project 1", deadline=timezone.now() + timedelta(days=7)
        )
        RatingCriterion.objects.create(period=self.period, name="Contribution")
        create_group(self.period, "G1", [self.s0.id, self.s1.id], self.s0.id)

    def test_leader_is_notified_when_assigned(self):
        self.assertTrue(
            Notification.objects.filter(recipient=self.s0, message__contains="leader").exists()
        )
        self.assertFalse(
            Notification.objects.filter(recipient=self.s1, message__contains="leader").exists()
        )

    def test_opening_notifies_enrolled_students_only(self):
        self.client.force_authenticate(self.instructor)
        self.client.post(f"/api/ratings/periods/{self.period.id}/open/")
        self.assertTrue(
            Notification.objects.filter(recipient=self.s1, message__contains="is open").exists()
        )
        self.assertFalse(Notification.objects.filter(recipient=self.outsider).exists())

    def test_list_returns_only_own_notifications(self):
        self.client.force_authenticate(self.s1)
        r = self.client.get("/api/notifications/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all(n["id"] for n in r.json()))
        self.assertEqual(
            Notification.objects.filter(recipient=self.s1).count(), len(r.json())
        )

    def test_cannot_mark_someone_elses_notification_read(self):
        note = Notification.objects.filter(recipient=self.s0).first()
        self.client.force_authenticate(self.s1)
        r = self.client.post(f"/api/notifications/{note.id}/read/")
        self.assertEqual(r.status_code, 404)
        note.refresh_from_db()
        self.assertIsNone(note.read_at)

    def test_owner_can_mark_read(self):
        note = Notification.objects.filter(recipient=self.s0).first()
        self.client.force_authenticate(self.s0)
        r = self.client.post(f"/api/notifications/{note.id}/read/")
        self.assertEqual(r.status_code, 200)
        note.refresh_from_db()
        self.assertIsNotNone(note.read_at)