"""WF-01.06 session expiry, CSRF and deployment-security tests; isolated MySQL only."""

import datetime
from unittest import mock

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from config.security_settings import build_security_settings
from . import session_timeout
from .models import Account

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Session security tests require --settings=config.test_settings")

AUTH = "/api/v1/auth/"
PASSWORD = "Copper!River7392"
IDLE, ABSOLUTE = 1800, 28800


class SessionExpiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = Role.objects.create(role_name="Student")
        cls.account = Account.objects.create_user(school_id="7000001", password=PASSWORD)
        Account.objects.filter(pk=cls.account.pk).update(is_active=True, request_status="Approved")
        AccountRole.objects.create(account=cls.account, role=cls.student)

    def setUp(self):
        cache.clear()
        self.clock = 1_900_000_000
        patcher = mock.patch.object(session_timeout, "_now", side_effect=lambda: self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self):
        return self.client.get(AUTH + "csrf/").json()["csrfToken"]

    def login(self):
        response = self.client.post(AUTH + "login/", {"school_id": "7000001", "password": PASSWORD},
                                    format="json", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(response.status_code, 200, response.content)
        return self.client.cookies[settings.SESSION_COOKIE_NAME].value

    def session(self):
        return self.client.get(AUTH + "session/")

    def authenticated(self):
        return self.session().json().get("authenticated") is True

    def stored(self, key):
        return Session.objects.get(session_key=key).get_decoded()

    # 1, 2 ---------------------------------------------------------------
    def test_valid_session_continues_inside_the_idle_window(self):
        self.login()
        self.clock += IDLE - 1
        self.assertTrue(self.authenticated())

    def test_idle_timeout_ends_the_session_exactly_at_thirty_minutes(self):
        key = self.login()
        self.clock += IDLE
        self.assertFalse(self.authenticated())
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    # 3, 4 ---------------------------------------------------------------
    def test_activity_extends_idle_time_but_never_the_eight_hour_lifetime(self):
        start = self.clock
        self.login()
        for offset in range(1700, ABSOLUTE, 1700):
            self.clock = start + offset
            self.assertTrue(self.authenticated(), offset)
        self.clock = start + ABSOLUTE - 1
        self.assertTrue(self.authenticated())
        self.clock = start + ABSOLUTE  # last activity 1,599 s ago, but the lifetime is over
        self.assertFalse(self.authenticated())

    # 5 ------------------------------------------------------------------
    def test_activity_is_written_at_most_once_per_minute(self):
        start = self.clock
        key = self.login()
        self.clock = start + 30
        self.assertTrue(self.authenticated())
        self.assertEqual(self.stored(key)[session_timeout.SEEN_AT], start)
        self.clock = start + 60
        response = self.session()
        self.assertEqual(self.stored(key)[session_timeout.SEEN_AT], start + 60)
        self.assertEqual(self.stored(key)[session_timeout.AUTH_AT], start)
        # Cookie and database expiry follow the absolute deadline, not a sliding window.
        self.assertEqual(int(response.cookies[settings.SESSION_COOKIE_NAME]["max-age"]), ABSOLUTE - 60)
        remaining = (Session.objects.get(session_key=key).expire_date - timezone.now()).total_seconds()
        self.assertAlmostEqual(remaining, ABSOLUTE - 60, delta=30)

    def test_login_stamps_a_fresh_session_and_rotates_csrf(self):
        token = self.csrf()
        anonymous_key = self.client.session.session_key
        key = self.login()
        self.assertNotEqual(anonymous_key, key)
        self.assertNotEqual(token, self.csrf())
        data = self.stored(key)
        self.assertEqual(data[session_timeout.AUTH_AT], self.clock)
        self.assertEqual(data[session_timeout.SEEN_AT], self.clock)

    # 6, 7 ---------------------------------------------------------------
    def test_legacy_session_without_timestamps_is_ended(self):
        key = self.login()
        store = SessionStore(session_key=key)
        del store[session_timeout.AUTH_AT]
        del store[session_timeout.SEEN_AT]
        store.save()
        self.assertFalse(self.authenticated())
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_tampered_future_timestamps_are_ended(self):
        key = self.login()
        store = SessionStore(session_key=key)
        store[session_timeout.SEEN_AT] = self.clock + 10_000
        store.save()
        self.assertFalse(self.authenticated())

    def test_django_admin_logins_are_stamped_too(self):
        admin = Account.objects.create_user(school_id="7000099", password=PASSWORD)
        Account.objects.filter(pk=admin.pk).update(is_active=True, request_status="Approved", is_staff=True, is_superuser=True)
        client = Client()
        client.force_login(Account.objects.get(pk=admin.pk))
        data = client.session
        self.assertEqual(data[session_timeout.AUTH_AT], self.clock)

    def test_expired_cookie_replay_is_rejected(self):
        key = self.login()
        self.clock += IDLE
        self.assertFalse(self.authenticated())
        self.client.cookies[settings.SESSION_COOKIE_NAME] = key
        self.assertFalse(self.authenticated())
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_a_concurrent_request_cannot_revive_an_expired_session(self):
        key = self.login()
        stale = SessionStore(session_key=key)
        self.assertIsNotNone(stale.get("_auth_user_id"))  # a slower request has read its session before expiry
        self.clock += IDLE
        self.assertFalse(self.authenticated())  # expiry flushes the row
        stale[session_timeout.SEEN_AT] = self.clock
        with self.assertRaises(UpdateError):
            stale.save()
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    # 8, 9, 10 -----------------------------------------------------------
    def test_deactivation_ends_access_on_the_next_request(self):
        self.login()
        Account.objects.filter(pk=self.account.pk).update(is_active=False)
        self.assertFalse(self.authenticated())

    def test_role_revocation_deny_and_disabled_service_are_reflected_immediately(self):
        service = Service.objects.create(service_code="clearance", service_name="Clearance")
        permission = Permission.objects.create(service=service, permission_code="clearance.requests.read",
                                               permission_name="Read", module_name="requests", action_name="read")
        RolePermission.objects.create(role=self.student, permission=permission)
        self.login()
        self.assertIn("clearance.requests.read", self.session().json()["permissions"])
        deny = AccountPermission.objects.create(account=self.account, permission=permission, effect="Deny")
        self.assertNotIn("clearance.requests.read", self.session().json()["permissions"])
        deny.delete()
        Service.objects.filter(pk=service.pk).update(is_active=False)
        self.assertNotIn("clearance.requests.read", self.session().json()["permissions"])
        self.assertTrue(self.authenticated())  # a denial never signs the user out
        AccountRole.objects.filter(account=self.account).delete()
        self.assertFalse(self.authenticated())

    # 15 -----------------------------------------------------------------
    def test_session_store_outage_fails_closed(self):
        self.login()
        with mock.patch.object(SessionStore, "load", side_effect=DatabaseError("store down")):
            api = self.session()
            page = self.client.get("/admin/")
        self.assertEqual(api.status_code, 503)
        self.assertEqual(api.json()["error"]["code"], "auth_unavailable")
        self.assertIn("no-store", api["Cache-Control"])
        self.assertEqual(page.status_code, 503)
        self.assertTrue(self.authenticated())  # nothing was lost once the store is back


class CSRFTests(TestCase):
    ENDPOINTS = ["login/", "logout/", "register/", "register/verify/", "register/resend/", "register/cancel/",
                 "reapply/link/", "reapply/complete/", "forgot-password/", "forgot-password/verify/", "reset-password/"]

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    # 11 -----------------------------------------------------------------
    def test_csrf_cookie_is_httponly_and_the_body_token_still_works(self):
        response = self.client.get(AUTH + "csrf/")
        cookie = response.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        token = response.json()["csrfToken"]
        self.assertTrue(token)
        logout = self.client.post(AUTH + "logout/", {}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(logout.status_code, 200)

    # 12 -----------------------------------------------------------------
    def test_missing_or_invalid_tokens_are_refused_before_any_effect(self):
        self.client.get(AUTH + "csrf/")
        for headers in ({}, {"HTTP_X_CSRFTOKEN": "x" * 64}):
            response = self.client.post(AUTH + "login/", {"school_id": "7000001", "password": PASSWORD}, format="json", **headers)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertNotIn(settings.SESSION_COOKIE_NAME, self.client.cookies)

    # 13 -----------------------------------------------------------------
    # Reapplication refuses everything with 503 while its gate is off; with the gate
    # on it runs the shared registration CSRF check, which is what this test proves.
    @override_settings(WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED=True)
    def test_untrusted_origin_is_refused_on_every_unsafe_auth_endpoint(self):
        token = self.client.get(AUTH + "csrf/").json()["csrfToken"]
        for path in self.ENDPOINTS:
            response = self.client.post(AUTH + path, {}, format="json", HTTP_X_CSRFTOKEN=token,
                                        HTTP_ORIGIN="https://malicious.example")
            self.assertEqual(response.status_code, 403, path)
            self.assertEqual(response.json()["error"]["code"], "csrf_failed", path)

    def test_https_requests_without_origin_need_a_same_site_referer(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get(AUTH + "csrf/", secure=True).json()["csrfToken"]
        bad = client.post(AUTH + "logout/", {}, format="json", secure=True, HTTP_X_CSRFTOKEN=token,
                          HTTP_REFERER="https://malicious.example/page")
        self.assertEqual(bad.status_code, 403)
        good = client.post(AUTH + "logout/", {}, format="json", secure=True, HTTP_X_CSRFTOKEN=token,
                           HTTP_REFERER="https://testserver/dashboard")
        self.assertEqual(good.status_code, 200)


class SessionCleanupTests(TestCase):
    # 18 -----------------------------------------------------------------
    def test_clearsessions_removes_only_expired_sessions(self):
        now = timezone.now()
        Session.objects.create(session_key="e" * 32, session_data="", expire_date=now - datetime.timedelta(seconds=1))
        Session.objects.create(session_key="v" * 32, session_data="", expire_date=now + datetime.timedelta(hours=1))
        call_command("clearsessions")
        self.assertEqual(list(Session.objects.values_list("session_key", flat=True)), ["v" * 32])


class SecuritySettingsTests(SimpleTestCase):
    # 14 -----------------------------------------------------------------
    def test_local_defaults_keep_http_working_with_debug_off(self):
        s = build_security_settings({})
        self.assertEqual(s["WORKSPACE_DEPLOYMENT_PROFILE"], "local")
        self.assertFalse(s["DEBUG"])
        self.assertFalse(s["SESSION_COOKIE_SECURE"])
        self.assertFalse(s["SECURE_SSL_REDIRECT"])
        self.assertTrue(s["SESSION_COOKIE_HTTPONLY"])
        self.assertTrue(s["CSRF_COOKIE_HTTPONLY"])
        self.assertEqual((s["WORKSPACE_SESSION_IDLE_SECONDS"], s["WORKSPACE_SESSION_ABSOLUTE_SECONDS"], s["SESSION_COOKIE_AGE"]),
                         (1800, 28800, 28800))
        self.assertEqual((s["CORS_ALLOWED_ORIGINS"], s["CORS_ALLOW_ALL_ORIGINS"], s["CORS_ALLOW_CREDENTIALS"]), ([], False, False))
        self.assertIsNone(s["SECURE_PROXY_SSL_HEADER"])
        self.assertTrue(build_security_settings({"DJANGO_DEBUG": "1"})["DEBUG"])

    def test_production_requires_https_and_debug_off(self):
        with self.assertRaises(ImproperlyConfigured):
            build_security_settings({"WORKSPACE_DEPLOYMENT_PROFILE": "production"})
        with self.assertRaises(ImproperlyConfigured):
            build_security_settings({"WORKSPACE_DEPLOYMENT_PROFILE": "production", "WORKSPACE_HTTPS": "1", "DJANGO_DEBUG": "1"})
        with self.assertRaises(ImproperlyConfigured):
            build_security_settings({"WORKSPACE_DEPLOYMENT_PROFILE": "production", "WORKSPACE_HTTPS": "1", "WORKSPACE_ALLOWED_HOSTS": "*"})
        s = build_security_settings({"WORKSPACE_DEPLOYMENT_PROFILE": "production", "WORKSPACE_HTTPS": "1",
                                     "WORKSPACE_HSTS_SECONDS": "3600", "WORKSPACE_TRUST_PROXY_SSL_HEADER": "1",
                                     "WORKSPACE_CSRF_TRUSTED_ORIGINS": "https://portal.example.edu"})
        self.assertTrue(s["SESSION_COOKIE_SECURE"] and s["CSRF_COOKIE_SECURE"] and s["SECURE_SSL_REDIRECT"])
        self.assertEqual(s["SECURE_HSTS_SECONDS"], 3600)
        self.assertEqual(s["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(s["CSRF_TRUSTED_ORIGINS"], ["https://portal.example.edu"])
        self.assertFalse(build_security_settings({"WORKSPACE_DEPLOYMENT_PROFILE": "production", "WORKSPACE_HTTPS": "1",
                                                  "WORKSPACE_SSL_REDIRECT": "0"})["SECURE_SSL_REDIRECT"])

    def test_unsafe_or_inconsistent_values_are_rejected(self):
        for env in ({"WORKSPACE_TRUST_PROXY_SSL_HEADER": "1"}, {"WORKSPACE_HSTS_SECONDS": "60"},
                    {"WORKSPACE_CSRF_TRUSTED_ORIGINS": "https://*.example.edu"}, {"WORKSPACE_CSRF_TRUSTED_ORIGINS": "example.edu"},
                    {"WORKSPACE_CSRF_TRUSTED_ORIGINS": "https://a.example.edu/path"},
                    {"WORKSPACE_HTTPS": "1", "WORKSPACE_CSRF_TRUSTED_ORIGINS": "http://a.example.edu"},
                    {"WORKSPACE_SESSION_IDLE_SECONDS": "40000", "WORKSPACE_SESSION_ABSOLUTE_SECONDS": "30000"},
                    {"WORKSPACE_SESSION_IDLE_SECONDS": "abc"}, {"DJANGO_DEBUG": "true"},
                    {"WORKSPACE_DEPLOYMENT_PROFILE": "staging"}):
            with self.assertRaises(ImproperlyConfigured, msg=str(env)):
                build_security_settings(env)

    def test_active_test_settings_use_the_approved_policy(self):
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertEqual((settings.WORKSPACE_SESSION_IDLE_SECONDS, settings.WORKSPACE_SESSION_ABSOLUTE_SECONDS), (1800, 28800))
        self.assertIn("apps.accounts.session_timeout.SessionTimeoutMiddleware", settings.MIDDLEWARE)
        auth_index = settings.MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        self.assertEqual(settings.MIDDLEWARE[auth_index + 1], "apps.accounts.session_timeout.SessionTimeoutMiddleware")
