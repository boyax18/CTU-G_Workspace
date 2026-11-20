"""Safe contract factored from PublicJSONView; no global DRF override."""
import math
import uuid

from django.core.exceptions import RequestDataTooBig
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from .services import RegistrationUnavailable

INSTRUCTOR_STAFF_ID_ERROR = "Staff ID must contain 1 to 7 digits only."
INSTRUCTOR_SCHOOL_FIELDS_ERROR = "Student-only school information is not accepted for Instructor registration."
ERRORS = {
    "validation_error": (400, "Check the submitted registration details."),
    "otp_invalid": (400, "The verification code is incorrect. Please try again."),
    "otp_expired": (400, "The code has expired or is unavailable. Request a new code."),
    "attempts_exhausted": (400, "Too many incorrect codes. Cancel this attempt or wait for it to expire before starting again."),
    "csrf_failed": (403, "Security check failed. Refresh the page and try again."),
    "authentication_required": (401, "Sign in to continue."),
    "access_denied": (403, "You cannot perform this action."),
    "not_found": (404, "The requested resource is unavailable."),
    "method_not_allowed": (405, "This request method is not supported."),
    "not_acceptable": (406, "Request an application/json response."),
    "unsupported_media_type": (415, "Send an application/json request."),
    "conflict": (409, "We could not complete this registration. Please check your information or contact support."),
    "expired": (410, "This registration has expired. Start a new registration."),
    "throttled": (429, "Too many requests. Please wait before trying again."),
    "resend_cooldown": (429, "Please wait before requesting another code."),
    "resends_exhausted": (429, "The resend limit has been reached. Cancel this attempt or wait for it to expire."),
    "delivery_failed": (503, "We could not send the verification email. Your details are saved temporarily; try resending after the waiting period."),
    "registration_unavailable": (503, "Registration is temporarily unavailable. Please try again later."),
    "server_error": (500, "We could not complete this request. Please try again later."),
    "request_failed": (400, "The request could not be completed."),
}
STATUS_CODES = {
    400: "validation_error", 401: "authentication_required", 403: "csrf_failed", 404: "not_found",
    405: "method_not_allowed", 406: "not_acceptable", 409: "conflict", 410: "expired",
    415: "unsupported_media_type", 429: "throttled", 500: "server_error", 503: "registration_unavailable",
}
FIELDS = {
    "school_id": "School ID must contain 1 to 7 digits only.", "email": "Enter a valid email address.",
    "first_name": "Enter a valid first name.", "middle_name": "Enter a valid middle name.",
    "last_name": "Enter a valid last name.", "suffix": "Enter a valid suffix.",
    "requested_role": "Select Student or Instructor.",
    "password": "Choose a stronger password using the requirements shown.",
    "password_confirmation": "Passwords do not match.", "code": "Enter a six-digit verification code.",
    "non_field_errors": "Check the submitted registration details.",
}


def public_fields(detail, *, instructor=False):
    """Translate validator codes to fixed text; never echo input/detail strings."""
    if not isinstance(detail, dict):
        return {}
    fields = {}
    for name, value in detail.items():
        if name not in FIELDS:
            continue
        values = value if isinstance(value, (list, tuple)) else [value]
        codes = {getattr(item, "code", "invalid") for item in values}
        if instructor and "student_only_fields" in codes:
            text = INSTRUCTOR_SCHOOL_FIELDS_ERROR
        elif codes & {"required", "blank", "null"}:
            text = "This field is required."
        elif "max_length" in codes:
            text = "This value is too long."
        else:
            text = INSTRUCTOR_STAFF_ID_ERROR if instructor and name == "school_id" else FIELDS[name]
        fields[name] = [text]
    return fields


def request_id(request):
    value = getattr(request, "public_api_request_id", None)
    if value is None:
        value = uuid.uuid4().hex
        request.public_api_request_id = value
    return value


def error_response(code, *, fields=None):
    status, message = ERRORS[code]
    error = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return Response({"error": error}, status=status)


def response_for_exception(exc, view):
    if isinstance(exc, RequestDataTooBig):
        exc = exceptions.ParseError()
    if isinstance(exc, (RegistrationUnavailable, WriterBoundaryUnavailable)):
        view.public_api_failure_kind = "writer_boundary" if isinstance(exc, WriterBoundaryUnavailable) else "dependency"
        return error_response("registration_unavailable")
    if not isinstance(exc, exceptions.APIException):
        view.public_api_failure_kind = "unexpected"
        return error_response("registration_unavailable")
    # Keep DRF Retry-After/authentication headers and rollback semantics.
    response = exception_handler(exc, {"view": view, "request": view.request})
    code = STATUS_CODES.get(response.status_code, "request_failed")
    response.data = {"error": {"code": code, "message": ERRORS[code][1]}}
    if isinstance(exc, exceptions.ValidationError):
        fields = public_fields(exc.detail, instructor=getattr(view, "public_registration_role", None) == "Instructor")
        if fields:
            response.data["error"]["fields"] = fields
    return response


def normalize_error(response, request):
    """Also covers explicit OTP errors and strips all unrecognized error data."""
    status = response.status_code
    original = response.data if isinstance(response.data, dict) else {}
    instructor = original.get("requested_role") == "Instructor"
    detail = original.get("error") if isinstance(original.get("error"), dict) else {}
    code = detail.get("code")
    if not isinstance(code, str) or code not in ERRORS or ERRORS[code][0] != status:
        code = STATUS_CODES.get(status, "request_failed")
    error = {"code": code, "message": ERRORS[code][1], "request_id": request_id(request)}
    if code == "validation_error" and isinstance(detail.get("fields"), dict):
        fields = {}
        safe_messages = set(FIELDS.values()) | {"This field is required.", "This value is too long."}
        if instructor:
            safe_messages |= {INSTRUCTOR_STAFF_ID_ERROR, INSTRUCTOR_SCHOOL_FIELDS_ERROR}
        for name, values in detail["fields"].items():
            if name in FIELDS and isinstance(values, list):
                fields[name] = [text if text in safe_messages else FIELDS[name] for text in values[:1] if isinstance(text, str)] or [FIELDS[name]]
        if fields:
            error["fields"] = fields
    body = {"error": error}
    if original.get("status") == code:
        body["status"] = code
    for name in ("expires_in", "retry_after", "attempts_remaining", "resends_remaining"):
        value = original.get(name)
        if type(value) is int and 0 <= value <= 86400:
            body[name] = value
    if type(original.get("delivery_sent")) is bool:
        body["delivery_sent"] = original["delivery_sent"]
    retry = body.get("retry_after") if code == "resend_cooldown" else response.get("Retry-After")
    try:
        retry = math.ceil(float(retry))
    except (ValueError, TypeError, OverflowError):
        retry = None
    if retry is not None and 0 <= retry <= 86400:
        error["retry_after"] = retry
        response["Retry-After"] = str(retry)
    response.data = body
    return code
