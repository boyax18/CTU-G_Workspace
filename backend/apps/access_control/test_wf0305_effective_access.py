"""WF-03.05 deferred regressions: execute in consolidated WF-03 phase only."""
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import URLPattern, URLResolver
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .effective_access_api import (
    EffectiveAccessSearchView, EffectiveAccessRolesView, EffectiveAccessDetailView,
)
from .effective_access_urls import urlpatterns


class WF0305RouteGuards(SimpleTestCase):
    def test_isolated_routes_only(self):
        self.assertEqual({str(p.pattern):p.callback.cls for p in urlpatterns if isinstance(p, URLPattern)}, {
            'accounts/': EffectiveAccessSearchView,
            'accounts/<int:account_id>/roles/': EffectiveAccessRolesView,
            'accounts/<int:account_id>/roles/<int:role_id>/': EffectiveAccessDetailView,
        })
        from config.urls import urlpatterns as normal
        self.assertFalse(any(isinstance(p,URLResolver) and str(p.pattern)=='api/v1/admin/effective-access/' for p in normal))
        from config.review_local_urls import urlpatterns as local
        from config.review_sandbox_urls import urlpatterns as sandbox
        for routes in (local,sandbox):
            self.assertEqual(sum(isinstance(p,URLResolver) and str(p.pattern)=='api/v1/admin/effective-access/' for p in routes),1)

    @override_settings(WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED=False)
    def test_gate_off(self):
        self.assertFalse(EffectiveAccessSearchView().review_gate_open())

    @override_settings(WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED=True, WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
    def test_executor_blocks_inspection(self):
        from apps.accounts.registration_review_api import ReviewAPIUnavailable
        with patch('apps.access_control.effective_access_api.executor_enabled',return_value=True):
            with self.assertRaises(ReviewAPIUnavailable):
                EffectiveAccessDetailView().initial(None)

if not getattr(settings, 'REGISTRATION_TEST_DATABASE', '').startswith('test_ctug_registration_'):
    raise ImproperlyConfigured('WF-03.05 database tests require isolated config.test_settings.')


@override_settings(WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True)
class WF0305EvaluatorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.accounts.models import Account
        from .models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
        cls.account = Account.objects.create(school_id='WF0305-S',request_status='Approved',is_active=True)
        cls.student = Role.objects.create(role_name='Student')
        cls.instructor = Role.objects.create(role_name='Instructor')
        for role in (cls.student,cls.instructor):
            AccountRole.objects.create(account=cls.account,role=role)
        cls.service = Service.objects.create(service_name='WF0305 service',service_code='wf0305')
        cls.student_permission = Permission.objects.create(service=cls.service,permission_code='wf0305.student',
            permission_name='Student',module_name='test',action_name='read')
        cls.instructor_permission = Permission.objects.create(service=cls.service,permission_code='wf0305.instructor',
            permission_name='Instructor',module_name='test',action_name='read')
        RolePermission.objects.create(role=cls.student,permission=cls.student_permission)
        RolePermission.objects.create(role=cls.instructor,permission=cls.instructor_permission)

    def test_selected_role_isolated_from_other_role(self):
        from apps.accounts.active_role_context import bind_role_scope
        from .services import get_effective_permissions
        with bind_role_scope(self.account.pk,self.student.pk):
            self.assertEqual(get_effective_permissions(self.account),{'wf0305.student'})

    def test_service_shutdown_blocks_access(self):
        from apps.accounts.active_role_context import bind_role_scope
        from .services import has_permission
        with bind_role_scope(self.account.pk,self.student.pk):
            self.assertTrue(has_permission(self.account,'wf0305.student'))
            type(self.service).objects.filter(pk=self.service.pk).update(is_active=False)
            self.assertFalse(has_permission(self.account,'wf0305.student'))

    def test_explicit_deny_wins(self):
        from apps.accounts.active_role_context import bind_role_scope
        from .models import AccountPermission
        from .services import has_permission
        AccountPermission.objects.create(account=self.account,permission=self.student_permission,effect='Deny')
        with bind_role_scope(self.account.pk,self.student.pk):
            self.assertFalse(has_permission(self.account,'wf0305.student'))
