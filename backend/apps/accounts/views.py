"""Public registration only; these endpoints never authenticate an account."""

import json
import logging

from django.core.exceptions import RequestDataTooBig
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework.parsers import BaseParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .serializers import RegistrationSerializer
from .services import register_account

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

    def initialize_request(self, request, *args, **kwargs):
        from .api_errors import request_id
        request = super().initialize_request(request, *args, **kwargs)
        request_id(request)
        return request

    def handle_exception(self, exc):
        from .api_errors import response_for_exception
        return response_for_exception(exc, self)

    def finalize_response(self, request, response, *args, **kwargs):
        from .api_errors import normalize_error, request_id
        if response.status_code >= 400 and isinstance(response.data, dict):
            if response.data.get("requested_role", getattr(self, "public_registration_role", None)) == "Instructor":
                response.data["requested_role"] = "Instructor"
        response["X-Request-ID"] = request_id(request)
        if response.status_code >= 400:
            code = normalize_error(response, request)
            event = {
                "event": "public_api_error",
                "request_id": request_id(request), "error_code": code, "http_status": response.status_code,
                "operation": type(self).__name__, "failure_kind": getattr(self, "public_api_failure_kind", "expected"),
            }
            logger.log(logging.ERROR if response.status_code >= 500 else logging.INFO,
                       json.dumps(event, sort_keys=True), extra=event)
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
            if isinstance(request.data, dict) and request.data.get("requested_role") == "Instructor":
                self.public_registration_role = "Instructor"
            serializer = RegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data["requested_role"] in {"Student", "Instructor"}:
                from .student_registration_api import COOKIE, verification_response
                result = register_account(serializer.validated_data, registration_token=request.COOKIES.get(COOKIE))
                return verification_response(result)
        except RequestDataTooBig as exc:
            raise exceptions.ParseError("Request body is too large.") from exc
        raise RuntimeError("Unsupported public registration role.")
