"""Password recovery tests against isolated MySQL only."""

import datetime
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from . import recovery_mail
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
        # D-21: recovery requires verified-email proof (as created by the WF-01.01/02 OTP flow).
        Account.objects.filter(pk=cls.account.pk).update(
            email_verified_at=timezone.now(), email_verified_address="student@example.edu")
        AccountRole.objects.create(account=cls.account, role=role)
        cls.role = role

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        token_response = self.client.get("/api/v1/auth/csrf/")
        self.token = token_response.json()["csrfToken"]
        recovery_mail.wait_until_idle()
        mail.outbox.clear()

    def post(self, path, data, token=None, **extra):
        response = self.client.post(path, data, format="json", HTTP_X_CSRFTOKEN=token or self.token, **extra)
        # D-20: mail is sent in the background; wait so assertions see the outcome.
        recovery_mail.wait_until_idle()
        return response

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

    # ---- WF-01.05 P-01 to P-07 (owner-approved 16 Nov 2026) ----
    REQUEST = {"school_id": "0012345", "email": "student@example.edu"}

    def request_link(self, **extra):
        self.post("/api/v1/auth/forgot-password/", self.REQUEST, **extra)
        link = mail.outbox[-1].body.split("/reset-password#", 1)[1].splitlines()[0]
        return {key: value[0] for key, value in parse_qs(link).items()}

    def reset(self, values, password="New!Password643", confirmation=None):
        return self.post("/api/v1/auth/reset-password/", {
            "uid": values["uid"], "token": values["token"],
            "password": password, "password_confirmation": confirmation or password})

    def make_account(self, school_id, email, *, verified_address=None):
        account = Account.objects.create_user(school_id=school_id, email=email, password="Old!Password543")
        account.is_active, account.request_status = True, "Approved"
        account.save(update_fields=["is_active", "request_status"])
        AccountRole.objects.create(account=account, role=self.role)
        if verified_address:
            Account.objects.filter(pk=account.pk).update(email_verified_at=timezone.now(), email_verified_address=verified_address)
        return account

    def test_d21_legacy_account_without_proof_gets_neutral_response_and_no_mail(self):
        legacy = self.make_account("0077777", "legacy@example.edu")
        response = self.post("/api/v1/auth/forgot-password/", {"school_id": "0077777", "email": "legacy@example.edu"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["message"], self.post("/api/v1/auth/forgot-password/", {"school_id": "0000001", "email": "x@example.edu"}).json()["message"])
        self.assertEqual(len(mail.outbox), 0)
        # A link for a legacy account cannot be used either.
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        values = {"uid": urlsafe_base64_encode(force_bytes(legacy.pk)), "token": default_token_generator.make_token(legacy)}
        refused = self.reset(values)
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()["error"]["code"], "reset_link_invalid")
        legacy.refresh_from_db()
        self.assertTrue(legacy.check_password("Old!Password543"))

    def test_d21_proof_for_a_different_address_is_not_accepted(self):
        self.make_account("0066666", "current@example.edu", verified_address="previous@example.edu")
        self.post("/api/v1/auth/forgot-password/", {"school_id": "0066666", "email": "current@example.edu"})
        self.assertEqual(len(mail.outbox), 0)

    def test_expired_link_is_refused_with_specific_code(self):
        values = self.request_link()
        later = datetime.datetime.now() + datetime.timedelta(seconds=1801)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=later):
            response = self.reset(values)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], {"code": "reset_link_invalid",
                                                    "message": "This reset link is invalid or expired. Request a new reset link."})
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password("Old!Password543"))

    def test_second_link_is_refused_after_the_first_is_used(self):
        first, second = self.request_link(), self.request_link()
        self.assertEqual(self.reset(first).status_code, 200)
        again = self.reset(second, password="Other!Password987")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["error"]["code"], "reset_link_invalid")

    def test_p01_safe_field_errors_for_password_rules_and_confirmation(self):
        values = self.request_link()
        weak = self.reset(values, password="password")
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(weak.json()["error"]["fields"], {"password": ["Choose a stronger password using the requirements shown."]})
        mismatch = self.reset(values, password="New!Password643", confirmation="New!Password644")
        self.assertEqual(mismatch.json()["error"]["fields"], {"password_confirmation": ["Passwords do not match."]})
        malformed = self.post("/api/v1/auth/reset-password/", {"uid": "!!", "token": "x", "password": "New!Password643", "password_confirmation": "New!Password643"})
        self.assertEqual(malformed.json()["error"]["code"], "reset_link_invalid")
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password("Old!Password543"))

    def test_sessions_including_executor_proof_end_after_reset_and_reset_creates_none(self):
        other = APIClient(enforce_csrf_checks=True)
        csrf = other.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.assertEqual(other.post("/api/v1/auth/login/", {"school_id": "0012345", "password": "Old!Password543"},
                                    format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        key = other.cookies[settings.SESSION_COOKIE_NAME].value
        store = SessionStore(session_key=key)
        store["workspace_executor_proof"] = "test-proof"
        store.save()
        self.assertTrue(other.get("/api/v1/auth/session/").json()["authenticated"])
        response = self.reset(self.request_link())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertEqual(self.client.get("/api/v1/auth/session/").json(), {"authenticated": False})
        self.assertEqual(other.get("/api/v1/auth/session/").json(), {"authenticated": False})
        self.assertFalse(SessionStore(session_key=key).exists(key))

    def test_d22_password_changed_notice_only_after_commit(self):
        values = self.request_link()
        with self.captureOnCommitCallbacks(execute=True) as failed:
            self.reset(values, password="password")
        self.assertEqual(failed, [])
        with self.captureOnCommitCallbacks(execute=True) as succeeded:
            self.assertEqual(self.reset(values).status_code, 200)
        recovery_mail.wait_until_idle()
        self.assertEqual(len(succeeded), 1)
        notice = mail.outbox[-1]
        self.assertEqual(notice.subject, "CTU-G Workspace password changed")
        self.assertEqual(notice.to, ["student@example.edu"])
        self.assertNotIn("reset-password", notice.body)
        self.assertNotIn(values["token"], notice.body)

    def test_d20_response_does_not_wait_for_mail_delivery(self):
        def slow_send(*args, **kwargs):
            time.sleep(1.0)
            return 1
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=slow_send):
            started = time.monotonic()
            response = self.client.post("/api/v1/auth/forgot-password/", self.REQUEST, format="json", HTTP_X_CSRFTOKEN=self.token)
            elapsed = time.monotonic() - started
            recovery_mail.wait_until_idle()
        self.assertEqual(response.status_code, 202)
        self.assertLess(elapsed, 0.8)

    def test_d20_mail_failure_is_neutral_and_logs_no_identity_or_token(self):
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("apps.accounts.recovery_mail", level="WARNING") as logs:
            response = self.post("/api/v1/auth/forgot-password/", self.REQUEST)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["message"], "If the account details match an eligible account, a password reset email will be sent.")
        text = " ".join(logs.output)
        self.assertIn("reset_link", text)
        for secret in ("0012345", "student@example.edu", "reset-password", "token"):
            self.assertNotIn(secret, text)

    def test_d20_full_queue_is_dropped_and_logged(self):
        import queue
        with mock.patch.object(recovery_mail._queue, "put_nowait", side_effect=queue.Full), \
                self.assertLogs("apps.accounts.recovery_mail", level="WARNING") as logs:
            self.assertFalse(recovery_mail.enqueue("reset_link", "s", "b", "r@example.edu"))
        self.assertNotIn("r@example.edu", " ".join(logs.output))

    def test_p03_identity_budget_applies_across_ip_addresses(self):
        for i in range(3):
            self.assertEqual(self.post("/api/v1/auth/forgot-password/", self.REQUEST, REMOTE_ADDR=f"10.1.0.{i + 1}").status_code, 202)
        self.assertEqual(len(mail.outbox), 3)
        blocked = self.post("/api/v1/auth/forgot-password/", {"school_id": " 0012345 ", "email": "student@example.edu"}, REMOTE_ADDR="10.1.1.1")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(len(mail.outbox), 3)

    def test_p03_request_burst_does_not_block_the_reset_step(self):
        values = self.request_link()
        self.post("/api/v1/auth/forgot-password/", self.REQUEST)
        self.post("/api/v1/auth/forgot-password/", {"school_id": "0000001", "email": "x@example.edu"})
        self.post("/api/v1/auth/forgot-password/", {"school_id": "0000002", "email": "y@example.edu"})
        self.assertEqual(self.post("/api/v1/auth/forgot-password/", self.REQUEST).status_code, 429)  # IP 4/min used
        self.assertEqual(self.reset(values).status_code, 200)

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_protected_executor_mode_fails_closed_without_mail_or_write(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        request = self.post("/api/v1/auth/forgot-password/", self.REQUEST)
        values = {"uid": urlsafe_base64_encode(force_bytes(self.account.pk)), "token": default_token_generator.make_token(self.account)}
        confirm = self.reset(values)
        for response in (request, confirm):
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "recovery_unavailable")
        self.assertEqual(len(mail.outbox), 0)
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password("Old!Password543"))

    @override_settings(WORKSPACE_PASSWORD_RESET_ENABLED=False)
    def test_confirm_is_also_gated(self):
        response = self.post("/api/v1/auth/reset-password/", {"uid": "MQ", "token": "t", "password": "New!Password643", "password_confirmation": "New!Password643"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "recovery_disabled")


@override_settings(
    WORKSPACE_PASSWORD_RESET_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
    PASSWORD_RESET_TIMEOUT=1800,
)
class PasswordResetConcurrencyTests(TransactionTestCase):
    def test_simultaneous_resets_with_one_token_succeed_exactly_once(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        role = Role.objects.create(role_name="Student")
        account = Account.objects.create_user(school_id="0012345", email="student@example.edu", password="Old!Password543")
        Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved",
                                                     email_verified_at=timezone.now(), email_verified_address="student@example.edu")
        AccountRole.objects.create(account=account, role=role)
        account.refresh_from_db()
        cache.clear()
        recovery_mail.wait_until_idle()
        mail.outbox.clear()
        body = {"uid": urlsafe_base64_encode(force_bytes(account.pk)), "token": default_token_generator.make_token(account)}
        barrier = Barrier(2, timeout=20)

        def confirm(password):
            try:
                client = Client()
                barrier.wait()
                return client.post("/api/v1/auth/reset-password/", {**body, "password": password, "password_confirmation": password},
                                   content_type="application/json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [f.result(timeout=30) for f in [pool.submit(confirm, "First!Password643"), pool.submit(confirm, "Second!Password987")]]
        recovery_mail.wait_until_idle()
        self.assertCountEqual(results, [200, 400])
        account.refresh_from_db()
        self.assertTrue(account.check_password("First!Password643") != account.check_password("Second!Password987"))
        self.assertEqual([m.subject for m in mail.outbox], ["CTU-G Workspace password changed"])
