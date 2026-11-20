"""WF-01.05 CR-01 password recovery by email OTP; isolated MySQL only."""

import queue
import re
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import mock

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from . import password_reset, recovery_mail
from .models import Account

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Password reset tests require --settings=config.test_settings")

REQUEST, VERIFY, RESET = "/api/v1/auth/forgot-password/", "/api/v1/auth/forgot-password/verify/", "/api/v1/auth/reset-password/"
EMAIL, OLD, NEW = "student@example.edu", "Old!Password543", "New!Password643"
RECOVERY_SETTINGS = dict(
    WORKSPACE_PASSWORD_RESET_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


def codes():
    return [m.group(1) for msg in mail.outbox for m in [re.search(r"code is (\d{6})\.", msg.body)] if m]


def make_account(role, school_id, email, *, proof=True, proof_address=None):
    account = Account.objects.create_user(school_id=school_id, email=email, password=OLD)
    Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved")
    if proof:
        Account.objects.filter(pk=account.pk).update(email_verified_at=timezone.now(),
                                                     email_verified_address=proof_address or email)
    AccountRole.objects.create(account=account, role=role)
    account.refresh_from_db()
    return account


@override_settings(**RECOVERY_SETTINGS)
class PasswordRecoveryOTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Role.objects.create(role_name="Student")
        cls.account = make_account(cls.role, "0012345", EMAIL)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        recovery_mail.wait_until_idle()
        mail.outbox.clear()
        self.clock = int(timezone.now().timestamp())
        patcher = mock.patch.object(password_reset, "_now", side_effect=lambda: self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, path, data, client=None, **extra):
        client = client or self.client
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(path, data, format="json", HTTP_X_CSRFTOKEN=self.token, **extra)
        recovery_mail.wait_until_idle()  # D-20: delivery happens in the background
        return response

    def request(self, email=EMAIL, **extra):
        return self.post(REQUEST, {"email": email}, **extra)

    def verify(self, code, email=EMAIL, **extra):
        return self.post(VERIFY, {"email": email, "code": code}, **extra)

    def reset(self, password=NEW, confirmation=None, email=EMAIL, **extra):
        return self.post(RESET, {"email": email, "password": password, "password_confirmation": confirmation or password}, **extra)

    def assert_code_invalid(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": {"code": "recovery_code_invalid", "message": "The code is incorrect or has expired."}})

    # ---- main flow ----
    def test_full_flow_changes_password_once_and_clears_the_record(self):
        response = self.request()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "code_requested", "message": password_reset.NEUTRAL_REQUEST,
                                           "resend_after": 60, "code_valid_seconds": 600})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "CTU-G Workspace password reset code")
        self.assertNotIn("http", mail.outbox[0].body)
        verified = self.verify(codes()[0])
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json(), {"status": "verified"})
        cookie = verified.cookies[password_reset.TICKET_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api/v1/auth/reset-password/")
        self.assertEqual(str(cookie["max-age"]), "600")
        self.assertNotIn(cookie.value, verified.content.decode())
        done = self.reset()
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.cookies[password_reset.TICKET_COOKIE].value, "")
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(NEW))
        self.assertIsNone(self.account.password_reset_token)
        self.assertIsNone(self.account.password_reset_token_expires)
        self.client.cookies[password_reset.TICKET_COOKIE] = cookie.value  # replay the used ticket
        again = self.reset(password="Other!Password987")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["error"]["code"], "reset_session_invalid")

    def test_stored_record_holds_only_digests(self):
        self.request()
        self.account.refresh_from_db()
        stored = self.account.password_reset_token
        self.assertRegex(stored, r"\Arv1:otp:0:\d+:\d+:[0-9a-f]{64}\Z")
        self.assertNotIn(codes()[0], stored)
        self.assertIsNotNone(self.account.password_reset_token_expires)

    def test_email_is_normalized(self):
        self.assertEqual(self.request(email="  Student@Example.EDU ").status_code, 202)
        self.assertEqual(len(codes()), 1)
        self.assertEqual(self.verify(codes()[0], email="STUDENT@example.edu").status_code, 200)

    # ---- neutrality and eligibility (D-21, D-25) ----
    def test_unknown_legacy_mismatched_and_inactive_emails_are_neutral(self):
        make_account(self.role, "0077777", "legacy@example.edu", proof=False)
        make_account(self.role, "0066666", "current@example.edu", proof_address="previous@example.edu")
        inactive = make_account(self.role, "0055555", "inactive@example.edu")
        Account.objects.filter(pk=inactive.pk).update(is_active=False)
        bodies = {str(self.request(email=e, REMOTE_ADDR=f"10.9.0.{i}").json())
                  for i, e in enumerate(["nobody@example.edu", "legacy@example.edu", "current@example.edu", "inactive@example.edu"])}
        self.assertEqual(bodies, {str(self.request(REMOTE_ADDR="10.9.1.1").json())})
        self.assertEqual(len(mail.outbox), 1)  # only the eligible account
        for email in ("nobody@example.edu", "legacy@example.edu"):
            self.assert_code_invalid(self.verify("123456", email=email, REMOTE_ADDR="10.9.2.1"))

    def test_framework_staff_never_receive_a_code(self):
        Account.objects.filter(pk=self.account.pk).update(is_staff=True)
        self.request()
        self.assertEqual(len(mail.outbox), 0)

    # ---- code rules (D-26) ----
    def test_code_expires_after_ten_minutes(self):
        self.request()
        self.clock += 601
        self.assert_code_invalid(self.verify(codes()[0]))

    def test_resend_needs_sixty_seconds_and_replaces_the_code(self):
        self.request()
        self.request()  # within 60 s: nothing sent
        self.assertEqual(len(codes()), 1)
        self.clock += 61
        self.request()
        first, second = codes()
        self.assertNotEqual(first, second)
        self.assert_code_invalid(self.verify(first))
        self.assertEqual(self.verify(second).status_code, 200)

    def test_five_cumulative_wrong_codes_lock_the_window_and_resend_does_not_reset(self):
        # The rate limits run on the real clock; vary the IP and clear their counters
        # where this test simulates time passing, so only the D-26 rules are exercised.
        ip = iter(f"10.3.0.{i}" for i in range(1, 50))
        self.request()
        wrong = lambda: f"{(int(codes()[-1]) + 1) % 1_000_000:06d}"
        for _ in range(2):
            self.assert_code_invalid(self.verify(wrong(), REMOTE_ADDR=next(ip)))
        self.clock += 61
        self.request()  # resend keeps the attempt count
        self.account.refresh_from_db()
        self.assertTrue(self.account.password_reset_token.startswith("rv1:otp:2:"))
        for _ in range(3):
            self.assert_code_invalid(self.verify(wrong(), REMOTE_ADDR=next(ip)))
        self.account.refresh_from_db()
        self.assertTrue(self.account.password_reset_token.startswith("rv1:locked:5:"))
        self.assert_code_invalid(self.verify(codes()[-1], REMOTE_ADDR=next(ip)))  # even the right code is refused
        self.clock += 61
        cache.clear()
        self.request()  # locked: no new code inside the window
        self.assertEqual(len(codes()), 2)
        self.clock += 1800  # window over: a new request starts fresh
        cache.clear()
        self.request()
        self.assertEqual(len(codes()), 3)
        self.assertEqual(self.verify(codes()[-1], REMOTE_ADDR=next(ip)).status_code, 200)

    def test_password_change_invalidates_a_live_code(self):
        self.request()
        self.account.set_password("Changed!Elsewhere77")
        self.account.save(update_fields=["password"])
        self.assert_code_invalid(self.verify(codes()[0]))

    # ---- ticket (D-27) ----
    def test_ticket_expires_after_ten_minutes_and_is_required(self):
        self.request()
        self.verify(codes()[0])
        self.clock += 601
        expired = self.reset()
        self.assertEqual(expired.json()["error"]["code"], "reset_session_invalid")
        self.client.cookies.pop(password_reset.TICKET_COOKIE, None)
        self.assertEqual(self.reset().json()["error"]["code"], "reset_session_invalid")
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(OLD))

    def test_ticket_cannot_reset_another_account(self):
        other = make_account(self.role, "0044444", "other@example.edu")
        self.request()
        self.verify(codes()[0])
        response = self.reset(email="other@example.edu")
        self.assertEqual(response.json()["error"]["code"], "reset_session_invalid")
        other.refresh_from_db()
        self.assertTrue(other.check_password(OLD))

    def test_field_errors_keep_the_ticket_for_correction(self):
        self.request()
        self.verify(codes()[0])
        weak = self.reset(password="password")
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(weak.json()["error"]["fields"], {"password": ["Choose a stronger password using the requirements shown."]})
        mismatch = self.reset(password=NEW, confirmation="New!Password644")
        self.assertEqual(mismatch.json()["error"]["fields"], {"password_confirmation": ["Passwords do not match."]})
        self.assertEqual(self.reset().status_code, 200)

    # ---- sessions and notice (D-22) ----
    def test_other_sessions_including_executor_proof_end_and_reset_creates_none(self):
        other = APIClient(enforce_csrf_checks=True)
        csrf = other.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.assertEqual(other.post("/api/v1/auth/login/", {"school_id": "0012345", "password": OLD},
                                    format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        key = other.cookies[settings.SESSION_COOKIE_NAME].value
        store = SessionStore(session_key=key)
        store["workspace_executor_proof"] = "test-proof"
        store.save()
        self.request()
        self.verify(codes()[0])
        done = self.reset()
        self.assertEqual(done.status_code, 200)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, done.cookies)
        self.assertEqual(other.get("/api/v1/auth/session/").json(), {"authenticated": False})
        self.assertFalse(SessionStore(session_key=key).exists(key))

    def test_notice_only_after_a_committed_change(self):
        self.request()
        self.verify(codes()[0])
        mail.outbox.clear()
        self.reset(password="password")
        self.assertEqual(mail.outbox, [])
        self.reset()
        self.assertEqual([m.subject for m in mail.outbox], ["CTU-G Workspace password changed"])
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        self.assertNotRegex(mail.outbox[0].body, r"\d{6}|http")

    # ---- delivery (D-20) ----
    def test_response_does_not_wait_for_mail_delivery(self):
        def slow_send(*args, **kwargs):
            time.sleep(1.0)
            return 1
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=slow_send):
            started = time.monotonic()
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(REQUEST, {"email": EMAIL}, format="json", HTTP_X_CSRFTOKEN=self.token)
            elapsed = time.monotonic() - started
            recovery_mail.wait_until_idle()
        self.assertEqual(response.status_code, 202)
        self.assertLess(elapsed, 0.8)

    def test_mail_failure_is_neutral_and_logs_no_identity_or_code(self):
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("apps.accounts.recovery_mail", level="WARNING") as logs:
            response = self.request()
        self.assertEqual(response.status_code, 202)
        text = " ".join(logs.output)
        self.assertIn("reset_code", text)
        self.assertNotRegex(text, r"\d{6}")
        for secret in ("0012345", EMAIL):
            self.assertNotIn(secret, text)

    def test_full_queue_is_dropped_and_logged(self):
        with mock.patch.object(recovery_mail._queue, "put_nowait", side_effect=queue.Full), \
                self.assertLogs("apps.accounts.recovery_mail", level="WARNING") as logs:
            self.assertFalse(recovery_mail.enqueue("reset_code", "s", "b", "r@example.edu"))
        self.assertNotIn("r@example.edu", " ".join(logs.output))

    # ---- limits (P-03, D-26) ----
    def test_request_budget_per_email_applies_across_ip_addresses(self):
        for i in range(3):
            self.assertEqual(self.request(REMOTE_ADDR=f"10.1.0.{i}").status_code, 202)
        blocked = self.request(email=" STUDENT@example.edu", REMOTE_ADDR="10.1.1.1")
        self.assertEqual(blocked.status_code, 429)

    def test_verify_budget_per_email_applies_across_ip_addresses(self):
        for i in range(10):
            self.assert_code_invalid(self.verify("000000", REMOTE_ADDR=f"10.2.0.{i}"))
        self.assertEqual(self.verify("000000", REMOTE_ADDR="10.2.1.1").status_code, 429)

    def test_request_burst_does_not_block_verify_or_reset(self):
        self.request()
        for other in ("a@example.edu", "b@example.edu", "c@example.edu"):
            self.request(email=other)
        self.assertEqual(self.request(email="d@example.edu").status_code, 429)  # IP request limit used
        self.assertEqual(self.verify(codes()[0]).status_code, 200)
        self.assertEqual(self.reset().status_code, 200)

    # ---- gates and protection ----
    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_protected_executor_mode_refuses_every_step_without_mail_or_write(self):
        for response in (self.request(), self.verify("123456"), self.reset()):
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "recovery_unavailable")
        self.assertEqual(len(mail.outbox), 0)
        self.account.refresh_from_db()
        self.assertIsNone(self.account.password_reset_token)
        self.assertTrue(self.account.check_password(OLD))

    @override_settings(WORKSPACE_PASSWORD_RESET_ENABLED=False)
    def test_gate_off_refuses_every_step(self):
        for response in (self.request(), self.verify("123456"), self.reset()):
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "recovery_disabled")
        self.assertEqual(len(mail.outbox), 0)

    def test_csrf_and_exact_fields_are_required(self):
        client = APIClient(enforce_csrf_checks=True)
        for path, body in ((REQUEST, {"email": EMAIL}), (VERIFY, {"email": EMAIL, "code": "123456"}),
                           (RESET, {"email": EMAIL, "password": NEW, "password_confirmation": NEW})):
            self.assertEqual(client.post(path, body, format="json").status_code, 403)
        self.assertEqual(self.post(REQUEST, {"email": EMAIL, "school_id": "0012345"}).status_code, 400)
        self.assert_code_invalid(self.verify("12a456"))
        self.assertEqual(len(mail.outbox), 0)


