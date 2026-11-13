"""No database writes: framework superuser Admin visibility is read-only."""

from types import SimpleNamespace

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole,
    Permission, Role, RolePermission, Service,
)
from .models import Account, UserProfile


class FrameworkAdminReadOnlyTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/admin/")

    def _as(self, *, staff=True, superuser=True, active=True):
        self.request.user = SimpleNamespace(
            is_authenticated=True,
            is_staff=staff,
            is_superuser=superuser,
            is_active=active,
        )
        return self.request

    def test_expected_models_registered(self):
        models = (
            Account, UserProfile, Role, AccountRole, Service, Permission,
            RolePermission, AccountPermission, AccessAuditLog,
        )
        for model in models:
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

    def test_superuser_sees_registered_models(self):
        request = self._as()
        for model_admin in admin.site._registry.values():
            if model_admin.model._meta.app_label in ("accounts", "access_control"):
                with self.subTest(model=model_admin.model.__name__):
                    self.assertTrue(model_admin.has_module_permission(request))
                    self.assertTrue(model_admin.has_view_permission(request))

    def test_staff_non_superuser_cannot_view(self):
        request = self._as(staff=True, superuser=False)
        for model in (Account, Role, AccessAuditLog):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_module_permission(request))
            self.assertFalse(model_admin.has_view_permission(request))

    def test_inactive_superuser_cannot_view(self):
        request = self._as(active=False)
        self.assertFalse(admin.site._registry[Account].has_view_permission(request))

    def test_superuser_cannot_add_change_or_delete(self):
        request = self._as()
        for model in (Account, UserProfile, Role, AccountRole, Service, Permission,
                      RolePermission, AccountPermission, AccessAuditLog):
            model_admin = admin.site._registry[model]
            with self.subTest(model=model.__name__):
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request))
                self.assertFalse(model_admin.has_delete_permission(request))
                self.assertEqual(model_admin.get_actions(request), {})

    def test_secrets_are_not_displayed(self):
        account_admin = admin.site._registry[Account]
        fields = set(account_admin.fields) | set(account_admin.list_display)
        for secret in ("password", "password_reset_token", "password_reset_token_expires"):
            self.assertNotIn(secret, fields)
        audit_admin = admin.site._registry[AccessAuditLog]
        self.assertNotIn("old_value", audit_admin.fields)
        self.assertNotIn("new_value", audit_admin.fields)
        self.assertNotIn("reason", audit_admin.fields)
