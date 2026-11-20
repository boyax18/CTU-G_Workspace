"""AR-5A HTTP session tests; run ONLY with --settings=config.test_settings."""

import re
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError
from django.test import TestCase, override_settings
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

    # WF-01.03 P-05 / D-16: per-identity login budget (owner-approved 16 Nov 2026).
    def test_identity_budget_applies_across_ip_addresses_and_normalized_ids(self):
        variants = ["2026-STUDENT-001", " 2026-student-001 ", "2026-Student-001"]
        responses = [
            self.login(school_id=variants[i % 3], password="Incorrect!9274", REMOTE_ADDR=f"10.0.0.{i + 1}")
            for i in range(8)
        ]
        self.assertTrue(all(response.status_code == 401 for response in responses), [r.status_code for r in responses])
        blocked = self.login(REMOTE_ADDR="10.0.1.1")  # correct password, fresh IP
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "too_many_attempts")
        self.assertTrue(blocked["Retry-After"].isdigit())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)
        # Another identity keeps its own budget.
        other = self.login(school_id="2026-STUDENT-999", password="Incorrect!9274", REMOTE_ADDR="10.0.1.2")
        self.assertEqual(other.status_code, 401)

    def test_identity_budget_is_checked_before_authentication(self):
        for i in range(8):
            self.login(password="Incorrect!9274", REMOTE_ADDR=f"10.0.2.{i + 1}")
        with mock.patch("apps.accounts.session_auth.authenticate") as authenticate:
            response = self.login(REMOTE_ADDR="10.0.3.1")
        self.assertEqual(response.status_code, 429)
        authenticate.assert_not_called()

    def test_identity_budget_cache_keys_never_contain_raw_identifier(self):
        self.login(password="Incorrect!9274")
        keys = [str(key).lower() for key in getattr(cache, "_cache", {})]
        self.assertTrue(any("login:school_id" in key for key in keys), keys)
        self.assertFalse(any("2026-student-001" in key for key in keys), keys)

    # WF-01.03 P-04: every authentication response carries a safe request reference.
    def test_auth_responses_carry_distinct_request_reference(self):
        responses = [
            self.login(password="Incorrect!9274"),
            self.client.post(self.base_path + "login/", {}, format="json"),  # CSRF failure
            self.login(),
            self.client.get(self.base_path + "session/"),
        ]
        responses.append(self.client.post(self.base_path + "logout/", {}, format="json",
                                          HTTP_X_CSRFTOKEN=self.current_csrf()))
        self.assertEqual([r.status_code for r in responses], [401, 403, 200, 200, 200])
        references = [r["X-Request-ID"] for r in responses]
        self.assertTrue(all(re.fullmatch(r"[a-f0-9]{32}", value) for value in references), references)
        self.assertEqual(len(set(references)), len(references))

    # WF-01.04 P-05 (owner-approved 16 Nov 2026): logout boundary tests.
    def logout(self):
        return self.client.post(self.base_path + "logout/", {}, format="json",
                                HTTP_X_CSRFTOKEN=self.current_csrf())

    def test_old_session_cookie_is_anonymous_after_logout(self):
        self.assertEqual(self.login().status_code, 200)
        old_key = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertTrue(Session.objects.filter(session_key=old_key).exists())
        self.assertEqual(self.logout().status_code, 200)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        # Replay the captured cookie: the server-side session no longer exists.
        self.client.cookies[settings.SESSION_COOKIE_NAME] = old_key
        self.assertEqual(self.client.get(self.base_path + "session/").json(), {"authenticated": False})
        with override_settings(
            ROOT_URLCONF="apps.accounts.registration_review_urls",
            WORKSPACE_REGISTRATION_REVIEW_API_ENABLED=True,
            WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
        ):
            self.client.cookies[settings.SESSION_COOKIE_NAME] = old_key
            review = self.client.get("/")
        self.assertEqual(review.status_code, 401)
        self.assertEqual(review.json()["error"]["code"], "authentication_required")

    def test_logout_response_expires_the_session_cookie(self):
        self.assertEqual(self.login().status_code, 200)
        response = self.logout()
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(cookie.value, "")
        self.assertEqual(str(cookie["max-age"]), "0")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("school_id", response.content.decode())

    def test_anonymous_logout_is_safe_and_creates_no_session(self):
        sessions_before = Session.objects.count()
        first, second = self.logout(), self.logout()
        for response in (first, second):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"authenticated": False})
        self.assertEqual(Session.objects.count(), sessions_before)
        self.assertEqual(self.client.get(self.base_path + "session/").json(), {"authenticated": False})

    def test_session_store_failure_never_claims_logout(self):
        self.assertEqual(self.login().status_code, 200)
        csrf = self.current_csrf()
        with mock.patch("django.contrib.sessions.backends.db.SessionStore.delete",
                        side_effect=DatabaseError("session store unavailable")):
            response = self.client.post(self.base_path + "logout/", {}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "auth_unavailable")
        self.assertNotIn("authenticated", response.json())
        # Django does not save sessions on 5xx responses: the session is honestly still active.
        self.assertTrue(self.client.get(self.base_path + "session/").json()["authenticated"])
