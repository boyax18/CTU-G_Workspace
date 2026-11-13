"""Authorization policy and query tests against disposable MySQL only."""

import re
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils.functional import SimpleLazyObject

from apps.accounts.models import Account

from .models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)
from .services import get_effective_permissions, has_permission

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Permission tests require --settings=config.test_settings; development data must never be used.")


class PermissionEvaluatorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
                raise ImproperlyConfigured("Refusing permission fixtures on an unexpected database.")
        # Approved/active state is a test fixture, never public provisioning.
        cls.account = Account(school_id="PERMISSION-TEST-001", request_status="Approved", is_active=True)
        cls.account.set_unusable_password()
        cls.account.save()
        cls.student = Role.objects.create(role_name="Student")
        cls.instructor = Role.objects.create(role_name="Instructor")
        cls.assignment = AccountRole.objects.create(account=cls.account, role=cls.student)
        cls.service = Service.objects.create(service_code="test_records", service_name="Test records")
        cls.view = cls.permission("test.records.view")
        cls.edit = cls.permission("test.records.edit")

    @classmethod
    def permission(cls, code, service=None):
        return Permission.objects.create(
            service=service or cls.service, permission_code=code,
            permission_name="Test permission", module_name="test", action_name="test",
        )

    def grant_role(self, permission=None, role=None, active=True):
        return RolePermission.objects.create(
            role=role or self.student, permission=permission or self.view, is_active=active,
        )

    def override(self, effect, permission=None, active=True):
        return AccountPermission.objects.create(
            account=self.account, permission=permission or self.view,
            effect=effect, is_active=active,
        )

    def assert_denied(self, code=None):
        self.assertFalse(has_permission(self.account, code or self.view.permission_code))
        self.assertNotIn(code or self.view.permission_code, get_effective_permissions(self.account))

    def test_catalogue_existence_alone_does_not_authorize(self):
        self.assert_denied()

    def test_unknown_permission_is_denied(self):
        self.grant_role()
        self.assert_denied("test.unknown")
        self.assert_denied("*")

    def test_missing_anonymous_wrong_type_and_unsaved_accounts_are_denied_without_queries(self):
        candidates = [None, AnonymousUser(), self.account.pk, str(self.account.pk),
                      {"account_id": self.account.pk}, Account(),
                      Account(account_id=self.account.pk, is_active=True, request_status="Approved")]
        with self.assertNumQueries(0):
            for account in candidates:
                with self.subTest(account_type=type(account).__name__):
                    self.assertFalse(has_permission(account, self.view.permission_code))
                    self.assertEqual(get_effective_permissions(account), frozenset())

    def test_nonexistent_persisted_account_is_denied(self):
        missing = Account.objects.create(school_id="PERMISSION-DELETED", is_active=True, request_status="Approved")
        Account.objects.filter(pk=missing.pk).delete()
        self.assertFalse(has_permission(missing, self.view.permission_code))
        self.assertEqual(get_effective_permissions(missing), frozenset())

    def test_pending_account_is_denied_despite_active_flag_and_grants(self):
        self.grant_role()
        self.override("Grant")
        Account.objects.filter(pk=self.account.pk).update(request_status="Pending")
        self.assert_denied()

    def test_rejected_account_is_denied(self):
        self.grant_role()
        Account.objects.filter(pk=self.account.pk).update(request_status="Rejected")
        self.assert_denied()

    def test_inactive_account_is_denied(self):
        self.grant_role()
        self.override("Grant")
        Account.objects.filter(pk=self.account.pk).update(is_active=False)
        self.assert_denied()

    def test_account_without_assigned_role_cannot_use_direct_grant(self):
        self.override("Grant")
        AccountRole.objects.filter(account=self.account).delete()
        self.assert_denied()

    def test_requested_role_without_assignment_does_not_authorize(self):
        self.grant_role()
        self.override("Grant")
        AccountRole.objects.filter(account=self.account).delete()
        Account.objects.filter(pk=self.account.pk).update(requested_role=self.student)
        self.assert_denied()

    def test_active_assigned_role_and_active_role_grant_authorize(self):
        self.grant_role()
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        self.assertEqual(get_effective_permissions(self.account), frozenset({self.view.permission_code}))

    def test_inactive_role_contributes_no_permissions(self):
        self.grant_role()
        Role.objects.filter(pk=self.student.pk).update(is_active=False)
        self.assert_denied()

    def test_direct_grant_requires_at_least_one_active_assigned_role(self):
        self.override("Grant")
        Role.objects.filter(pk=self.student.pk).update(is_active=False)
        self.assert_denied()

    def test_inactive_role_is_excluded_even_when_another_role_establishes_eligibility(self):
        self.grant_role()
        Role.objects.filter(pk=self.student.pk).update(is_active=False)
        AccountRole.objects.create(account=self.account, role=self.instructor)
        self.assert_denied()

    def test_unassigned_role_grant_is_not_used(self):
        self.grant_role(role=self.instructor)
        self.assert_denied()

    def test_inactive_role_permission_does_not_grant_access(self):
        self.grant_role(active=False)
        self.assert_denied()

    def test_multiple_active_role_permissions_are_combined(self):
        self.grant_role()
        AccountRole.objects.create(account=self.account, role=self.instructor)
        self.grant_role(permission=self.edit, role=self.instructor)
        self.assertEqual(get_effective_permissions(self.account), frozenset({self.view.permission_code, self.edit.permission_code}))

    def test_direct_grant_works_without_matching_role_permission(self):
        self.override("Grant")
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        self.assertEqual(get_effective_permissions(self.account), frozenset({self.view.permission_code}))

    def test_active_deny_overrides_all_assigned_role_grants(self):
        self.grant_role()
        AccountRole.objects.create(account=self.account, role=self.instructor)
        self.grant_role(role=self.instructor)
        self.override("Deny")
        self.assert_denied()

    def test_changing_a_direct_grant_to_deny_removes_access_even_with_a_role_grant(self):
        self.grant_role()
        override = self.override("Grant")
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        AccountPermission.objects.filter(pk=override.pk).update(effect="Deny")
        self.assert_denied()

    def test_inactive_deny_has_no_effect_on_a_valid_role_grant(self):
        self.grant_role()
        self.override("Deny", active=False)
        self.assertTrue(has_permission(self.account, self.view.permission_code))

    def test_inactive_direct_grant_has_no_effect(self):
        self.override("Grant", active=False)
        self.assert_denied()

    def test_inactive_service_blocks_role_and_direct_grants(self):
        self.grant_role()
        self.override("Grant")
        Service.objects.filter(pk=self.service.pk).update(is_active=False)
        self.assert_denied()

    def test_admin_name_confers_no_bypass(self):
        admin = Role.objects.create(role_name="Admin")
        AccountRole.objects.create(account=self.account, role=admin)
        self.assert_denied()
        self.grant_role(role=admin)
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        self.assert_denied(self.edit.permission_code)

    def test_technical_super_admin_name_confers_no_bypass_test_fixture_only(self):
        technical = Role.objects.create(role_name="Technical Super Admin")
        AccountRole.objects.create(account=self.account, role=technical)
        self.account.is_superuser = True
        self.account.is_staff = True
        self.assert_denied()
        self.grant_role(role=technical)
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        self.override("Deny")
        self.assert_denied()

    def test_requested_role_manipulation_cannot_use_an_unassigned_privileged_role(self):
        admin = Role.objects.create(role_name="Admin")
        self.grant_role(role=admin)
        Account.objects.filter(pk=self.account.pk).update(requested_role=admin)
        self.account.requested_role = admin
        self.assert_denied()

    def test_listing_agrees_with_individual_checks(self):
        self.grant_role()
        self.override("Grant", permission=self.edit)
        blocked = self.permission("test.records.blocked")
        self.grant_role(permission=blocked)
        self.override("Deny", permission=blocked)
        disabled_service = Service.objects.create(service_code="disabled", service_name="Disabled", is_active=False)
        disabled = self.permission("test.disabled", service=disabled_service)
        self.override("Grant", permission=disabled)
        effective = get_effective_permissions(self.account)
        self.assertIsInstance(effective, frozenset)
        for code in [*Permission.objects.values_list("permission_code", flat=True), "unknown", "TEST.RECORDS.VIEW"]:
            with self.subTest(code=code):
                self.assertEqual(has_permission(self.account, code), code in effective)

    def test_permission_codes_are_exact_despite_case_accent_or_space_insensitive_mysql_collation(self):
        self.grant_role()
        for code in ("TEST.RECORDS.VIEW", "tést.records.view", "test.records.view ", " test.records.view"):
            with self.subTest(code=code):
                self.assertFalse(has_permission(self.account, code))
        self.assertTrue(has_permission(self.account, self.view.permission_code))

    def test_invalid_permission_inputs_are_denied_without_queries(self):
        with self.assertNumQueries(0):
            for code in (None, 1, True, [], {}, b"test.records.view", "", "   ", "x" * 151):
                self.assertFalse(has_permission(self.account, code))

    def test_blank_catalogue_codes_do_not_become_effective_permissions(self):
        blank = self.permission("")
        self.override("Grant", permission=blank)
        self.assertEqual(get_effective_permissions(self.account), frozenset())
        self.assertFalse(has_permission(self.account, ""))

    def test_role_grant_revocation_takes_effect_on_the_same_account_instance(self):
        grant = self.grant_role()
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        RolePermission.objects.filter(pk=grant.pk).update(is_active=False)
        self.assert_denied()

    def test_role_assignment_removal_takes_effect_immediately(self):
        self.grant_role()
        self.override("Grant")
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        AccountRole.objects.filter(account=self.account).delete()
        self.assert_denied()

    def test_direct_grant_revocation_takes_effect_immediately(self):
        grant = self.override("Grant")
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        AccountPermission.objects.filter(pk=grant.pk).update(is_active=False)
        self.assert_denied()

    def test_permission_deletion_takes_effect_without_stale_authorization(self):
        grant = self.grant_role()
        self.assertTrue(has_permission(self.account, self.view.permission_code))
        grant.delete()
        Permission.objects.filter(pk=self.view.pk).delete()
        self.assert_denied()

    def test_database_state_overrides_stale_instance_flags_and_prefetched_relations(self):
        self.grant_role()
        cached = Account.objects.prefetch_related("role_assignments__role__permission_grants", "permission_overrides").get(pk=self.account.pk)
        self.assertTrue(has_permission(cached, self.view.permission_code))
        cached._perm_cache = {self.view.permission_code}
        cached.is_superuser = True
        Account.objects.filter(pk=cached.pk).update(is_active=False)
        self.assertFalse(has_permission(cached, self.view.permission_code))
        self.assertEqual(get_effective_permissions(cached), frozenset())

    def test_database_eligibility_is_not_replaced_by_unsaved_local_edits(self):
        self.grant_role()
        Account.objects.filter(pk=self.account.pk).update(request_status="Pending", is_active=False)
        self.account.request_status, self.account.is_active = "Approved", True
        self.assert_denied()

    def test_account_from_another_database_alias_is_rejected_without_queries(self):
        self.account._state.db = "untrusted_database"
        with self.assertNumQueries(0):
            self.assert_denied()

    def test_lazy_request_user_and_account_has_perm_use_the_same_evaluator(self):
        self.grant_role()
        user = SimpleLazyObject(lambda: self.account)
        self.assertTrue(has_permission(user, self.view.permission_code))
        self.assertTrue(user.has_perm(self.view.permission_code))
        self.override("Deny")
        self.assertFalse(user.has_perm(self.view.permission_code))

    def test_object_permissions_and_django_module_permissions_remain_denied(self):
        self.grant_role()
        self.assertTrue(self.account.has_perm(self.view.permission_code))
        with self.assertNumQueries(0):
            self.assertFalse(self.account.has_perm(self.view.permission_code, obj=self.service))
            self.assertFalse(self.account.has_module_perms("access_control"))

    def test_database_and_unexpected_evaluation_errors_fail_closed_without_secret_logging(self):
        for error in (DatabaseError("sensitive SQL or credential detail"), RuntimeError("sensitive internal detail")):
            with self.subTest(error_type=type(error).__name__):
                with patch("apps.access_control.services._authorized_permissions", side_effect=error):
                    with self.assertLogs("apps.access_control.services", level="ERROR") as captured:
                        self.assert_denied()
                self.assertNotIn("sensitive", " ".join(captured.output))

    def test_mid_read_error_discards_any_partially_loaded_grants(self):
        def partial(*args, **kwargs):
            yield self.view.permission_code
            raise DatabaseError("sensitive detail")

        query = Mock()
        query.filter.return_value = query
        query.values_list.side_effect = partial
        with patch("apps.access_control.services._authorized_permissions", return_value=query):
            with self.assertLogs("apps.access_control.services", level="ERROR"):
                self.assert_denied()

    def test_listing_and_individual_checks_each_use_one_read_only_query(self):
        self.grant_role()
        with self.assertNumQueries(1):
            self.assertTrue(has_permission(self.account, self.view.permission_code))
        with self.assertNumQueries(1):
            self.assertEqual(get_effective_permissions(self.account), frozenset({self.view.permission_code}))
        with CaptureQueriesContext(connection) as queries:
            get_effective_permissions(self.account)
            self.account.has_perm(self.view.permission_code)
        self.assertTrue(all(re.match(r"^\s*SELECT\b", entry["sql"], re.I) for entry in queries))
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_query_count_does_not_grow_with_roles_and_permissions(self):
        expected = set()
        for index in range(8):
            role = Role.objects.create(role_name=f"Fixture role {index}")
            AccountRole.objects.create(account=self.account, role=role)
            for suffix in ("read", "write", "inspect"):
                permission = self.permission(f"test.fixture{index}.{suffix}")
                self.grant_role(permission=permission, role=role)
                expected.add(permission.permission_code)
        with self.assertNumQueries(1):
            self.assertEqual(get_effective_permissions(self.account), frozenset(expected))
        with self.assertNumQueries(1):
            self.assertTrue(has_permission(self.account, "test.fixture7.inspect"))
