"""Task 2 isolated reference tests; NEVER execute with development settings.

These fixtures are disposable only. They do not provision CTU-G Workspace users,
activate governance grants, or validate a production bootstrap/recovery flow.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Account
from apps.access_control.delegation import is_reserved_role
from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import get_effective_permissions, has_permission
from apps.access_control.tests_support.technical_super_admin_test_only import (
    composed_profile_test_only, simulated_governance_boundary_test_only,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured(
        "Task 2 contract tests require --settings=config.test_settings and a disposable MySQL database."
    )


class PreflightIsolationTests(SimpleTestCase):
    def test_local_read_only_preflight_refuses_test_configuration(self):
        with self.assertRaises(CommandError):
            call_command(
                "report_technical_super_admin_preflight_p2",
                expected_db="ctug_workspace", ack="READ_ONLY_PREFLIGHT",
            )

    def test_reserved_role_name_is_protected_from_ordinary_delegation(self):
        self.assertTrue(is_reserved_role("Admin"))
        self.assertTrue(is_reserved_role("Technical Super Admin"))
        self.assertTrue(is_reserved_role("super-admin"))
        self.assertFalse(is_reserved_role("Student"))


class TechnicalSuperAdminContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Technical profile fixtures require the disposable test schema.")

        cls.school_service = Service.objects.create(
            service_code="fixture_school", service_name="Task 2 school test service",
        )
        cls.governance_service = Service.objects.create(
            service_code="access_control", service_name="Task 2 governance test service",
        )
        cls.school_permission = Permission.objects.create(
            service=cls.school_service, permission_code="fixture.school.read",
            permission_name="Fixture school access", module_name="fixture", action_name="read",
        )
        cls.governance_permission = Permission.objects.create(
            service=cls.governance_service, permission_code="access_control.fixture_governance.read",
            permission_name="Fixture governance access", module_name="access_control", action_name="read",
        )
        cls.admin_role = Role.objects.create(role_name="Admin")
        cls.technical_role = Role.objects.create(role_name="Technical Super Admin")
        cls.student_role = Role.objects.create(role_name="Student")
        RolePermission.objects.create(role=cls.admin_role, permission=cls.school_permission)
        RolePermission.objects.create(role=cls.technical_role, permission=cls.governance_permission)

        def fixture(school_id, roles=(), *, framework=False):
            account = Account(school_id=school_id, request_status="Approved", is_active=True,
                              is_staff=framework, is_superuser=framework)
            account.set_unusable_password()
            account.save()
            for role in roles:
                AccountRole.objects.create(account=account, role=role)
            return account

        cls.normal_admin = fixture("T2-NORMAL-ADMIN", (cls.admin_role,))
        cls.technical_admin = fixture("T2-TECHNICAL-ADMIN", (cls.admin_role, cls.technical_role))
        cls.technical_only = fixture("T2-TECHNICAL-ONLY", (cls.technical_role,))
        cls.framework_user = fixture("T2-FRAMEWORK-ADMIN", (), framework=True)
        cls.student = fixture("T2-STUDENT", (cls.student_role,))

    def test_normal_admin_has_school_permission_but_no_technical_authority(self):
        self.assertTrue(has_permission(self.normal_admin, self.school_permission.permission_code))
        self.assertFalse(has_permission(self.normal_admin, self.governance_permission.permission_code))
        self.assertFalse(composed_profile_test_only(self.normal_admin))

    def test_dual_role_combines_explicit_permissions_without_role_name_bypass(self):
        self.assertTrue(composed_profile_test_only(self.technical_admin))
        self.assertEqual(get_effective_permissions(self.technical_admin), frozenset({
            self.school_permission.permission_code, self.governance_permission.permission_code,
        }))
        self.assertFalse(has_permission(self.technical_admin, "access_control.unapproved"))
        self.assertTrue(simulated_governance_boundary_test_only(
            self.technical_admin, self.governance_permission.permission_code,
        ))

    def test_technical_role_alone_cannot_pass_composite_boundary(self):
        # Important: the EXISTING evaluator considers a granted Technical-only
        # role sufficient for that specific code. Future protected APIs MUST
        # enforce composition independently; this reference gate does so.
        self.assertTrue(has_permission(self.technical_only, self.governance_permission.permission_code))
        self.assertFalse(composed_profile_test_only(self.technical_only))
        self.assertFalse(simulated_governance_boundary_test_only(
            self.technical_only, self.governance_permission.permission_code,
        ))

    def test_direct_deny_overrides_technical_governance_role_grant(self):
        AccountPermission.objects.create(
            account=self.technical_admin, permission=self.governance_permission, effect="Deny",
        )
        self.assertTrue(composed_profile_test_only(self.technical_admin))
        self.assertFalse(has_permission(self.technical_admin, self.governance_permission.permission_code))
        self.assertFalse(simulated_governance_boundary_test_only(
            self.technical_admin, self.governance_permission.permission_code,
        ))
        self.assertTrue(has_permission(self.technical_admin, self.school_permission.permission_code))

    def test_inactive_technical_role_breaks_composite_profile_and_grants(self):
        self.technical_role.is_active = False
        self.technical_role.save(update_fields=["is_active"])
        self.assertFalse(composed_profile_test_only(self.technical_admin))
        self.assertFalse(has_permission(self.technical_admin, self.governance_permission.permission_code))

    def test_inactive_governance_service_disables_permission(self):
        self.governance_service.is_active = False
        self.governance_service.save(update_fields=["is_active"])
        self.assertTrue(composed_profile_test_only(self.technical_admin))
        self.assertFalse(simulated_governance_boundary_test_only(
            self.technical_admin, self.governance_permission.permission_code,
        ))

    def test_rejected_or_inactive_account_cannot_pass_composite_boundary(self):
        Account.objects.filter(pk=self.technical_admin.pk).update(request_status="Rejected")
        self.assertFalse(composed_profile_test_only(self.technical_admin))
        self.assertFalse(has_permission(self.technical_admin, self.governance_permission.permission_code))

    def test_framework_superuser_does_not_become_workspace_super_admin(self):
        self.assertTrue(self.framework_user.is_superuser)
        self.assertFalse(composed_profile_test_only(self.framework_user))
        self.assertFalse(has_permission(self.framework_user, self.governance_permission.permission_code))

    def test_requested_protected_role_is_not_assigned_authority(self):
        Account.objects.filter(pk=self.student.pk).update(requested_role=self.technical_role)
        self.assertFalse(composed_profile_test_only(self.student))
        self.assertFalse(has_permission(self.student, self.governance_permission.permission_code))

    def test_unapproved_catalogue_code_is_not_granted_to_composite_profile(self):
        self.assertFalse(simulated_governance_boundary_test_only(
            self.technical_admin, "access_control.some_unapproved_action",
        ))
        self.assertFalse(simulated_governance_boundary_test_only(
            self.technical_admin, self.school_permission.permission_code,
        ))

    def test_unsaved_account_and_spoofed_primary_key_do_not_pass_reference_gate(self):
        self.assertFalse(composed_profile_test_only(Account()))
        spoof = Account(account_id=self.technical_admin.pk, request_status="Approved", is_active=True)
        self.assertFalse(composed_profile_test_only(spoof))

    def test_no_real_technical_provisioning_or_governance_mutations_exported(self):
        import apps.access_control.tests_support.technical_super_admin_test_only as sim
        for method in ("bootstrap", "promote", "revoke", "grant", "activate", "save"):
            self.assertFalse(hasattr(sim, method))
