"""WF-02.04 D-57: recipient erasure at terminal outbox states, worker and executor trigger.

Run: python manage.py test apps.accounts.test_wf0204_outbox_erasure --settings=config.test_settings --noinput
Owner-authorized 18 Nov 2026 (protected outbox_worker.py and executor/schema.py). Disposable MySQL and
the locmem backend only. The live-trigger tests install ONLY the generated outbox UPDATE trigger in
the disposable test database, with the test user standing in for the notifications principal.
"""

import smtplib
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from apps.access_control.executor.schema import grants, statements
from apps.access_control.models import AccessAuditLog

from .models import Account
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import MAX_ATTEMPTS, RECIPIENT_FIELDS, _claim_next, _finish, _now, process_one
from .rejection_test_support import fresh_test_key
from .registration_outbox import record_registration_decision_outbox

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.04 erasure tests require --settings=config.test_settings.")

SETTINGS = dict(
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
TRIGGER = "wex_registration_notification_outbox_update"


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing erasure fixtures on an unexpected database.")


class JobMixin:
    def start(self):
        verify_database()
        self.env = patch.dict("os.environ", {"WORKSPACE_OUTBOX_WORKER_ENABLED": "1",
                                             "WORKSPACE_OUTBOX_KEK_V1_B64": fresh_test_key()})
        self.env.start()
        self.addCleanup(self.env.stop)
        mail.outbox = []
        self.serial = 0
        self.actor = Account.objects.create(school_id="ERASE-ADMIN", request_status="Approved", is_active=True)

    def job(self, email="recipient@example.edu"):
        self.serial += 1
        target = Account.objects.create(school_id=f"ERASE-{self.serial}", email=f"t{self.serial}@example.edu",
                                        request_status="Approved", is_active=True)
        with transaction.atomic():
            audit = AccessAuditLog.objects.create(
                actor_account=self.actor, target_account=target, action="account.registration.approve",
                old_value={"request_status": "Pending"}, new_value={"request_status": "Approved"},
            )
            pk = record_registration_decision_outbox(audit_log_id=audit.pk, target_account_id=target.pk,
                                                     approved=True, recipient_email=email)
        return RegistrationNotificationOutbox.objects.get(pk=pk)

    def assert_erased(self, row, status):
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, status)
        for field in RECIPIENT_FIELDS:
            self.assertIsNone(getattr(row, field), field)
        self.assertIsNotNone(row.recipient_erased_at)
        self.assertIsNone(row.lease_token)

    def assert_recipient_kept(self, row):
        row.refresh_from_db()
        for field in RECIPIENT_FIELDS:
            self.assertIsNotNone(getattr(row, field), field)
        self.assertIsNone(row.recipient_erased_at)


