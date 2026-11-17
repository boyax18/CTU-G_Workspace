"""WF-01.01/WF-01.02 audit corrections (owner-approved 16 Nov 2026).

R-02: verification mail is sent only after the staging write commits, and a
      failed send invalidates only that same code.
R-03: per-identity budgets apply to Student as well as Instructor.
R-04: the cookie-bound status endpoint is IP-throttled for both roles before
      any database work.
OD-3: success summaries carry the configured code lifetime for guidance.

Runs exclusively in the guarded disposable MySQL database.
"""
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.access_control.models import Role
from .models import Account, StudentRegistrationStage
from .registration_staging import begin_student_registration, begin_instructor_registration, student_verification_action

if settings.SETTINGS_MODULE != "config.test_settings" or not settings.REGISTRATION_TEST_DATABASE.startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Audit-correction tests require the disposable MySQL runner.")

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def data(n=1, role="Student"):
    return {"school_id": f"80000{n}", "email": f"audit{n}@example.edu", "first_name": "Ana",
            "middle_name": "", "last_name": "Reyes", "suffix": "", "requested_role": role,
            "password": "Copper!River7392", "password_confirmation": "Copper!River7392"}


def _committed_digest(stage_id):
    """Read through a separate connection, which sees only committed rows."""
    other = connection.copy()
    try:
        with other.cursor() as cursor:
            cursor.execute("SELECT otp_digest FROM student_registration_staging WHERE id=%s", [stage_id])
            row = cursor.fetchone()
            return row[0] if row else None
    finally:
        other.close()


@override_settings(EMAIL_BACKEND=LOCMEM)
class MailAfterCommitTests(TransactionTestCase):
    """TransactionTestCase: no wrapping test transaction, so commits are real."""

    def setUp(self):
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()

    def _recording_sender(self, seen):
        def sender(*args, **kwargs):
            stage = StudentRegistrationStage.objects.get()
            seen.append({
                "in_atomic_block": connection.in_atomic_block,
                "committed_digest": _committed_digest(stage.pk),
            })
            return 1
        return sender

    def test_initial_send_happens_after_the_stage_commits_for_both_roles(self):
        for role, begin in (("Student", begin_student_registration), ("Instructor", begin_instructor_registration)):
            with self.subTest(role=role):
                StudentRegistrationStage.objects.all().delete()
                seen = []
                with patch("apps.accounts.registration_staging.send_mail", side_effect=self._recording_sender(seen)):
                    result = begin(data(1 if role == "Student" else 2, role))
                self.assertEqual(result["status"], "verification_required")
                self.assertEqual(len(seen), 1)
                self.assertFalse(seen[0]["in_atomic_block"], "mail must not be sent inside a transaction")
                self.assertTrue(seen[0]["committed_digest"], "stage and code digest must be committed before sending")

    def test_resend_happens_after_the_new_digest_commits(self):
        result = begin_student_registration(data())
        stage = StudentRegistrationStage.objects.get()
        StudentRegistrationStage.objects.filter(pk=stage.pk).update(last_sent_at=stage.last_sent_at.replace(year=2000))
        before = StudentRegistrationStage.objects.get().otp_digest
        seen = []
        with patch("apps.accounts.registration_staging.send_mail", side_effect=self._recording_sender(seen)):
            resent = student_verification_action(result["browser_token"], "resend")
        self.assertEqual(resent["status"], "verification_required")
        self.assertFalse(seen[0]["in_atomic_block"])
        self.assertNotEqual(seen[0]["committed_digest"], before)
        self.assertEqual(StudentRegistrationStage.objects.get().resend_count, 1)

    def test_failed_send_invalidates_its_own_code_and_retains_the_stage(self):
        with patch("apps.accounts.registration_staging.send_mail", side_effect=RuntimeError("private transport")):
            result = begin_student_registration(data())
        self.assertEqual(result["status"], "delivery_failed")
        self.assertIn("browser_token", result)
        stage = StudentRegistrationStage.objects.get()
        self.assertEqual(stage.otp_digest, "")
        self.assertIsNone(stage.otp_expires_at)
        self.assertFalse(Account.objects.exists())

    def test_failed_send_never_clears_a_newer_code(self):
        # Simulates a concurrent resend committing a different digest while the
        # first message is still being handed to SMTP.
        def newer_code_then_fail(*args, **kwargs):
            StudentRegistrationStage.objects.update(otp_digest="f" * 64)
            raise RuntimeError("private transport")

        with patch("apps.accounts.registration_staging.send_mail", side_effect=newer_code_then_fail):
            result = begin_student_registration(data())
        self.assertEqual(result["status"], "delivery_failed")
        self.assertEqual(StudentRegistrationStage.objects.get().otp_digest, "f" * 64)


