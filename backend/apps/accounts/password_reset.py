"""Opt-in Workspace password recovery. Distinct from Django /admin/ recovery.

WF-01.05 (owner-approved 16 Nov 2026): verified-email eligibility (D-21),
background delivery (D-20, development only), password-changed notice after
commit (D-22), Django's stateless token (D-23), and the feature gate stays off
(D-24). Protected executor mode refuses recovery: there is no reviewed
executor operation for it, and the permitted-writer boundary is never bypassed.
"""

import logging
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.access_control.models import AccountRole
from . import recovery_mail
from .models import Account
from .session_auth import WorkspaceSessionAPI

logger = logging.getLogger(__name__)
GENERIC_ACK = "If the account details match an eligible account, a password reset email will be sent."
LINK_INVALID = "This reset link is invalid or expired. Request a new reset link."
PASSWORD_FIELD_TEXT = "Choose a stronger password using the requirements shown."
CONFIRMATION_FIELD_TEXT = "Passwords do not match."
# P-03 / D-16: per-identity budget for reset requests, before any lookup or mail.
RESET_IDENTITY_RATES = ("3/hour", "6/day")


class ResetThrottle(SimpleRateThrottle):
    scope = "workspace_password_reset"
    rate = "4/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": request.META.get("REMOTE_ADDR", "unknown")}


class ResetDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_daily"
    rate = "20/day"


# P-03: the reset step has its own counters, so a burst of requests cannot block it.
class ResetConfirmThrottle(ResetThrottle):
    scope = "workspace_password_reset_confirm"
    rate = "4/min"


class ResetConfirmDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_confirm_daily"
    rate = "20/day"


def _enforce_reset_identity_budget(school_id):
    from .registration_staging import _IdentityThrottle, _digest

    digest = _digest("password-reset-school-id", school_id.strip().lower())
    for period, rate in enumerate(RESET_IDENTITY_RATES):
        throttle = _IdentityThrottle(digest, f"password-reset:school_id:{period}", rate)
        if not throttle.allow_request(None, None):
            raise exceptions.Throttled(wait=throttle.wait())


class PasswordResetRequestSerializer(serializers.Serializer):
    # Retain School ID (Staff ID for Instructors) plus registered email as the recovery contract.
    school_id = serializers.CharField(max_length=50, trim_whitespace=True)
    email = serializers.EmailField(max_length=150)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != {"school_id", "email"}:
            raise serializers.ValidationError("Provide School ID and registered email.")
        return super().to_internal_value(data)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=40)
    token = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    password_confirmation = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != set(self.fields):
            raise serializers.ValidationError("Provide the reset link details and new password.")
        return super().to_internal_value(data)

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": [CONFIRMATION_FIELD_TEXT]})
        return data


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


class PasswordResetRequestView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ResetThrottle, ResetDailyThrottle]

    def post(self, request):
        refusal = _refusal()
        if refusal is not None:
            return refusal
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _enforce_reset_identity_budget(data["school_id"])
        try:
            account = eligible_account_queryset().filter(
                school_id=data["school_id"], email__iexact=data["email"]
            ).first()
            if account:
                base = settings.WORKSPACE_PUBLIC_BASE_URL
                parts = urlsplit(base)
                if parts.scheme not in ("https", "http") or not parts.netloc or parts.username or parts.password or parts.fragment or parts.query:
                    raise ValueError("Invalid public application base URL")
                uid = urlsafe_base64_encode(force_bytes(account.pk))
                token = default_token_generator.make_token(account)
                # Fragment is not sent in HTTP requests or Referer headers.
                link = f"{base}/reset-password#{urlencode({'uid': uid, 'token': token})}"
                # D-20: delivered in the background so response time is the same
                # whether or not an account matched.
                recovery_mail.enqueue(
                    "reset_link",
                    "CTU-G Workspace password reset",
                    "A password reset was requested for your CTU-G Workspace account.\n\n"
                    f"Use this link within 30 minutes:\n{link}\n\n"
                    "If this wasn't you, ignore this email.",
                    account.email,
                )
        except Exception as exc:
            # Never reveal the target identity or reset token to API callers or logs.
            logger.warning("Workspace password reset request could not be completed (%s).", type(exc).__name__)
        return Response({"message": GENERIC_ACK}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ResetConfirmThrottle, ResetConfirmDailyThrottle]

    def handle_exception(self, exc):
        # P-01: return allowlisted field feedback instead of the generic 400 body.
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict):
            if {"uid", "token"} & set(exc.detail):
                return Response({"error": {"code": "reset_link_invalid", "message": LINK_INVALID}}, status=400)
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
        data = serializer.validated_data
        try:
            account_id = force_str(urlsafe_base64_decode(data["uid"]))
            if not account_id.isascii() or not account_id.isdecimal():
                raise ValueError("Invalid uid")
        except (ValueError, TypeError, UnicodeError, OverflowError):
            raise exceptions.ValidationError({"token": ["invalid"]})
        try:
            with transaction.atomic():
                account = Account.objects.select_for_update().filter(pk=int(account_id)).first()
                eligible = (
                    account is not None
                    and eligible_account_queryset().filter(pk=account.pk).exists()
                    and AccountRole.objects.filter(account=account, role__is_active=True).exists()
                )
                if not eligible or not default_token_generator.check_token(account, data["token"]):
                    raise exceptions.ValidationError({"token": ["invalid"]})
                try:
                    validate_password(data["password"], user=account)
                except DjangoValidationError as exc:
                    raise exceptions.ValidationError({"password": ["invalid"]}) from exc
                account.set_password(data["password"])
                account.save(update_fields=["password"])
                recipient = account.email
                # D-22: queued only if the password update commits.
                transaction.on_commit(lambda: recovery_mail.enqueue(
                    "password_changed",
                    "CTU-G Workspace password changed",
                    "The password for your CTU-G Workspace account was just changed.\n\n"
                    "If you made this change, no action is needed. "
                    "If you did not, contact support immediately.",
                    recipient,
                ))
        except DatabaseError:
            logger.warning("Workspace password reset confirmation database error.")
            return _recovery_unavailable()
        return Response({"message": "Password changed. You can now sign in."})
