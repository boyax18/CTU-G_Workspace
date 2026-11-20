"""D-113 deferred database regression. Run only in WF-03 consolidated testing."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from apps.accounts.active_role_context import bind_role_scope, allowed_role_ids
from apps.accounts.models import Account
from .models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from .services import get_effective_permissions, has_permission

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("D-113 tests require isolated config.test_settings.")


@override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
class ActiveRoleContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = Account.objects.create(school_id="D113-USER", request_status="Approved", is_active=True)
        cls.base = Role.objects.create(role_name="Student")
        cls.admin = Role.objects.create(role_name="Admin")
        cls.tech = Role.objects.create(role_name="Technical Super Admin")
        for r in (cls.base, cls.admin, cls.tech):
            AccountRole.objects.create(account=cls.account, role=r)
        cls.svc = Service.objects.create(service_name="D113 Test", service_code="d113_test")
        cls.codes = []
        for role, suffix in ((cls.base, "student"), (cls.admin, "admin"), (cls.tech, "tech")):
            p = Permission.objects.create(service=cls.svc, permission_code="d113." + suffix,
                permission_name=suffix, module_name="test", action_name="read")
            RolePermission.objects.create(role=role, permission=p)
            cls.codes.append(p)

    def test_default_no_scope_denies_all(self):
        self.assertEqual(get_effective_permissions(self.account), frozenset())

    def test_student_context_cannot_use_admin_or_technical(self):
        with bind_role_scope(self.account.pk, self.base.pk):
            self.assertEqual(get_effective_permissions(self.account), {"d113.student"})
            self.assertFalse(has_permission(self.account, "d113.admin"))
            self.assertFalse(has_permission(self.account, "d113.tech"))

    def test_technical_context_inherits_only_assigned_admin_stored_grants(self):
        with bind_role_scope(self.account.pk, self.tech.pk):
            self.assertEqual(get_effective_permissions(self.account), {"d113.admin", "d113.tech"})
        AccountRole.objects.filter(account=self.account, role=self.admin).delete()
        with bind_role_scope(self.account.pk, self.tech.pk):
            self.assertEqual(get_effective_permissions(self.account), {"d113.tech"})

    def test_unassigned_or_cross_account_role_refused(self):
        outsider = Account.objects.create(school_id="D113-OTHER", request_status="Approved", is_active=True)
        with bind_role_scope(outsider.pk, self.tech.pk):
            self.assertEqual(get_effective_permissions(self.account), frozenset())
        with bind_role_scope(self.account.pk, 999999):
            self.assertEqual(get_effective_permissions(self.account), frozenset())

    def test_direct_grant_never_bypasses_role_scope_and_deny_still_applies(self):
        direct = Permission.objects.create(service=self.svc, permission_code="d113.direct",
            permission_name="direct", module_name="test", action_name="read")
        AccountPermission.objects.create(account=self.account, permission=direct, effect="Grant")
        with bind_role_scope(self.account.pk, self.base.pk):
            self.assertFalse(has_permission(self.account, "d113.direct"))
        AccountPermission.objects.create(account=self.account, permission=self.codes[0], effect="Deny")
        with bind_role_scope(self.account.pk, self.base.pk):
            self.assertFalse(has_permission(self.account, "d113.student"))