@override_settings(EMAIL_BACKEND=LOCMEM)
class StatusThrottleTests(TestCase):
    def setUp(self):
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()
        self.client = APIClient()

    def test_status_is_ip_throttled_for_both_roles_before_any_lookup(self):
        for query in ("", "?requested_role=Instructor"):
            with self.subTest(query=query or "Student"):
                cache.clear()
                for _ in range(30):
                    self.assertEqual(self.client.get("/api/v1/auth/register/verification/" + query).status_code, 410)
                with patch("apps.accounts.student_registration_api.student_verification_status") as lookup:
                    response = self.client.get("/api/v1/auth/register/verification/" + query)
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response.json()["error"]["code"], "throttled")
                lookup.assert_not_called()


@override_settings(EMAIL_BACKEND=LOCMEM)
class StudentIdentityLimitTests(TestCase):
    def setUp(self):
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()

    def submit(self, payload, ip):
        client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR=ip)
        csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        return client.post("/api/v1/auth/register/", payload, format="json", HTTP_X_CSRFTOKEN=csrf, REMOTE_ADDR=ip)

    def test_student_identity_budget_applies_across_ip_addresses(self):
        statuses = [self.submit(data(), f"10.0.0.{n}").status_code for n in range(1, 7)]
        # First attempt stages; other browsers get the generic conflict; the
        # sixth attempt for the same identity in a minute is refused.
        self.assertEqual(statuses[0], 202)
        self.assertEqual(statuses[1:5], [409] * 4)
        self.assertEqual(statuses[5], 429)
        self.assertEqual(len(mail.outbox), 1)

    def test_identity_budget_is_shared_across_roles(self):
        for n in range(1, 6):
            self.submit(data(), f"10.0.1.{n}")
        response = self.submit({**data(), "requested_role": "Instructor"}, "10.0.1.9")
        self.assertEqual(response.status_code, 429)

    def test_student_otp_actions_use_identity_budget(self):
        # Service-level calls bypass the per-IP view throttles, isolating the
        # per-identity OTP budget (30/min) that now also applies to Student.
        from rest_framework.exceptions import Throttled
        token = begin_student_registration(data())["browser_token"]
        statuses = [student_verification_action(token, "verify", "000000")["status"] for _ in range(30)]
        self.assertEqual(statuses[4], "attempts_exhausted")
        with self.assertRaises(Throttled):
            student_verification_action(token, "verify", "000000")
        self.assertFalse(Account.objects.exists())


@override_settings(EMAIL_BACKEND=LOCMEM, STUDENT_REGISTRATION_OTP_SECONDS=300)
class CodeLifetimeGuidanceTests(TestCase):
    def setUp(self):
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()

    def test_success_summaries_expose_the_configured_code_lifetime(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        response = client.post("/api/v1/auth/register/", data(), format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.json()["code_valid_seconds"], 300)
        status = client.get("/api/v1/auth/register/verification/")
        self.assertEqual(status.json()["code_valid_seconds"], 300)

    def test_error_envelopes_do_not_gain_the_field(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        client.post("/api/v1/auth/register/", data(), format="json", HTTP_X_CSRFTOKEN=csrf)
        wrong = client.post("/api/v1/auth/register/verify/", {"code": "000000"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(wrong.status_code, 400)
        self.assertNotIn("code_valid_seconds", wrong.json())
