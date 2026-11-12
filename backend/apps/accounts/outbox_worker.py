"""AR-6C5B.5: explicitly gated, bounded registration-email outbox worker.

There is no startup hook, background scheduler, API, role grant or schema change.
Never log the decrypted address, mail backend exception, or message body.
At-least-once *attempts*: if a lease expires after remote SMTP acceptance,
recovery can re-send. A successful Django backend call is not inbox delivery.
"""

import os
import secrets
import smtplib
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import get_connection, send_mail
from django.core.validators import validate_email
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from django.db.models import Q
from django.utils import timezone

from .outbox_crypto import OutboxCryptoUnavailable, decrypt_recipient
from .registration_email_templates import (
    REJECTION_LABELS, branded_sender_address, render_decision_email,
    _public_url,
)
from .outbox_models import RegistrationNotificationOutbox

MAX_ATTEMPTS = 5
LEASE_SECONDS = 180
MAX_BATCH = 100
FIRST_RETRY_SECONDS = 60
MAX_RETRY_SECONDS = 3600


class OutboxWorkerUnavailable(RuntimeError):
    """Delivery gates, configuration, or required database are unavailable."""


@dataclass(frozen=True)
class ClaimedJob:
    outbox_id: int
    token: str
    attempt: int


# Deliberately use a second environment gate without changing settings.py.
# Both this AND the existing outbox writer gate are mandatory. The worker
# remains off even when the writer is on.
def _require_delivery_enabled():
    if os.environ.get("WORKSPACE_OUTBOX_WORKER_ENABLED", "0") != "1":
        raise OutboxWorkerUnavailable("Registration email worker is disabled.")
    if not getattr(settings, "WORKSPACE_REGISTRATION_OUTBOX_ENABLED", False):
        raise OutboxWorkerUnavailable("Registration email outbox is disabled.")
    if connections[DEFAULT_DB_ALIAS].vendor != "mysql":
        raise OutboxWorkerUnavailable("Worker requires the primary MySQL database.")
    backend = getattr(settings, "EMAIL_BACKEND", "")
    if backend == "django.core.mail.backends.locmem.EmailBackend":
        return  # Only used in isolated tests.
    if backend == "django.core.mail.backends.console.EmailBackend":
        # The Django console backend prints recipient addresses and bodies.
        if os.environ.get("WORKSPACE_OUTBOX_LOCAL_CONSOLE_ACK", "0") != "1":
            raise OutboxWorkerUnavailable("Console delivery requires local privacy acknowledgement.")
        return
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        if not (getattr(settings, "WORKSPACE_EMAIL_SMTP_ENABLED", False)
                and os.environ.get("WORKSPACE_OUTBOX_SMTP_DELIVERY_APPROVED", "0") == "1"):
            raise OutboxWorkerUnavailable("SMTP delivery is not approved.")
        # Never allow externally delivered decision email to contain localhost
        # URLs, an unapproved redirect target, or an invalid From address.
        try:
            _public_url("/register")
            branded_sender_address()
        except ValueError as exc:
            raise OutboxWorkerUnavailable("Public email configuration is not approved.") from exc
        return
    raise OutboxWorkerUnavailable("Unapproved email backend.")


def _now():
    # MySQL schema uses zero-precision datetime fields.
    return timezone.now().replace(microsecond=0)


def _due_filter(now):
    return (
        # AR-6C5B.4 creates Pending rows for immediate delivery. MySQL's
        # DATETIME(0) can round an inserted fractional next_attempt_at up by
        # one second, so an initial Pending row is always eligible.
        Q(delivery_status="Pending")
        | (Q(delivery_status="Retry")
           & (Q(next_attempt_at__lte=now) | Q(next_attempt_at__isnull=True)))
        | (Q(delivery_status="Leased")
           & (Q(lease_expires_at__lte=now) | Q(lease_expires_at__isnull=True)))
    )


def due_job_count():
    """Read-only operational count. Does not fetch recipient ciphertext."""
    now = _now()
    return RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS).filter(
        _due_filter(now)
    ).count()


def _claim_next():
    """Take one due row with SKIP LOCKED; make expired leases recoverable."""
    now = _now()
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        row = (RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS)
               .filter(_due_filter(now))
               .select_for_update(skip_locked=True)
               .order_by("outbox_id")
               .first())
        if row is None:
            return None
        if row.attempt_count >= MAX_ATTEMPTS:
            # A previous worker can die after consuming its final attempt.
            # Do not leave its expired Leased row stuck forever.
            row.delivery_status = "Dead"
            row.lease_token = None
            row.lease_expires_at = None
            row.next_attempt_at = None
            row.last_failure_code = "attempts_exhausted"
            row.updated_at = now
            row.save(using=DEFAULT_DB_ALIAS, update_fields=[
                "delivery_status", "lease_token", "lease_expires_at",
                "next_attempt_at", "last_failure_code", "updated_at",
            ])
            return "exhausted"
        token = secrets.token_urlsafe(32)  # 43 chars, fits VARCHAR(64)
        row.delivery_status = "Leased"
        row.attempt_count += 1
        row.lease_token = token
        row.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        row.next_attempt_at = None
        row.updated_at = now
        row.save(using=DEFAULT_DB_ALIAS, update_fields=[
            "delivery_status", "attempt_count", "lease_token",
            "lease_expires_at", "next_attempt_at", "updated_at",
        ])
        return ClaimedJob(row.pk, token, row.attempt_count)


