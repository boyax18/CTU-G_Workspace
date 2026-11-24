"""Email verification for existing signed-in accounts (24 Nov 2026).

Legacy accounts (for example administrators provisioned before OTP registration) have no
``email_verified_at`` / ``email_verified_address`` and therefore cannot use password recovery
(D-21, unchanged). This lets the SIGNED-IN owner prove control of the account's CURRENT email:

* GET  /api/v1/auth/email-verification/          own status
* POST /api/v1/auth/email-verification/request/  send a 6-digit code to the current address
* POST /api/v1/auth/email-verification/confirm/  {"code"}: on success record the proof

Same OTP policy as registration and recovery: 10-minute code, 60 s resend, at most 4 sends and
5 wrong codes per 30-minute window, then locked until the window ends. Only the keyed digest of
the code is stored (the outgoing message is sealed in the durable security outbox). Proof is
written only after a correct code for the unchanged address; an audit event records the change
without the code. IDs, passwords, roles, permissions and approval status are untouched.
"""

import hmac
import secrets

from django.contrib.auth import get_user
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from . import recovery_mail
from .email_trace import new_correlation_id, trace
from .models import Account
from .security_mail_models import AccountEmailVerification, SecurityMailOutbox
from .session_auth import WorkspaceSessionAPI, _workspace_account

AUDIT_ACTION = "account.email.verified"


def _policy():
    from .registration_staging import policy
    p = policy()
    return {"code": p["otp_seconds"], "resend": p["resend_seconds"], "attempts": p["max_attempts"],
            "window": p["stage_seconds"], "sends": p["max_resends"] + 1}


def _digest(purpose, value):
    from .registration_staging import _digest as keyed_digest
    return keyed_digest(purpose, value)


def _now():
    return int(timezone.now().timestamp())


def is_verified(account):
    email = (account.email or "").strip()
    proof = (account.email_verified_address or "").strip()
    return bool(email) and account.email_verified_at is not None and proof.lower() == email.lower()


def _email_digest(account):
    return _digest("email-verification-address", (account.email or "").strip().lower())


def _code_digest(account, challenge, code):
    return _digest("email-verification-otp",
                   f"{account.pk}:{challenge.window_start}:{challenge.issued_at}:{(account.email or '').lower()}:{code}")


def _expires(challenge, p):
    return min(challenge.issued_at + p["code"], challenge.window_start + p["window"])


def verification_challenge_state(account, challenge_issued_at, code):
    """For the durable sender: ("current", expires_epoch) or ("expired" | "superseded", None)."""
    account = Account.objects.filter(pk=account.pk).first()
    challenge = AccountEmailVerification.objects.filter(account_id=getattr(account, "pk", None)).first()
    if account is None or challenge is None or is_verified(account) or challenge.locked:
        return "superseded", None
    if (challenge.issued_at != challenge_issued_at
            or not hmac.compare_digest(challenge.email_digest, _email_digest(account))
            or not hmac.compare_digest(challenge.code_digest, _code_digest(account, challenge, code))):
        return "superseded", None
    p = _policy()
    if challenge.attempts >= p["attempts"] or _now() >= _expires(challenge, p):
        return "expired", None
    return "current", _expires(challenge, p)


# ----------------------------------------------------------------------------- views
class _AccountThrottle(SimpleRateThrottle):
    """Per signed-in account (never per address): identifies, never authorizes."""

    def get_cache_key(self, request, view):
        user = get_user(request._request)
        ident = f"account:{user.pk}" if getattr(user, "pk", None) else "address:" + request.META.get("REMOTE_ADDR", "")
        return self.cache_format % {"scope": self.scope, "ident": ident}


class VerificationRequestThrottle(_AccountThrottle):
    scope = "workspace_email_verification_request"
    rate = "6/min"


class VerificationConfirmThrottle(_AccountThrottle):
    scope = "workspace_email_verification_confirm"
    rate = "10/min"


