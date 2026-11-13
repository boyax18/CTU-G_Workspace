"""Opt-in Workspace password recovery. Distinct from Django /admin/ recovery."""

import logging
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import DatabaseError, transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.access_control.models import AccountRole
from .models import Account
from .session_auth import WorkspaceSessionAPI

logger = logging.getLogger(__name__)
GENERIC_ACK = "If the account details match an eligible account, a password reset email will be sent."


class ResetThrottle(SimpleRateThrottle):
    scope = "workspace_password_reset"
    rate = "4/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": request.META.get("REMOTE_ADDR", "unknown")}


class ResetDailyThrottle(ResetThrottle):
    scope = "workspace_password_reset_daily"
    rate = "20/day"


class PasswordResetRequestSerializer(serializers.Serializer):
    # School ID plus email is needed because email is not unique in the ERD.
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
            raise serializers.ValidationError({"password_confirmation": ["Passwords do not match."]})
        return data


def eligible_account_queryset():
    return Account.objects.filter(
        is_active=True,
        request_status="Approved",
        is_staff=False,
        is_superuser=False,
        role_assignments__role__is_active=True,
    ).distinct()


class PasswordResetRequestView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ResetThrottle, ResetDailyThrottle]

    def post(self, request):
        if not getattr(settings, "WORKSPACE_PASSWORD_RESET_ENABLED", False):
            return Response({"error": {"code": "recovery_disabled", "message": "Password recovery is not available yet."}}, status=503)
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            account = eligible_account_queryset().filter(
                school_id=data["school_id"], email__iexact=data["email"]
            ).first()
            if account and account.email:
                base = settings.WORKSPACE_PUBLIC_BASE_URL
                parts = urlsplit(base)
                if parts.scheme not in ("https", "http") or not parts.netloc or parts.username or parts.password or parts.fragment or parts.query:
                    raise ValueError("Invalid public application base URL")
                uid = urlsafe_base64_encode(force_bytes(account.pk))
                token = default_token_generator.make_token(account)
                # Fragment is not sent in HTTP requests or Referer headers.
                link = f"{base}/reset-password#{urlencode({'uid': uid, 'token': token})}"
                send_mail(
                    "CTU-G Workspace password reset",
                    "A password reset was requested for your CTU-G Workspace account.\n\n"
                    f"Use this link within 30 minutes:\n{link}\n\n"
                    "If this wasn't you, ignore this email.",
                    settings.DEFAULT_FROM_EMAIL,
                    [account.email],
                    fail_silently=False,
                )
        except Exception as exc:
            # Never reveal the target identity or reset token to API callers or logs.
            logger.warning("Workspace password reset request could not be completed (%s).", type(exc).__name__)
        return Response({"message": GENERIC_ACK}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ResetThrottle, ResetDailyThrottle]

    def post(self, request):
        if not getattr(settings, "WORKSPACE_PASSWORD_RESET_ENABLED", False):
            return Response({"error": {"code": "recovery_disabled", "message": "Password recovery is not available yet."}}, status=503)
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            account_id = force_str(urlsafe_base64_decode(data["uid"]))
            if not account_id.isascii() or not account_id.isdecimal():
                raise ValueError("Invalid uid")
        except (ValueError, TypeError, UnicodeError, OverflowError):
            raise exceptions.ValidationError({"token": ["This reset link is invalid or expired."]})
        try:
            with transaction.atomic():
                account = Account.objects.select_for_update().filter(pk=int(account_id)).first()
                eligible = (
                    account is not None
                    and account.is_active
                    and account.request_status == "Approved"
                    and not account.is_staff
                    and not account.is_superuser
                    and AccountRole.objects.filter(account=account, role__is_active=True).exists()
                )
                if not eligible or not default_token_generator.check_token(account, data["token"]):
                    raise exceptions.ValidationError({"token": ["This reset link is invalid or expired."]})
                try:
                    validate_password(data["password"], user=account)
                except DjangoValidationError as exc:
                    raise exceptions.ValidationError({"password": exc.messages}) from exc
                account.set_password(data["password"])
                account.save(update_fields=["password"])
        except DatabaseError:
            logger.warning("Workspace password reset confirmation database error.")
            return Response({"error": {"code": "recovery_unavailable", "message": "Password recovery is temporarily unavailable."}}, status=503)
        return Response({"message": "Password changed. You can now sign in."})
