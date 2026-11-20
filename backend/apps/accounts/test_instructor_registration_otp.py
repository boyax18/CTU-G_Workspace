"""Owner-stated WF-01.02 acceptance; guarded disposable MySQL, synthetic mail."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccountRole, Role
from .api_errors import ERRORS, INSTRUCTOR_SCHOOL_FIELDS_ERROR
from .models import Account, StudentRegistrationStage, UserProfile
from .registration_staging import _decrypt, purge_expired_stages
from .student_registration_api import COOKIE
from .test_student_registration_otp import data as student_data, last_code

if settings.SETTINGS_MODULE != "config.test_settings":
    raise ImproperlyConfigured("Instructor OTP tests require guarded disposable settings.")


def data(n=1):
    return {**student_data(n), "school_id": f"500000{n}", "email": f"instructor{n}@example.edu", "requested_role": "Instructor"}


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", WORKSPACE_REGISTRATION_SUPPORT_CONTACT="")
class InstructorOTPTests(TestCase):
    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            self.assertEqual(cursor.fetchone()[0], settings.REGISTRATION_TEST_DATABASE)
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()
        for name in ("RegistrationBurstThrottle", "RegistrationDailyThrottle"):
            limiter = patch("apps.accounts.views." + name + ".rate", "1000/min")
            limiter.start()
            self.addCleanup(limiter.stop)
        self.client, self.csrf = self.browser()

    def browser(self):
        client = APIClient(enforce_csrf_checks=True)
        return client, client.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def post(self, suffix="", payload=None, *, client=None, csrf=None):
        query = "?requested_role=Instructor" if suffix else ""
        return (client or self.client).post(
            "/api/v1/auth/register/" + suffix + query, data() if payload is None else payload,
            format="json", HTTP_X_CSRFTOKEN=csrf or self.csrf,
        )

    def start(self):
        response = self.post()
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(response.json()["status"], "verification_required")
        return last_code()

    def verify(self, code):
        return self.post("verify/", {"code": code})

    def assert_conflict(self, response):
        self.assertEqual(response.status_code, 409, response.content)
        error = response.json()["error"]
        self.assertEqual(error["code"], "conflict")
        self.assertEqual(error["message"], ERRORS["conflict"][1])
        self.assertNotIn("fields", error)
        self.assertEqual(error["request_id"], response["X-Request-ID"])
        self.assertLessEqual(set(response.json()), {"error", "status"})

    def test_no_account_until_otp_then_atomic_instructor_proof_and_profile_without_role(self):
        code = self.start()
        stage = StudentRegistrationStage.objects.get()
        self.assertEqual(_decrypt(stage)["requested_role"], "Instructor")
        for private in (data()["password"], data()["email"], code):
            self.assertNotIn(private, stage.encrypted_payload)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertIn("Your Instructor registration", mail.outbox[0].body)
        response = self.verify(code)
        self.assertEqual(response.status_code, 200, response.content)
        account = Account.objects.get()
        self.assertEqual(account.requested_role.role_name, "Instructor")
        self.assertEqual(account.request_status, "Pending")
        self.assertFalse(account.is_active)
        self.assertTrue(account.check_password(data()["password"]))
        self.assertEqual(account.email_verified_address, data()["email"])
        self.assertIsNotNone(account.email_verified_at)
        self.assertEqual(account.profile.first_name, data()["first_name"])
        self.assertFalse(AccountRole.objects.exists())
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertEqual(self.verify(code).status_code, 410)

    def test_existing_email_all_account_states_is_409_with_no_stage_or_mail(self):
        for n, state in enumerate(("Pending", "Approved", "Rejected"), 1):
            with self.subTest(state=state):
                cache.clear()
                submitted = data(n)
                Account.objects.create(school_id=f"owner{n}", email=submitted["email"], request_status=state)
                submitted["email"] = "  " + submitted["email"].upper() + "  "
                with patch("apps.accounts.registration_staging.send_mail") as sender:
                    self.assert_conflict(self.post(payload=submitted))
                sender.assert_not_called()
                self.assertFalse(StudentRegistrationStage.objects.exists())
                self.assertFalse(UserProfile.objects.exists())

    def test_existing_staff_id_has_identical_generic_conflict_without_mail(self):
        Account.objects.create(school_id=data()["school_id"], email="other@example.edu")
        with patch("apps.accounts.registration_staging.send_mail") as sender:
            self.assert_conflict(self.post())
        sender.assert_not_called()

    def test_changed_conflicting_details_use_student_feedback_and_preserve_original_resume(self):
        self.start()
        original = StudentRegistrationStage.objects.get().encrypted_payload
        Account.objects.create(school_id="owner", email="used@example.edu")
        response = self.post(payload={**data(), "email": "used@example.edu", "first_name": "Changed"})
        self.assert_conflict(response)
        self.assertEqual(StudentRegistrationStage.objects.get().encrypted_payload, original)
        response = self.post()
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(response.json()["status"], "existing_verification")
        self.assertNotIn("email", response.json())
        self.assertEqual(_decrypt(StudentRegistrationStage.objects.get())["email"], data()["email"])
        self.assertNotIn("error", response.json())
        self.assertEqual(StudentRegistrationStage.objects.get().encrypted_payload, original)
        self.assertEqual(len(mail.outbox), 1)

    def test_another_browser_cannot_resume_cancel_or_reserve_the_same_id_or_email(self):
        self.start()
        other, csrf = self.browser()
        for submitted in ({**data(), "email": "new@example.edu"}, {**data(), "school_id": "5000002"}):
            self.assert_conflict(self.post(payload=submitted, client=other, csrf=csrf))
        self.assertEqual(other.get("/api/v1/auth/register/verification/?requested_role=Instructor").status_code, 410)
        self.assertEqual(self.post("cancel/", {}, client=other, csrf=csrf).status_code, 410)
        self.assertEqual(StudentRegistrationStage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_final_conflict_uses_same_sentence_even_after_prior_delivery(self):
        code = self.start()
        Account.objects.create(school_id="owner", email=data()["email"])
        self.assert_conflict(self.verify(code))
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(UserProfile.objects.exists())
        self.assertFalse(StudentRegistrationStage.objects.exists())

    def test_wrong_code_reports_remaining_attempts_then_refuses_until_cancel_or_expiry(self):
        code = self.start()
        wrong = "000000" if code != "000000" else "999999"
        for remaining in (4, 3, 2, 1, 0):
            response = self.verify(wrong)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["attempts_remaining"], remaining)
        self.assertEqual(response.json()["error"]["code"], "attempts_exhausted")
        self.assertGreater(response.json()["expires_in"], 0)
        self.assertEqual(self.verify(code).status_code, 400)
        self.assertEqual(self.post("resend/", {}).json()["error"]["code"], "attempts_exhausted")
        self.assertEqual(self.post("cancel/", {}).status_code, 200)
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertFalse(Account.objects.exists())

    def test_expired_code_resends_on_same_stage_without_extending_deadline(self):
        old = self.start()
        stage = StudentRegistrationStage.objects.get()
        deadline = stage.expires_at
        StudentRegistrationStage.objects.update(otp_expires_at=timezone.now() - timedelta(seconds=1), last_sent_at=timezone.now() - timedelta(seconds=61))
        response = self.verify(old)
        self.assertEqual(response.json()["error"]["code"], "otp_expired")
        self.assertNotIn("otp_expires_in", response.json())
        self.assertEqual(self.post("resend/", {}).status_code, 202)
        stage.refresh_from_db()
        self.assertEqual(stage.expires_at, deadline)
        self.assertNotEqual(last_code(), old)
        self.assertEqual(self.verify(old).json()["error"]["code"], "otp_invalid")
        self.assertEqual(self.verify(last_code()).status_code, 200)

    def test_resend_cooldown_and_limit_do_not_reset_attempts(self):
        code = self.start()
        self.verify("000000" if code != "000000" else "999999")
        self.assertEqual(self.post("resend/", {}).status_code, 429)
        for _ in range(3):
            StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
            self.assertEqual(self.post("resend/", {}).status_code, 202)
        stage = StudentRegistrationStage.objects.get()
        self.assertEqual(stage.attempt_count, 1)
        self.assertEqual(self.post("resend/", {}).json()["error"]["code"], "resends_exhausted")

    def test_delivery_failure_keeps_owned_stage_and_invalidates_uncertain_code(self):
        with patch("apps.accounts.registration_staging.send_mail", side_effect=RuntimeError("private transport detail")):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "delivery_failed")
        self.assertFalse(response.json()["delivery_sent"])
        self.assertIn(COOKIE, response.cookies)
        self.assertEqual(StudentRegistrationStage.objects.get().otp_digest, "")
        self.assertFalse(Account.objects.exists())
        self.assertNotIn("private transport detail", response.content.decode())
        StudentRegistrationStage.objects.update(last_sent_at=timezone.now() - timedelta(seconds=61))
        self.assertEqual(self.post("resend/", {}).status_code, 202)

    def test_expired_stage_and_cleanup_never_create_or_delete_accounts(self):
        self.start()
        owner = Account.objects.create(school_id="owner", email="owner@example.edu")
        StudentRegistrationStage.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/v1/auth/register/verification/?requested_role=Instructor").status_code, 410)
        self.assertEqual(purge_expired_stages(), 1)
        self.assertTrue(Account.objects.filter(pk=owner.pk).exists())
        self.assertFalse(UserProfile.objects.exists())

    def test_student_only_fields_are_rejected_clearly_and_not_stored(self):
        for field in ("course", "year_level", "section"):
            response = self.post(payload={**data(), field: "not accepted"})
            self.assertEqual(response.status_code, 400, response.content)
            self.assertEqual(response.json()["error"]["fields"]["non_field_errors"], [INSTRUCTOR_SCHOOL_FIELDS_ERROR])
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertFalse(Account.objects.exists())

    def test_staff_id_validation_uses_staff_label(self):
        response = self.post(payload={**data(), "school_id": "bad-id"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["fields"]["school_id"], ["CTU-G ID must contain 1 to 7 digits only."])

    def test_identity_registration_limits_apply_to_id_and_email(self):
        Account.objects.create(school_id=data()["school_id"], email=data()["email"])
        for same in ("id", "email"):
            cache.clear()
            for n in range(5):
                submitted = {**data(), **({"email": f"other{n}@example.edu"} if same == "id" else {"school_id": f"600000{n}"})}
                self.assert_conflict(self.post(payload=submitted))
            self.assertEqual(self.post().status_code, 429)
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_owned_status_is_identity_and_ip_rate_limited(self):
        self.start()
        for _ in range(30):
            self.assertEqual(self.client.get("/api/v1/auth/register/verification/?requested_role=Instructor").status_code, 202)
        self.assertEqual(self.client.get("/api/v1/auth/register/verification/?requested_role=Instructor").status_code, 429)

    def test_shared_error_envelope_excludes_retired_instructor_action_configuration(self):
        Account.objects.create(school_id=data()["school_id"], email=data()["email"])
        for enabled, contact in ((False, ""), (True, "support@example.edu"), (False, "https://support.example.edu/help"), (False, "javascript:alert(1)"), (False, "https://user:private-key@example.edu")):
            with self.subTest(enabled=enabled, contact=contact), override_settings(WORKSPACE_PASSWORD_RESET_ENABLED=enabled, WORKSPACE_REGISTRATION_SUPPORT_CONTACT=contact):
                cache.clear()
                response = self.post()
                self.assert_conflict(response)
                self.assertFalse(set(response.json()) & {"requested_role", "password_reset_enabled", "support_contact", "can_continue", "email", "otp_expires_in"})
                if contact:
                    self.assertNotIn(contact, response.content.decode())
                self.assertEqual(settings.WORKSPACE_PASSWORD_RESET_ENABLED, enabled)

    def test_failure_rolls_back_account_profile_and_verified_stage(self):
        code = self.start()
        with patch("apps.accounts.registration_staging.UserProfile.objects.create", side_effect=RuntimeError("private internal detail")):
            response = self.verify(code)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Account.objects.exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertIsNone(StudentRegistrationStage.objects.get().email_verified_at)
        self.assertNotIn("private internal detail", response.content.decode())

    def test_csrf_and_protected_writer_are_not_bypassed(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post("/api/v1/auth/register/", data(), format="json").status_code, 403)
        with override_settings(WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER=True), CaptureQueriesContext(connection) as queries:
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(queries), 0)
        self.assertFalse(StudentRegistrationStage.objects.exists())

    def test_legacy_student_stage_cannot_be_reinterpreted_as_instructor(self):
        self.post(payload=student_data())
        original = StudentRegistrationStage.objects.get().encrypted_payload
        response = self.post()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "existing_verification")
        self.assertEqual(response.json()["requested_role"], "Student")
        self.assertEqual(StudentRegistrationStage.objects.get().encrypted_payload, original)
        status = self.client.get("/api/v1/auth/register/verification/?requested_role=Instructor")
        self.assertEqual(status.json()["requested_role"], "Student")
        self.assertEqual(self.verify(last_code()).status_code, 200)
        self.assertEqual(Account.objects.get().requested_role.role_name, "Student")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ConcurrentInstructorOTPTests(TransactionTestCase):
    def test_concurrent_otp_verification_creates_exactly_one_instructor_pair(self):
        cache.clear()
        Role.objects.create(role_name="Instructor")
        owner = APIClient(enforce_csrf_checks=True)
        csrf = owner.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = owner.post("/api/v1/auth/register/", data(), format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 202, response.content)
        token, code = owner.cookies[COOKIE].value, last_code()
        barrier = Barrier(2, timeout=20)

        def verify():
            try:
                client = APIClient(enforce_csrf_checks=True)
                csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                client.cookies[COOKIE] = token
                barrier.wait()
                return client.post("/api/v1/auth/register/verify/?requested_role=Instructor", {"code": code}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(verify), pool.submit(verify)]
            self.assertCountEqual([future.result(timeout=30) for future in futures], [200, 410])
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertIsNotNone(Account.objects.get().email_verified_at)
        self.assertFalse(AccountRole.objects.exists())
