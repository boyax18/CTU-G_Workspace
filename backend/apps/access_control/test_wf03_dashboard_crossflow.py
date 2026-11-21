"""Task 4: six-subflow browser-session -> isolated HTTP journey.

This suite is exclusively for config.test_settings' randomly named disposable MySQL
schema. It uses the actual Django Client, session role switching, CSRF, and
review-local URL wiring. NO real account, persistent DB, or protected executor.
It does not claim to replace human browser/UI acceptance or production activation.
"""
import json

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings

from apps.accounts.active_role_context import SESSION_ROLE_KEY
from apps.accounts.models import Account
from .models import AccountRole, Permission, Role, RolePermission, Service, AccessAuditLog, AccountPermission

if not getattr(settings, 'REGISTRATION_TEST_DATABASE', '').startswith('test_ctug_registration_'):
    raise ImproperlyConfigured('WF-03 cross-flow tests require config.test_settings.')
if settings.DATABASES['default']['NAME'] != settings.REGISTRATION_TEST_DATABASE:
    raise ImproperlyConfigured('WF-03 cross-flow tests refuse a non-isolated database.')

FLAGS = dict(
    ROOT_URLCONF='config.review_local_urls',
    MIDDLEWARE=[*settings.MIDDLEWARE, 'apps.accounts.active_role_context.ActiveRoleContextMiddleware'],
    WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED=True,
    WORKSPACE_ROLE_ASSIGNMENT_ENABLED=True,
    WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED=True,
    WORKSPACE_WF0302_ROLE_PERMISSION_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED=True,
    WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED=True,
    WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED=False,
    WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED=True,
    WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED=True,
)

BASE = '/api/v1/admin/'
ROLE_SWITCH = '/api/v1/auth/role-context/'


