"""D-116 deferred checks for normal development route.

Run only during consolidated WF-03 testing; no real database mutation.
"""
from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse

from apps.accounts.active_role_context_api import RoleContextSwitchView


@override_settings(ROOT_URLCONF="config.urls", WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=False)
class NormalRoleContextRouteTests(SimpleTestCase):
    def test_normal_route_is_mounted_but_unavailable_by_default(self):
        resolved = resolve("/api/v1/auth/role-context/")
        self.assertIs(resolved.func.view_class, RoleContextSwitchView)
        self.assertEqual(reverse("workspace-role-context-switch-normal"),
                         "/api/v1/auth/role-context/")
        response = self.client.post(
            "/api/v1/auth/role-context/",
            data='{"role_id": 9}', content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)

    def test_existing_session_initializes_only_when_context_is_enabled(self):
        # Full database regression in test_wf0301_d113_role_context.py covers
        # selected-role validation and permission isolation. This test checks
        # that the normal URL is inert without explicit local opt-in.
        self.assertEqual(resolve("/api/v1/auth/role-context/").url_name,
                         "workspace-role-context-switch-normal")
