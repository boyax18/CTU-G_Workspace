"""AR-6C5B.5: isolated MySQL worker tests. NEVER run with development DB."""

import base64
import io
import os
import secrets
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection, transaction
from django.test import TestCase, override_settings

from apps.access_control.models import AccessAuditLog
from .models import Account
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import (
    OutboxWorkerUnavailable, _claim_next, _finish, _now,
    due_job_count, process_due, process_one,
)
from .registration_outbox import record_registration_decision_outbox

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Outbox worker tests require --settings=config.test_settings.")


@override_settings(
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
)
class RegistrationOutboxWorkerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected test database.")
        cls.actor = Account.objects.create(
            school_id="WK-ADMIN", request_status="Approved", is_active=True,
        )

    def setUp(self):
        self.flags = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_WORKER_ENABLED": "1",
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.flags.start()
        self.addCleanup(self.flags.stop)
        self.serial = 0
        mail.outbox = []

    def make_job(self, *, approved=True, email="recipient@example.edu"):
        self.serial += 1
        target = Account.objects.create(
            school_id=f"WK-STUDENT-{self.serial}", email=email,
            request_status="Approved" if approved else "Rejected",
            is_active=approved,
        )
        action = "account.registration.approve" if approved else "account.registration.reject"
        with transaction.atomic():
            audit = AccessAuditLog.objects.create(
                actor_account=self.actor, target_account=target,
                action=action, old_value={"request_status": "Pending"},
                new_value={"request_status": target.request_status},
            )
            record_registration_decision_outbox(
                audit_log_id=audit.pk, target_account_id=target.pk,
                approved=approved, recipient_email=email,
            )
        return RegistrationNotificationOutbox.objects.get(decision_audit_log=audit)

    def test_delivery_is_disabled_by_default_without_explicit_gate(self):
        row = self.make_job()
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_WORKER_ENABLED": "0"}):
            with self.assertRaises(OutboxWorkerUnavailable):
                process_one()
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Pending")
        self.assertEqual(row.attempt_count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_writer_gate_must_also_be_enabled(self):
        self.make_job()
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False):
            with self.assertRaises(OutboxWorkerUnavailable):
                process_one()

    def test_smtp_requires_separate_approval(self):
        self.make_job()
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            WORKSPACE_EMAIL_SMTP_ENABLED=True,
        ):
            with self.assertRaises(OutboxWorkerUnavailable):
                process_one()

    def test_console_requires_privacy_acknowledgement(self):
        self.make_job()
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
            with self.assertRaises(OutboxWorkerUnavailable):
                process_one()

    def test_read_only_management_preview_does_not_need_worker_gate(self):
        self.make_job()
        output = io.StringIO()
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_WORKER_ENABLED": "0"}):
            call_command("process_registration_outbox", stdout=output)
        self.assertIn("READ-ONLY: 1 due jobs", output.getvalue())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(RegistrationNotificationOutbox.objects.get().attempt_count, 0)

    def test_one_approved_mail_marks_delivered(self):
        row = self.make_job()
        self.assertEqual(due_job_count(), 1)
        self.assertEqual(process_one(), "delivered")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Delivered")
        self.assertEqual(row.attempt_count, 1)
        self.assertIsNotNone(row.delivered_at)
        self.assertIsNone(row.lease_token)
        self.assertIsNone(row.next_attempt_at)
        self.assertEqual(mail.outbox[0].to, ["recipient@example.edu"])
        self.assertIn("approved", mail.outbox[0].subject.lower())
        self.assertEqual(process_one(), "empty")
        self.assertEqual(len(mail.outbox), 1)

    def test_rejected_template_uses_neutral_language(self):
        row = self.make_job(approved=False)
        self.assertEqual(process_one(), "delivered")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Delivered")
        self.assertIn("not approved", mail.outbox[0].subject.lower())
        self.assertNotIn("WK-STUDENT", mail.outbox[0].body)

    def test_temporary_mail_failure_is_retried_without_exposing_exception(self):
        row = self.make_job()
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("private SMTP detail")):
            self.assertEqual(process_one(), "retry")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Retry")
        self.assertEqual(row.attempt_count, 1)
        self.assertEqual(row.last_failure_code, "mail_backend_unavailable")
        self.assertNotIn("private", row.last_failure_code)
        self.assertGreater(row.next_attempt_at, _now())
        self.assertEqual(len(mail.outbox), 0)

    def test_retry_when_due_can_succeed(self):
        row = self.make_job()
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("mail down")):
            self.assertEqual(process_one(), "retry")
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(
            next_attempt_at=_now() - timedelta(seconds=1)
        )
        self.assertEqual(process_one(), "delivered")
        row.refresh_from_db()
        self.assertEqual(row.attempt_count, 2)
        self.assertEqual(row.delivery_status, "Delivered")
        self.assertEqual(len(mail.outbox), 1)

    def test_final_failed_attempt_becomes_dead(self):
        row = self.make_job()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(
            delivery_status="Retry", attempt_count=4,
            next_attempt_at=_now() - timedelta(seconds=1),
        )
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("mail down")):
            self.assertEqual(process_one(), "dead")
        row.refresh_from_db()
        self.assertEqual(row.attempt_count, 5)
        self.assertEqual(row.delivery_status, "Dead")
        self.assertIsNone(row.next_attempt_at)

    def test_expired_lease_can_be_reclaimed(self):
        row = self.make_job()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(
            delivery_status="Leased", attempt_count=1,
            lease_token="expired-token",
            lease_expires_at=_now() - timedelta(seconds=1),
            next_attempt_at=None,
        )
        self.assertEqual(process_one(), "delivered")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Delivered")
        self.assertEqual(row.attempt_count, 2)
        self.assertEqual(len(mail.outbox), 1)

    def test_stale_worker_cannot_overwrite_current_lease(self):
        row = self.make_job()
        claim = _claim_next()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(lease_token="new-worker")
        self.assertEqual(_finish(claim), "lost_lease")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Leased")
        self.assertEqual(row.lease_token, "new-worker")

    def test_expired_final_attempt_is_dead_without_sending(self):
        row = self.make_job()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(
            delivery_status="Leased", attempt_count=5,
            lease_token="abandoned", lease_expires_at=_now() - timedelta(seconds=1),
            next_attempt_at=None,
        )
        self.assertEqual(process_one(), "dead")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Dead")
        self.assertEqual(row.last_failure_code, "attempts_exhausted")
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_decryption_key_retries_without_sending(self):
        row = self.make_job()
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": ""}):
            self.assertEqual(process_one(), "retry")
        row.refresh_from_db()
        self.assertEqual(row.last_failure_code, "crypto_unavailable")
        self.assertEqual(len(mail.outbox), 0)

    def test_unsupported_template_dead_letters_without_sending(self):
        row = self.make_job()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(template_code="registration.unknown")
        self.assertEqual(process_one(), "dead")
        row.refresh_from_db()
        self.assertEqual(row.last_failure_code, "unsupported_template")
        self.assertEqual(len(mail.outbox), 0)

    def test_bounded_batch_and_management_command(self):
        self.make_job()
        output = io.StringIO()
        call_command("process_registration_outbox", "--deliver", "--limit", "1", stdout=output)
        self.assertIn("delivered=1", output.getvalue())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(process_due(limit=1)["delivered"], 0)
        with self.assertRaises(ValueError):
            process_due(limit=101)
