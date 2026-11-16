"""Disposable-MySQL-only AR-6C7C.7 inactive Admin-binding transaction exercise.

This is NOT an operational grant initializer, approval mechanism or permission
activation path. Only import from Django tests with --settings=config.test_settings.
No management command, API, task or live service may call this test fixture.
"""
from __future__ import annotations

from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccountPermission, AccountRole, Permission, Role, RolePermission, Service,
)
from apps.access_control.tests_support import registration_review_metadata as metadata


class TestInactiveGrantRefused(RuntimeError):
    """An unsafe or unapproved test fixture state was encountered."""


def exercise_inactive_admin_bindings_in_disposable_test(*, test_audit_actor):
    """Stage exactly three INACTIVE Admin bindings and audited receipts in TEST DB.

    This intentionally has no parameter to activate grants or services. A
    synthetic test actor supplies attribution, NEVER governance authorization.
    Calling this with real development settings is refused before any query.
    """
    try:
        metadata._assert_test_database()
        service_defs, permission_defs = metadata._metadata_from_frozen_draft()
    except Exception as exc:
        raise TestInactiveGrantRefused("Disposable database and pinned blocked draft are required.") from exc

    if (not isinstance(test_audit_actor, Account)
            or test_audit_actor._state.adding
            or test_audit_actor._state.db != DEFAULT_DB_ALIAS
            or type(test_audit_actor.pk) is not int):
        raise TestInactiveGrantRefused("A persisted synthetic test audit actor is required.")

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        try:
            admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
            raise TestInactiveGrantRefused("A unique active Admin fixture role is required.") from exc
        if not Account.objects.filter(pk=test_audit_actor.pk).exists():
            raise TestInactiveGrantRefused("The synthetic actor does not exist.")
        if AccountPermission.objects.exists():
            raise TestInactiveGrantRefused("Account overrides are not part of this fixture.")
        if Service.objects.count() != len(metadata.SERVICE_CODES):
            raise TestInactiveGrantRefused("Unexpected service count.")
        services = {row.service_code: row for row in Service.objects.select_for_update()}
        if set(services) != set(metadata.SERVICE_CODES):
            raise TestInactiveGrantRefused("Unexpected services.")
        for code, service in services.items():
            if not metadata._same_service(service, service_defs[code]):
                raise TestInactiveGrantRefused("Service mismatch or service already active.")
        if Permission.objects.count() != len(metadata.PERMISSION_CODES):
            raise TestInactiveGrantRefused("Unexpected permission count.")
        permissions = {row.permission_code: row for row in Permission.objects.select_for_update()}
        if set(permissions) != set(metadata.PERMISSION_CODES):
            raise TestInactiveGrantRefused("Unexpected permission definitions.")
        for code, permission in permissions.items():
            expected = permission_defs[code]
            if not metadata._same_permission(permission, expected, services[expected["service_code"]].pk):
                raise TestInactiveGrantRefused("Permission metadata mismatch.")

        # Existing role assignments are never changed by this test fixture.
        assignment_count = AccountRole.objects.count()
        existing = list(RolePermission.objects.select_for_update())
        if any(row.role_id != admin.pk or row.permission_id not in {p.pk for p in permissions.values()}
               or row.is_active or row.granted_by_id != test_audit_actor.pk for row in existing):
            raise TestInactiveGrantRefused("Existing active, foreign, or unattributed bindings are not allowed.")
        if len(existing) != len({row.permission_id for row in existing}):
            raise TestInactiveGrantRefused("Duplicate role bindings are not allowed.")
        already_present = {row.permission_id for row in existing}
        created = 0
        for code in metadata.PERMISSION_CODES:
            permission = permissions[code]
            if permission.pk in already_present:
                continue
            row = RolePermission.objects.create(
                role=admin, permission=permission,
                is_active=False, granted_by=test_audit_actor,
            )
            record_access_audit_receipt(
                actor=test_audit_actor, role=admin, permission=permission,
                action="test.role_permission.stage_inactive",
                old_value=None,
                new_value={"role_id": admin.pk, "permission_id": permission.pk,
                           "role_permission_id": row.pk, "is_active": False},
                reason="permission_change",
            )
            created += 1
        if (Service.objects.filter(is_active=True).exists()
                or RolePermission.objects.filter(is_active=True).exists()
                or AccountPermission.objects.exists()
                or AccountRole.objects.count() != assignment_count):
            raise TestInactiveGrantRefused("The test fixture changed protected effective access or assignments.")
    return {"inactive_bindings_created": created, "active_grants": 0,
            "services_activated": 0, "test_database_only": True}
