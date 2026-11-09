"""Password recovery tests against isolated MySQL only."""

from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from .models import Account

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Password reset tests require --settings=config.test_settings")


@override_settings(
    WORKSPACE_PASSWORD_RESET_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    PASSWORD_RESET_TIMEOUT=1800,
)
class PasswordResetAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        role = Role.objects.create(role_name="Student")
        cls.account = Account.objects.create_user(
            school_id="0012345", email="student@example.edu", password="Old!Password543"
        )
        cls.account.is_active = True
        cls.account.request_status = "Approved"
        cls.account.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.account, role=role)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        token_response = self.client.get("/api/v1/auth/csrf/")
        self.token = token_response.json()["csrfToken"]
        mail.outbox.clear()

    def post(self, path, data, token=None):
        return self.client.post(path, data, format="json", HTTP_X_CSRFTOKEN=token or self.token)

    def test_matching_request_sends_email_and_wrong_details_are_neutral(self):
        correct = self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"})
        self.assertEqual(correct.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        wrong = self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "wrong@example.edu"})
        self.assertEqual(wrong.status_code, 202)
        self.assertEqual(correct.json(), wrong.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("student@example.edu", str(correct.json()))

    def test_reset_changes_password_only_once(self):
        self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"})
        link = mail.outbox[0].body.split("http://localhost:5173/reset-password#", 1)[1].splitlines()[0]
        values = {key: value[0] for key, value in parse_qs(link).items()}
        body = {"uid": values["uid"], "token": values["token"], "password": "New!Password643", "password_confirmation": "New!Password643"}
        response = self.post("/api/v1/auth/reset-password/", body)
        self.assertEqual(response.status_code, 200, response.content)
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password("New!Password643"))
        again = self.post("/api/v1/auth/reset-password/", body)
        self.assertEqual(again.status_code, 400)
        self.assertIn("error", again.json())

    def test_bad_token_does_not_change_password(self):
        response = self.post("/api/v1/auth/reset-password/", {"uid": "MQ", "token": "bad-token", "password": "New!Password643", "password_confirmation": "New!Password643"})
        self.assertEqual(response.status_code, 400)
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password("Old!Password543"))

    @override_settings(WORKSPACE_PASSWORD_RESET_ENABLED=False)
    def test_feature_disabled_by_default_does_not_send_mail(self):
        response = self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_and_framework_staff_accounts_cannot_request_reset(self):
        self.account.is_active = False
        self.account.save(update_fields=["is_active"])
        response = self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)
        self.account.is_active, self.account.is_staff = True, True
        self.account.save(update_fields=["is_active", "is_staff"])
        response = self.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)

    def test_csrf_required(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post("/api/v1/auth/forgot-password/", {"school_id": "0012345", "email": "student@example.edu"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)
