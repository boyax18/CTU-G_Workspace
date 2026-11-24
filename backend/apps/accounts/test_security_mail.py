"""Durable security mail + signed-in email verification (24 Nov 2026). Isolated MySQL, locmem mail."""

import re
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access_control.models import AccessAuditLog, AccountRole, Role
from . import password_reset, recovery_mail
from .models import Account
from .security_mail_models import AccountEmailVerification, SecurityMailOutbox
from .rejection_test_support import fresh_test_key

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use config.test_settings and a disposable MySQL database.")

EMAIL, PASSWORD = "learner@example.edu", "Old!Password543"
SETTINGS = dict(WORKSPACE_PASSWORD_RESET_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")


def make_account(role, school_id, email, *, proof=True):
    account = Account.objects.create_user(school_id=school_id, email=email, password=PASSWORD)
    Account.objects.filter(pk=account.pk).update(is_active=True, request_status="Approved")
    if proof:
        Account.objects.filter(pk=account.pk).update(email_verified_at=timezone.now(), email_verified_address=email)
    AccountRole.objects.create(account=account, role=role)
    return Account.objects.get(pk=account.pk)


def reset_codes():
    return [m.group(1) for msg in mail.outbox for m in [re.search(r"reset code is (\d{6})\.", msg.body)] if m]


def verification_codes():
    return [m.group(1) for msg in mail.outbox for m in [re.search(r"verification code is (\d{6})\.", msg.body)] if m]


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Role.objects.create(role_name="Student")

    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        key = mock.patch.dict("os.environ", {"WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()})
        key.start()
        self.addCleanup(key.stop)
        self.clock = int(timezone.now().timestamp())
        clock = mock.patch.object(password_reset, "_now", side_effect=lambda: self.clock)
        clock.start()
        self.addCleanup(clock.stop)

    def post(self, client, path, data=None):
        token = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        with self.captureOnCommitCallbacks(execute=True):
            return client.post(path, data or {}, format="json", HTTP_X_CSRFTOKEN=token)

    def make_due(self):
        SecurityMailOutbox.objects.filter(status="Retry").update(next_attempt_at=timezone.now() - timedelta(seconds=1))


@override_settings(**SETTINGS)
class DurableResetMailTests(_Base):
    def setUp(self):
        super().setUp()
        self.account = make_account(self.role, "0099001", EMAIL)
        self.client = APIClient(enforce_csrf_checks=True)

    def request(self):
        return self.post(self.client, "/api/v1/auth/forgot-password/", {"email": EMAIL})

    def test_code_is_sealed_at_rest_and_never_logged(self):
        with mock.patch.object(recovery_mail, "kick"), self.assertLogs("ctug.email", level="INFO") as logs:
            self.assertEqual(self.request().status_code, 202)
        row = SecurityMailOutbox.objects.get()
        self.assertEqual((row.kind, row.status), ("reset_code", "Pending"))
        self.assertIsNotNone(row.encrypted_secret)
        recovery_mail.process_due()
        code = reset_codes()[0]
        self.assertNotIn(code.encode(), bytes(row.encrypted_secret))
        self.assertNotIn(code, " ".join(logs.output))
        row.refresh_from_db()
        self.assertEqual(row.status, "Accepted")
        self.assertIsNone(row.encrypted_secret)  # erased on the terminal state
        self.assertTrue(row.message_id.startswith("<"))
        self.assertEqual(mail.outbox[0].extra_headers.get("Message-ID"), row.message_id)

    def test_temporary_smtp_failure_retries_then_recovers(self):
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=OSError("smtp down")):
            self.request()
        row = SecurityMailOutbox.objects.get()
        self.assertEqual((row.status, row.attempt_count, row.last_failure_code), ("Retry", 1, "OSError"))
        self.assertEqual(recovery_mail.process_due(), {}, "not due before the backoff")
        self.make_due()
        self.assertEqual(recovery_mail.process_due(), {"accepted": 1})
        row.refresh_from_db()
        self.assertEqual((row.status, row.attempt_count), ("Accepted", 2))
        self.assertEqual(len(reset_codes()), 1)

    def test_pending_rows_survive_a_restart(self):
        with mock.patch.object(recovery_mail, "kick"):  # process stops before any attempt
            self.request()
        self.assertEqual(SecurityMailOutbox.objects.get().status, "Pending")
        self.assertEqual(mail.outbox, [])
        self.assertEqual(recovery_mail.process_due(), {"accepted": 1})  # a later worker/kick delivers it

    def test_superseded_code_is_never_delivered(self):
        with mock.patch.object(recovery_mail, "kick"):
            self.request()
            self.clock += 61  # resend interval passed: a NEW code replaces the first one
            self.request()
        self.assertEqual(recovery_mail.process_due(), {"superseded": 1, "accepted": 1})
        first, second = SecurityMailOutbox.objects.order_by("outbox_id")
        self.assertEqual((first.status, second.status), ("Superseded", "Accepted"))
        self.assertIsNone(first.encrypted_secret)
        self.assertEqual(len(reset_codes()), 1)
        verify = self.post(self.client, "/api/v1/auth/forgot-password/verify/", {"email": EMAIL, "code": reset_codes()[0]})
        self.assertEqual(verify.status_code, 200, "the delivered code is the current one")

    def test_expired_code_is_never_delivered(self):
        with mock.patch.object(recovery_mail, "kick"):
            self.request()
        self.clock += 601
        self.assertEqual(recovery_mail.process_due(), {"expired": 1})
        self.assertEqual(mail.outbox, [])

    def test_retry_limit_dead_letters_and_erases(self):
        account = self.account
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=OSError("down")):
            recovery_mail.queue("password_changed", account)
            for _ in range(recovery_mail.MAX_ATTEMPTS):
                self.make_due()
                recovery_mail.process_due()
        row = SecurityMailOutbox.objects.get()
        self.assertEqual((row.status, row.attempt_count), ("Dead", recovery_mail.MAX_ATTEMPTS))
        self.assertIsNotNone(row.secret_erased_at)

    def test_permanent_refusal_is_dead_immediately(self):
        import smtplib
        refused = smtplib.SMTPRecipientsRefused({EMAIL: (550, b"no such user")})
        with mock.patch("apps.accounts.recovery_mail.send_mail", side_effect=refused):
            self.request()
        self.assertEqual(SecurityMailOutbox.objects.get().status, "Dead")

    def test_leased_row_cannot_be_sent_twice(self):
        with mock.patch.object(recovery_mail, "kick"):
            self.request()
        claimed = recovery_mail._claim()
        self.assertEqual(claimed.status, "Leased")
        self.assertEqual(recovery_mail.process_one(), "empty", "a live lease blocks a second worker")
        stale = SecurityMailOutbox.objects.get()
        stale.lease_token = "not-the-current-lease"
        self.assertEqual(recovery_mail._finish(stale, status="Accepted"), "lost_lease")
        self.assertEqual(mail.outbox, [])

    def test_ineligible_request_stays_neutral_and_queues_nothing(self):
        Account.objects.filter(pk=self.account.pk).update(email_verified_at=None, email_verified_address=None)
        with self.assertLogs("ctug.email", level="INFO") as logs:
            self.assertEqual(self.request().status_code, 202)
        self.assertFalse(SecurityMailOutbox.objects.exists())
        text = " ".join(logs.output)
        self.assertIn("event=account_ineligible", text)
        self.assertIn("code=email_unverified", text)  # server-log reason only; the response is unchanged
        self.assertNotIn(EMAIL, text)
        with self.assertLogs("ctug.email", level="INFO") as logs:
            response = self.post(self.client, "/api/v1/auth/forgot-password/", {"email": "nobody@example.edu"})
        self.assertEqual(response.status_code, 202)
        self.assertIn("code=no_account", " ".join(logs.output))


@override_settings(**SETTINGS)
class LegacyEmailVerificationTests(_Base):
    ROOT = "/api/v1/auth/email-verification/"

    def setUp(self):
        super().setUp()
        self.legacy = make_account(self.role, "0099100", "legacy@example.edu", proof=False)
        self.other = make_account(self.role, "0099200", "other@example.edu", proof=False)
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.legacy)
        self.before = Account.objects.values("password", "request_status", "is_active", "school_id").get(pk=self.legacy.pk)

    def test_unauthenticated_callers_are_refused(self):
        anonymous = APIClient(enforce_csrf_checks=True)
        self.assertEqual(anonymous.get(self.ROOT).status_code, 401)
        self.assertEqual(self.post(anonymous, self.ROOT + "request/").status_code, 401)

    def test_verification_records_proof_only_after_the_correct_code(self):
        self.assertEqual(self.client.get(self.ROOT).json(), {"email": "legacy@example.edu", "email_verified": False})
        self.assertEqual(self.post(self.client, self.ROOT + "request/").status_code, 202)
        self.assertEqual(mail.outbox[0].to, ["legacy@example.edu"])
        code = verification_codes()[0]
        wrong = "000000" if code != "000000" else "111111"
        self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": wrong}).status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.legacy.pk).email_verified_at)
        self.assertFalse(password_reset.eligible_account_queryset().filter(pk=self.legacy.pk).exists())
        self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": code}).status_code, 200)
        account = Account.objects.get(pk=self.legacy.pk)
        self.assertIsNotNone(account.email_verified_at)
        self.assertEqual(account.email_verified_address, "legacy@example.edu")
        self.assertEqual(Account.objects.values("password", "request_status", "is_active", "school_id")
                         .get(pk=self.legacy.pk), self.before)
        self.assertEqual(list(AccountRole.objects.filter(account=account).values_list("role_id", flat=True)), [self.role.pk])
        audit = AccessAuditLog.objects.get(action="account.email.verified")
        self.assertEqual((audit.actor_account_id, audit.target_account_id), (account.pk, account.pk))
        self.assertEqual((audit.old_value, audit.new_value), (None, None))  # no address, code or digest
        self.assertTrue(password_reset.eligible_account_queryset().filter(pk=account.pk).exists(),
                        "password recovery becomes available under the unchanged D-21 rule")
        self.assertEqual(self.post(self.client, self.ROOT + "request/").status_code, 409)

    def test_wrong_codes_lock_the_challenge(self):
        self.post(self.client, self.ROOT + "request/")
        code = verification_codes()[0]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.post(self.client, self.ROOT + "confirm/", {"code": wrong})
        self.assertTrue(AccountEmailVerification.objects.get(account=self.legacy).locked)
        self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": code}).status_code, 400)
        self.assertEqual(self.post(self.client, self.ROOT + "request/").status_code, 429)

    def test_resend_interval_and_superseded_code(self):
        self.post(self.client, self.ROOT + "request/")
        self.assertEqual(self.post(self.client, self.ROOT + "request/").status_code, 429)
        first = verification_codes()[0]
        challenge = AccountEmailVerification.objects.get(account=self.legacy)
        AccountEmailVerification.objects.filter(pk=challenge.pk).update(issued_at=challenge.issued_at - 61)
        self.assertEqual(self.post(self.client, self.ROOT + "request/").status_code, 202)
        second = verification_codes()[-1]
        if first != second:
            self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": first}).status_code, 400)
        self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": second}).status_code, 200)

    def test_another_account_cannot_use_this_code_and_email_change_invalidates_it(self):
        self.post(self.client, self.ROOT + "request/")
        code = verification_codes()[0]
        intruder = APIClient(enforce_csrf_checks=True)
        intruder.force_login(self.other)
        self.assertEqual(self.post(intruder, self.ROOT + "confirm/", {"code": code}).status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.other.pk).email_verified_at)
        Account.objects.filter(pk=self.legacy.pk).update(email="changed@example.edu")
        self.assertEqual(self.post(self.client, self.ROOT + "confirm/", {"code": code}).status_code, 400)
        self.assertIsNone(Account.objects.get(pk=self.legacy.pk).email_verified_at)

    def test_queued_verification_code_is_superseded_after_verification(self):
        with mock.patch.object(recovery_mail, "kick"):
            self.post(self.client, self.ROOT + "request/")
        Account.objects.filter(pk=self.legacy.pk).update(email_verified_at=timezone.now(),
                                                         email_verified_address="legacy@example.edu")
        self.assertEqual(recovery_mail.process_due(), {"superseded": 1})
        self.assertEqual(mail.outbox, [])


class WatchWorkerSecurityBatchTests(TestCase):
    def test_missing_security_table_warns_once_and_does_not_stop_the_watcher(self):
        from io import StringIO
        from django.db import DatabaseError
        from .management.commands.process_registration_outbox import Command
        command = Command(stdout=StringIO())
        with mock.patch.object(recovery_mail, "process_due", side_effect=DatabaseError("no table")):
            self.assertEqual(command._security_batch(5), {})
            self.assertEqual(command._security_batch(5), {})
        self.assertEqual(command.stdout._out.getvalue().count("Security mail unavailable"), 1)
        with mock.patch.object(recovery_mail, "process_due", return_value={"accepted": 1}):
            self.assertEqual(command._security_batch(5), {"accepted": 1})