class _CodeSerializer(serializers.Serializer):
    code = serializers.RegexField(r"\A[0-9]{6}\Z", max_length=6, trim_whitespace=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != {"code"}:
            raise serializers.ValidationError({"non_field_errors": ["Send only the 6-digit code."]})
        return super().to_internal_value(data)


def _error(code, message, http_status, **extra):
    return Response({"error": {"code": code, "message": message, **extra}}, status=http_status)


class _EmailVerificationAPI(WorkspaceSessionAPI):
    def account_or_refusal(self, request):
        from .password_reset import _refusal
        refusal = _refusal()  # same gate and protected-executor refusal as password recovery
        if refusal is not None:
            return None, refusal
        account = _workspace_account(get_user(request._request))
        if account is None:
            return None, _error("authentication_required", "Sign in to continue.", 401)
        return account, None


class EmailVerificationStatusView(_EmailVerificationAPI):
    http_method_names = ["get", "options"]

    def get(self, request):
        account, refusal = self.account_or_refusal(request)
        if refusal is not None:
            return refusal
        # The signed-in owner's own address only.
        return Response({"email": account.email or None, "email_verified": is_verified(account)})


class EmailVerificationRequestView(_EmailVerificationAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [VerificationRequestThrottle]

    def post(self, request):
        account, refusal = self.account_or_refusal(request)
        if refusal is not None:
            return refusal
        if request.data:  # the request takes no fields; the address is always the account's own
            raise exceptions.ValidationError({"non_field_errors": ["No fields are accepted."]})
        p, corr = _policy(), new_correlation_id()
        trace("request_accepted", corr, flow="email_verification_code")
        try:
            with transaction.atomic():
                account = Account.objects.select_for_update().get(pk=account.pk)
                if is_verified(account):
                    return _error("already_verified", "Your email address is already verified.", 409)
                if not account.email:
                    return _error("email_missing", "Your account has no email address. Contact the campus administrator.", 409)
                now = _now()
                challenge = AccountEmailVerification.objects.select_for_update().filter(account=account).first()
                if challenge is None or now >= challenge.window_start + p["window"]:
                    challenge = challenge or AccountEmailVerification(account=account)
                    challenge.window_start, challenge.attempts, challenge.sends, challenge.locked = now, 0, 0, False
                    challenge.issued_at = 0
                retry_after = None
                if challenge.locked or challenge.sends >= p["sends"]:
                    retry_after = challenge.window_start + p["window"] - now
                elif challenge.issued_at and now - challenge.issued_at < p["resend"]:
                    retry_after = challenge.issued_at + p["resend"] - now
                if retry_after is not None:
                    return _error("verification_wait", "Please wait before requesting another code.", 429,
                                  retry_after=max(1, retry_after))
                code = f"{secrets.randbelow(1_000_000):06d}"
                challenge.issued_at, challenge.sends = now, challenge.sends + 1
                challenge.email_digest = _email_digest(account)
                challenge.code_digest = _code_digest(account, challenge, code)
                challenge.save()
                trace("otp_created", corr, flow="email_verification_code")
                recovery_mail.queue(SecurityMailOutbox.KIND_EMAIL_VERIFICATION, account, code=code,
                                    challenge_issued_at=now, correlation_id=corr)
        except DatabaseError:
            return _error("verification_unavailable", "Email verification is temporarily unavailable.", 503)
        return Response({"status": "code_sent", "resend_after": p["resend"], "code_valid_seconds": p["code"]},
                        status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(_EmailVerificationAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [VerificationConfirmThrottle]

    def handle_exception(self, exc):
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict) and "code" in exc.detail:
            return _error("verification_code_invalid", "The code is incorrect or has expired.", 400)
        return super().handle_exception(exc)

    def post(self, request):
        account, refusal = self.account_or_refusal(request)
        if refusal is not None:
            return refusal
        serializer = _CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code, p = serializer.validated_data["code"], _policy()
        invalid = _error("verification_code_invalid", "The code is incorrect or has expired.", 400)
        try:
            with transaction.atomic():
                account = Account.objects.select_for_update().get(pk=account.pk)
                if is_verified(account):
                    return _error("already_verified", "Your email address is already verified.", 409)
                challenge = AccountEmailVerification.objects.select_for_update().filter(account=account).first()
                now = _now()
                live = (challenge is not None and not challenge.locked and challenge.issued_at
                        and challenge.attempts < p["attempts"] and now < _expires(challenge, p)
                        and hmac.compare_digest(challenge.email_digest, _email_digest(account)))
                if not live:
                    return invalid
                if not hmac.compare_digest(challenge.code_digest, _code_digest(account, challenge, code)):
                    challenge.attempts += 1
                    challenge.locked = challenge.attempts >= p["attempts"]
                    challenge.save(update_fields=["attempts", "locked"])
                    return invalid
                Account.objects.filter(pk=account.pk).update(
                    email_verified_at=timezone.now(), email_verified_address=account.email)
                challenge.delete()
                from apps.access_control.audit import record_access_audit_receipt
                record_access_audit_receipt(
                    # The audit primitive accepts only allow-listed authorization state, so the
                    # event carries no snapshot: action + actor/target + time is the evidence.
                    # No address, code or digest is ever written to the audit log.
                    actor=account, target=account, action=AUDIT_ACTION,
                )
        except DatabaseError:
            return _error("verification_unavailable", "Email verification is temporarily unavailable.", 503)
        return Response({"status": "verified", "email_verified": True})
