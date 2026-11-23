"""AR-6C5B.4 MySQL-only transactional outbox tests; never use development DB."""

import base64
import os
import secrets
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError, connection, transaction
from django.test import TestCase, override_settings

from apps.access_control.models import AccessAuditLog, AccountRole, Permission, Role, RolePermission, Service
from .models import Account, UserProfile
from .outbox_crypto import OutboxCryptoUnavailable, decrypt_recipient
from .outbox_models import RegistrationNotificationOutbox
from .registration_review import (
    RegistrationRejectionNotAllowed, RegistrationReviewDenied, RegistrationReviewUnavailable,
    approve_registration, reject_registration,
)
from .registration_outbox import RegistrationOutboxError, record_registration_decision_outbox

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Outbox tests require --settings=config.test_settings.")

# WF-02.03 (D-44/D-45): approval needs verified email ownership and the reviewer's attestation.
STUDENT_ATTESTATION = {"confirmed": True, "source": "ctu_main_system_records"}
INSTRUCTOR_ATTESTATION = {"confirmed": True, "source": "institutional_employment_records"}
APPROVAL_BODY = {"eligibility_confirmed": True, "eligibility_source": "ctu_main_system_records"}


def with_email_proof(account, email):
    """Record OTP proof for the account's current address, as WF-01.01/01.02 registration does."""
    from django.utils import timezone
    type(account).objects.filter(pk=account.pk).update(
        email=email, email_verified_at=timezone.now(), email_verified_address=email,
    )
    account.refresh_from_db()
    return account


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
        self.target = with_email_proof(Account.objects.create_user(
            school_id="OUTBOX-STUDENT", email=self.email,
            password="Strong!Enrollment6283", requested_role=self.student_role,
        ), self.email)
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
        approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
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

    @override_settings(WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True)  # WF-02.04 D-54 test correction
    def test_rejection_stores_pending_event_and_deletes_account(self):
        reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="identity_mismatch")
        row = RegistrationNotificationOutbox.objects.get()
        self.assertEqual(row.template_code, "registration.rejected")
        self.assertEqual(self._email(row), self.email)
        self.assertFalse(Account.objects.filter(pk=self.target.pk).exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertEqual(AccessAuditLog.objects.get().action, "account.registration.reject")

    def _writer_row(self, recipient_email):
        """The outbox writer's own disposition for an unusable address (no decision involved)."""
        audit = AccessAuditLog.objects.create(
            actor_account=self.reviewer, target_account=self.target, action="account.registration.approve",
            old_value={"request_status": "Pending"}, new_value={"request_status": "Approved"},
        )
        pk = record_registration_decision_outbox(audit_log_id=audit.pk, target_account_id=self.target.pk,
                                                 approved=True, recipient_email=recipient_email)
        return RegistrationNotificationOutbox.objects.get(pk=pk)

    def _assert_refused_unchanged(self):
        self.target.refresh_from_db()
        self.assertEqual((self.target.request_status, self.target.is_active), ("Pending", False))
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    @override_settings(WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True)
    def test_missing_email_is_a_dead_record_without_ciphertext(self):
        # WF-02.04 D-55 (revised, owner-approved rewrite): a rejection without a verified recipient is
        # refused with nothing written, so no decision creates a recipient-less row any more.
        self.target.email = None
        self.target.save(update_fields=["email"])
        with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
            reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.assertEqual(caught.exception.reason, "recipient_unverified")
        self._assert_refused_unchanged()
        # The writer's safe Dead disposition stays covered: no ciphertext, no plaintext, not due.
        row = self._writer_row(None)
        self.assertEqual(row.delivery_status, "Dead")
        self.assertEqual(row.last_failure_code, "recipient_unavailable")
        self.assertIsNone(row.encrypted_recipient)
        self.assertIsNone(row.recipient_nonce)
        self.assertIsNone(row.wrapped_data_key)
        self.assertIsNone(row.next_attempt_at)

    @override_settings(WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True)
    def test_invalid_historical_email_is_dead(self):
        # WF-02.04 D-55 (revised, owner-approved rewrite): an address changed after verification
        # (here not even a valid address) refuses the rejection with nothing written.
        self.target.email = "not-an-address"
        self.target.save(update_fields=["email"])
        with self.assertRaises(RegistrationRejectionNotAllowed) as caught:
            reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.assertEqual(caught.exception.reason, "recipient_unverified")
        self._assert_refused_unchanged()
        # The writer still never encrypts an invalid address: a terminal Dead row without ciphertext.
        row = self._writer_row("not-an-address")
        self.assertEqual((row.delivery_status, row.last_failure_code), ("Dead", "recipient_unavailable"))
        self.assertIsNone(row.encrypted_recipient)
        self.assertNotIn(b"not-an-address", bytes(row.encrypted_recipient or b""))

    def test_tampered_associated_data_cannot_decrypt(self):
        approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
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
            with self.assertRaises(RegistrationReviewUnavailable):
                approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    def test_outbox_insert_error_rolls_back_status_role_and_audit(self):
        with patch("apps.accounts.registration_review.record_registration_decision_outbox", side_effect=RuntimeError("outbox unavailable")):
            with self.assertRaises(RuntimeError):
                approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(self.target.is_active)
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertFalse(AccountRole.objects.filter(account=self.target).exists())

    @override_settings(WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True)  # WF-02.04 D-54 test correction
    def test_receipt_failure_rolls_back_without_outbox(self):
        with patch("apps.accounts.registration_review.record_access_audit_receipt", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="incomplete_submission")
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_second_review_is_refused_without_duplicate_audit_or_outbox(self):
        approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        with self.assertRaises(RegistrationReviewDenied):
            approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.assertEqual(AccessAuditLog.objects.count(), 1)
        self.assertEqual(RegistrationNotificationOutbox.objects.count(), 1)

    def test_outbox_disabled_fails_closed_even_when_legacy_notifications_are_enabled(self):
        with override_settings(WORKSPACE_REGISTRATION_OUTBOX_ENABLED=False,
                               WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED=True):
            from .registration_review import RegistrationReviewUnavailable
            with self.assertRaises(RegistrationReviewUnavailable):
                approve_registration(actor=self.reviewer, target_id=self.target.pk, attestation=STUDENT_ATTESTATION)
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self._assert_refused_unchanged()

    @override_settings(WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED=True)  # WF-02.04 D-54 test correction
    def test_account_delete_failure_rolls_back_profile_audit_and_outbox(self):
        profile = UserProfile.objects.create(account=self.target, first_name="Synthetic")

        def deny_account_delete(execute, sql, params, many, context):
            if sql.startswith("DELETE FROM accounts "):
                raise OperationalError(1142, "synthetic denial")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(deny_account_delete):
            with self.assertRaises(OperationalError):
                reject_registration(actor=self.reviewer, target_id=self.target.pk, rejection_code="identity_mismatch")
        self.target.refresh_from_db()
        self.assertEqual(self.target.request_status, "Pending")
        self.assertTrue(UserProfile.objects.filter(pk=profile.pk).exists())
        self.assertFalse(AccessAuditLog.objects.exists())
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())

    def test_deleted_rejection_outbox_requires_matching_immutable_snapshot(self):
        for changes in ({"account_id": self.target.pk + 1}, {"account_deleted": False}):
            with self.subTest(changes=changes):
                snapshot = {"account_id": self.target.pk, "request_status": "Rejected",
                            "account_deleted": True, "rejection_code": "identity_mismatch", **changes}
                event = AccessAuditLog.objects.create(
                    actor_account=self.reviewer, target_account=None, action="account.registration.reject",
                    old_value={"account_id": self.target.pk, "request_status": "Pending"}, new_value=snapshot,
                )
                with self.assertRaises(RegistrationOutboxError), transaction.atomic():
                    record_registration_decision_outbox(
                        audit_log_id=event.pk, target_account_id=self.target.pk,
                        approved=False, recipient_email=self.email,
                    )
        self.assertFalse(RegistrationNotificationOutbox.objects.exists())
