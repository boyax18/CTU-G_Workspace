"""Public registration only; these endpoints never authenticate an account."""

import json
import logging

from django.core.exceptions import RequestDataTooBig
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control
from rest_framework import exceptions, status
from rest_framework.authentication import CSRFCheck
from rest_framework.parsers import BaseParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .serializers import RegistrationSerializer
from .services import RegistrationUnavailable, register_account

logger = logging.getLogger(__name__)


class RegistrationJSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, stream, media_type=None, parser_context=None):
        raw = stream.read(16_385)
        if len(raw) > 16_384:
            raise exceptions.ParseError("Request body is too large.")

        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result

        def invalid_constant(value):
            raise ValueError("Invalid JSON constant")

        try:
            return json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs, parse_constant=invalid_constant)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise exceptions.ParseError("Provide a valid JSON object.") from exc


class RegistrationBurstThrottle(SimpleRateThrottle):
    scope = "registration_burst"
    rate = "5/min"

    def get_cache_key(self, request, view):
        # Ignore untrusted client-supplied forwarding headers.
        return self.cache_format % {"scope": self.scope, "ident": request.META.get("REMOTE_ADDR", "unknown")}


class RegistrationDailyThrottle(RegistrationBurstThrottle):
    scope = "registration_daily"
    rate = "30/day"


class PublicJSONView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    parser_classes = [RegistrationJSONParser]

    def handle_exception(self, exc):
        if not isinstance(exc, exceptions.APIException):
            # DEBUG is enabled locally; never expose a technical error page or
            # submitted credentials through this public API.
            logger.error("Public registration request failed (%s).", type(exc).__name__)
            return Response(
                {"error": {"code": "registration_unavailable", "message": "Registration is temporarily unavailable. Please try again later."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = super().handle_exception(exc)
        codes = {
            400: ("validation_error", "Check the submitted registration details."),
            403: ("csrf_failed", "Security check failed. Refresh the page and try again."),
            405: ("method_not_allowed", "This request method is not supported."),
            406: ("not_acceptable", "Request an application/json response."),
            415: ("unsupported_media_type", "Send an application/json request."),
            429: ("throttled", "Too many requests. Please wait before trying again."),
        }
        code, message = codes.get(response.status_code, ("request_failed", "The request could not be completed."))
        error = {"code": code, "message": message}
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict):
            error["fields"] = exc.detail
        response.data = {"error": error}
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response


class CSRFView(PublicJSONView):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegistrationView(PublicJSONView):
    http_method_names = ["post", "options"]
    throttle_classes = [RegistrationBurstThrottle, RegistrationDailyThrottle]

    def initial(self, request, *args, **kwargs):
        # Anonymous SessionAuthentication skips CSRF: enforce it before parsing,
        # validation, hashing, or any database operations.
        check = CSRFCheck(lambda req: None)
        check.process_request(request)
        if check.process_view(request, None, (), {}):
            raise exceptions.PermissionDenied("CSRF validation failed.")
        super().initial(request, *args, **kwargs)

    def post(self, request):
        try:
            serializer = RegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            register_account(serializer.validated_data)
        except RequestDataTooBig as exc:
            raise exceptions.ParseError("Request body is too large.") from exc
        except RegistrationUnavailable:
            return Response(
                {"error": {"code": "registration_unavailable", "message": "Registration is temporarily unavailable. Please try again later."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {"message": "Registration request received. Eligible new accounts are pending administrative review."},
            status=status.HTTP_202_ACCEPTED,
        )
