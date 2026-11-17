# classes/tests.py
from rest_framework.test import APITestCase
from accounts.models import User
from .models import Class

PW = "StrongPass!123"


class ClassTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user("prof1", password=PW, role=User.Role.INSTRUCTOR)
        self.other = User.objects.create_user("prof2", password=PW, role=User.Role.INSTRUCTOR)
        self.student = User.objects.create_user("stu1", password=PW, role=User.Role.STUDENT)
        self.student2 = User.objects.create_user("stu2", password=PW, role=User.Role.STUDENT)

    def test_instructor_creates_class_and_owns_it(self):
        self.client.force_authenticate(self.instructor)
        r = self.client.post("/api/classes/", {"code": "CS101", "name": "SE"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Class.objects.get(pk=r.json()["id"]).instructor, self.instructor)

    def test_student_cannot_create_class(self):
        self.client.force_authenticate(self.student)
        r = self.client.post("/api/classes/", {"code": "X", "name": "Y"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_other_instructor_gets_404_on_someone_elses_class(self):
        cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        self.client.force_authenticate(self.other)
        r = self.client.get(f"/api/classes/{cls.id}/")
        self.assertEqual(r.status_code, 404)

    def test_enroll_students(self):
        cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        self.client.force_authenticate(self.instructor)
        r = self.client.post(
            f"/api/classes/{cls.id}/enroll/",
            {"student_ids": [self.student.id, self.student2.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["enrolled"], 2)

    def test_enroll_rejects_non_student_ids(self):
        cls = Class.objects.create(code="CS101", name="SE", instructor=self.instructor)
        self.client.force_authenticate(self.instructor)
        r = self.client.post(
            f"/api/classes/{cls.id}/enroll/",
            {"student_ids": [self.other.id]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)