@override_settings(**FLAGS)
class WF03DashboardCrossFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.accounts_service = Service.objects.create(service_name='Accounts', service_code='accounts')
        cls.governance_service = Service.objects.create(service_name='Access Control', service_code='access_control')
        cls.student_service = Service.objects.create(service_name='Task4 Synthetic', service_code='wf03_task4')
        cls.admin = Role.objects.create(role_name='Admin')
        cls.technical = Role.objects.create(role_name='Technical Super Admin')
        cls.student_role = Role.objects.create(role_name='Student')
        cls.instructor = Role.objects.create(role_name='Instructor')

        def approved(code, roles):
            account = Account.objects.create_user(school_id=code, password='Test-Only!48124')
            Account.objects.filter(pk=account.pk).update(request_status='Approved', is_active=True)
            for role in roles:
                AccountRole.objects.create(account=account, role=role)
            return Account.objects.get(pk=account.pk)

        cls.actor = approved('TASK4-TECH', [cls.admin, cls.technical])
        cls.school_admin = approved('TASK4-ADMIN', [cls.admin])
        cls.student = approved('TASK4-STUDENT', [cls.student_role, cls.instructor])

        for code in (
            'access_control.admin_assignments.manage',
            'access_control.role_permissions.manage',
            'access_control.account_permissions.manage',
            'access_control.effective_permissions.inspect',
            'access_control.audit.read',
        ):
            p = Permission.objects.create(
                service=cls.governance_service, permission_code=code, permission_name=code,
                module_name='test', action_name='read',
            )
            RolePermission.objects.create(role=cls.technical, permission=p)
        cls.read_permission = Permission.objects.create(
            service=cls.student_service, permission_code='wf03.task4.read',
            permission_name='Synthetic read', module_name='test', action_name='read',
        )
        RolePermission.objects.create(role=cls.student_role, permission=cls.read_permission)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.login(self.actor, self.admin)

    def login(self, account, role):
        self.client.force_login(Account.objects.get(pk=account.pk))
        session = self.client.session
        session[SESSION_ROLE_KEY] = role.pk
        session.save()
        self.client.cookies[settings.CSRF_COOKIE_NAME] = 'a' * 32

    def get(self, suffix):
        return self.client.get(BASE + suffix, HTTP_ACCEPT='application/json')

    def post(self, path, payload):
        return self.client.post(
            path, data=json.dumps(payload), content_type='application/json',
            HTTP_ACCEPT='application/json', HTTP_X_CSRFTOKEN='a' * 32,
        )

    def paths(self):
        return (
            ('WF-03.01 Role assignments', 'role-assignments/', 'results'),
            ('WF-03.02 Role permissions', 'role-permissions/roles/', 'roles'),
            ('WF-03.03 Account Grants', 'account-grants/accounts/?q=TASK4-STUDENT', 'accounts'),
            ('WF-03.04 Restrictions', 'account-restrictions/accounts/?q=TASK4-STUDENT', 'accounts'),
            ('WF-03.05 Effective access', 'effective-access/accounts/?q=TASK4-STUDENT', 'accounts'),
            ('WF-03.06 Audit history', 'access-audit/events/?page=1', 'events'),
        )

    def switch(self, role):
        return self.post(ROLE_SWITCH, {'role_id': role.pk})

    def test_switch_from_school_admin_to_technical_and_back_gates_all_six(self):
        # No extra permission leaks through a multi-role account's School Admin context.
        for name, path, _ in self.paths():
            with self.subTest(role='School Admin', subflow=name):
                self.assertEqual(self.get(path).status_code, 403)
        response = self.switch(self.technical)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['authenticated'])
        self.assertEqual(response.json()['role_context']['active_role_id'], self.technical.pk)
        self.assertIn('access_control.audit.read', response.json()['permissions'])
        self.assertEqual(self.client.session[SESSION_ROLE_KEY], self.technical.pk)
        for name, path, key in self.paths():
            with self.subTest(role='Technical Super Admin', subflow=name):
                reply = self.get(path)
                self.assertEqual(reply.status_code, 200, reply.content)
                self.assertIn(key, reply.json())
                self.assertEqual(reply.get('Cache-Control'), 'no-store')
        response = self.switch(self.admin)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['role_context']['active_role_id'], self.admin.pk)
        self.assertNotIn('access_control.audit.read', response.json()['permissions'])
        for name, path, _ in self.paths():
            with self.subTest(role='School Admin again', subflow=name):
                self.assertEqual(self.get(path).status_code, 403)

    def test_role_assignment_and_five_other_directories_return_expected_shapes(self):
        self.assertEqual(self.switch(self.technical).status_code, 200)
        role_list = self.get('role-assignments/')
        self.assertEqual(role_list.status_code, 200, role_list.content)
        self.assertTrue(any(x['school_id'] == self.student.school_id for x in role_list.json()['results']))
        cases = (
            ('role-permissions/roles/%d/permissions/' % self.student_role.pk, 'permissions'),
            ('account-grants/accounts/%d/grants/' % self.student.pk, 'permissions'),
            ('account-restrictions/accounts/%d/overrides/' % self.student.pk, 'permissions'),
            ('effective-access/accounts/%d/roles/' % self.student.pk, 'roles'),
            ('effective-access/accounts/%d/roles/%d/' % (self.student.pk, self.student_role.pk), 'permissions'),
        )
        for path, key in cases:
            with self.subTest(path=path):
                reply = self.get(path)
                self.assertEqual(reply.status_code, 200, reply.content)
                self.assertIn(key, reply.json())
        snapshot = self.get('effective-access/accounts/%d/roles/%d/' % (self.student.pk, self.student_role.pk))
        row = next(row for row in snapshot.json()['permissions']
                   if row['permission_code'] == self.read_permission.permission_code)
        self.assertTrue(row['effective'])

    def test_school_admin_and_anonymous_cannot_open_any_six_api_routes(self):
        self.login(self.school_admin, self.admin)
        for name, path, _ in self.paths():
            with self.subTest(identity='School Admin', subflow=name):
                self.assertEqual(self.get(path).status_code, 403)
        self.client.logout()
        for name, path, _ in self.paths():
            with self.subTest(identity='Anonymous', subflow=name):
                self.assertEqual(self.get(path).status_code, 401)

    def test_retracted_technical_role_cannot_be_selected_or_used(self):
        AccountRole.objects.filter(account=self.actor, role=self.technical).delete()
        result = self.switch(self.technical)
        self.assertEqual(result.status_code, 403, result.content)
        self.assertEqual(self.client.session[SESSION_ROLE_KEY], self.admin.pk)
        for name, path, _ in self.paths():
            with self.subTest(subflow=name):
                self.assertEqual(self.get(path).status_code, 403)

    def test_all_six_read_gates_fail_closed_and_do_not_change_state(self):
        self.assertEqual(self.switch(self.technical).status_code, 200)
        counts = (AccountRole.objects.count(), RolePermission.objects.count(),
                  AccountPermission.objects.count(), AccessAuditLog.objects.count())
        disabled = {
            'WORKSPACE_ROLE_ASSIGNMENT_ENABLED': False,
            'WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED': False,
            'WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED': False,
            'WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED': False,
            'WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED': False,
            'WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED': False,
        }
        with override_settings(**disabled):
            for name, path, _ in self.paths():
                with self.subTest(subflow=name):
                    reply = self.get(path)
                    self.assertEqual(reply.status_code, 503, reply.content)
        self.assertEqual(counts, (AccountRole.objects.count(), RolePermission.objects.count(),
                                  AccountPermission.objects.count(), AccessAuditLog.objects.count()))

    def test_normal_urlconf_never_mounts_wf03_governance(self):
        from django.urls import resolve, Resolver404
        with override_settings(ROOT_URLCONF='config.urls'):
            for name, path, _ in self.paths():
                with self.subTest(subflow=name):
                    with self.assertRaises(Resolver404):
                        resolve(BASE + path.split('?', 1)[0])
