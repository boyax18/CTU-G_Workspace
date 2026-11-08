"""CTU-G Workspace browser session API (not Django Admin authentication).

No account approval or role grant occurs in these endpoints.  Every request that
claims a Workspace identity rechecks the database's current account/role state.
"""

import logging

from django.contrib.auth import authenticate, get_user, login, logout
from django.core.exceptions import RequestDataTooBig
from django.utils.cache import patch_cache_control
from rest_framework import exceptions, serializers, status
from rest_framework.authentication import CSRFCheck
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.access_control.models import AccountRole
from apps.access_control.services import get_effective_permissions
from .models import Account
from .views import RegistrationJSONParser

logger = logging.getLogger(__name__)


class LoginBurstThrottle(SimpleRateThrottle):
    scope = "workspace_login_burst"
    rate = "8/min"

    def get_cache_key(self, request, view):
        # Never trust X-Forwarded-For from an unverified proxy.
        address = request.META.get("REMOTE_ADDR", "unknown")
        return self.cache_format % {"scope": self.scope, "ident": address}


class LoginHourlyThrottle(LoginBurstThrottle):
    scope = "workspace_login_hourly"
    rate = "40/hour"


class LoginSerializer(serializers.Serializer):
    school_id = serializers.CharField(max_length=50, trim_whitespace=True)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class WorkspaceSessionAPI(APIView):
    """Use direct Django session reads; DRF anonymous CSRF bypass is not allowed."""

    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    parser_classes = [RegistrationJSONParser]

    def initial(self, request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            # APIView is csrf_exempt by default, and DRF only enforces CSRF for
            # authenticated SessionAuthentication requests.  Check even when
            # the visitor is anonymous, before parsing credentials or throttling.
            check = CSRFCheck(lambda req: None)
            check.process_request(request)
            if check.process_view(request, None, (), {}):
                raise exceptions.PermissionDenied("Invalid CSRF token or origin.")
        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response

    def handle_exception(self, exc):
        if isinstance(exc, RequestDataTooBig):
            exc = exceptions.ParseError("Request body is too large.")
        if not isinstance(exc, exceptions.APIException):
            logger.error("Workspace authentication failed (%s).", type(exc).__name__)
            return Response(
                {"error": {"code": "auth_unavailable", "message": "Authentication is temporarily unavailable."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = super().handle_exception(exc)
        by_status = {
            400: ("invalid_request", "Check the submitted data."),
            403: ("csrf_failed", "Security check failed. Refresh the page and try again."),
            405: ("method_not_allowed", "This method is not supported."),
            406: ("not_acceptable", "Accept application/json."),
            415: ("unsupported_media_type", "Send application/json."),
            429: ("too_many_attempts", "Too many attempts. Please try again later."),
        }
        code, message = by_status.get(
            response.status_code, ("request_failed", "Unable to complete the request.")
        )
        response.data = {"error": {"code": code, "message": message}}
        return response


def _workspace_account(user):
    """Return a current eligible Workspace identity or None; never use request roles."""
    if not isinstance(user, Account) or not user.pk:
        return None
    # Framework administrators belong to /admin/, never the Workspace UI.
    if user.is_staff or user.is_superuser:
        return None
    # Django's session backend loads a user each request. Recheck current
    # approval and at least one *active assigned* role, not requested_role.
    if not AccountRole.objects.filter(
        account_id=user.pk,
        account__is_active=True,
        account__request_status="Approved",
        role__is_active=True,
    ).exists():
        return None
    return user


def _account_payload(account):
    roles = sorted(set(AccountRole.objects.filter(
        account_id=account.pk,
        account__is_active=True,
        account__request_status="Approved",
        role__is_active=True,
    ).values_list("role__role_name", flat=True)))
    return {
        "account": {"school_id": account.school_id, "roles": roles},
        # Point-in-time UI hints, NEVER authorization or session-stored grants.
        "permissions": sorted(get_effective_permissions(account)),
    }


class LoginView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [LoginBurstThrottle, LoginHourlyThrottle]

    def post(self, request):
        if not isinstance(request.data, dict):
            raise exceptions.ParseError("Expected a JSON object.")
        if set(request.data) - {"school_id", "password"}:
            raise exceptions.ValidationError("Unsupported login fields.")
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        account = authenticate(
            request=request._request,
            school_id=values["school_id"],
            password=values["password"],
        )
        if _workspace_account(account) is None:
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Unable to sign in with these credentials."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        payload = _account_payload(account)
        if not payload["account"]["roles"]:
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Unable to sign in with these credentials."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        # Compute the response before creating the session, so a database error
        # never leaves behind a logged-in session and a failed API response.
        login(request._request, account)
        return Response({"authenticated": True, **payload})


class LogoutView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]

    def post(self, request):
        # Always allow a CSRF-verified browser to discard its own Django
        # session, including one that's lost Workspace eligibility.
        logout(request._request)
        return Response({"authenticated": False})


class SessionView(WorkspaceSessionAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        # DRF authentication_classes=[] marks request.user anonymous; read
        # the real Django session directly rather than trusting DRF request.user.
        account = _workspace_account(get_user(request._request))
        if account is None:
            return Response({"authenticated": False})
        return Response({"authenticated": True, **_account_payload(account)})
