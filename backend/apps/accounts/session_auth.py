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


# WF-01.03 P-05 / D-16 (owner-approved 16 Nov 2026): a per-identity budget in
# addition to the per-IP throttles above, so guessing spread across many IP
# addresses is still bounded per School ID / Staff ID. Defaults equal the IP
# budgets; the values remain an open policy decision. No account lockout.
LOGIN_IDENTITY_RATES = ("8/min", "40/hour")


def _enforce_login_identity_budget(school_id):
    """Raise Throttled when this normalized identifier exceeds its budget.

    The cache key holds only a keyed digest (D-14 mechanism), never the raw ID.
    """
    from .registration_staging import _IdentityThrottle, _digest

    digest = _digest("login-school-id", school_id.strip().lower())
    for period, rate in enumerate(LOGIN_IDENTITY_RATES):
        throttle = _IdentityThrottle(digest, f"login:school_id:{period}", rate)
        if not throttle.allow_request(None, None):
            raise exceptions.Throttled(wait=throttle.wait())


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
        from .api_errors import request_id

        response = super().finalize_response(request, response, *args, **kwargs)
        # WF-01.03 P-04: a safe opaque reference the UI may show ("Request
        # reference"), the same helper the public registration API uses.
        response["X-Request-ID"] = request_id(request)
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
        # Before any password hashing or executor call.
        _enforce_login_identity_budget(values["school_id"])
        from apps.access_control.executor.client import enabled, authenticate_actor
        proof = None
        if enabled():
            from apps.access_control.executor.errors import AuthenticationDenied
            try:
                verified = authenticate_actor(values["school_id"], values["password"])
            except AuthenticationDenied:
                return Response({"error": {"code": "invalid_credentials", "message": "Unable to sign in with these credentials."}}, status=401)
            proof = verified["proof"]
            account = Account.objects.filter(pk=verified["actor_id"]).first()
            if account is not None:
                account.backend = "django.contrib.auth.backends.ModelBackend"
        else:
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
        # WF-02.05 D-66: login() has just bound the session to the current suspension epoch.
        # Re-read eligibility AFTER that, from the database: a suspension committed before the
        # epoch was read is seen here (sign-out, refuse); one committed after it changes the
        # epoch, so this session already fails the next request's hash check.
        if _workspace_account(Account.objects.filter(pk=account.pk).first()) is None:
            logout(request._request)
            return Response(
                {"error": {"code": "invalid_credentials", "message": "Unable to sign in with these credentials."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if proof is not None:
            request.session["workspace_executor_proof"] = proof
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
