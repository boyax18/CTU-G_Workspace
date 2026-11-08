"""HTTP/transaction tests. Run only with --settings=config.test_settings."""

from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connection
from django.test import TestCase
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from .models import Account, UserProfile
from .views import RegistrationDailyThrottle

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Registration database tests require --settings=config.test_settings; development data must never be used.")


class RegistrationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Refusing registration tests on an unexpected database.")
        for name in ("Student", "Instructor", "Treasurer", "Admin"):
            Role.objects.create(role_name=name)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        response = self.client.get("/api/v1/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.token = response.json()["csrfToken"]
        self.data = {
            "school_id": "2026-REG-001", "email": "registrant@example.edu",
            "first_name": "Maria", "middle_name": "Cruz", "last_name": "Santos", "suffix": "Jr.",
            "requested_role": "Student", "password": "Copper!River7392", "password_confirmation": "Copper!River7392",
        }

    def post(self, data=None, **headers):
        return self.client.post("/api/v1/auth/register/", self.data if data is None else data,
                                format="json", HTTP_X_CSRFTOKEN=self.token, **headers)

    def assert_rejected(self, response, field=None, status=400):
        self.assertEqual(response.status_code, status, response.content)
        self.assertIn("error", response.json())
        if field:
            self.assertIn(field, response.json()["error"]["fields"])
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)
        self.assertEqual(AccountRole.objects.count(), 0)

    def assert_pending(self, role):
        response = self.post()
        self.assertEqual(response.status_code, 202, response.content)
        account = Account.objects.get()
        profile = UserProfile.objects.get(account=account)
        self.assertEqual(account.request_status, "Pending")
        self.assertFalse(account.is_active)
        self.assertEqual(account.requested_role.role_name, role)
        self.assertNotEqual(account.password, self.data["password"])
        self.assertTrue(account.check_password(self.data["password"]))
        self.assertEqual(profile.first_name, "Maria")
        self.assertEqual(profile.middle_name, "Cruz")
        self.assertEqual(profile.last_name, "Santos")
        self.assertEqual(profile.suffix, "Jr.")
        self.assertIsNone(account.reviewed_by_id)
        self.assertIsNone(account.reviewed_at)
        self.assertFalse(AccountRole.objects.exists())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)
        self.assertEqual(set(response.json()), {"message"})
        self.assertNotIn(account.password, response.content.decode())
        self.assertNotIn(self.data["password"], response.content.decode())

    def test_student_registration_creates_only_pending_inactive_account_and_profile(self):
        self.assert_pending("Student")

    def test_instructor_registration_creates_only_pending_inactive_account_and_profile(self):
        self.data["requested_role"] = "Instructor"
        self.assert_pending("Instructor")

    def test_duplicate_school_id_is_neutral_and_does_not_update_existing_account(self):
        first = self.post()
        account = Account.objects.get()
        original_hash = account.password
        account.request_status, account.is_active = "Approved", True
        account.save(update_fields=["request_status", "is_active"])
        self.data.update(email="different@example.edu", first_name="Changed")
        second = self.post()
        self.assertEqual((first.status_code, first.json()), (second.status_code, second.json()))
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        account.refresh_from_db()
        self.assertEqual(account.password, original_hash)
        self.assertEqual(account.email, "registrant@example.edu")
        self.assertEqual(account.profile.first_name, "Maria")
        self.assertEqual(account.request_status, "Approved")
        self.assertTrue(account.is_active)

    def test_duplicate_school_id_uses_mysql_case_insensitive_uniqueness(self):
        self.post()
        self.data["school_id"] = self.data["school_id"].lower()
        self.assertEqual(self.post().status_code, 202)
        self.assertEqual(Account.objects.count(), 1)

    def test_invalid_email(self):
        self.data["email"] = "not-an-email"
        self.assert_rejected(self.post(), "email")

    def test_optional_fields_can_be_omitted(self):
        for key in ("email", "middle_name", "suffix"):
            self.data.pop(key)
        self.assertEqual(self.post().status_code, 202)
        account = Account.objects.get()
        self.assertIsNone(account.email)
        self.assertIsNone(account.profile.middle_name)
        self.assertIsNone(account.profile.suffix)

    def test_missing_required_fields(self):
        for field in ("school_id", "first_name", "last_name", "requested_role", "password", "password_confirmation"):
            with self.subTest(field=field):
                cache.clear()
                data = {key: value for key, value in self.data.items() if key != field}
                self.assert_rejected(self.post(data), field)

    def test_password_mismatch(self):
        self.data["password_confirmation"] = "Other!Password4739"
        self.assert_rejected(self.post(), "password_confirmation")

    def test_django_password_policies(self):
        for password in ("short", "password", "123456789012", "registrant@example.edu"):
            with self.subTest(password_policy=password):
                self.data["password"] = self.data["password_confirmation"] = password
                self.assert_rejected(self.post(), "password")

    def test_password_similarity_includes_profile_names(self):
        self.data["first_name"] = "Alexandrianna"
        self.data["password"] = self.data["password_confirmation"] = "Alexandrianna"
        self.assert_rejected(self.post(), "password")

    def test_restricted_unknown_or_numeric_requested_roles(self):
        for role in ("Admin", "Treasurer", "Technical Super Admin", "Super Admin", "Unknown", 1, "student", None):
            with self.subTest(role=role):
                cache.clear()
                self.data["requested_role"] = role
                self.assert_rejected(self.post(), "requested_role")

    def test_privilege_field_injection_is_rejected(self):
        for field in ("is_active", "request_status", "account_roles", "is_superuser", "requested_role_id", "extra_fields", "reviewed_by"):
            with self.subTest(field=field):
                cache.clear()
                self.assert_rejected(self.post({**self.data, field: True}), "non_field_errors")

    def test_public_fields_require_strings(self):
        for field, value in (("password", 12345), ("school_id", 123), ("first_name", []), ("email", None)):
            with self.subTest(field=field):
                self.assert_rejected(self.post({**self.data, field: value}), field)

    def test_field_length_limits(self):
        for field, length in (("school_id", 51), ("email", 151), ("first_name", 101), ("last_name", 101), ("middle_name", 101), ("suffix", 21), ("password", 129)):
            with self.subTest(field=field):
                cache.clear()
                self.assert_rejected(self.post({**self.data, field: "x" * length}), field)

    def test_blank_required_fields(self):
        self.assert_rejected(self.post({**self.data, "school_id": "   ", "first_name": " "}), "school_id")

    def test_missing_csrf_cookie_and_token(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post("/api/v1/auth/register/", self.data, format="json")
        self.assert_rejected(response, status=403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")

    def test_missing_csrf_header(self):
        self.assert_rejected(self.client.post("/api/v1/auth/register/", self.data, format="json"), status=403)

    def test_invalid_csrf_token(self):
        response = self.client.post("/api/v1/auth/register/", self.data, format="json", HTTP_X_CSRFTOKEN="a" * 64)
        self.assert_rejected(response, status=403)

    def test_untrusted_origin_is_rejected_with_valid_csrf_token(self):
        self.assert_rejected(self.post(HTTP_ORIGIN="https://attacker.example"), status=403)

    def test_same_origin_csrf_submission_is_accepted(self):
        self.assertEqual(self.post(HTTP_ORIGIN="http://testserver").status_code, 202)

    def test_csrf_bootstrap_is_not_cached_or_authenticated(self):
        response = self.client.get("/api/v1/auth/csrf/")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_profile_integrity_failure_rolls_back_account(self):
        with patch("apps.accounts.services.UserProfile.objects.create", side_effect=IntegrityError(1048, "sensitive database detail")):
            response = self.post()
        self.assert_rejected(response, status=503)
        self.assertNotIn("sensitive", response.content.decode())
        self.assertEqual(response.json()["error"]["code"], "registration_unavailable")

    def test_unexpected_profile_failure_is_safe_and_atomic(self):
        with patch("apps.accounts.services.UserProfile.objects.create", side_effect=RuntimeError("sensitive internal detail")):
            with self.assertLogs("apps.accounts.views", level="ERROR") as captured:
                response = self.post()
        self.assert_rejected(response, status=503)
        self.assertNotIn("sensitive", response.content.decode())
        self.assertNotIn("sensitive", " ".join(captured.output))

    def test_inactive_or_missing_role_fails_without_writes(self):
        Role.objects.filter(role_name="Student").update(is_active=False)
        self.assert_rejected(self.post(), status=503)
        Role.objects.filter(role_name="Student").delete()
        self.assert_rejected(self.post(), status=503)

    def test_malformed_nonobject_and_duplicate_key_json(self):
        for raw in ('{"school_id":', '[]', 'null', '{"school_id":"one","school_id":"two"}', '{"x":NaN}'):
            with self.subTest(raw=raw):
                response = self.client.post("/api/v1/auth/register/", raw, content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
                self.assert_rejected(response)

    def test_oversized_payload_is_rejected(self):
        response = self.client.post("/api/v1/auth/register/", '{"x":"' + "x" * 17000 + '"}', content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
        self.assert_rejected(response)

    def test_only_json_is_supported(self):
        response = self.client.post("/api/v1/auth/register/", self.data, HTTP_X_CSRFTOKEN=self.token)
        self.assert_rejected(response, status=415)

    def test_get_does_not_create_account(self):
        self.assert_rejected(self.client.get("/api/v1/auth/register/"), status=405)

    def test_burst_limit_cannot_be_bypassed_with_forwarded_for(self):
        for index in range(5):
            self.assertEqual(self.post({}, HTTP_X_FORWARDED_FOR=f"192.0.2.{index}").status_code, 400)
        response = self.post({}, HTTP_X_FORWARDED_FOR="203.0.113.1")
        self.assert_rejected(response, status=429)
        self.assertIn("Retry-After", response)

    def test_daily_limit(self):
        with patch.object(RegistrationDailyThrottle, "rate", "1/day"):
            self.assertEqual(self.post({}).status_code, 400)
            self.assert_rejected(self.post({}), status=429)
