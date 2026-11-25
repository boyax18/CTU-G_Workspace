"""Durable security mail: password-reset codes, password-changed notices, email-verification codes.

24 Nov 2026: replaces the former in-memory queue + daemon thread (WF-01.05 D-20), which lost
messages on restart and never retried. Now:

* ``queue()`` writes one SecurityMailOutbox row INSIDE the caller's transaction. The only secret
  (an OTP) is sealed with the existing outbox KEK; nothing else sensitive is stored, and the
  recipient is read from the account at send time.
* After commit, a background "kick" attempts that row at once, so responses stay equally fast
  for eligible and ineligible requests (no account enumeration) and the code arrives quickly.
  The same claim code is used by the ``process_registration_outbox --watch`` worker, which
  retries whatever a kick could not finish (also after a server restart).
* Claims use SELECT ... FOR UPDATE SKIP LOCKED plus a lease token, so two workers can never send
  the same row; only the current lease may finalize it.
* Before sending, an OTP is re-checked against the account's CURRENT challenge. An expired or
  superseded code (resend, verification, password change, email change) is never mailed.
* Temporary SMTP failures retry with exponential backoff (max 5 attempts, never past the code's
  expiry); permanent refusals are dead-lettered. Terminal rows erase the sealed secret.
* ``Accepted`` = SMTP accepted the message. Inbox delivery is never claimed.
"""

import logging
import math
import queue as queue_module
import secrets
import smtplib
import threading
from datetime import timedelta

from django.db import DEFAULT_DB_ALIAS, close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from . import email_design
from .email_design import send_mail  # branded multipart drop-in (patched by tests)
from .email_trace import mask, new_correlation_id, trace
from .outbox_crypto import OutboxCryptoUnavailable, open_secret, seal_secret
from .security_mail_models import SecurityMailOutbox

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
LEASE_SECONDS = 120
FIRST_RETRY_SECONDS = 30
MAX_RETRY_SECONDS = 600
NOTICE_MAX_AGE = timedelta(hours=24)  # a password-changed notice older than this is stale
KICK_QUEUE_SIZE = 200
_TERMINAL = ("Accepted", "Dead", "Expired", "Superseded")
_SECRET_FIELDS = ("encrypted_secret", "secret_nonce", "wrapped_data_key", "encryption_key_version")

_kicks = queue_module.Queue(maxsize=KICK_QUEUE_SIZE)
_start_lock = threading.Lock()
_kick_thread = None


# ----------------------------------------------------------------------------- queueing
def queue(kind, account, *, code=None, challenge_issued_at=None, correlation_id=None):
    """Durably queue one message in the caller's transaction; attempt delivery after commit."""
    if kind not in dict(SecurityMailOutbox.KINDS):
        raise ValueError("Unknown security mail kind.")
    needs_code = kind != SecurityMailOutbox.KIND_PASSWORD_CHANGED
    if needs_code != (type(code) is str and code.isdigit()):
        raise ValueError("An OTP message needs exactly its code; a notice has none.")
    correlation_id = correlation_id or new_correlation_id()
    token = secrets.token_hex(16)
    sealed = seal_secret(code, row_token=token, kind=kind, account_id=account.pk) if code else {}
    row = SecurityMailOutbox.objects.using(DEFAULT_DB_ALIAS).create(
        account=account, kind=kind, row_token=token, correlation_id=correlation_id,
        challenge_issued_at=challenge_issued_at, **sealed,
    )
    trace("email_queued", correlation_id, flow=kind, outbox=row.pk)
    transaction.on_commit(lambda: kick(row.pk), using=DEFAULT_DB_ALIAS)
    return row


def kick(outbox_id):
    """Ask the background sender to attempt a committed row now. The row is durable either way."""
    from django.conf import settings
    if getattr(settings, "WORKSPACE_SECURITY_MAIL_INLINE", False) is True:
        # Test settings only: same thread/connection, so uncommitted test transactions are visible.
        process_one(outbox_id=outbox_id)
        return
    _ensure_kick_thread()
    try:
        _kicks.put_nowait(outbox_id)
    except queue_module.Full:
        logger.warning("Security mail kick queue is full; the durable worker will deliver it.")


def _ensure_kick_thread():
    global _kick_thread
    with _start_lock:
        if _kick_thread is None or not _kick_thread.is_alive():
            _kick_thread = threading.Thread(target=_kick_loop, name="ctug-security-mail", daemon=True)
            _kick_thread.start()


def _kick_loop():
    while True:
        outbox_id = _kicks.get()
        try:
            process_one(outbox_id=outbox_id)
            process_due(limit=5)  # opportunistically finish earlier rows (e.g. after a restart)
        except Exception as exc:  # never log addresses, codes or SMTP text
            logger.warning("Security mail attempt could not run (%s).", type(exc).__name__)
        finally:
            close_old_connections()
            _kicks.task_done()