@override_settings(**SETTINGS)
class RecipientErasureWorkerTests(JobMixin, TestCase):
    def setUp(self):
        self.start()

    def test_delivery_erases_the_recipient_and_keeps_non_sensitive_metadata(self):
        row = self.job()
        audit_before = AccessAuditLog.objects.values().get(pk=row.decision_audit_log_id)
        self.assertEqual(process_one(), "delivered")
        self.assertEqual(mail.outbox[0].to, ["recipient@example.edu"])
        self.assert_erased(row, "Delivered")
        self.assertEqual(row.attempt_count, 1)
        self.assertIsNotNone(row.delivered_at)
        self.assertIsNone(row.last_failure_code)
        self.assertEqual((row.template_code, row.template_version), ("registration.approved", 1))
        self.assertEqual(AccessAuditLog.objects.values().get(pk=row.decision_audit_log_id), audit_before)
        self.assertEqual(process_one(), "empty")  # an erased, delivered row is never sent again
        self.assertEqual(len(mail.outbox), 1)

    def test_pending_leased_and_retry_rows_keep_the_recipient(self):
        row = self.job()
        self.assert_recipient_kept(row)  # Pending
        claim = _claim_next()
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Leased")
        self.assert_recipient_kept(row)  # actively processed
        self.assertEqual(_finish(claim, failure_code="smtp_unavailable"), "retry")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Retry")
        self.assert_recipient_kept(row)

    def test_repeated_failures_erase_only_when_the_last_retry_is_used(self):
        row = self.job()
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=OSError("mail down")):
            for attempt in range(1, MAX_ATTEMPTS + 1):
                RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(next_attempt_at=_now())
                outcome = process_one()
                if attempt < MAX_ATTEMPTS:
                    self.assertEqual(outcome, "retry", attempt)
                    self.assert_recipient_kept(row)
        self.assertEqual(outcome, "dead")
        self.assert_erased(row, "Dead")
        self.assertEqual((row.attempt_count, row.last_failure_code), (MAX_ATTEMPTS, "mail_backend_unavailable"))
        self.assertEqual(len(mail.outbox), 0)

    def test_permanent_refusal_is_terminal_dead_and_erased(self):
        row = self.job()
        refused = smtplib.SMTPRecipientsRefused({"recipient@example.edu": (550, b"no")})
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=refused):
            self.assertEqual(process_one(), "dead")
        self.assert_erased(row, "Dead")
        self.assertEqual((row.attempt_count, row.last_failure_code), (1, "recipient_rejected"))

    def test_exhausted_expired_lease_becomes_dead_and_erased(self):
        row = self.job()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(
            delivery_status="Leased", attempt_count=MAX_ATTEMPTS, lease_token="x" * 43,
            lease_expires_at=_now() - timedelta(seconds=1))
        self.assertEqual(process_one(), "dead")
        self.assert_erased(row, "Dead")
        self.assertEqual(row.last_failure_code, "attempts_exhausted")

    def test_a_stale_worker_cannot_finish_or_erase(self):
        row = self.job()
        claim = _claim_next()
        RegistrationNotificationOutbox.objects.filter(pk=row.pk).update(lease_expires_at=_now() - timedelta(seconds=1))
        self.assertEqual(_finish(claim), "lost_lease")
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "Leased")
        self.assert_recipient_kept(row)

    def test_no_reopening_path_exists_for_terminal_rows(self):
        delivered, dead = self.job(), self.job()
        self.assertEqual(process_one(), "delivered")
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=smtplib.SMTPRecipientsRefused({})):
            self.assertEqual(process_one(), "dead")
        self.assertEqual(process_one(), "empty")
        for row, status in ((delivered, "Delivered"), (dead, "Dead")):
            self.assert_erased(row, status)


@override_settings(**SETTINGS)
class RecipientErasureConcurrencyTests(JobMixin, TransactionTestCase):
    def setUp(self):
        self.start()

    def tearDown(self):
        connections.close_all()

    def test_two_workers_deliver_and_erase_exactly_once(self):
        row = self.job()
        barrier = threading.Barrier(2)

        def work():
            try:
                verify_database()
                barrier.wait(timeout=10)
                return process_one()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(f.result(timeout=30) for f in [pool.submit(work), pool.submit(work)])
        self.assertEqual(results, ["delivered", "empty"])
        self.assertEqual(len(mail.outbox), 1)
        self.assert_erased(row, "Delivered")
        self.assertEqual(row.attempt_count, 1)