def _finish(claim, *, failure_code=None, permanent=False):
    """Fence stale workers: only the current, unexpired lease can finalize."""
    now = _now()
    values = {
        "lease_token": None,
        "lease_expires_at": None,
        "updated_at": now,
    }
    if failure_code is None:
        values.update(
            delivery_status="Delivered", delivered_at=now,
            next_attempt_at=None, last_failure_code=None,
        )
        result = "delivered"
    elif permanent or claim.attempt >= MAX_ATTEMPTS:
        values.update(
            delivery_status="Dead", next_attempt_at=None,
            last_failure_code=failure_code,
        )
        result = "dead"
    else:
        wait_seconds = min(FIRST_RETRY_SECONDS * (2 ** (claim.attempt - 1)), MAX_RETRY_SECONDS)
        values.update(
            delivery_status="Retry", next_attempt_at=now + timedelta(seconds=wait_seconds),
            last_failure_code=failure_code,
        )
        result = "retry"
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        affected = (RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS)
                    .filter(pk=claim.outbox_id, delivery_status="Leased",
                            lease_token=claim.token, lease_expires_at__gt=now)
                    .update(**values))
    return result if affected == 1 else "lost_lease"


def _message_for(row):
    if row.template_version == 2:
        # Immutable audit snapshot belongs to THIS outbox decision, not the
        # mutable account row. Legacy v1 rendering stays exactly as before.
        audit = row.decision_audit_log
        expected = (
            "account.registration.approve" if row.template_code == "registration.approved"
            else "account.registration.reject" if row.template_code == "registration.rejected"
            else None
        )
        if not expected or audit.action != expected:
            return None
        snapshot = audit.new_value if type(audit.new_value) is dict else {}
        if row.template_code == "registration.rejected":
            code = snapshot.get("rejection_code")
            if code not in REJECTION_LABELS:
                return None
            return render_decision_email(approved=False, rejection_code=code)
        return render_decision_email(approved=True)
    if row.template_version != 1:
        return None
    if row.template_code == "registration.approved":
        return (
            "CTU-G Workspace: Registration approved",
            "Your CTU-G Workspace registration has been approved. "
            "You may now sign in using your School ID and password.\n\n"
            "If you did not request an account, contact your campus office.",
        )
    if row.template_code == "registration.rejected":
        return (
            "CTU-G Workspace: Registration not approved",
            "Your CTU-G Workspace registration was not approved. "
            "Please contact your campus office if you need clarification.\n\n"
            "This message does not contain your password or personal details.",
        )
    return None


def _valid_recipient(email):
    if type(email) is not str or email != email.strip() or len(email.encode("utf-8")) > 150:
        return False
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def process_one():
    """Process at most one job. Never hold a database lock during email I/O.

    Returns empty, delivered, retry, dead, or lost_lease. Exceptions from the
    backend are handled without logging private details. Configuration errors
    fail closed *before* any row is claimed.
    """
    _require_delivery_enabled()
    claim = _claim_next()
    if claim is None:
        return "empty"
    if claim == "exhausted":
        return "dead"
    try:
        row = RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS).get(pk=claim.outbox_id)
        message = _message_for(row)
        if message is None:
            return _finish(claim, failure_code="unsupported_template", permanent=True)
        if (row.encrypted_recipient is None or row.recipient_nonce is None
                or row.wrapped_data_key is None or row.encryption_key_version is None
                or row.recipient_erased_at is not None):
            return _finish(claim, failure_code="recipient_unavailable", permanent=True)
        try:
            address = decrypt_recipient(
                encrypted_recipient=row.encrypted_recipient,
                recipient_nonce=row.recipient_nonce,
                wrapped_data_key=row.wrapped_data_key,
                encryption_key_version=row.encryption_key_version,
                audit_log_id=row.decision_audit_log_id,
                template_code=row.template_code,
                template_version=row.template_version,
            )
        except OutboxCryptoUnavailable:
            return _finish(claim, failure_code="crypto_unavailable")
        if not _valid_recipient(address):
            return _finish(claim, failure_code="recipient_unavailable", permanent=True)
        try:
            # No raw exception/recipient/details are surfaced to the CLI.
            connection = get_connection(timeout=15)
            accepted = send_mail(
                subject=message[0], message=message[1],
                from_email=branded_sender_address(),
                recipient_list=[address], fail_silently=False,
                connection=connection,
                **({"html_message": message[2]} if len(message) == 3 else {}),
            )
        except smtplib.SMTPRecipientsRefused:
            return _finish(claim, failure_code="recipient_rejected", permanent=True)
        except smtplib.SMTPAuthenticationError:
            # Admin may fix mail credentials without replacing outbox rows.
            return _finish(claim, failure_code="mail_configuration_unavailable")
        except smtplib.SMTPResponseException as exc:
            permanent = 500 <= exc.smtp_code < 600
            return _finish(claim, failure_code="smtp_rejected" if permanent else "smtp_unavailable",
                           permanent=permanent)
        except Exception:
            return _finish(claim, failure_code="mail_backend_unavailable")
        if accepted != 1:
            return _finish(claim, failure_code="mail_not_accepted")
        return _finish(claim)
    except Exception:
        # Unexpected errors still consume the lease safely; do not leak raw
        # exception text. If database itself is unavailable, recovery begins
        # after the lease expires (and may retry at least once).
        try:
            return _finish(claim, failure_code="worker_unavailable")
        except Exception:
            return "lost_lease"


def process_due(*, limit=25):
    """Bounded single invocation; no daemon, automatic scheduler or HTTP API."""
    if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError("Worker limit must be between 1 and 100.")
    _require_delivery_enabled()
    results = {"delivered": 0, "retry": 0, "dead": 0, "lost_lease": 0}
    for _ in range(limit):
        outcome = process_one()
        if outcome == "empty":
            break
        results[outcome] += 1
    return results