def wait_until_idle():
    """Block until every kicked row has been attempted (used by tests)."""
    _kicks.join()


# ----------------------------------------------------------------------------- worker
def _now():
    return timezone.now()


def _due(now):
    return (Q(status="Pending")
            | (Q(status="Retry") & (Q(next_attempt_at__lte=now) | Q(next_attempt_at__isnull=True)))
            | (Q(status="Leased") & (Q(lease_expires_at__lte=now) | Q(lease_expires_at__isnull=True))))


def _claim(outbox_id=None):
    now = _now()
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        rows = SecurityMailOutbox.objects.using(DEFAULT_DB_ALIAS).filter(_due(now))
        if outbox_id is not None:
            rows = rows.filter(pk=outbox_id)
        row = rows.select_for_update(skip_locked=True).order_by("outbox_id").first()
        if row is None:
            return None
        if row.attempt_count >= MAX_ATTEMPTS:
            _terminal(row, "Dead", "attempts_exhausted", now)
            row.save(using=DEFAULT_DB_ALIAS)
            trace("permanent_failure", row.correlation_id, flow=row.kind, outbox=row.pk, code="attempts_exhausted")
            return "exhausted"
        row.status, row.attempt_count = "Leased", row.attempt_count + 1
        row.lease_token = secrets.token_urlsafe(32)
        row.lease_expires_at, row.next_attempt_at = now + timedelta(seconds=LEASE_SECONDS), None
        row.save(using=DEFAULT_DB_ALIAS, update_fields=[
            "status", "attempt_count", "lease_token", "lease_expires_at", "next_attempt_at", "updated_at"])
        return row


def _terminal(row, status, failure_code, now):
    row.status, row.last_failure_code = status, failure_code
    row.lease_token = row.lease_expires_at = row.next_attempt_at = None
    for field in _SECRET_FIELDS:
        setattr(row, field, None)
    row.secret_erased_at = now


def _finish(row, *, status, failure_code=None, retry_at=None, message_id=None):
    """Fence stale workers: only the current, unexpired lease can finalize this row."""
    now = _now()
    values = {"lease_token": None, "lease_expires_at": None, "updated_at": now, "last_failure_code": failure_code}
    if status in _TERMINAL:
        values.update({f: None for f in _SECRET_FIELDS}, secret_erased_at=now, next_attempt_at=None)
        if status == "Accepted":
            values.update(accepted_at=now, message_id=message_id)
    else:
        values.update(next_attempt_at=retry_at)
    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        updated = (SecurityMailOutbox.objects.using(DEFAULT_DB_ALIAS)
                   .filter(pk=row.pk, status="Leased", lease_token=row.lease_token, lease_expires_at__gt=now)
                   .update(status=status, **values))
    return status.lower() if updated == 1 else "lost_lease"


def _otp_state(row):
    """('current', code, minutes_left, expires_at) for a live OTP, else (state, None, None, None)."""
    if row.encrypted_secret is None:
        return "superseded", None, None, None
    try:
        code = open_secret(encrypted_secret=row.encrypted_secret, secret_nonce=row.secret_nonce,
                           wrapped_data_key=row.wrapped_data_key, encryption_key_version=row.encryption_key_version,
                           row_token=row.row_token, kind=row.kind, account_id=row.account_id)
    except OutboxCryptoUnavailable:
        return "crypto_unavailable", None, None, None
    if row.kind == SecurityMailOutbox.KIND_RESET_CODE:
        from .password_reset import reset_challenge_state
        state, expires_at = reset_challenge_state(row.account, row.challenge_issued_at, code)
    else:
        from .email_verification import verification_challenge_state
        from .security_mail_models import AccountEmailVerification
        purpose = (AccountEmailVerification.PURPOSE_ASSISTED if row.kind == SecurityMailOutbox.KIND_ASSISTED_RECOVERY
                   else AccountEmailVerification.PURPOSE_SELF)
        state, expires_at = verification_challenge_state(row.account, row.challenge_issued_at, code, purpose)
    if state != "current":
        return state, None, None, None
    return "current", code, max(1, math.ceil((expires_at - _now().timestamp()) / 60)), expires_at


def _message(row, code=None, minutes=None):
    from .password_reset import _first_name
    first = _first_name(row.account)
    if row.kind == SecurityMailOutbox.KIND_RESET_CODE:
        return email_design.password_reset_otp(code=code, minutes=minutes, first_name=first)
    if row.kind == SecurityMailOutbox.KIND_EMAIL_VERIFICATION:
        return email_design.email_verification_otp(code=code, minutes=minutes, first_name=first)
    if row.kind == SecurityMailOutbox.KIND_ASSISTED_RECOVERY:
        return email_design.assisted_recovery_otp(code=code, minutes=minutes, first_name=first)
    return email_design.password_changed(first_name=first)


