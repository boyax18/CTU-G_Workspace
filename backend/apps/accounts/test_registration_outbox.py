"""AR-6C5B.4 MySQL-only transactional outbox tests; never use development DB."""

import base64
import os
import secrets
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings

from apps.access_control.models import AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service
from .models import Account
from .outbox_crypto import OutboxCryptoUnavailable, decrypt_recipient
from .outbox_models import RegistrationNotificationOutbox
from .registration_review import (
    RegistrationReviewDenied, approve_registration, reject_registration,
)

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Outbox tests require --settings=config.test_settings.")


@override_settings(
    WORKSPACE_REGISTRATION_APPROVAL_ENABLED=True,
    WORKSPACE_REGISTRATION_OUTBOX_ENABLED=True,
    WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=True,
    WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION="v1",
)
class RegistrationOutboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Unexpected test database.")
        accounts = Service.objects.create(service_code="accounts", service_name="Accounts")
        Service.objects.create(service_code="access_control", service_name="Access Control")
        approve_perm = Permission.objects.create(
            service=accounts, permission_code="accounts.registration_requests.approve",
            permission_name="Approve registrations", module_name="registration_requests", action_name="approve",
        )
        reject_perm = Permission.objects.create(
            service=accounts, permission_code="accounts.registration_requests.reject",
            permission_name="Reject registrations", module_name="registration_requests", action_name="reject",
        )
        cls.student_role = Role.objects.create(role_name="Student")
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.reviewer = Account.objects.create(
            school_id="OUTBOX-ADMIN", request_status="Approved", is_active=True,
        )
        AccountRole.objects.create(account=cls.reviewer, role=cls.admin_role)
        RolePermission.objects.create(role=cls.admin_role, permission=approve_perm)
        RolePermission.objects.create(role=cls.admin_role, permission=reject_perm)

    def setUp(self):
        self.email = "recipient@example.edu"
        self.target = Account.objects.create_user(
            school_id="OUTBOX-STUDENT", email=self.email,
            password="Strong!Enrollment6283", requested_role=self.student_role,
        )
        # Random test-only key never written to Git or a database.
        self.key_env = patch.dict(os.environ, {
            "WORKSPACE_OUTBOX_KEK_V1_B64": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
        })
        self.key_env.start()
        self.addCleanup(self.key_env.stop)

    def _email(self, row):
        return decrypt_recipient(
            encrypted_recipient=row.encrypted_recipient,
            recipient_nonce=row.recipient_nonce,
            wrapped_data_key=row.wrapped_data_key,
            encryption_key_version=row.encryption_key_version,
            audit_log_id=row.decision_audit_log_id,
            template_code=row.template_code,
            template_version=row.template_version,
        )

    def test_approval_atomically_stores_encrypted_pending_event(self):
        with patch("apps.accounts.registration_review.schedule_registration_decision_email_after_commit") as legacy:
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        legacy.assert_not_called()
        row = RegistrationNotificationOutbox.objects.get()
        audit = AccessAuditLog.objects.get()
        self.assertEqual(row.decision_audit_log_id, audit.pk)
        self.assertEqual(row.template_code, "registration.approved")
        self.assertEqual(row.delivery_status, "Pending")
        self.assertEqual(row.attempt_count, 0)
        self.assertIsNotNone(row.next_attempt_at)
        self.assertEqual(self._email(row), self.email)
        self.assertNotIn(self.email.encode(), bytes(row.encrypted_recipient))
        self.assertEqual(AccountRole.objects.filter(account=self.target).count(), 1)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertEqual(self.target.request_status, "Approved")

    def test_rejection_stores_pending_event_and_preserves_inactive_account(self):
        reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="identity_mismatch")
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual(row.template_code, "registration.rejected")
        self.assertEqual(self._email(row), self.email)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.target.request_status, "Rejected")
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.reject")

    def test_missing_email_is_a_dead_record_without_ciphertext(self):
        self.target.email = None
        self.target.save(update_fields=["email"])
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual(row.delivery_status, "Dead")
        self.assertEqual(row.last_failure_code, "recipient_unavailable")
        self.assertIsNone(row.encrypted_recipient)
        self.assertIsNone(row.recipient_nonce)
        self.assertIsNone(row.wrapped_data_key)
        self.assertIsNone(row.next_attempt_at)

    def test_invalid_historical_email_is_dead(self):
        self.target.email = "not-an-address"
        self.target.save(update_fields=["email"])
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(RegistrationNotificationOutbox.objects.get().delivery_status, "Dead")

    def test_tampered_associated_data_cannot_decrypt(self):
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        row = RegistrationNotificationOutbox.objects.get()
        with self.assertRaises(OutboxCryptoUnavailable):
            decrypt_recipient(
                encrypted_recipient=row.encrypted_recipient,
                recipient_nonce=row.recipient_nonce,
                wrapped_data_key=row.wrapped_data_key,
                encryption_key_version=row.encryption_key_version,
                audit_log_id=row.decision_audit_log_id,
                template_code="registration.rejected",
            )
        with self.assertRaises(OutboxCryptoUnavailable):
            decrypt_recipient(
                encrypted_recipient=b"x" + bytes(row.encrypted_recipient)[1:],
                recipient_nonce=row.recipient_nonce,
                wrapped_data_key=row.wrapped_data_key,
                encryption_key_version=row.encryption_key_version,
                audit_log_id=row.decision_audit_log_id,
                template_code=row.template_code,
            )

    def test_missing_key_fails_closed_and_rolls_back_decision(self):
        with patch.dict(os.environ, {"WORKSPACE_OUTBOX_KEK_V1_B64": ""}):
            with self.assertRaises(OutboxCryptoUnavailable):
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_outbox_insert_error_rolls_back_status_role_and_audit(self):
        with patch("apps.accounts.registration_review.record_registration_decision_outbox", side_effect=RuntimeError("outbox unavailable")):
            with self.assertRaises(RuntimeError):
                approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_receipt_failure_rolls_back_without_outbox(self):
        with patch("apps.accounts.registration_review.record_access_audit_receipt", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_second_review_is_refused_without_duplicate_audit_or_outbox(self):
        approve_registration(actor=self.reviewer, target_id=self.target.pk)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 1)

    def test_outbox_disabled_keeps_original_no_outbox_behavior(self):
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
                               WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=False):
            approve_registration(actor=self.reviewer, target_id=self.target.pk)
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertEqual(AccessAuditLog.objects.count(), 1)
