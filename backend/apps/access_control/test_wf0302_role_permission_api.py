"""WF-03.02 read and routing contracts (defer execution to consolidated WF-03 tests)."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver

from .role_permission_api import (
    RolePermissionChangeView, RolePermissionListView, RolePermissionRolesView,
    ReviewAPIUnavailable,
)
from .role_permission_urls import urlpatterns as role_urls


class WF0302IsolatedRoutingTests(SimpleTestCase):
    def test_exact_role_permission_routes(self):
        paths = {str(item.pattern): item.callback.cls for item in role_urls if isinstance(item, URLPattern)}
        self.assertEqual(paths, {
            'roles/': RolePermissionRolesView,
            'roles/<int:role_id>/permissions/': RolePermissionListView,
            'roles/<int:role_id>/permissions/<int:permission_id>/<str:action>/': RolePermissionChangeView,
        })
        self.assertEqual(RolePermissionRolesView.http_method_names, ['get', 'head', 'options'])
        self.assertEqual(RolePermissionListView.http_method_names, ['get', 'head', 'options'])
        self.assertEqual(RolePermissionChangeView.http_method_names, ['post', 'options'])

    def test_not_mounted_in_standard_urlconf(self):
        from config.urls import urlpatterns
        self.assertFalse(any(isinstance(item, URLResolver) and
            str(item.pattern) == 'api/v1/admin/role-permissions/' for item in urlpatterns))

    def test_only_isolated_profiles_mount_the_route(self):
        from config.review_local_urls import urlpatterns as local
        from config.review_sandbox_urls import urlpatterns as sandbox
        for patterns in (local, sandbox):
            self.assertEqual(sum(isinstance(item, URLResolver) and
                str(item.pattern) == 'api/v1/admin/role-permissions/' for item in patterns), 1)

    @override_settings(WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED=False)
    def test_gate_is_off_without_explicit_activation(self):
        for view in (RolePermissionRolesView(), RolePermissionListView(), RolePermissionChangeView()):
            self.assertFalse(view.review_gate_open())

    @override_settings(WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED=True)
    def test_protected_executor_refuses_even_read_only_endpoints(self):
        for view in (RolePermissionRolesView(), RolePermissionListView(), RolePermissionChangeView()):
            with patch('apps.access_control.role_permission_api.executor_enabled', return_value=True):
                with self.assertRaises(ReviewAPIUnavailable):
                    view.initial(None)