def process_one(*, outbox_id=None):
    """Claim and attempt at most one row. Returns a status word; never raises SMTP details."""
    row = _claim(outbox_id)
    if row is None:
        return "empty"
    if row == "exhausted":
        return "dead"
    corr = row.correlation_id
    code = minutes = expires_at = None
    if row.kind == SecurityMailOutbox.KIND_PASSWORD_CHANGED:
        if _now() - row.created_at > NOTICE_MAX_AGE:
            trace("expired", corr, flow=row.kind, outbox=row.pk)
            return _finish(row, status="Expired", failure_code="stale_notice")
    else:
        state, code, minutes, expires_at = _otp_state(row)
        if state == "crypto_unavailable":
            return _temporary(row, state, None)
        if state != "current":
            trace(state, corr, flow=row.kind, outbox=row.pk)
            return _finish(row, status="Expired" if state == "expired" else "Superseded", failure_code=state)
    recipient = row.account.email
    subject, text, html = _message(row, code, minutes)
    message_id = email_design.new_message_id()
    trace("smtp_attempt", corr, flow=row.kind, outbox=row.pk, attempt=row.attempt_count, to=mask(recipient))
    try:
        accepted = send_mail(subject, text, None, [recipient], fail_silently=False, html_message=html,
                             headers={"Message-ID": message_id})
    except smtplib.SMTPRecipientsRefused:
        return _permanent(row, "recipient_rejected")
    except smtplib.SMTPResponseException as exc:
        if 500 <= exc.smtp_code < 600 and not isinstance(exc, smtplib.SMTPAuthenticationError):
            return _permanent(row, f"smtp_{exc.smtp_code}")
        return _temporary(row, f"smtp_{exc.smtp_code}", expires_at)
    except Exception as exc:
        return _temporary(row, type(exc).__name__[:40], expires_at)
    if accepted != 1:
        return _temporary(row, "not_accepted", expires_at)
    trace("smtp_accepted", corr, flow=row.kind, outbox=row.pk, attempt=row.attempt_count, msgid=message_id,
          reply=email_design.last_smtp_reply(), to=mask(recipient))
    trace("recipient_unconfirmed", corr, flow=row.kind, outbox=row.pk, status="awaiting_recipient")
    return _finish(row, status="Accepted", message_id=message_id)


def confirm_receipt(account, kind, challenge_issued_at):
    """A correct code was just entered: the message that carried it demonstrably arrived.

    Links the redemption to the original request through the row's correlation ID (server log
    only). Never raises: a diagnostics problem must not affect verification or recovery.
    """
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS):  # savepoint: a failure never poisons the caller
            row = (SecurityMailOutbox.objects.using(DEFAULT_DB_ALIAS)
                   .filter(account_id=account.pk, kind=kind, challenge_issued_at=challenge_issued_at)
                   .order_by("-outbox_id").only("outbox_id", "correlation_id", "status").first())
        if row is None:
            trace("recipient_confirmed", None, flow=kind, status="code_redeemed_no_outbox_row")
            return
        trace("recipient_confirmed", row.correlation_id, flow=kind, outbox=row.pk,
              status=f"code_redeemed_after_{row.status.lower()}")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Receipt confirmation trace failed (%s).", type(exc).__name__)


def _permanent(row, code):
    trace("permanent_failure", row.correlation_id, flow=row.kind, outbox=row.pk, attempt=row.attempt_count, code=code)
    return _finish(row, status="Dead", failure_code=code)


def _temporary(row, code, expires_at):
    trace("temporary_failure", row.correlation_id, flow=row.kind, outbox=row.pk, attempt=row.attempt_count, code=code)
    wait = min(FIRST_RETRY_SECONDS * (2 ** (row.attempt_count - 1)), MAX_RETRY_SECONDS)
    retry_at = _now() + timedelta(seconds=wait)
    if row.attempt_count >= MAX_ATTEMPTS:
        trace("permanent_failure", row.correlation_id, flow=row.kind, outbox=row.pk, code="attempts_exhausted")
        return _finish(row, status="Dead", failure_code=code)
    if expires_at is not None and retry_at.timestamp() >= expires_at:
        trace("expired", row.correlation_id, flow=row.kind, outbox=row.pk)
        return _finish(row, status="Expired", failure_code=code)
    trace("retry_scheduled", row.correlation_id, flow=row.kind, outbox=row.pk, attempt=row.attempt_count,
          next_in=f"{wait}s")
    return _finish(row, status="Retry", failure_code=code, retry_at=retry_at)


def process_due(*, limit=25):
    """Bounded batch for the watch worker and kicks; aggregate counts only."""
    results = {}
    for _ in range(max(1, min(int(limit), 100))):
        outcome = process_one()
        if outcome == "empty":
            break
        results[outcome] = results.get(outcome, 0) + 1
    return results
