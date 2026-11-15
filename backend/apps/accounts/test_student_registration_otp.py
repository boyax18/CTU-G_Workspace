"""WF-01.01 real HTTP/MySQL checks, exclusively in the guarded disposable DB."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection, connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from .models import Account, StudentRegistrationStage, UserProfile
from .registration_staging import CONFLICT, _decrypt, begin_student_registration, student_verification_action
from .student_registration_api import COOKIE

if settings.SETTINGS_MODULE != "config.test_settings" or not settings.REGISTRATION_TEST_DATABASE.startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("OTP tests require the disposable MySQL runner.")


def data(n=1):
    return {"school_id": f"700000{n}", "email": f"applicant{n}@example.edu", "first_name": "Maria",
            "middle_name": "", "last_name": "Santos", "suffix": "", "requested_role": "Student",
            "password": "Copper!River7392", "password_confirmation": "Copper!River7392"}


def last_code():
    return re.search(r"code is: ([0-9]{6})", mail.outbox[-1].body)[1]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StudentOTPTests(TestCase):
    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(cursor.fetchone()[0], settings.REGISTRATION_TEST_DATABASE)
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()
        for name in ("RegistrationBurstThrottle", "RegistrationDailyThrottle"):
            patched = patch("apps.accounts.views." + name + ".rate", "1000/min")
            patched.start()
            self.addCleanup(patched.stop)
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def post(self, path="register/", payload=None, client=None):
        return (client or self.client).post("/api/v1/auth/" + path, data(1) if payload is None else payload,
                                           format="json", HTTP_X_CSRFTOKEN=self.csrf)

    def start(self):
        response = self.post()
        self.assertEqual(response.status_code, 202, response.content)
        return last_code()

    def verify(self, code):
        return self.post("register/verify/", {"code": code})

    def test_no_permanent_data_before_otp_and_only_encrypted_hashed_payload(self):
        response = self.post()
        self.assertEqual(response.status_code, 202)
        stage = StudentRegistrationStage.objects.get()
        raw = str(StudentRegistrationStage.objects.values().get())
        for value in (data()["password"], data()["email"], data()["school_id"], last_code()):
            self.assertNotIn(value, raw)
        payload = _decrypt(stage)
        self.assertTrue(check_password(data()["password"], payload["password_hash"]))
        self.assertNotIn("password", payload)
        self.assertNotIn("password_confirmation", payload)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertFalse(AccountRole.objects.exists())
        cookie = response.cookies[COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertNotIn("browser_token", response.json())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_valid_code_atomically_creates_pending_profile_and_proof_without_roles(self):
        code = self.start()
        hashed = _decrypt(StudentRegistrationStage.objects.get())["password_hash"]
        response = self.verify(code)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "completed")
        account = Account.objects.get()
        self.assertEqual(account.request_status, "Pending")
        self.assertFalse(account.is_active or account.is_staff or account.is_superuser)
        self.assertEqual(account.password, hashed)
        self.assertEqual(account.email_verified_address, data()["email"])
        self.assertIsNotNone(account.email_verified_at)
        self.assertEqual(account.profile.first_name, "Maria")
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(StudentRegistrationStage.objects.exists())

    def test_replay_cannot_create_a_second_account(self):
        code = self.start()
        token = self.client.cookies[COOKIE].value
        self.assertEqual(self.verify(code).status_code, 200)
        self.client.cookies[COOKIE] = token
        self.assertEqual(self.verify(code).status_code, 410)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_failed_attempts_persist_and_invalidate_code(self):
        code = self.start()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            self.assertEqual(self.verify(wrong).json()["error"]["code"], "otp_invalid")
        self.assertEqual(self.verify(wrong).json()["error"]["code"], "attempts_exhausted")
        self.assertEqual(self.verify(code).json()["error"]["code"], "attempts_exhausted")
        self.assertEqual(StudentRegistrationStage.objects.get().attempt_count, 5)
        self.assertFalse(Account.objects.exists())

    def test_expired_code_does_not_create_account(self):
        code = self.start()
        StudentRegistrationStage.objects.update(otp_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.verify(code).json()["error"]["code"], "otp_expired")
        self.assertFalse(Account.objects.exists())

    def test_resend_interval_limit_old_code_invalidation_and_fixed_stage_expiry(self):
        old = self.start()
        expires = StudentRegistrationStage.objects.get().expires_at
        self.assertEqual(self.post("register/resend/", {}).status_code, 429)
        for _ in range(3):
            StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
            self.assertEqual(self.post("register/resend/", {}).status_code, 202)
        stage = StudentRegistrationStage.objects.get()
        self.assertEqual(stage.expires_at, expires)
        self.assertEqual(stage.resend_count, 3)
        self.assertEqual(self.verify(old).json()["error"]["code"], "otp_invalid")
        self.assertEqual(self.post("register/resend/", {}).json()["error"]["code"], "resends_exhausted")
        self.assertEqual(self.verify(last_code()).status_code, 200)

    def test_resends_do_not_reset_failed_attempt_count(self):
        code = self.start()
        self.verify("000000" if code != "000000" else "111111")
        StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
        self.post("register/resend/", {})
        self.assertEqual(StudentRegistrationStage.objects.get().attempt_count, 1)

    def test_resend_does_not_reissue_the_same_numeric_code(self):
        with patch("apps.accounts.registration_staging.secrets.randbelow", return_value=123456):
            self.start()
        StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
        with patch("apps.accounts.registration_staging.secrets.randbelow", side_effect=[123456, 234567]):
            self.assertEqual(self.post("register/resend/", {}).status_code, 202)
        self.assertEqual(last_code(), "234567")
        self.assertEqual(self.verify("123456").json()["error"]["code"], "otp_invalid")

    def test_failed_resend_invalidates_uncertain_code_and_keeps_stage(self):
        self.start()
        StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
        with patch("apps.accounts.registration_staging.send_mail", return_value=0):
            self.assertEqual(self.post("register/resend/", {}).status_code, 503)
        stage = StudentRegistrationStage.objects.get()
        self.assertFalse(stage.otp_digest)
        self.assertEqual(stage.resend_count, 1)
        self.assertFalse(Account.objects.exists())

    def test_duplicate_staged_attempt_never_overwrites_and_owner_can_resume(self):
        self.start()
        original = StudentRegistrationStage.objects.values().get()
        changed = data()
        changed["first_name"] = "Changed"
        response = self.post(payload=changed)
        self.assertEqual(response.json()["status"], "existing_verification")
        self.assertEqual(StudentRegistrationStage.objects.values().get(), original)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.get("/api/v1/auth/register/verification/").status_code, 202)

    def test_another_browser_cannot_resume_cancel_or_overwrite_from_identity_alone(self):
        code = self.start()
        other = APIClient(enforce_csrf_checks=True)
        other_csrf = other.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = other.post("/api/v1/auth/register/", data(), format="json", HTTP_X_CSRFTOKEN=other_csrf)
        self.assertEqual(response.json()["error"]["message"], CONFLICT)
        other.cookies[COOKIE] = "x" * 43
        response = other.post("/api/v1/auth/register/cancel/", {}, format="json", HTTP_X_CSRFTOKEN=other_csrf)
        self.assertEqual(response.status_code, 410)
        self.assertEqual(StudentRegistrationStage.objects.count(), 1)
        self.assertEqual(self.verify(code).status_code, 200)

    def test_cancel_purges_stage_and_invalidates_code(self):
        code = self.start()
        token = self.client.cookies[COOKIE].value
        self.assertEqual(self.post("register/cancel/", {}).status_code, 200)
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.client.cookies[COOKIE] = token
        self.assertEqual(self.verify(code).status_code, 410)

    def test_abandoned_cleanup_never_deletes_accounts_or_unexpired_stages(self):
        self.start()
        Account.objects.create(school_id="existing", email="existing@example.edu")
        StudentRegistrationStage.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        call_command("purge_student_registration_staging", verbosity=0)
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertEqual(Account.objects.count(), 1)

    def test_stage_expiry_is_enforced_without_waiting_for_cleanup(self):
        code = self.start()
        StudentRegistrationStage.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.verify(code).status_code, 410)
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertFalse(Account.objects.exists())

    def test_expiry_is_checked_after_a_stage_lock_wait(self):
        code = self.start()
        clock = [timezone.now()]
        StudentRegistrationStage.objects.update(expires_at=clock[0] + timedelta(seconds=10))
        original_first = QuerySet.first

        def first_after_wait(queryset):
            row = original_first(queryset)
            if queryset.model is StudentRegistrationStage:
                clock[0] += timedelta(seconds=20)
            return row

        with patch("apps.accounts.registration_staging.timezone.now", side_effect=lambda: clock[0]), patch.object(QuerySet, "first", first_after_wait):
            self.assertEqual(self.verify(code).status_code, 410)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())

    def test_mail_failure_retains_encrypted_stage_without_claiming_delivery(self):
        with patch("apps.accounts.registration_staging.send_mail", side_effect=RuntimeError("private transport detail")):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "delivery_failed")
        self.assertNotIn(b"private transport detail", response.content)
        self.assertIn(COOKIE, response.cookies)
        stage = StudentRegistrationStage.objects.get()
        self.assertFalse(stage.otp_digest)
        self.assertFalse(Account.objects.exists())
        StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
        self.assertEqual(self.post("register/resend/", {}).status_code, 202)
        self.assertEqual(self.verify(last_code()).status_code, 200)

    def test_final_profile_failure_rolls_back_account_proof_and_verified_stage(self):
        code = self.start()
        with patch("apps.accounts.registration_staging.UserProfile.objects.create", side_effect=RuntimeError("fail")):
            self.assertEqual(self.verify(code).status_code, 503)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertIsNone(StudentRegistrationStage.objects.get().email_verified_at)
        self.assertEqual(self.verify(code).status_code, 200)

    def test_identity_conflict_before_and_after_otp_uses_same_message(self):
        code = self.start()
        Account.objects.create(school_id=data()["school_id"], email="other@example.edu")
        final = self.verify(code)
        self.assertEqual(final.status_code, 409)
        self.assertEqual(final.json()["error"]["message"], CONFLICT)
        self.assertEqual(self.post().json()["error"]["message"], CONFLICT)
        self.assertEqual(Account.objects.count(), 1)
        self.assertFalse(UserProfile.objects.exists())

    def test_student_role_disappearing_rolls_back_verified_stage(self):
        code = self.start()
        Role.objects.filter(role_name="Student").update(is_active=False)
        self.assertEqual(self.verify(code).status_code, 503)
        self.assertIsNone(StudentRegistrationStage.objects.get().email_verified_at)
        self.assertFalse(Account.objects.exists())

    def test_all_mutating_endpoints_enforce_csrf_before_work(self):
        self.start()
        for suffix, payload in (("verify", {"code": last_code()}), ("resend", {}), ("cancel", {})):
            response = self.client.post(f"/api/v1/auth/register/{suffix}/", payload, format="json")
            self.assertEqual(response.status_code, 403)
        self.assertEqual(StudentRegistrationStage.objects.count(), 1)
        self.assertFalse(Account.objects.exists())

    @override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True)
    def test_fenced_deployment_never_falls_back_to_a_local_student_writer(self):
        with self.assertNumQueries(0):
            self.assertEqual(self.post().status_code, 503)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class StudentOTPConcurrencyTests(TransactionTestCase):
    def test_simultaneous_verification_is_exactly_once(self):
        Role.objects.create(role_name="Student")
        result = begin_student_registration(data())
        token, code = result["browser_token"], last_code()
        barrier = Barrier(2, timeout=20)

        def verify():
            try:
                barrier.wait()
                return student_verification_action(token, "verify", code)["status"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(verify), pool.submit(verify)]]
        self.assertCountEqual(results, ["completed", "expired"])
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertFalse(AccountRole.objects.exists())

    def test_simultaneous_stage_reservations_cannot_overwrite(self):
        Role.objects.create(role_name="Student")
        barrier = Barrier(2, timeout=20)

        def begin():
            try:
                barrier.wait()
                return begin_student_registration(data())["status"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(begin), pool.submit(begin)]]
        self.assertCountEqual(results, ["verification_required", "conflict"])
        self.assertEqual(StudentRegistrationStage.objects.count(), 1)
        self.assertFalse(Account.objects.exists())