@override_settings(**SETTINGS)
class ExecutorOutboxTriggerTests(JobMixin, TransactionTestCase):
    """The generated executor trigger, installed for real, with this test user as notifications."""

    def setUp(self):
        self.start()
        self.row = self.job()
        with connection.cursor() as cursor:
            cursor.execute("SELECT SUBSTRING_INDEX(USER(),'@',1)")
            user = cursor.fetchone()[0]
        sql = [s for s in statements(notifications=user) if s.startswith(f"CREATE TRIGGER {TRIGGER} ")]
        self.assertEqual(len(sql), 1)
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")
            cursor.execute(sql[0])
        self.addCleanup(self.drop)

    def drop(self):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")

    def update(self, assignments, params=()):
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE registration_notification_outbox SET {assignments} WHERE outbox_id=%s",
                           [*params, self.row.pk])

    ERASE = ("encrypted_recipient=NULL, recipient_nonce=NULL, wrapped_data_key=NULL, "
             "encryption_key_version=NULL, recipient_erased_at=NOW()")

    def lease(self):
        self.update("delivery_status='Leased', lease_token=%s, lease_expires_at=NOW() + INTERVAL 1 MINUTE", ["t" * 43])

    def assert_refused(self, assignments, params=()):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                self.update(assignments, params)

    def test_status_only_updates_are_still_allowed(self):
        self.lease()
        self.update("delivery_status='Retry', lease_token=NULL, lease_expires_at=NULL, attempt_count=1")
        self.assert_recipient_kept(self.row)

    def test_terminal_erasure_from_a_lease_is_allowed(self):
        for status in ("Delivered", "Dead"):
            with self.subTest(status=status):
                RegistrationNotificationOutbox.objects.filter(pk=self.row.pk).delete()
                self.row = self.job()
                self.lease()
                self.update(f"delivery_status='{status}', lease_token=NULL, " + self.ERASE)
                self.assert_erased(self.row, status)

    def test_erasure_outside_a_terminal_transition_is_refused(self):
        self.assert_refused("delivery_status='Delivered', " + self.ERASE)  # from Pending, not a lease
        self.lease()
        self.assert_refused("delivery_status='Retry', " + self.ERASE)
        self.assert_refused(self.ERASE)  # still Leased
        self.assert_refused("delivery_status='Delivered', recipient_erased_at=NOW()")  # nothing erased
        self.assert_refused("delivery_status='Delivered', encrypted_recipient=NULL, recipient_nonce=NULL, "
                            "wrapped_data_key=NULL, encryption_key_version=NULL")  # no erased_at
        self.assert_refused("delivery_status='Delivered', encrypted_recipient=NULL, wrapped_data_key=NULL, "
                            "encryption_key_version=NULL, recipient_erased_at=NOW()")  # nonce kept
        self.assert_refused("encrypted_recipient=%s", [b"forged"])
        self.assert_refused("encryption_key_version='v9'")
        self.assert_recipient_kept(self.row)

    def test_immutable_evidence_and_erased_rows_cannot_be_reopened(self):
        self.assert_refused("template_code='registration.rejected'")
        self.assert_refused("decision_audit_log_id=decision_audit_log_id + 1")
        self.lease()
        self.update("delivery_status='Delivered', lease_token=NULL, " + self.ERASE)
        self.assert_refused("delivery_status='Pending'")
        self.assert_refused("delivery_status='Retry', next_attempt_at=NOW()")
        self.assert_refused("recipient_erased_at=NULL")
        self.assert_erased(self.row, "Delivered")

    def test_the_real_worker_delivers_and_erases_under_the_trigger(self):
        self.assertEqual(process_one(), "delivered")
        self.assert_erased(self.row, "Delivered")
        with patch("apps.accounts.outbox_worker.send_mail", side_effect=smtplib.SMTPRecipientsRefused({})):
            second = self.job()
            self.assertEqual(process_one(), "dead")
        self.assert_erased(second, "Dead")


class ExecutorOutboxGrantTests(TestCase):
    def test_notifications_principal_gets_only_the_erasure_columns_added(self):
        lines = [g for g in grants("ctug", "wex_runtime", "wex_ordinary", "wex_protected", "wex_recovery")
                 if "registration_notification_outbox" in g and "wex_notifications" in g]
        updates = [g for g in lines if g.startswith("GRANT UPDATE(")]
        self.assertEqual(len(updates), 1)
        columns = set(updates[0][len("GRANT UPDATE("):updates[0].index(")")].split(","))
        self.assertEqual(columns, {
            "delivery_status", "attempt_count", "next_attempt_at", "lease_expires_at", "lease_token",
            "last_failure_code", "updated_at", "delivered_at",
            "encrypted_recipient", "recipient_nonce", "wrapped_data_key", "encryption_key_version", "recipient_erased_at",
        })
        self.assertNotIn("outbox_id", columns)
        self.assertNotIn("decision_audit_log_id", columns)
        self.assertFalse(any("DELETE" in g or "INSERT" in g for g in lines))
        self.assertFalse(any(" ALL " in g or "GRANT OPTION" in g for g in grants("ctug", "a", "b", "c", "d")))
