"""Public error/correlation/privacy contract; guarded disposable MySQL only."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.test import APIClient, APIRequestFactory

from apps.access_control.models import AccountRole, Role
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from .api_errors import ERRORS, FIELDS
from .models import Account, StudentRegistrationStage, UserProfile
from .test_student_registration_otp import data, last_code
from .views import PublicJSONView

if settings.SETTINGS_MODULE != "config.test_settings":
    raise ImproperlyConfigured("Public API error checks require disposable MySQL settings.")

PRIVATE = "private-password-otp-654321-cookie-key-recipient@example.edu"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PublicErrorContractTests(TestCase):
    def setUp(self):
        Role.objects.create(role_name="Student")
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def post(self, suffix="", body=None, **headers):
        return self.client.post("/api/v1/auth/register/" + suffix, data() if body is None else body,
                                format="json", HTTP_X_CSRFTOKEN=self.csrf, **headers)

    def assert_error(self, response, code):
        self.assertEqual(response.status_code, ERRORS[code][0], response.content)
        body = response.json()
        error = body["error"]
        self.assertEqual(error["code"], code)
        self.assertEqual(error["message"], ERRORS[code][1])
        self.assertRegex(error["request_id"], r"\A[a-f0-9]{32}\Z")
        self.assertEqual(error["request_id"], response["X-Request-ID"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertLessEqual(set(error), {"code", "message", "request_id", "fields", "retry_after"})
        self.assertLessEqual(set(body), {"error", "status", "expires_in", "retry_after", "attempts_remaining", "resends_remaining", "delivery_sent"})
        self.assertNotIn(PRIVATE, json.dumps(body))
        return error

    def start(self):
        self.assertEqual(self.post().status_code, 202)
        return last_code()

    def test_unrelated_profile_duplicate_key_is_safe_503_for_both_registration_roles(self):
        Role.objects.get_or_create(role_name="Instructor")
        for n, role in enumerate(("Student", "Instructor"), 1):
            with self.subTest(role=role):
                client = APIClient(enforce_csrf_checks=True)
                csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                submitted = {**data(n), "requested_role": role}
                started = client.post("/api/v1/auth/register/", submitted, format="json", HTTP_X_CSRFTOKEN=csrf)
                self.assertEqual(started.status_code, 202, started.content)
                code = last_code()
                with patch("apps.accounts.registration_staging.UserProfile.objects.create", side_effect=IntegrityError(1062, PRIVATE)):
                    response = client.post("/api/v1/auth/register/verify/", {"code": code}, format="json", HTTP_X_CSRFTOKEN=csrf)
                self.assert_error(response, "registration_unavailable")
                self.assertFalse(Account.objects.exists())
                self.assertFalse(UserProfile.objects.exists())
                self.assertFalse(AccountRole.objects.exists())
                self.assertFalse(StudentRegistrationStage.objects.filter(email_verified_at__isnull=False).exists())

    def test_validation_fields_are_safe_and_correlated(self):
        body = data()
        body.update(email=PRIVATE, password=PRIVATE, password_confirmation="different")
        error = self.assert_error(self.post(body=body), "validation_error")
        self.assertLessEqual(set(error["fields"]), set(FIELDS))
        self.assertNotIn(PRIVATE, str(error))

    def test_malformed_json_and_media_negotiation(self):
        response = self.client.post("/api/v1/auth/register/", '{"password":', content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assert_error(response, "validation_error")
        self.assert_error(self.client.get("/api/v1/auth/register/"), "method_not_allowed")
        self.assert_error(self.client.get("/api/v1/auth/csrf/", HTTP_ACCEPT="text/html"), "not_acceptable")
        self.assert_error(self.client.post("/api/v1/auth/register/", data(), HTTP_X_CSRFTOKEN=self.csrf), "unsupported_media_type")

    def test_csrf_refusal_is_correlated_before_staging(self):
        self.assert_error(self.client.post("/api/v1/auth/register/", data(), format="json"), "csrf_failed")
        self.assertFalse(StudentRegistrationStage.objects.exists())
        self.assertFalse(Account.objects.exists())

    def test_incoming_request_reference_is_not_reflected(self):
        incoming = "f" * 32
        error = self.assert_error(self.post(body={}, HTTP_X_REQUEST_ID=incoming), "validation_error")
        self.assertNotEqual(error["request_id"], incoming)

    def test_missing_tampered_and_expired_cookie_remain_410(self):
        self.assert_error(self.client.get("/api/v1/auth/register/verification/"), "expired")
        self.client.cookies["ctug_student_registration"] = PRIVATE
        self.assert_error(self.client.get("/api/v1/auth/register/verification/"), "expired")
        self.start()
        StudentRegistrationStage.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assert_error(self.post("verify/", {"code": "123456"}), "expired")

    def test_conflicts_are_generic_before_and_after_otp(self):
        code = self.start()
        Account.objects.create(school_id=data()["school_id"], email="unrelated@example.edu")
        after = self.assert_error(self.post("verify/", {"code": code}), "conflict")
        before = self.assert_error(self.post(), "conflict")
        self.assertEqual(after["message"], before["message"])
        self.assertNotIn("fields", after)
        self.assertNotIn("fields", before)

    def test_wrong_code_expired_code_and_exhaustion_contracts(self):
        code = self.start()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(4):
            error = self.assert_error(self.post("verify/", {"code": wrong}), "otp_invalid")
            self.assertNotIn(code, str(error))
        self.assert_error(self.post("verify/", {"code": wrong}), "attempts_exhausted")
        self.assertFalse(Account.objects.exists())
        self.post("cancel/", {})
        self.start()
        StudentRegistrationStage.objects.update(otp_expires_at=timezone.now() - timedelta(seconds=1))
        self.assert_error(self.post("verify/", {"code": "123456"}), "otp_expired")

    def test_resend_and_framework_throttles_keep_retry_hints(self):
        self.start()
        response = self.post("resend/", {})
        error = self.assert_error(response, "resend_cooldown")
        self.assertTrue(1 <= error["retry_after"] <= 60)
        self.assertEqual(response["Retry-After"], str(error["retry_after"]))
        StudentRegistrationStage.objects.update(resend_count=3)
        self.assert_error(self.post("resend/", {}), "resends_exhausted")
        cache.clear()
        with patch("apps.accounts.views.RegistrationDailyThrottle.rate", "1/day"):
            self.assert_error(self.post(body={}), "validation_error")
            response = self.post(body={})
            error = self.assert_error(response, "throttled")
            self.assertIn("retry_after", error)
            self.assertEqual(response["Retry-After"], str(error["retry_after"]))

    def test_mail_failures_are_not_success_and_are_logged_without_exception_text(self):
        with patch("apps.accounts.registration_staging.send_mail", side_effect=RuntimeError(PRIVATE)), self.assertLogs("apps.accounts.views", level="ERROR") as captured:
            response = self.post()
        error = self.assert_error(response, "delivery_failed")
        self.assertFalse(response.json()["delivery_sent"])
        self.assertFalse(Account.objects.exists())
        self.assertEqual(captured.records[0].request_id, error["request_id"])
        self.assertNotIn(PRIVATE, str(captured.records[0].__dict__))
        self.assertIsNone(captured.records[0].exc_info)
        self.assertIsNone(captured.records[0].stack_info)

    def test_writer_boundary_mapping_never_queries_database(self):
        with patch("apps.accounts.student_registration_api.student_verification_status", side_effect=WriterBoundaryUnavailable(PRIVATE)), self.assertNumQueries(0):
            self.assert_error(self.client.get("/api/v1/auth/register/verification/"), "registration_unavailable")

    def test_unexpected_error_is_safe_and_structurally_logged(self):
        with patch("apps.accounts.views.register_account", side_effect=RuntimeError(PRIVATE)), self.assertLogs("apps.accounts.views", level="ERROR") as captured:
            response = self.post()
        error = self.assert_error(response, "registration_unavailable")
        record = captured.records[0]
        self.assertEqual(json.loads(record.getMessage())["event"], "public_api_error")
        self.assertEqual(record.request_id, error["request_id"])
        self.assertEqual(record.http_status, 503)
        self.assertEqual(record.failure_kind, "unexpected")
        self.assertNotIn(PRIVATE, str(record.__dict__))

    def test_unknown_service_state_never_becomes_200(self):
        with patch("apps.accounts.student_registration_api.student_verification_status", return_value={"status": "surprise", "password": PRIVATE}):
            self.assert_error(self.client.get("/api/v1/auth/register/verification/"), "registration_unavailable")

    def test_api_exceptions_and_unsafe_validation_detail_are_sanitized(self):
        class Probe(PublicJSONView):
            failure = None

            def get(self, request):
                raise self.failure

        class ServerFailure(exceptions.APIException):
            status_code = 500

        factory = APIRequestFactory()
        for failure, code in ((ServerFailure(PRIVATE), "server_error"),
                              (exceptions.ValidationError({"password": [PRIVATE], "encryption_key": [PRIVATE]}), "validation_error")):
            response = Probe.as_view(failure=failure)(factory.get("/probe/"))
            response.render()
            body = json.loads(response.content)
            self.assertEqual(response.status_code, ERRORS[code][0])
            self.assertEqual(body["error"]["message"], ERRORS[code][1])
            self.assertNotIn(PRIVATE, str(body))
            self.assertNotIn("encryption_key", str(body))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PublicErrorConcurrencyTests(TransactionTestCase):
    def test_concurrent_verification_has_one_success_one_correlated_410(self):
        Role.objects.create(role_name="Student")
        cache.clear()
        original = APIClient(enforce_csrf_checks=True)
        csrf = original.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.assertEqual(original.post("/api/v1/auth/register/", data(), format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 202)
        code = last_code()
        barrier = Barrier(2, timeout=20)

        def verify():
            try:
                client = APIClient(enforce_csrf_checks=True)
                for name, morsel in original.cookies.items():
                    client.cookies[name] = morsel.value
                barrier.wait()
                response = client.post("/api/v1/auth/register/verify/", {"code": code}, format="json", HTTP_X_CSRFTOKEN=csrf)
                return response.status_code, response.json(), response["X-Request-ID"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(verify), pool.submit(verify)]]
        self.assertCountEqual([r[0] for r in results], [200, 410])
        self.assertNotEqual(results[0][2], results[1][2])
        expired = next(r for r in results if r[0] == 410)
        self.assertEqual(expired[1]["error"]["request_id"], expired[2])
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertFalse(AccountRole.objects.exists())
