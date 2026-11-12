"""G1D-P0/P1 contracts. Fixture writes ONLY in Django's disposable MySQL DB."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import Account
from apps.access_control.delegation import is_reserved_role
from apps.access_control.management.commands.init_system_roles import SYSTEM_ROLES
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.services import has_permission
from apps.access_control.tests_support.technical_super_admin_test_only import composed_profile_test_only
from apps.access_control.tests_support.g1d_p1_dormant_role_test_only import (
    TECHNICAL_ROLE_NAME, TestOnlyRoleProvisioningRefused,
    create_inactive_technical_role_fixture_test_only,
)


if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("G1D tests require config.test_settings and a disposable MySQL schema.")


class G1DP0IsolationTests(SimpleTestCase):
    def test_read_only_p0_command_rejects_test_configuration(self):
        with self.assertRaises(CommandError):
            call_command(
                "report_g1d_p0_role_readiness",
                expected_db="ctug_workspace", ack="G1D_P0_READ_ONLY",
            )

    def test_normal_initializer_has_exactly_four_roles(self):
        self.assertEqual(
            tuple(name for name, _ in SYSTEM_ROLES),
            ("Student", "Instructor", "Treasurer", "Admin"),
        )

    def test_protected_role_name_is_exact(self):
        self.assertEqual(TECHNICAL_ROLE_NAME, "Technical Super Admin")
        self.assertTrue(is_reserved_role(TECHNICAL_ROLE_NAME))
        self.assertFalse(is_reserved_role("Instructor"))

    def test_test_only_helper_has_no_live_bootstrap_grant_or_activation_methods(self):
        from apps.access_control.tests_support import g1d_p1_dormant_role_test_only as fixture
        for name in ("bootstrap", "promote", "activate", "grant", "assign", "release", "migrate", "seed"):
            self.assertFalse(hasattr(fixture, name))

    def test_missing_disposable_ack_refuses_before_database_access(self):
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            create_inactive_technical_role_fixture_test_only(ack="LIVE_ROLE_CREATE")


class G1DP1DisposableMySQLTests(TestCase):
    """Every database mutation in this class is inside Django's disposable test DB."""

    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Connected G1D fixture DB does not match disposable settings.")
        cls.admin_role = Role.objects.create(role_name="Admin", is_active=True)
        cls.student_role = Role.objects.create(role_name="Student")
        cls.instructor_role = Role.objects.create(role_name="Instructor")
        cls.treasurer_role = Role.objects.create(role_name="Treasurer")

        def make_account(school_id, *, superuser=False):
            account = Account(
                school_id=school_id, request_status="Approved", is_active=True,
                is_staff=superuser, is_superuser=superuser,
            )
            account.set_unusable_password()
            account.save()
            return account

        cls.normal_admin = make_account("G1D-P1-NORMAL")
        AccountRole.objects.create(account=cls.normal_admin, role=cls.admin_role)
        cls.framework_superuser = make_account("G1D-P1-FRAMEWORK", superuser=True)

    def provision(self):
        return create_inactive_technical_role_fixture_test_only(ack="G1D_P1_DISPOSABLE_ONLY")

    def test_precondition_has_only_four_standard_roles(self):
        self.assertEqual(Role.objects.count(), 4)
        self.assertFalse(Role.objects.filter(role_name=TECHNICAL_ROLE_NAME).exists())

    def test_creates_exactly_one_inactive_technical_role_fixture(self):
        role = self.provision()
        role.refresh_from_db()
        self.assertEqual(role.role_name, TECHNICAL_ROLE_NAME)
        self.assertFalse(role.is_active)
        self.assertEqual(Role.objects.count(), 5)

    def test_description_is_clearly_fictional(self):
        role = self.provision()
        self.assertIn("TEST FIXTURE", role.description)

    def test_fixture_creation_does_not_create_assignments(self):
        role = self.provision()
        self.assertEqual(AccountRole.objects.filter(role=role).count(), 0)
        self.assertEqual(AccountRole.objects.count(), 1)  # only existing Normal Admin

    def test_fixture_creation_does_not_create_permission_grants(self):
        role = self.provision()
        self.assertEqual(RolePermission.objects.filter(role=role).count(), 0)
        self.assertEqual(RolePermission.objects.count(), 0)

    def test_fixture_creation_does_not_seed_permission_metadata(self):
        self.provision()
        self.assertEqual(Permission.objects.count(), 0)

    def test_fixture_creation_does_not_add_account_permission_overrides(self):
        self.provision()
        self.assertEqual(AccountPermission.objects.count(), 0)

    def test_fixture_creation_does_not_add_accounts(self):
        before = Account.objects.count()
        self.provision()
        self.assertEqual(Account.objects.count(), before)

    def test_fixture_creation_does_not_write_audit_rows(self):
        before = AccessAuditLog.objects.count()
        self.provision()
        self.assertEqual(AccessAuditLog.objects.count(), before)

    def test_normal_admin_remains_without_protected_profile(self):
        self.provision()
        self.assertFalse(composed_profile_test_only(self.normal_admin))
        self.assertFalse(has_permission(self.normal_admin, "access_control.catalogue.read"))

    def test_framework_superuser_does_not_gain_technical_authority(self):
        self.provision()
        self.assertFalse(composed_profile_test_only(self.framework_superuser))
        self.assertFalse(has_permission(self.framework_superuser, "access_control.catalogue.read"))

    def test_disposable_fixture_rejects_second_creation(self):
        self.provision()
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()
        self.assertEqual(Role.objects.filter(role_name=TECHNICAL_ROLE_NAME).count(), 1)

    def test_refuses_preexisting_dormant_technical_role(self):
        Role.objects.create(role_name=TECHNICAL_ROLE_NAME, is_active=False)
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()
        self.assertEqual(Role.objects.count(), 5)

    def test_refuses_protected_punctuation_alias(self):
        Role.objects.create(role_name="Technical-Super-Admin", is_active=False)
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_protected_super_admin_alias(self):
        Role.objects.create(role_name="Super Admin", is_active=False)
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_protected_case_alias(self):
        Role.objects.create(role_name="TECHNICAL SUPER ADMIN", is_active=False)
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_inactive_normal_admin_baseline(self):
        Role.objects.filter(pk=self.admin_role.pk).update(is_active=False)
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_missing_normal_admin_baseline(self):
        AccountRole.objects.filter(role=self.admin_role).delete()
        Role.objects.filter(pk=self.admin_role.pk).delete()
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_installed_core_k_metadata(self):
        service = Service.objects.create(service_code="access_control", service_name="G1D test governance")
        Permission.objects.create(
            service=service, permission_code="access_control.catalogue.read",
            permission_name="TEST ONLY", module_name="catalogue", action_name="read",
        )
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_refuses_active_governance_direct_override(self):
        service = Service.objects.create(service_code="access_control", service_name="G1D test governance")
        permission = Permission.objects.create(
            service=service, permission_code="access_control.fixture.test",
            permission_name="TEST ONLY", module_name="fixture", action_name="test",
        )
        AccountPermission.objects.create(
            account=self.normal_admin, permission=permission, effect="Grant", is_active=True,
        )
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    @override_settings(REGISTRATION_TEST_DATABASE="ctug_workspace")
    def test_refuses_main_database_label_even_if_test_settings_imported(self):
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    @override_settings(REGISTRATION_TEST_DATABASE="test_ctug_registration_nothex")
    def test_refuses_unexpected_disposable_schema_name(self):
        with self.assertRaises(TestOnlyRoleProvisioningRefused):
            self.provision()

    def test_inactive_technical_role_cannot_grant_even_if_fixture_binds_it(self):
        role = self.provision()
        service = Service.objects.create(service_code="access_control", service_name="G1D test governance")
        permission = Permission.objects.create(
            service=service, permission_code="access_control.catalogue.read",
            permission_name="TEST ONLY", module_name="catalogue", action_name="read",
        )
        # Only test fixtures can do this; a real role grant is expressly blocked.
        RolePermission.objects.create(role=role, permission=permission)
        AccountRole.objects.create(account=self.normal_admin, role=role)
        self.assertFalse(composed_profile_test_only(self.normal_admin))
        self.assertFalse(has_permission(self.normal_admin, permission.permission_code))

    def test_test_only_role_activating_without_any_grant_is_still_not_authority(self):
        role = self.provision()
        Role.objects.filter(pk=role.pk).update(is_active=True)
        AccountRole.objects.create(account=self.normal_admin, role=role)
        self.assertTrue(composed_profile_test_only(self.normal_admin))
        self.assertFalse(has_permission(self.normal_admin, "access_control.catalogue.read"))
