"""Delivery evidence (25 Nov 2026): provider reply per message, receipt proof, one-message trace.

Isolated MySQL and locmem/fake SMTP only: nothing here opens a network connection.
"""

import re
import smtplib
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.access_control.models import Role
from . import email_design, recovery_mail
from .security_mail_models import SecurityMailOutbox
from .test_security_mail import SETTINGS, _Base, make_account, reset_codes, verification_codes

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use config.test_settings and a disposable MySQL database.")

GMAIL_REPLY = b"2.0.0 OK  1764036782 41be03b00d2f7-b5c4f2b8f6fsm1234567a12.12 - gsmtp"
SMTP = "django.core.mail.backends.smtp.EmailBackend"


class _FakeSMTP:
    """Stands in for an open, authenticated SMTP session; records nothing but the reply."""

    def __init__(self, reply=(250, GMAIL_REPLY)):
        self.reply, self.last_data_reply, self.sent = reply, None, []

    def sendmail(self, from_addr, to_addrs, msg):
        self.sent.append((from_addr, tuple(to_addrs)))
        self.last_data_reply = self.reply
        return {}


class ProviderReplyTests(SimpleTestCase):
    def test_smtp_reply_for_this_message_is_recorded_and_sanitized(self):
        backend = email_design.TracedSMTPBackend(host="127.0.0.1", port=2525)
        backend.connection = _FakeSMTP()  # already open: send_messages() will not connect
        sent = email_design.send_mail("Subject", "Body", "CTU-G <sender@example.edu>", ["to@example.edu"],
                                      html_message="<p>x</p>", connection=backend)
        self.assertEqual(sent, 1)
        self.assertEqual(email_design.last_smtp_reply(),
                         "250 2.0.0 OK 1764036782 41be03b00d2f7-b5c4f2b8f6fsm1234567a12.12 - gsmtp")
        self.assertEqual(backend.connection.sent, [("sender@example.edu", ("to@example.edu",))])

    def test_reply_is_reset_for_every_message(self):
        backend = email_design.TracedSMTPBackend(host="127.0.0.1", port=2525)
        backend.connection = _FakeSMTP()
        email_design.send_mail("S", "B", "s@example.edu", ["to@example.edu"], connection=backend)
        self.assertIsNotNone(email_design.last_smtp_reply())
        with self.assertRaises(smtplib.SMTPServerDisconnected):
            backend.connection.sendmail = mock.Mock(side_effect=smtplib.SMTPServerDisconnected())
            email_design.send_mail("S", "B", "s@example.edu", ["to@example.edu"], connection=backend)
        self.assertIsNone(email_design.last_smtp_reply(), "a failed send never inherits an earlier reply")

    def test_recording_smtp_keeps_the_data_reply(self):
        conn = email_design._RecordingSMTP()  # not connected
        with mock.patch.object(smtplib.SMTP, "data", return_value=(250, GMAIL_REPLY)):
            self.assertEqual(conn.data(b"msg"), (250, GMAIL_REPLY))
        self.assertEqual(conn.last_data_reply, (250, GMAIL_REPLY))

    def test_unexpected_reply_text_is_reduced_to_safe_characters(self):
        unsafe = b"OK <someone@example.edu> \x1b[31m queued as ABC123\r\n" + b"x" * 500
        safe = email_design._safe_reply(250, unsafe)
        self.assertNotIn("@", safe)
        self.assertNotIn("<", safe)
        self.assertNotIn("\x1b", safe)
        self.assertLessEqual(len(safe), 120)

    def test_backend_selection_keeps_the_approved_backend_string(self):
        with override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="127.0.0.1", EMAIL_PORT=2525):
            self.assertIsInstance(email_design.get_connection(timeout=5), email_design.TracedSMTPBackend)
            self.assertEqual(settings.EMAIL_BACKEND, SMTP, "the delivery gates still see the approved backend")
            with mock.patch.object(email_design.TracedSMTPBackend, "send_messages", return_value=1) as sender:
                self.assertEqual(email_design.send_mail("S", "B", None, ["to@example.edu"]), 1)
            self.assertEqual(sender.call_count, 1, "send_mail without a connection uses the traced backend")
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self.assertNotIsInstance(email_design.get_connection(), email_design.TracedSMTPBackend)

    def test_fail_silently_is_still_honoured(self):
        with override_settings(EMAIL_BACKEND=SMTP, EMAIL_HOST="127.0.0.1", EMAIL_PORT=2525):
            self.assertTrue(email_design.get_connection(fail_silently=True).fail_silently)
            # The connection itself fails; Django's own open() decides whether to raise.
            with mock.patch.object(email_design._RecordingSMTP, "__init__", side_effect=OSError("refused")):
                self.assertEqual(email_design.send_mail("S", "B", None, ["to@example.edu"], fail_silently=True), 0)
                with self.assertRaises(OSError):
                    email_design.send_mail("S", "B", None, ["to@example.edu"], fail_silently=False)


