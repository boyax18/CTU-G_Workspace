"""D-113 isolated role-context endpoint. Changes only the browser session selector."""
from django.contrib.auth import get_user
from rest_framework import exceptions
from rest_framework.response import Response

from .active_role_context import SESSION_ROLE_KEY, available_roles, context_enabled
from .session_auth import WorkspaceSessionAPI, _account_payload, _workspace_account


class RoleContextSwitchView(WorkspaceSessionAPI):
    http_method_names = ["post", "options"]

    def post(self, request):
        if not context_enabled():
            return Response({"error": {"code": "role_context_unavailable",
                                       "message": "Role switching is not activated."}}, status=503)
        # Defense in depth: isolated URL wiring or middleware ordering must
        # never make role switching usable against a protected executor that
        # cannot validate the active-role authority context.
        from apps.access_control.executor.client import enabled as executor_enabled
        from django.conf import settings
        if executor_enabled() and getattr(settings, "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED", False) is not True:
            return Response({"error": {"code": "role_context_unavailable",
                                       "message": "Role context is not available."}}, status=503)
        account = _workspace_account(get_user(request._request))
        if account is None:
            return Response({"error": {"code": "authentication_required",
                                       "message": "Sign in to continue."}}, status=401)
        data = request.data
        if (not isinstance(data, dict) or set(data) != {"role_id"}
                or type(data["role_id"]) is not int or data["role_id"] <= 0
                or data["role_id"] > 2147483647):
            raise exceptions.ValidationError("Select exactly one assigned role ID.")
        options = available_roles(account.pk)
        if not any(option["role_id"] == data["role_id"] for option in options):
            # No account/role enumeration, including revoked or inactive choices.
            raise exceptions.PermissionDenied("That role is not available.")
        # Server-side session mutation, not a role assignment or permission grant.
        request.session[SESSION_ROLE_KEY] = data["role_id"]
        return Response({"authenticated": True,
                         **_account_payload(account, active_role_id=data["role_id"])})
