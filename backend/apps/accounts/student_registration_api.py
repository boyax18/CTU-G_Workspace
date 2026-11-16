"""CSRF-protected OTP endpoints; bearer challenge lives only in HttpOnly cookie."""
from django.conf import settings
from rest_framework import serializers
from rest_framework.response import Response

from .registration_staging import policy, student_verification_action, student_verification_status
from .api_errors import ERRORS, error_response
from .views import PublicJSONView, RegistrationView, RegistrationBurstThrottle

COOKIE = "ctug_student_registration"
COOKIE_PATH = "/api/v1/auth/"


def verification_response(result):
    result = dict(result)
    token = result.pop("browser_token", None)
    preserve_cookie = result.pop("preserve_verification_cookie", False) is True
    state = result["status"]
    if state in ERRORS:
        response = error_response(state)
        result.pop("message", None)
        response.data.update(result)
    elif state in {"verification_required", "existing_verification", "completed", "cancelled"}:
        response = Response(result, status=202 if state in {"verification_required", "existing_verification"} else 200)
    else:
        raise RuntimeError("Unexpected registration state.")
    if token:
        response.set_cookie(COOKIE, token, max_age=policy()["stage_seconds"],
                            httponly=True, secure=settings.SESSION_COOKIE_SECURE,
                            samesite="Strict", path=COOKIE_PATH)
    if state in {"completed", "cancelled", "expired"} or (state == "conflict" and not preserve_cookie):
        response.delete_cookie(COOKIE, path=COOKIE_PATH, samesite="Strict")
    return response


class OTPActionSerializer(serializers.Serializer):
    code = serializers.RegexField(r"\A[0-9]{6}\Z", trim_whitespace=False, max_length=6)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != {"code"}:
            raise serializers.ValidationError("Provide a six-digit verification code only.")
        return super().to_internal_value(data)


class StudentOTPThrottle(RegistrationBurstThrottle):
    scope = "student_registration_otp_burst"
    rate = "30/min"


class StudentOTPDailyThrottle(StudentOTPThrottle):
    scope = "student_registration_otp_daily"
    rate = "200/day"


class StudentVerificationStatusView(PublicJSONView):
    http_method_names = ["get", "options"]
    # Same IP budgets as the OTP actions, for both roles, checked before any
    # database work (WF-01 R-04, owner-approved 16 Nov 2026).
    throttle_classes = [StudentOTPThrottle, StudentOTPDailyThrottle]

    def get(self, request):
        if request.query_params.get("requested_role") == "Instructor":
            self.public_registration_role = "Instructor"
        result = student_verification_status(request.COOKIES.get(COOKIE))
        if request.query_params.get("requested_role") == "Instructor" and result.get("status") in {"verification_required", "existing_verification"} and "requested_role" not in result:
            # A query may select presentation, never reinterpret a legacy stage.
            result["requested_role"] = "Student"
        return verification_response(result)


class StudentVerificationActionView(RegistrationView):
    action = "verify"
    throttle_classes = [StudentOTPThrottle, StudentOTPDailyThrottle]

    def post(self, request):
        if request.query_params.get("requested_role") == "Instructor":
            self.public_registration_role = "Instructor"
        code = ""
        if self.action == "verify":
            serializer = OTPActionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            code = serializer.validated_data["code"]
        elif not isinstance(request.data, dict) or request.data:
            raise serializers.ValidationError("Provide an empty JSON object.")
        result = student_verification_action(request.COOKIES.get(COOKIE), self.action, code)
        return verification_response(result)


class StudentVerificationResendView(StudentVerificationActionView):
    action = "resend"


class StudentVerificationCancelView(StudentVerificationActionView):
    action = "cancel"