@override_settings(**SETTINGS)
class ReceiptProofTests(_Base):
    """recipient_confirmed is logged only when the code from that exact message is redeemed."""

    ROOT = "/api/v1/auth/email-verification/"

    def test_email_verification_redeem_confirms_receipt_of_that_message(self):
        legacy = make_account(self.role, "0099300", "legacy3@example.edu", proof=False)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(legacy)
        with self.assertLogs("ctug.email", level="INFO") as logs:
            self.assertEqual(self.post(client, self.ROOT + "request/").status_code, 202)
            code = verification_codes()[0]
            wrong = "000000" if code != "000000" else "111111"
            self.post(client, self.ROOT + "confirm/", {"code": wrong})
        self.assertNotIn("event=recipient_confirmed", " ".join(logs.output), "a wrong code proves nothing")
        row = SecurityMailOutbox.objects.get()
        with self.assertLogs("ctug.email", level="INFO") as logs:
            self.assertEqual(self.post(client, self.ROOT + "confirm/", {"code": code}).status_code, 200)
        text = " ".join(logs.output)
        self.assertIn(f"event=recipient_confirmed corr={row.correlation_id} flow=email_verification_code "
                      f"outbox={row.pk} status=code_redeemed_after_accepted", text)
        self.assertNotIn(code, text)
        self.assertNotIn("legacy3@example.edu", text)

    def test_password_reset_verify_confirms_receipt_and_response_is_unchanged(self):
        make_account(self.role, "0099301", "reset3@example.edu")
        client = APIClient(enforce_csrf_checks=True)
        self.post(client, "/api/v1/auth/forgot-password/", {"email": "reset3@example.edu"})
        row = SecurityMailOutbox.objects.get(kind="reset_code")
        with self.assertLogs("ctug.email", level="INFO") as logs:
            response = self.post(client, "/api/v1/auth/forgot-password/verify/",
                                 {"email": "reset3@example.edu", "code": reset_codes()[0]})
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"event=recipient_confirmed corr={row.correlation_id} flow=reset_code", " ".join(logs.output))

    def test_smtp_accepted_trace_carries_the_provider_reply(self):
        legacy = make_account(self.role, "0099302", "legacy4@example.edu", proof=False)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(legacy)
        with mock.patch.object(email_design, "last_smtp_reply", return_value="250 2.0.0 OK 1764 abc - gsmtp"), \
                self.assertLogs("ctug.email", level="INFO") as logs:
            self.post(client, self.ROOT + "request/")
        accepted = [line for line in logs.output if "event=smtp_accepted" in line]
        self.assertEqual(len(accepted), 1)
        self.assertIn("reply=250_2.0.0_OK_1764_abc_-_gsmtp", accepted[0])

    def test_confirm_receipt_never_breaks_verification(self):
        legacy = make_account(self.role, "0099303", "legacy5@example.edu", proof=False)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(legacy)
        self.post(client, self.ROOT + "request/")
        with mock.patch.object(SecurityMailOutbox.objects, "using", side_effect=RuntimeError("db hiccup")):
            response = self.post(client, self.ROOT + "confirm/", {"code": verification_codes()[0]})
        self.assertEqual(response.status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationReceiptTests(TestCase):
    def setUp(self):
        Role.objects.create(role_name="Student")
        Role.objects.create(role_name="Instructor")
        cache.clear()
        for name in ("RegistrationBurstThrottle", "RegistrationDailyThrottle"):
            patched = mock.patch("apps.accounts.views." + name + ".rate", "1000/min")
            patched.start()
            self.addCleanup(patched.stop)
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def _post(self, path, payload):
        return self.client.post("/api/v1/auth/" + path, payload, format="json", HTTP_X_CSRFTOKEN=self.csrf)

    def test_send_and_redeem_share_one_correlation_id(self):
        for role, query in (("Student", ""), ("Instructor", "?requested_role=Instructor")):
            with self.subTest(role=role):
                n = 1 if role == "Student" else 2
                payload = {"school_id": f"710000{n}", "email": f"applicant-ev{n}@example.edu", "first_name": "Ana",
                           "middle_name": "", "last_name": "Cruz", "suffix": "", "requested_role": role,
                           "password": "Copper!River7392", "password_confirmation": "Copper!River7392"}
                self.client = APIClient(enforce_csrf_checks=True)
                self.csrf = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
                with self.assertLogs("ctug.email", level="INFO") as sent:
                    response = self._post("register/", payload)
                self.assertEqual(response.status_code, 202, response.content)
                code = re.search(r"code is: ([0-9]{6})", mail.outbox[-1].body)[1]
                corr = re.search(r"event=smtp_accepted corr=([0-9a-f]{16})", " ".join(sent.output))[1]
                with self.assertLogs("ctug.email", level="INFO") as redeemed:
                    verified = self._post("register/verify/" + query, {"code": code})
                    self.assertEqual(verified.status_code, 200, verified.content)
                    self.assertEqual(verified.json()["status"], "completed")
                text = " ".join(redeemed.output)
                self.assertIn(f"event=recipient_confirmed corr={corr} flow=registration_otp_{role.lower()}", text)
                self.assertNotIn(code, text)


@override_settings(**SETTINGS)
class DeliveryReportTraceTests(_Base):
    def test_trace_shows_one_message_from_request_to_proven_receipt(self):
        legacy = make_account(self.role, "0099400", "legacy6@example.edu", proof=False)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(legacy)
        with self.assertLogs("ctug.email", level="INFO") as logs:
            self.post(client, "/api/v1/auth/email-verification/request/")
            self.post(client, "/api/v1/auth/email-verification/confirm/", {"code": verification_codes()[0]})
        row = SecurityMailOutbox.objects.get()
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "email-trace.log"
            # Same "[time] ctug.email message" layout the file handler writes.
            log.write_text("".join(f"[2026-11-25 10:00:00,000] ctug.email {line.split(':', 2)[2]}\n"
                                   for line in logs.output), encoding="utf-8")
            with override_settings(WORKSPACE_EMAIL_TRACE_LOG=str(log)):
                out = StringIO()
                call_command("email_delivery_report", "--trace", row.correlation_id, stdout=out)
                report = out.getvalue()
                summary = StringIO()
                call_command("email_delivery_report", stdout=summary)
        for event in ("request_accepted", "otp_created", "email_queued", "smtp_attempt", "smtp_accepted",
                      "recipient_unconfirmed", "recipient_confirmed"):
            self.assertIn(f"event={event} corr={row.correlation_id}", report)
        self.assertIn("receipt CONFIRMED (code redeemed)", report)
        self.assertIn("receipt CONFIRMED (code redeemed)", summary.getvalue())
        self.assertNotIn("legacy6@example.edu", report)

    def test_accepted_without_redeem_stays_unconfirmed_and_bad_ids_are_refused(self):
        legacy = make_account(self.role, "0099401", "legacy7@example.edu", proof=False)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(legacy)
        self.post(client, "/api/v1/auth/email-verification/request/")
        row = SecurityMailOutbox.objects.get()
        out = StringIO()
        call_command("email_delivery_report", "--trace", row.correlation_id, stdout=out)
        self.assertIn("SMTP accepted; receipt unconfirmed", out.getvalue())
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("email_delivery_report", "--trace", "../etc/passwd", stdout=StringIO())


class LocalTraceFileSettingTests(SimpleTestCase):
    def test_trace_file_lines_are_masked_and_code_free(self):
        """The file handler only receives what trace() emits: allow-listed, masked fields."""
        from .email_trace import trace
        with self.assertLogs("ctug.email", level="INFO") as logs:
            trace("smtp_accepted", "abcd1234abcd1234", flow="reset_code", outbox=1,
                  msgid="<1.ctug@example.edu>", reply="250 2.0.0 OK", to="pe***@example.edu", body="123456")
        self.assertNotIn("123456", logs.output[0], "unknown fields (e.g. a body) are never written")
