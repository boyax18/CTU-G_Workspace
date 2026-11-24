"""Local development email delivery (24 Nov 2026): watch-mode watermark, dev links, opt-in.

Isolated MySQL only (config.test_settings); every message goes to Django's locmem backend.
"""

import base64
import io
import os
import secrets
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import TestCase, override_settings

from apps.access_control.models import AccessAuditLog
from .models import Account
from .outbox_models import RegistrationNotificationOutbox
from .outbox_worker import due_job_count, newest_outbox_id, process_due
from .registration_email_templates import _public_url
from .registration_outbox import record_registration_decision_outbox

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Use config.test_settings and a disposable MySQL database.")


@override_settings(
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
)
class WatchModeWatermarkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            assert cursor.fetchone()[0] == settings.REGISTRATION_TEST_DATABASE
        cls.actor = Account.objects.create(school_id="LE-ADMIN", request_status="Approved", is_active=True)

    def setUp(self):
        flags = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_WORKER_ENABLED": "1",
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        flags.start()
        self.addCleanup(flags.stop)
        self.serial = 0
        mail.outbox = []

    def make_job(self, *, approved=True):
        self.serial += 1
        email = f"applicant{self.serial}@example.edu"
        target = Account.objects.create(school_id=f"LE-{self.serial}", email=email,
                                        request_status="Approved" if approved else "Rejected", is_active=approved)
        with transaction.atomic():
            audit = AccessAuditLog.objects.create(
                actor_account=self.actor, target_account=target,
                action="account.registration.approve" if approved else "account.registration.reject",
                old_value={"request_status": "Pending"}, new_value={"request_status": target.request_status})
            record_registration_decision_outbox(audit_log_id=audit.pk, target_account_id=target.pk,
                                                approved=approved, recipient_email=email)
        return RegistrationNotificationOutbox.objects.get(decision_audit_log=audit)

    def test_watermark_skips_earlier_rows_and_delivers_only_new_ones_individually(self):
        earlier = self.make_job()
        watermark = newest_outbox_id()
        new_rows = [self.make_job(), self.make_job(approved=False), self.make_job()]
        self.assertEqual(due_job_count(after_id=watermark), 3)
        result = process_due(limit=25, after_id=watermark)
        self.assertEqual(result["delivered"], 3)
        earlier.refresh_from_db()
        self.assertEqual(earlier.delivery_status, "Pending", "an earlier queued row is never sent by watch mode")
        self.assertEqual(earlier.attempt_count, 0)
        # One message per decision, each to its own recipient only (never a combined email).
        self.assertEqual(sorted(tuple(m.to) for m in mail.outbox),
                         sorted((f"applicant{n}@example.edu",) for n in (2, 3, 4)))
        for row in new_rows:
            row.refresh_from_db()
            self.assertEqual(row.delivery_status, "Delivered")
            self.assertIsNone(row.encrypted_recipient)  # D-57 erasure on terminal state
        # A deliberate one-off delivery still handles the earlier row.
        self.assertEqual(process_due(limit=25)["delivered"], 1)
        earlier.refresh_from_db()
        self.assertEqual(earlier.delivery_status, "Delivered")

    def test_watch_refuses_to_start_when_a_gate_is_off(self):
        self.make_job()
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_WORKER_ENABLED": "0"}):
            with self.assertRaises(CommandError):
                call_command("process_registration_outbox", "--deliver", "--watch", "5", stdout=io.StringIO())
        self.assertEqual(len(mail.outbox), 0)
        with self.assertRaises(CommandError):
            call_command("process_registration_outbox", "--deliver", "--watch", "2", stdout=io.StringIO())

    def test_watch_announces_held_back_rows_and_sends_nothing_old(self):
        self.make_job()
        output = io.StringIO()
        with patch("apps.accounts.management.commands.process_registration_outbox.time.sleep",
                   side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                call_command("process_registration_outbox", "--deliver", "--watch", "5", stdout=output)
        self.assertIn("1 earlier queued notification(s) are left for a manual --deliver", output.getvalue())
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("@", output.getvalue())  # aggregate output only, no addresses


class DevelopmentLinkTests(TestCase):
    smtp = "django.core.mail.backends.smtp.EmailBackend"

    def test_loopback_http_link_needs_explicit_allowance_debug_and_local_profile(self):
        with override_settings(EMAIL_BACKEND=self.smtp, WORKSPACE_PUBLIC_BASE_URL="http://localhost:5173",
                               WORKSPACE_EMAIL_PUBLIC_HOSTS=frozenset()):
            with self.assertRaises(ValueError):
                _public_url("/")
            with override_settings(WORKSPACE_EMAIL_DEV_LINKS_ALLOWED=True, DEBUG=True,
                                   WORKSPACE_DEPLOYMENT_PROFILE="local"):
                self.assertEqual(_public_url("/register"), "http://localhost:5173/register")
                with override_settings(DEBUG=False):
                    self.assertRaises(ValueError, _public_url, "/")
                with override_settings(WORKSPACE_DEPLOYMENT_PROFILE="production"):
                    self.assertRaises(ValueError, _public_url, "/")

    def test_allowance_never_permits_lan_or_public_http_links(self):
        for base in ("http://192.168.1.5:5173", "http://example.com", "http://localhost:5173/x?y=1"):
            with self.subTest(base=base), override_settings(
                EMAIL_BACKEND=self.smtp, WORKSPACE_PUBLIC_BASE_URL=base, WORKSPACE_EMAIL_DEV_LINKS_ALLOWED=True,
                DEBUG=True, WORKSPACE_DEPLOYMENT_PROFILE="local", WORKSPACE_EMAIL_PUBLIC_HOSTS=frozenset()):
                self.assertRaises(ValueError, _public_url, "/")
