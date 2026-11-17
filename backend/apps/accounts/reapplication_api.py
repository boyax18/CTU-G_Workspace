"""Explicitly gated public reapplication; no account enumeration or role grants."""

from django.conf import settings
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response

from .reapplication import (
    GENERIC_LINK_ACK, ReapplicationDenied, ReapplicationUnavailable,
    complete_reapplication, issue_reapplication_email_if_eligible,
)
from .serializers import RegistrationSerializer, StringField
from .views import RegistrationView


class ReapplicationAPIUnavailable(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Reapplication is not currently available."
    default_code = "reapplication_unavailable"


class ReapplicationLinkSerializer(serializers.Serializer):
    school_id = StringField(max_length=7, trim_whitespace=False)
    email = serializers.EmailField(max_length=150)

    def to_internal_value(self, data):
        if type(data) is not dict or set(data) != {"school_id", "email"}:
            raise serializers.ValidationError("Provide your School ID and registered email.")
        return super().to_internal_value(data)

    def validate_school_id(self, value):
        import re
        if not re.fullmatch(r"[0-9]{1,7}", value):
            raise serializers.ValidationError("School ID must contain 1 to 7 digits.")
        return value


class ReapplicationBaseView(RegistrationView):
    """Inherit JSON parser, explicit CSRF check, rate limits and no-store."""

    def initial(self, request, *args, **kwargs):
        if not getattr(settings, "WORKSPACE_REGISTRATION_REAPPLICATION_ENABLED", False):
            raise ReapplicationAPIUnavailable()
        super().initial(request, *args, **kwargs)


class ReapplicationLinkView(ReapplicationBaseView):
    http_method_names = ["post", "options"]

    def post(self, request):
        serializer = ReapplicationLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            issue_reapplication_email_if_eligible(**serializer.validated_data)
        except ReapplicationUnavailable:
            raise ReapplicationAPIUnavailable()
        return Response({"message": GENERIC_LINK_ACK}, status=status.HTTP_202_ACCEPTED)


class ReapplicationCompleteView(ReapplicationBaseView):
    http_method_names = ["post", "options"]

    def post(self, request):
        if type(request.data) is not dict:
            raise exceptions.ValidationError("Provide a registration object.")
        fields = set(RegistrationSerializer().fields)
        if set(request.data) - fields != {"reapplication_token"}:
            raise exceptions.ValidationError("Provide a valid full registration and verification token.")
        token = request.data["reapplication_token"]
        registration = {key: value for key, value in request.data.items()
                        if key != "reapplication_token"}
        serializer = RegistrationSerializer(data=registration)
        serializer.is_valid(raise_exception=True)
        try:
            complete_reapplication(token=token, data=serializer.validated_data)
        except ReapplicationDenied:
            return Response({"error": {
                "code": "invalid_reapplication_link",
                "message": "This verification link is invalid, expired or already used. Request a new link."
            }}, status=status.HTTP_400_BAD_REQUEST)
        except ReapplicationUnavailable:
            raise ReapplicationAPIUnavailable()
        return Response({"message": "Registration request received. It is pending administrative review."},
                        status=status.HTTP_202_ACCEPTED)
