"""Opt-in Workspace password recovery by email OTP. Distinct from Django /admin/ recovery.

WF-01.05 CR-01 (owner-approved 16-17 Nov 2026): email-only request (D-25), a
6-digit code with 10-minute validity, 5 cumulative wrong attempts per 30-minute
window and a 60-second resend interval (D-26), storage in the existing
accounts.password_reset_token / password_reset_token_expires columns with a
single-use reset ticket in an HttpOnly cookie (D-27), and no reset links (D-28).

Carried over: verified-email eligibility (D-21), background delivery (D-20,
development only), password-changed notice after commit (D-22), the gate stays
off (D-24), and protected executor mode refuses recovery: the fencing DDL blocks
credential-state writes on Approved accounts, password_reset_token is part of the
executor's protected-state hash, and the permitted-writer boundary is never bypassed.
"""

import hmac
import logging
import secrets
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from . import recovery_mail, session_revocation
from .email_trace import new_correlation_id, trace
from .email_identity import normalize_account_email
from .models import Account
from .session_auth import WorkspaceSessionAPI

logger = logging.getLogger(__name__)

NEUTRAL_REQUEST = "If an eligible account uses this email, we sent a 6-digit code. It expires in 10 minutes."
CODE_INVALID = "The code is incorrect or has expired."
TICKET_INVALID = "Your verification has expired. Request a new code."
PASSWORD_FIELD_TEXT = "Choose a stronger password using the requirements shown."
CONFIRMATION_FIELD_TEXT = "Passwords do not match."

TICKET_COOKIE = "ctug_password_reset_ticket"
TICKET_COOKIE_PATH = "/api/v1/auth/reset-password/"
TICKET_SECONDS = 600
RECORD_VERSION = "rv1"
# P-03 / D-16 / D-26: per-email budgets keyed by an HMAC digest of the normalized email.
REQUEST_IDENTITY_RATES = ("3/hour", "6/day")
VERIFY_IDENTITY_RATES = ("10/hour",)


def _policy():
    """D-26 reuses the WF-01.01 OTP defaults: 600 s code, 60 s resend, 5 attempts, 1800 s window."""
    from .registration_staging import policy
    p = policy()
    return {"code": p["otp_seconds"], "resend": p["resend_seconds"],
            "attempts": p["max_attempts"], "window": p["stage_seconds"]}


def _now():
    return int(timezone.now().timestamp())


def _digest(purpose, value):
    from .registration_staging import _digest as keyed_digest
    return keyed_digest(purpose, value)


# ---------- throttles ----------

class ResetThrottle(SimpleRateThrottle):
    scope = "workspace_password_reset"
    rate = "4/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": request.META.get("REMOTE_ADDR", "unknown")}


class ResetDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_daily"
    rate = "20/day"


class VerifyThrottle(ResetThrottle):
    scope = "workspace_password_reset_verify"
    rate = "4/min"


class VerifyDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_verify_daily"
    rate = "20/day"


# The reset step has its own counters, so requests and verifications cannot block it.
class ResetConfirmThrottle(ResetThrottle):
    scope = "workspace_password_reset_confirm"
    rate = "4/min"


class ResetConfirmDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_confirm_daily"
    rate = "20/day"


def _enforce_identity_budget(email, kind, rates):
    from .registration_staging import _IdentityThrottle

    digest = _digest("password-recovery-email", email)
    for period, rate in enumerate(rates):
        throttle = _IdentityThrottle(digest, f"password-recovery:{kind}:{period}", rate)
        if not throttle.allow_request(None, None):
            raise exceptions.Throttled(wait=throttle.wait())


# ---------- serializers ----------

