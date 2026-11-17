# accounts/tests.py
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory, APITestCase

from .models import User
from .permissions import IsAdmin, IsInstructor, IsStudent

PASSWORD = "StrongPass!123"


class AuthTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", password=PASSWORD, role=User.Role.STUDENT
        )

    def login(self, username=None, password=PASSWORD):
        return self.client.post(
            "/api/auth/login/",
            {"username": username or self.student.username, "password": password},
            format="json",
        )

    def test_login_returns_tokens(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.json())
        self.assertIn("refresh", r.json())

    def test_login_rejects_wrong_password(self):
        r = self.login(password="wrong")
        self.assertEqual(r.status_code, 401)

    def test_me_requires_token(self):
        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 401)

    def test_me_returns_current_user_only(self):
        access = self.login().json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        r = self.client.get("/api/auth/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "student1")
        self.assertEqual(r.json()["role"], "student")
        self.assertNotIn("password", r.json())

    def test_logout_blacklists_refresh_token(self):
        tokens = self.login().json()
        r = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(r.status_code, 200)

        # The same refresh token must no longer work.
        r = self.client.post(
            "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(r.status_code, 401)


class RolePermissionTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.student = User.objects.create_user("s", password=PASSWORD, role=User.Role.STUDENT)
        self.instructor = User.objects.create_user("i", password=PASSWORD, role=User.Role.INSTRUCTOR)
        self.admin = User.objects.create_user("a", password=PASSWORD, role=User.Role.ADMIN)

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_anonymous_user_is_denied_everywhere(self):
        req = self._request(AnonymousUser())
        self.assertFalse(IsStudent().has_permission(req, None))
        self.assertFalse(IsInstructor().has_permission(req, None))
        self.assertFalse(IsAdmin().has_permission(req, None))

    def test_student_cannot_use_instructor_or_admin_permissions(self):
        req = self._request(self.student)
        self.assertTrue(IsStudent().has_permission(req, None))
        self.assertFalse(IsInstructor().has_permission(req, None))
        self.assertFalse(IsAdmin().has_permission(req, None))

    def test_instructor_is_not_admin(self):
        req = self._request(self.instructor)
        self.assertTrue(IsInstructor().has_permission(req, None))
        self.assertFalse(IsAdmin().has_permission(req, None))

    def test_admin_role_passes_admin_permission(self):
        req = self._request(self.admin)
        self.assertTrue(IsAdmin().has_permission(req, None))