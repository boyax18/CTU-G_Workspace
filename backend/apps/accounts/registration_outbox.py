"""Transactional review-notification writer. No sending, routing or worker.

Only called after an authorized review has created its exact audit receipt,
within the SAME primary MySQL transaction. Failures must abort the decision.
"""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DEFAULT_DB_ALIAS, transaction
from django.utils import timezone

from apps.access_control.models import AccessAuditLog
from .outbox_crypto import encrypt_recipient
from .outbox_models import RegistrationNotificationOutbox


class RegistrationOutboxError(RuntimeError):
    """Outbox creation was unavailable; caller must roll back the decision."""


def _recipient_valid(value):
    if type(value) is not str or not value or value != value.strip():
        return False
    if len(value.encode("utf-8")) > 150:
        return False
    try:
        validate_email(value)
    except ValidationError:
        return False
    return True


def record_registration_decision_outbox(*, audit_log_id, target_account_id,
                                         approved, recipient_email):
    """Insert exactly one pending or dead outbox row for the audit decision."""
    connection = transaction.get_connection(DEFAULT_DB_ALIAS)
    if not connection.in_atomic_block or connection.needs_rollback:
        raise RegistrationOutboxError("Registration outbox requires a usable transaction.")
    try:
        if (type(audit_log_id) is not int or not 1 <= audit_log_id <= 2_147_483_647
                or type(target_account_id) is not int
                or not 1 <= target_account_id <= 2_147_483_647
                or type(approved) is not bool):
            raise RegistrationOutboxError("Invalid registration outbox decision.")
        code = "registration.approved" if approved else "registration.rejected"
        expected_action = "account.registration.approve" if approved else "account.registration.reject"
        event = AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).only(
            "action", "target_account_id"
        ).get(pk=audit_log_id)
        if event.action != expected_action or event.target_account_id != target_account_id:
            raise RegistrationOutboxError("Registration outbox audit binding is invalid.")

        values = {
            "decision_audit_log_id": audit_log_id,
            "template_code": code,
            "template_version": 1,
            "updated_at": timezone.now(),
        }
        if _recipient_valid(recipient_email):
            values.update(encrypt_recipient(
                email=recipient_email, audit_log_id=audit_log_id,
                template_code=code, template_version=1,
            ))
            values.update(delivery_status="Pending", next_attempt_at=timezone.now())
        else:
            # Historical accounts without a valid address still receive a
            # durable, auditable disposition; no unencrypted PII is written.
            values.update(delivery_status="Dead", last_failure_code="recipient_unavailable")
        row = RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS).create(**values)
        return row.pk
    except Exception:
        transaction.set_rollback(True, using=DEFAULT_DB_ALIAS)
        raise