class _ExactFields(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != set(self.fields):
            # DRF requires a dict here; a bare string crashes error rendering (found by test).
            raise serializers.ValidationError({"non_field_errors": ["Unsupported recovery fields."]})
        return super().to_internal_value(data)


class PasswordResetRequestSerializer(_ExactFields):
    email = serializers.EmailField(max_length=150)


class PasswordResetVerifySerializer(_ExactFields):
    email = serializers.EmailField(max_length=150)
    code = serializers.RegexField(r"\A[0-9]{6}\Z", max_length=6, trim_whitespace=False)


class PasswordResetConfirmSerializer(_ExactFields):
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    password_confirmation = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": [CONFIRMATION_FIELD_TEXT]})
        return data


# ---------- eligibility and the stored record ----------

def eligible_account_queryset():
    # D-21: only accounts whose current email carries verification proof.
    # Legacy accounts without proof need a future authorized assisted recovery.
    return Account.objects.filter(
        is_active=True,
        request_status="Approved",
        is_staff=False,
        is_superuser=False,
        role_assignments__role__is_active=True,
        email__isnull=False,
        email_verified_at__isnull=False,
        email_verified_address__iexact=F("email"),
    ).distinct()


def _first_name(account):
    """Greeting only. A missing profile simply means a neutral greeting."""
    try:
        name = (account.profile.first_name or "").strip()
    except Exception:
        return None
    return name[:100] or None


def _lock_eligible(email):
    """Inside a transaction: lock and return the one eligible account using `email`, or None."""
    ids = list(eligible_account_queryset().filter(email__iexact=email).values_list("pk", flat=True)[:2])
    if len(ids) != 1:
        if len(ids) > 1:
            logger.warning("Workspace password recovery lookup was ambiguous.")
        return None
    account = Account.objects.select_for_update().filter(pk=ids[0]).first()
    # Recheck under the lock: approval, activity, role or proof may have changed.
    if account is None or not eligible_account_queryset().filter(pk=account.pk).exists():
        return None
    return account


class _Record:
    """password_reset_token = rv1:{state}:{attempts}:{window_start}:{issued_at}:{digest}."""

    def __init__(self, state, attempts, window_start, issued_at, digest):
        self.state, self.attempts, self.window_start, self.issued_at, self.digest = state, attempts, window_start, issued_at, digest

    @classmethod
    def load(cls, value):
        try:
            version, state, attempts, window_start, issued_at, digest = (value or "").split(":")
            if version != RECORD_VERSION or state not in {"otp", "ticket", "locked"}:
                return None
            return cls(state, int(attempts), int(window_start), int(issued_at), digest)
        except ValueError:
            return None

    def dump(self):
        return ":".join([RECORD_VERSION, self.state, str(self.attempts), str(self.window_start), str(self.issued_at), self.digest])


def reset_challenge_state(account, challenge_issued_at, code):
    """Is this queued code still the account's CURRENT live reset challenge?

    Returns ("current", expires_epoch) or ("expired" | "superseded", None). Superseded covers a
    resend (new issued_at), a verified/locked challenge, a changed password or email, and an
    account that is no longer eligible. Used by the durable sender before every attempt.
    """
    account = Account.objects.filter(pk=account.pk).first()
    if account is None or not eligible_account_queryset().filter(pk=account.pk).exists():
        return "superseded", None
    record = _Record.load(account.password_reset_token)
    if record is None or record.state != "otp" or record.issued_at != challenge_issued_at:
        return "superseded", None
    if not hmac.compare_digest(record.digest, _code_digest(account, record, code)):
        return "superseded", None
    p = _policy()
    expires_at = min(record.issued_at + p["code"], record.window_start + p["window"])
    if record.attempts >= p["attempts"] or _now() >= expires_at:
        return "expired", None
    return "current", expires_at


def _code_digest(account, record, code):
    return _digest("password-recovery-otp",
                   f"{account.pk}:{record.window_start}:{record.issued_at}:{account.password}:{account.email.lower()}:{code}")


def _ticket_digest(account, record, ticket):
    return _digest("password-recovery-ticket",
                   f"{account.pk}:{record.issued_at}:{account.password}:{account.email.lower()}:{ticket}")


def _save(account, record, expires_at):
    account.password_reset_token = record.dump() if record else None
    account.password_reset_token_expires = (
        datetime.fromtimestamp(expires_at, tz=dt_timezone.utc) if record and expires_at else None)
    account.save(update_fields=["password_reset_token", "password_reset_token_expires"])


def _recovery_unavailable():
    return Response({"error": {"code": "recovery_unavailable", "message": "Password recovery is temporarily unavailable."}},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _refusal():
    """Gate off, or protected executor mode (no reviewed executor operation): fail closed."""
    if not getattr(settings, "WORKSPACE_PASSWORD_RESET_ENABLED", False):
        return Response({"error": {"code": "recovery_disabled", "message": "Password recovery is not available yet."}}, status=503)
    from apps.access_control.executor.client import enabled
    if enabled():
        return _recovery_unavailable()
    return None


def _code_invalid():
    return Response({"error": {"code": "recovery_code_invalid", "message": CODE_INVALID}}, status=400)


def _ticket_invalid():
    response = Response({"error": {"code": "reset_session_invalid", "message": TICKET_INVALID}}, status=400)
    response.delete_cookie(TICKET_COOKIE, path=TICKET_COOKIE_PATH, samesite="Strict")
    return response


# ---------- views ----------

class PasswordResetRequestView(WorkspaceSessionAPI):
    """Step 1: email in, neutral 202 out; an eligible account gets a code by email."""

    http_method_names = ["post", "options"]
    throttle_classes = [ResetThrottle, ResetDailyThrottle]

    def post(self, request):
        refusal = _refusal()
        if refusal is not None:
            return refusal
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = normalize_account_email(serializer.validated_data["email"])
        _enforce_identity_budget(email, "request", REQUEST_IDENTITY_RATES)
        p = _policy()
        corr = new_correlation_id()
        trace("request_accepted", corr, flow="reset_code")
        try:
            with transaction.atomic():
                account = _lock_eligible(email)
                if account is None:
                    # Server log only; the HTTP response below stays identical (no enumeration).
                    trace("account_ineligible", corr, flow="reset_code")
                if account is not None:
                    now = _now()
                    record = _Record.load(account.password_reset_token)
                    if record is None or now >= record.window_start + p["window"]:
                        record = _Record("otp", 0, now, 0, "")
                    window_end = record.window_start + p["window"]
                    # D-26: locked windows stay locked; resends need 60 s and keep the attempt count.
                    if record.state != "locked" and now - record.issued_at >= p["resend"]:
                        code = f"{secrets.randbelow(1_000_000):06d}"
                        record.state, record.issued_at = "otp", now
                        record.digest = _code_digest(account, record, code)
                        _save(account, record, min(now + p["code"], window_end))
                        trace("otp_created", corr, flow="reset_code")
                        # Durable, encrypted, bound to THIS challenge; sent after commit and
                        # re-validated before every attempt (a superseded code is never mailed).
                        recovery_mail.queue("reset_code", account, code=code,
                                            challenge_issued_at=record.issued_at, correlation_id=corr)
        except Exception as exc:
            # Never reveal the target identity or code to API callers or logs.
            logger.warning("Workspace password recovery request could not be completed (%s).", type(exc).__name__)
        return Response({"status": "code_requested", "message": NEUTRAL_REQUEST,
                         "resend_after": p["resend"], "code_valid_seconds": p["code"]},
                        status=status.HTTP_202_ACCEPTED)


class PasswordResetVerifyView(WorkspaceSessionAPI):
    """Step 2: email + code in; a correct live code becomes a single-use ticket cookie."""

    http_method_names = ["post", "options"]
    throttle_classes = [VerifyThrottle, VerifyDailyThrottle]

    def handle_exception(self, exc):
        # A malformed code is just another wrong code to the user.
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict) and "code" in exc.detail:
            return _code_invalid()
        return super().handle_exception(exc)

    def post(self, request):
        refusal = _refusal()
        if refusal is not None:
            return refusal
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = normalize_account_email(serializer.validated_data["email"])
        code = serializer.validated_data["code"]
        _enforce_identity_budget(email, "verify", VERIFY_IDENTITY_RATES)
        p = _policy()
        try:
            with transaction.atomic():
                account = _lock_eligible(email)
                if account is None:
                    _digest("password-recovery-otp", code)  # similar work for unknown emails
                    return _code_invalid()
                now = _now()
                record = _Record.load(account.password_reset_token)
                live = (record is not None and record.state == "otp" and record.attempts < p["attempts"]
                        and now < min(record.issued_at + p["code"], record.window_start + p["window"]))
                if not live:
                    return _code_invalid()
                if not hmac.compare_digest(record.digest, _code_digest(account, record, code)):
                    # Counted and committed before replying (the response does not raise).
                    record.attempts += 1
                    if record.attempts >= p["attempts"]:
                        record.state, record.digest = "locked", ""
                    _save(account, record, record.window_start + p["window"] if record.state == "locked"
                          else min(record.issued_at + p["code"], record.window_start + p["window"]))
                    return _code_invalid()
                ticket = secrets.token_urlsafe(32)
                record.state, record.issued_at = "ticket", now
                record.digest = _ticket_digest(account, record, ticket)
                _save(account, record, now + TICKET_SECONDS)
        except DatabaseError:
            logger.warning("Workspace password recovery verification database error.")
            return _recovery_unavailable()
        response = Response({"status": "verified"})
        response.set_cookie(TICKET_COOKIE, ticket, max_age=TICKET_SECONDS, httponly=True,
                            secure=settings.SESSION_COOKIE_SECURE, samesite="Strict", path=TICKET_COOKIE_PATH)
        return response


class PasswordResetConfirmView(WorkspaceSessionAPI):
    """Step 3: email + new password in; the ticket cookie authorizes exactly one change."""

    http_method_names = ["post", "options"]
    throttle_classes = [ResetConfirmThrottle, ResetConfirmDailyThrottle]

    def handle_exception(self, exc):
        # P-01: allowlisted field feedback instead of the generic 400 body.
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict):
            fields = {}
            if "password" in exc.detail:
                fields["password"] = [PASSWORD_FIELD_TEXT]
            if "password_confirmation" in exc.detail:
                fields["password_confirmation"] = [CONFIRMATION_FIELD_TEXT]
            if fields:
                return Response({"error": {"code": "invalid_request", "message": "Check the highlighted fields.", "fields": fields}}, status=400)
        return super().handle_exception(exc)

    def post(self, request):
        refusal = _refusal()
        if refusal is not None:
            return refusal
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = normalize_account_email(serializer.validated_data["email"])
        ticket = request.COOKIES.get(TICKET_COOKIE, "")
        try:
            with transaction.atomic():
                account = _lock_eligible(email) if ticket else None
                record = _Record.load(account.password_reset_token) if account else None
                valid = (record is not None and record.state == "ticket"
                         and _now() < record.issued_at + TICKET_SECONDS
                         and hmac.compare_digest(record.digest, _ticket_digest(account, record, ticket)))
                if not valid:
                    return _ticket_invalid()
                try:
                    validate_password(serializer.validated_data["password"], user=account)
                except DjangoValidationError as exc:
                    # Nothing was written; the ticket stays usable until it expires.
                    raise exceptions.ValidationError({"password": ["invalid"]}) from exc
                account.set_password(serializer.validated_data["password"])
                account.password_reset_token = None
                account.password_reset_token_expires = None
                account.save(update_fields=["password", "password_reset_token", "password_reset_token_expires"])
                # SR-1: the new password already ends old sessions; the counter also means restoring an
                # old password hash alone cannot revive them. _lock_eligible already holds this row's lock.
                session_revocation.advance(account.pk)
                # D-22: durably queued in the same transaction, so it exists only if the change commits.
                recovery_mail.queue("password_changed", account)
        except DatabaseError:
            logger.warning("Workspace password recovery confirmation database error.")
            return _recovery_unavailable()
        response = Response({"message": "Password changed. You can now sign in."})
        response.delete_cookie(TICKET_COOKIE, path=TICKET_COOKIE_PATH, samesite="Strict")
        return response
