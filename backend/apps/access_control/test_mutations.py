"""Trusted permission mutation policy and real MySQL transaction tests."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from apps.accounts.models import Account

from . import audit
from .delegation import (
    ACCOUNT_PERMISSION_MANAGE, ROLE_PERMISSION_MANAGE, DelegationPolicyUnavailable,
    PermissionManagementDenied, PermissionManagementValidationError,
    approved_scope, require_delegation,
)
from .models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from .mutations import (
    deactivate_account_override, deny_account_permission, grant_account_permission,
    grant_role_permission, revoke_role_permission,
)
from .services import has_permission

POLICY = {"test_records": {
    "authority_permission": "access_control.delegate.test_records",
    "permission_codes": ["test.records.read", "test.records.write"],
    "role_names": ["Student", "Instructor"],
}}

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("Mutation tests require --settings=config.test_settings; development data must never be used.")


def verify_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        if cursor.fetchone()[0] != settings.REGISTRATION_TEST_DATABASE:
            raise ImproperlyConfigured("Refusing mutation fixtures on an unexpected database.")


def make_permission(service, code, module="records"):
    return Permission.objects.create(service=service, permission_code=code,
        permission_name="Test fixture", module_name=module, action_name="test")


def make_account(school_id):
    account = Account(school_id=school_id, request_status="Approved", is_active=True)
    account.set_unusable_password()
    account.save()
    return account


def fixtures(owner):
    verify_database()
    owner.governance = Service.objects.create(service_code="access_control", service_name="Governance fixture")
    owner.service = Service.objects.create(service_code="test_records", service_name="Records fixture")
    owner.role_manage = make_permission(owner.governance, ROLE_PERMISSION_MANAGE, "access_control")
    owner.account_manage = make_permission(owner.governance, ACCOUNT_PERMISSION_MANAGE, "access_control")
    owner.delegate = make_permission(owner.governance, "access_control.delegate.test_records", "access_control")
    owner.read = make_permission(owner.service, "test.records.read")
    owner.write = make_permission(owner.service, "test.records.write")
    owner.outside = make_permission(owner.service, "test.records.outside")
    owner.operator_role = Role.objects.create(role_name="Fixture Operator")
    owner.student = Role.objects.create(role_name="Student")
    owner.instructor = Role.objects.create(role_name="Instructor")
    owner.actor = make_account("MUTATION-ACTOR")
    owner.target = make_account("MUTATION-TARGET")
    AccountRole.objects.create(account=owner.actor, role=owner.operator_role)
    AccountRole.objects.create(account=owner.target, role=owner.student)
    for permission in (owner.role_manage, owner.account_manage, owner.delegate):
        RolePermission.objects.create(role=owner.operator_role, permission=permission)


class _Helpers:
    def grant_role(self, **kwargs):
        return grant_role_permission(**{"actor": self.actor, "role": self.student, "permission": self.read, **kwargs})

    def grant_account(self, **kwargs):
        return grant_account_permission(**{"actor": self.actor, "target": self.target, "permission": self.read, **kwargs})

    def deny_account(self, **kwargs):
        return deny_account_permission(**{"actor": self.actor, "target": self.target, "permission": self.read, **kwargs})

    def deactivate(self, **kwargs):
        return deactivate_account_override(**{"actor": self.actor, "target": self.target, "permission": self.read, **kwargs})

    def state(self):
        return (list(RolePermission.objects.order_by("pk").values()),
                list(AccountPermission.objects.order_by("pk").values()),
                list(AccessAuditLog.objects.order_by("pk").values()))

    def assert_denied_unchanged(self, operation, exception=PermissionManagementDenied):
        before = self.state()
        with self.assertRaises(exception):
            operation()
        self.assertEqual(self.state(), before)


@override_settings(ACCESS_CONTROL_DELEGATION_POLICY=POLICY)
class PermissionMutationTests(_Helpers, TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)

    def test_valid_role_grant_is_effective_and_audited(self):
        self.assertFalse(has_permission(self.actor, self.read.permission_code))
        self.assertTrue(self.grant_role())
        row = RolePermission.objects.get(role=self.student, permission=self.read)
        self.assertTrue(row.is_active)
        self.assertEqual(row.granted_by_id, self.actor.pk)
        self.assertTrue(has_permission(self.target, self.read.permission_code))
        event = AccessAuditLog.objects.get()
        self.assertEqual(event.actor_account_id, self.actor.pk)
        self.assertEqual((event.role_id, event.permission_id), (self.student.pk, self.read.pk))
        self.assertIsNone(event.old_value)
        self.assertEqual(event.new_value["role_permission_id"], row.pk)
        self.assertTrue(event.new_value["is_active"])
        self.assertEqual(event.action, "role_permission.grant")

    def test_role_revoke_disables_grant_without_inserting_a_deny(self):
        self.grant_role()
        self.assertTrue(revoke_role_permission(actor=self.actor, role=self.student, permission=self.read))
        self.assertFalse(RolePermission.objects.get(role=self.student, permission=self.read).is_active)
        self.assertEqual(AccountPermission.objects.count(), 0)
        self.assertFalse(has_permission(self.target, self.read.permission_code))
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "role_permission.revoke")

    def test_reenable_reuses_role_grant_and_updates_grant_attribution(self):
        row = RolePermission.objects.create(role=self.student, permission=self.read, is_active=False)
        original_id = row.pk
        self.assertTrue(self.grant_role())
        row.refresh_from_db()
        self.assertEqual(row.pk, original_id)
        self.assertEqual(row.granted_by_id, self.actor.pk)
        self.assertIsNotNone(row.granted_at)
        self.assertEqual(RolePermission.objects.filter(role=self.student, permission=self.read).count(), 1)

    def test_valid_direct_grant_is_effective_without_target_role_grants(self):
        self.assertTrue(self.grant_account())
        row = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.assertEqual(row.effect, "Grant")
        self.assertTrue(row.is_active)
        self.assertEqual(row.assigned_by_id, self.actor.pk)
        self.assertTrue(has_permission(self.target, self.read.permission_code))
        self.assertFalse(has_permission(self.actor, self.read.permission_code))
        self.assertEqual(AccessAuditLog.objects.get().target_account_id, self.target.pk)

    def test_active_deny_after_mutation_overrides_role_grants(self):
        self.grant_role()
        self.assertTrue(self.deny_account())
        self.assertFalse(has_permission(self.target, self.read.permission_code))
        self.assertTrue(RolePermission.objects.get(role=self.student, permission=self.read).is_active)
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "account_permission.deny")

    def test_grant_to_deny_reuses_unique_override_and_audits_both_states(self):
        self.grant_account()
        original = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.deny_account()
        row = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.assertEqual(row.pk, original.pk)
        self.assertEqual(row.effect, "Deny")
        self.assertIsNotNone(row.updated_at)
        event = AccessAuditLog.objects.latest("pk")
        self.assertEqual(event.old_value["effect"], "Grant")
        self.assertEqual(event.new_value["effect"], "Deny")

    def test_deny_to_grant_is_audited_and_restores_access_only_with_full_authority(self):
        self.deny_account()
        self.assertFalse(has_permission(self.target, self.read.permission_code))
        self.grant_account()
        self.assertTrue(has_permission(self.target, self.read.permission_code))
        self.assertEqual(AccessAuditLog.objects.latest("pk").old_value["effect"], "Deny")

    def test_deactivating_direct_grant_is_distinct_from_deny_and_keeps_record(self):
        self.grant_account()
        self.assertTrue(self.deactivate())
        row = AccountPermission.objects.get(account=self.target, permission=self.read)
        self.assertEqual(row.effect, "Grant")
        self.assertFalse(row.is_active)
        self.assertFalse(has_permission(self.target, self.read.permission_code))
        self.assertEqual(AccessAuditLog.objects.latest("pk").action, "account_permission.grant.deactivate")

    def test_deactivating_deny_can_increase_access_and_is_audited_distinctly(self):
        self.grant_role()
        self.deny_account()
        self.assertTrue(self.deactivate())
        self.assertTrue(has_permission(self.target, self.read.permission_code))
        event = AccessAuditLog.objects.latest("pk")
        self.assertEqual(event.action, "account_permission.deny.deactivate")
        self.assertTrue(event.old_value["is_active"])
        self.assertFalse(event.new_value["is_active"])

    def test_idempotent_operations_do_not_duplicate_rows_audits_or_attribution(self):
        self.assertTrue(self.grant_role())
        before = self.state()
        self.assertFalse(self.grant_role())
        self.assertEqual(self.state(), before)
        self.assertTrue(self.grant_account())
        before = self.state()
        self.assertFalse(self.grant_account())
        self.assertEqual(self.state(), before)
        self.assertTrue(self.deny_account())
        before = self.state()
        self.assertFalse(self.deny_account())
        self.assertEqual(self.state(), before)
        self.deactivate()
        before = self.state()
        self.assertFalse(self.deactivate())
        self.assertEqual(self.state(), before)

    def test_revoke_and_deactivate_missing_rows_are_noops(self):
        before = self.state()
        self.assertFalse(revoke_role_permission(actor=self.actor, role=self.student, permission=self.read))
        self.assertFalse(self.deactivate())
        self.assertEqual(self.state(), before)

    def test_missing_management_permissions_are_rejected(self):
        RolePermission.objects.filter(role=self.operator_role, permission=self.role_manage).delete()
        self.assert_denied_unchanged(self.grant_role)
        RolePermission.objects.filter(role=self.operator_role, permission=self.account_manage).delete()
        self.assert_denied_unchanged(self.grant_account)

    def test_management_authority_does_not_replace_delegation(self):
        RolePermission.objects.filter(role=self.operator_role, permission=self.delegate).delete()
        self.assert_denied_unchanged(self.grant_role)
        self.assert_denied_unchanged(self.grant_account)

    def test_possession_of_target_permission_does_not_replace_delegation(self):
        RolePermission.objects.create(role=self.operator_role, permission=self.read)
        RolePermission.objects.filter(role=self.operator_role, permission=self.delegate).delete()
        self.assertTrue(has_permission(self.actor, self.read.permission_code))
        self.assert_denied_unchanged(self.grant_role)

    def test_management_permission_under_wrong_service_is_not_governance_authority(self):
        Permission.objects.filter(pk=self.role_manage.pk).update(service=self.service)
        self.assertTrue(has_permission(self.actor, ROLE_PERMISSION_MANAGE))
        self.assert_denied_unchanged(self.grant_role)

    def test_delegation_permission_under_wrong_service_is_rejected(self):
        Permission.objects.filter(pk=self.delegate.pk).update(service=self.service)
        self.assert_denied_unchanged(self.grant_account)

    def test_pending_rejected_inactive_or_roleless_actor_is_rejected_using_live_state(self):
        for status, active in (("Pending", True), ("Rejected", True), ("Approved", False)):
            with self.subTest(status=status, active=active):
                Account.objects.filter(pk=self.actor.pk).update(request_status=status, is_active=active)
                self.assert_denied_unchanged(self.grant_role)
        Account.objects.filter(pk=self.actor.pk).update(request_status="Approved", is_active=True)
        AccountRole.objects.filter(account=self.actor).delete()
        self.assert_denied_unchanged(self.grant_role)

    def test_inactive_actor_role_does_not_authorize(self):
        Role.objects.filter(pk=self.operator_role.pk).update(is_active=False)
        self.assert_denied_unchanged(self.grant_account)

    def test_inactive_management_grants_and_active_denies_are_respected(self):
        RolePermission.objects.filter(role=self.operator_role, permission=self.role_manage).update(is_active=False)
        self.assert_denied_unchanged(self.grant_role)
        RolePermission.objects.filter(role=self.operator_role, permission=self.role_manage).update(is_active=True)
        AccountPermission.objects.create(account=self.actor, permission=self.role_manage, effect="Deny")
        self.assert_denied_unchanged(self.grant_role)

    def test_delegation_revocation_takes_effect_on_next_operation(self):
        self.grant_account()
        RolePermission.objects.filter(role=self.operator_role, permission=self.delegate).update(is_active=False)
        self.assert_denied_unchanged(lambda: self.grant_account(permission=self.write))
        self.assert_denied_unchanged(self.deactivate)

    def test_removing_deny_requires_delegation_even_when_it_would_restore_access(self):
        self.grant_role()
        self.deny_account()
        RolePermission.objects.filter(role=self.operator_role, permission=self.delegate).delete()
        self.assert_denied_unchanged(self.deactivate)
        self.assertFalse(has_permission(self.target, self.read.permission_code))

    def test_no_policy_means_no_live_grants_or_revocations(self):
        with self.settings(ACCESS_CONTROL_DELEGATION_POLICY={}):
            for operation in (self.grant_role, self.grant_account, self.deny_account, self.deactivate):
                self.assert_denied_unchanged(operation, DelegationPolicyUnavailable)

    def test_unapproved_permission_or_recipient_role_is_rejected(self):
        self.assert_denied_unchanged(lambda: self.grant_role(permission=self.outside))
        outsider = Role.objects.create(role_name="Unreviewed recipient")
        self.assert_denied_unchanged(lambda: self.grant_role(role=outsider))

    def test_scope_requires_exact_service_and_permission_codes(self):
        mismatched = deepcopy(POLICY)
        mismatched["other_service"] = mismatched.pop("test_records")
        mismatched["other_service"]["authority_permission"] = "access_control.delegate.other_service"
        with self.settings(ACCESS_CONTROL_DELEGATION_POLICY=mismatched):
            self.assert_denied_unchanged(self.grant_role)

    def test_malformed_or_broad_policy_configuration_fails_closed(self):
        bad = [True, [], {"test_records": {**POLICY["test_records"], "allow_all": True}},
               {"test_records": {**POLICY["test_records"], "authority_permission": ROLE_PERMISSION_MANAGE}},
               {"test_records": {**POLICY["test_records"], "permission_codes": ["*"]}},
               {"test_records": {**POLICY["test_records"], "role_names": ["Admin"]}},
               {"test_records": {**POLICY["test_records"], "permission_codes": ["test.records.read"] * 2}}]
        for registry in bad:
            with self.subTest(policy_type=type(registry).__name__):
                with self.settings(ACCESS_CONTROL_DELEGATION_POLICY=registry):
                    self.assert_denied_unchanged(self.grant_role, DelegationPolicyUnavailable)

    def test_delegation_interface_is_read_only_and_validates_references(self):
        before = self.state()
        scope = require_delegation(self.actor, self.read)
        self.assertEqual(scope, approved_scope("test_records"))
        self.assertEqual(scope.permission_codes, frozenset(POLICY["test_records"]["permission_codes"]))
        self.assertEqual(self.state(), before)
        self.assert_denied_unchanged(lambda: require_delegation(None, self.read))

    def test_self_account_grant_deny_and_deny_removal_are_all_rejected(self):
        AccountPermission.objects.create(account=self.actor, permission=self.read, effect="Deny")
        for operation in (self.grant_account, self.deny_account, self.deactivate):
            self.assert_denied_unchanged(lambda operation=operation: operation(target=self.actor))

    def test_any_role_currently_assigned_to_actor_is_protected(self):
        AccountRole.objects.create(account=self.actor, role=self.student)
        self.assert_denied_unchanged(self.grant_role)
        self.assert_denied_unchanged(lambda: revoke_role_permission(actor=self.actor, role=self.student, permission=self.read))

    def test_reserved_administrative_roles_cannot_be_mutated(self):
        for name in ("Admin", "Technical Super Admin"):
            role = Role.objects.create(role_name=name)
            self.assert_denied_unchanged(lambda: self.grant_role(role=role))

    def test_stale_forged_role_label_does_not_hide_reserved_role(self):
        role = Role.objects.create(role_name="Admin")
        role.role_name = "Student"
        self.assert_denied_unchanged(lambda: self.grant_role(role=role))

    def test_accounts_with_reserved_roles_are_protected_even_if_that_role_is_inactive(self):
        admin = Role.objects.create(role_name="Admin", is_active=False)
        AccountRole.objects.create(account=self.target, role=admin)
        self.assert_denied_unchanged(self.grant_account)
        self.assert_denied_unchanged(self.deny_account)

    def test_governance_permissions_cannot_be_mutated_even_if_policy_lists_them(self):
        for permission in (self.role_manage, self.account_manage, self.delegate):
            self.assert_denied_unchanged(lambda permission=permission: self.grant_role(permission=permission))
            self.assert_denied_unchanged(lambda permission=permission: self.grant_account(permission=permission))

    def test_governance_classification_cannot_be_hidden_by_stale_permission_fields(self):
        self.role_manage.permission_code = self.read.permission_code
        self.role_manage.service = self.service
        self.assert_denied_unchanged(lambda: self.grant_role(permission=self.role_manage))

    def test_governance_module_namespace_and_service_are_all_protected(self):
        hidden = make_permission(self.service, "test.records.hidden", "access_control")
        self.assert_denied_unchanged(lambda: self.grant_role(permission=hidden))
        namespace = make_permission(self.service, "accounts.approve")
        self.assert_denied_unchanged(lambda: self.grant_role(permission=namespace))
        accounts_service = Service.objects.create(service_code="accounts", service_name="Protected accounts")
        other = make_permission(accounts_service, "test.accounts.hidden")
        self.assert_denied_unchanged(lambda: self.grant_role(permission=other))

    def test_inactive_target_service_or_governance_service_is_rejected(self):
        Service.objects.filter(pk=self.service.pk).update(is_active=False)
        self.assert_denied_unchanged(self.grant_role)
        Service.objects.filter(pk=self.service.pk).update(is_active=True)
        Service.objects.filter(pk=self.governance.pk).update(is_active=False)
        self.assert_denied_unchanged(self.grant_account)

    def test_inactive_target_role_is_rejected(self):
        Role.objects.filter(pk=self.student.pk).update(is_active=False)
        self.assert_denied_unchanged(self.grant_role)

    def test_ineligible_target_accounts_are_rejected(self):
        for status, active in (("Pending", True), ("Rejected", True), ("Approved", False)):
            Account.objects.filter(pk=self.target.pk).update(request_status=status, is_active=active)
            self.assert_denied_unchanged(self.grant_account)
        Account.objects.filter(pk=self.target.pk).update(request_status="Approved", is_active=True)
        AccountRole.objects.filter(account=self.target).delete()
        self.assert_denied_unchanged(self.grant_account)

    def test_unreviewed_extra_active_target_role_blocks_override(self):
        extra = Role.objects.create(role_name="Unreviewed role")
        AccountRole.objects.create(account=self.target, role=extra)
        self.assert_denied_unchanged(self.grant_account)

    def test_requested_role_alone_does_not_create_management_authority(self):
        admin = Role.objects.create(role_name="Admin")
        Account.objects.filter(pk=self.actor.pk).update(requested_role=admin)
        RolePermission.objects.filter(role=self.operator_role, permission=self.role_manage).delete()
        RolePermission.objects.create(role=admin, permission=self.role_manage)
        self.assert_denied_unchanged(self.grant_role)

    def test_raw_wrong_unsaved_or_missing_references_are_rejected(self):
        for actor in (None, AnonymousUser(), self.actor.pk, Account(account_id=self.actor.pk)):
            self.assert_denied_unchanged(lambda actor=actor: self.grant_role(actor=actor), PermissionManagementValidationError)
        self.assert_denied_unchanged(lambda: self.grant_role(role=self.student.pk), PermissionManagementValidationError)
        self.assert_denied_unchanged(lambda: self.grant_account(target=None), PermissionManagementValidationError)
        self.assert_denied_unchanged(lambda: self.grant_role(permission=Permission(permission_id=self.read.pk)), PermissionManagementValidationError)

    def test_cross_database_references_are_rejected(self):
        self.actor._state.db = "untrusted"
        self.assert_denied_unchanged(self.grant_role, PermissionManagementValidationError)

    def test_deleted_permission_is_rejected_without_audit(self):
        Permission.objects.filter(pk=self.read.pk).delete()
        self.assert_denied_unchanged(self.grant_role, PermissionManagementValidationError)

    def test_invalid_reason_is_rejected_even_for_an_idempotent_request(self):
        self.grant_role()
        self.assert_denied_unchanged(lambda: self.grant_role(reason="password=private"), PermissionManagementValidationError)

    def test_authorization_failure_on_repeated_operation_is_not_hidden_as_a_noop(self):
        self.grant_role()
        RolePermission.objects.filter(role=self.operator_role, permission=self.role_manage).delete()
        self.assert_denied_unchanged(self.grant_role)

    def test_audit_failure_rolls_back_new_role_grant(self):
        with patch("apps.access_control.mutations.audit.record_access_audit", side_effect=RuntimeError("audit unavailable")):
            self.assert_denied_unchanged(self.grant_role, RuntimeError)

    def test_audit_failure_rolls_back_override_effect_activation_and_attribution(self):
        AccountPermission.objects.create(account=self.target, permission=self.read, effect="Deny", is_active=False)
        with patch("apps.access_control.mutations.audit.record_access_audit", side_effect=IntegrityError("audit write failed")):
            self.assert_denied_unchanged(self.grant_account, IntegrityError)

    def test_audit_validation_failure_rolls_back_permission_mutation(self):
        with patch("apps.access_control.mutations.audit.record_access_audit", side_effect=audit.AuditValidationError("rejected audit")):
            self.assert_denied_unchanged(self.grant_account, audit.AuditValidationError)

    def test_no_role_assignments_account_changes_or_privileged_roles_are_created(self):
        assignments = list(AccountRole.objects.order_by("pk").values())
        accounts = list(Account.objects.order_by("pk").values("pk", "is_active", "request_status"))
        self.grant_role()
        self.grant_account()
        self.deny_account()
        self.deactivate()
        self.assertEqual(list(AccountRole.objects.order_by("pk").values()), assignments)
        self.assertEqual(list(Account.objects.order_by("pk").values("pk", "is_active", "request_status")), accounts)
        self.assertFalse(Role.objects.filter(role_name="Technical Super Admin").exists())


@override_settings(ACCESS_CONTROL_DELEGATION_POLICY=POLICY)
class PermissionMutationTransactionTests(_Helpers, TransactionTestCase):
    def setUp(self):
        fixtures(self)

    def test_success_is_returned_only_after_mutation_and_audit_are_committed(self):
        original = audit.record_access_audit
        role_id, permission_id = self.student.pk, self.read.pk

        def observed():
            try:
                verify_database()
                return RolePermission.objects.filter(role_id=role_id, permission_id=permission_id).exists(), AccessAuditLog.objects.count()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as executor:
            def stage_and_observe(**kwargs):
                original(**kwargs)
                self.assertEqual(executor.submit(observed).result(timeout=10), (False, 0))

            with patch("apps.access_control.mutations.audit.record_access_audit", side_effect=stage_and_observe):
                self.assertTrue(self.grant_role())
            self.assertEqual(executor.submit(observed).result(timeout=10), (True, 1))

    def test_audit_failure_rolls_back_a_real_owned_transaction(self):
        with patch("apps.access_control.mutations.audit.record_access_audit", side_effect=IntegrityError("audit failed")):
            self.assert_denied_unchanged(self.grant_role, IntegrityError)

    def test_nesting_in_a_caller_transaction_is_rejected_without_writes(self):
        before = self.state()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.grant_role()
        self.assertEqual(self.state(), before)

    def test_concurrent_identical_grants_create_one_unique_row_and_one_audit(self):
        actor_id, role_id, permission_id = self.actor.pk, self.student.pk, self.read.pk
        barrier = Barrier(2)

        def run():
            try:
                verify_database()
                actor, role, permission = Account.objects.get(pk=actor_id), Role.objects.get(pk=role_id), Permission.objects.get(pk=permission_id)
                barrier.wait(timeout=10)
                return grant_role_permission(actor=actor, role=role, permission=permission)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(RolePermission.objects.filter(role_id=role_id, permission_id=permission_id).count(), 1)
        self.assertEqual(AccessAuditLog.objects.count(), 1)

    def test_concurrent_grant_and_deny_are_serialized_with_a_consistent_audit_chain(self):
        actor_id, target_id, permission_id = self.actor.pk, self.target.pk, self.read.pk
        barrier = Barrier(2)

        def run(operation):
            try:
                verify_database()
                actor, target, permission = Account.objects.get(pk=actor_id), Account.objects.get(pk=target_id), Permission.objects.get(pk=permission_id)
                barrier.wait(timeout=10)
                return operation(actor=actor, target=target, permission=permission)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, operation) for operation in (grant_account_permission, deny_account_permission)]
            self.assertTrue(all(future.result(timeout=20) for future in futures))
        rows = list(AccountPermission.objects.filter(account_id=target_id, permission_id=permission_id))
        events = list(AccessAuditLog.objects.order_by("pk"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1].old_value, events[0].new_value)
        self.assertEqual(events[1].new_value["effect"], rows[0].effect)
        self.assertEqual(has_permission(self.target, self.read.permission_code), rows[0].effect == "Grant")
