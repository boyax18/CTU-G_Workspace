"""AR-5A HTTP session tests; run ONLY with --settings=config.test_settings."""

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from .models import Account


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured(
        "Session authentication integration tests require isolated MySQL test settings."
    )


class WorkspaceSessionTests(TestCase):
    password = "Copper!River7392"
    base_path = "/api/v1/auth/"

    @classmethod
    def setUpTestData(cls):
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.account = Account.objects.create_user(
            school_id="2026-STUDENT-001", password=cls.password
        )
        cls.account.is_active = True
        cls.account.request_status = "Approved"
        cls.account.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=cls.account, role=cls.student)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.token = self.client.get(self.base_path + "csrf/").json()["csrfToken"]

    def login(self, school_id="2026-STUDENT-001", password=None, **headers):
        return self.client.post(
            self.base_path + "login/",
            {"school_id": school_id, "password": password or self.password},
            format="json",
            HTTP_X_CSRFTOKEN=self.token,
            **headers,
        )

    def current_csrf(self):
        return self.client.get(self.base_path + "csrf/").json()["csrfToken"]

    def test_approved_active_account_with_assigned_role_can_login(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["account"]["school_id"], self.account.school_id)
        self.assertEqual(response.json()["account"]["roles"], ["Student"])
        self.assertEqual(response.json()["permissions"], [])
        self.assertIn(settings.SESSION_COOKIE_NAME, self.client.cookies)
        session = self.client.get(self.base_path + "session/")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["account"]["roles"], ["Student"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("no-store", session["Cache-Control"])

    def test_login_rotates_anonymous_session_key_and_csrf_token(self):
        prior_session = self.client.session
        prior_session["nonce"] = "unprivileged"
        prior_session.save()
        old_session_key = prior_session.session_key
        old_csrf = self.token
        self.assertEqual(self.login().status_code, 200)
        new_session_key = self.client.session.session_key
        self.assertNotEqual(old_session_key, new_session_key)
        self.assertNotEqual(old_csrf, self.current_csrf())

    def test_password_failure_and_unknown_id_are_indistinguishable(self):
        wrong = self.login(password="Incorrect!9274")
        missing = self.login(school_id="no-such-school-id")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.json(), missing.json())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

    def test_pending_rejected_and_inactive_accounts_cannot_login(self):
        for state, active in (("Pending", True), ("Rejected", True), ("Approved", False)):
            with self.subTest(state=state, active=active):
                account = Account.objects.get(pk=self.account.pk)
                account.request_status = state
                account.is_active = active
                account.save(update_fields=["request_status", "is_active"])
                response = self.login()
                self.assertEqual(response.status_code, 401, response.content)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

    def test_unassigned_and_inactive_role_cannot_login(self):
        AccountRole.objects.filter(account=self.account).delete()
        self.assertEqual(self.login().status_code, 401)
        AccountRole.objects.create(account=self.account, role=self.student)
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.assertEqual(self.login().status_code, 401)

    def test_framework_superuser_cannot_use_workspace_even_with_role(self):
        account = Account.objects.get(pk=self.account.pk)
        account.is_staff = True
        account.is_superuser = True
        account.save(update_fields=["is_staff", "is_superuser"])
        self.assertEqual(self.login().status_code, 401)
        self.client.force_login(account)
        response = self.client.get(self.base_path + "session/")
        self.assertEqual(response.json(), {"authenticated": False})

    def test_session_reflects_removed_role_without_cached_grants(self):
        self.assertEqual(self.login().status_code, 200)
        AccountRole.objects.filter(account=self.account).delete()
        session = self.client.get(self.base_path + "session/")
        self.assertEqual(session.json(), {"authenticated": False})

    def test_session_reflects_revoked_approval(self):
        self.assertEqual(self.login().status_code, 200)
        account = Account.objects.get(pk=self.account.pk)
        account.request_status = "Pending"
        account.save(update_fields=["request_status"])
        self.assertEqual(
            self.client.get(self.base_path + "session/").json(),
            {"authenticated": False},
        )

    def test_logout_requires_csrf_and_clears_session(self):
        self.assertEqual(self.login().status_code, 200)
        no_csrf = self.client.post(self.base_path + "logout/", {}, format="json")
        self.assertEqual(no_csrf.status_code, 403)
        self.assertTrue(self.client.get(self.base_path + "session/").json()["authenticated"])
        response = self.client.post(
            self.base_path + "logout/", {}, format="json",
            HTTP_X_CSRFTOKEN=self.current_csrf(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False})
        self.assertEqual(
            self.client.get(self.base_path + "session/").json(),
            {"authenticated": False},
        )

    def test_csrf_required_for_anonymous_login(self):
        response = self.client.post(
            self.base_path + "login/",
            {"school_id": self.account.school_id, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")

    def test_untrusted_origin_rejected(self):
        response = self.login(HTTP_ORIGIN="https://malicious.example")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")

    def test_reject_extra_fields_and_non_object_data(self):
        response = self.client.post(
            self.base_path + "login/",
            {"school_id": self.account.school_id, "password": self.password, "is_staff": True},
            format="json", HTTP_X_CSRFTOKEN=self.token,
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            self.base_path + "login/", ["not a login object"],
            format="json", HTTP_X_CSRFTOKEN=self.token,
        )
        self.assertEqual(response.status_code, 400)

    def test_login_rate_limit(self):
        responses = [self.login(password="Incorrect!9274") for _ in range(9)]
        self.assertTrue(all(response.status_code == 401 for response in responses[:8]))
        self.assertEqual(responses[-1].status_code, 429)

    def test_session_is_anonymous_by_default_and_logout_is_post_only(self):
        response = self.client.get(self.base_path + "session/")
        self.assertEqual(response.json(), {"authenticated": False})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get(self.base_path + "logout/").status_code, 405)