@override_settings(**RECOVERY_SETTINGS)
class PasswordRecoveryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        recovery_mail.wait_until_idle()
        mail.outbox.clear()
        self.account = make_account(Role.objects.create(role_name="Student"), "0012345", EMAIL)

    def post_parallel(self, calls):
        barrier = Barrier(len(calls), timeout=20)

        def run(client, path, body):
            try:
                barrier.wait()
                return client.post(path, body, content_type="application/json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            results = [f.result(timeout=30) for f in [pool.submit(run, *call) for call in calls]]
        recovery_mail.wait_until_idle()
        return results

    def request_code(self):
        Client().post(REQUEST, {"email": EMAIL}, content_type="application/json")
        recovery_mail.wait_until_idle()
        return codes()[-1]

    def test_simultaneous_correct_codes_issue_exactly_one_ticket(self):
        code = self.request_code()
        body = {"email": EMAIL, "code": code}
        self.assertCountEqual(self.post_parallel([(Client(), VERIFY, body), (Client(), VERIFY, body)]), [200, 400])

    def test_simultaneous_wrong_codes_are_each_counted(self):
        code = self.request_code()
        wrong = f"{(int(code) + 1) % 1_000_000:06d}"
        body = {"email": EMAIL, "code": wrong}
        self.assertEqual(self.post_parallel([(Client(), VERIFY, body) for _ in range(3)]), [400, 400, 400])
        self.account.refresh_from_db()
        self.assertTrue(self.account.password_reset_token.startswith("rv1:otp:3:"))

    def test_simultaneous_resets_with_one_ticket_succeed_exactly_once(self):
        code = self.request_code()
        first = Client()
        response = first.post(VERIFY, {"email": EMAIL, "code": code}, content_type="application/json")
        ticket = response.cookies[password_reset.TICKET_COOKIE].value
        second = Client()
        second.cookies[password_reset.TICKET_COOKIE] = ticket
        mail.outbox.clear()
        calls = [(first, RESET, {"email": EMAIL, "password": "First!Password643", "password_confirmation": "First!Password643"}),
                 (second, RESET, {"email": EMAIL, "password": "Second!Password987", "password_confirmation": "Second!Password987"})]
        self.assertCountEqual(self.post_parallel(calls), [200, 400])
        self.account.refresh_from_db()
        self.assertNotEqual(self.account.check_password("First!Password643"), self.account.check_password("Second!Password987"))
        self.assertEqual([m.subject for m in mail.outbox], ["CTU-G Workspace password changed"])
