"""AR-6C7C.6: disposable-MySQL-only registration-review metadata fixture.

NOT a live initializer, bootstrap mechanism, permission grant, or approval system.
No command, URL, task, or live entrypoint should import/call this fixture.
Only call it inside Django tests with --settings=config.test_settings.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.models import (
    AccountPermission,
    Permission,
    Role,
    RolePermission,
    Service,
)
from scripts.validate_registration_review_execution_contract import (
    load_local,
    verify_contract,
)


SERVICE_CODES = ("accounts", "access_control")
PERMISSION_CODES = (
    "accounts.registration_requests.read",
    "accounts.registration_requests.approve",
    "accounts.registration_requests.reject",
)
TEST_NAME_PATTERN = re.compile(r"test_ctug_registration_[0-9a-f]{16}\Z")


class TestMetadataRefused(RuntimeError):
    """Unsafe database, unexpected metadata, or unapproved fixture shape."""


def _assert_test_database():
    """Do not even query MySQL unless the disposable-test safeguards agree."""
    name = getattr(settings, "REGISTRATION_TEST_DATABASE", None)
    if not isinstance(name, str) or TEST_NAME_PATTERN.fullmatch(name) is None:
        raise TestMetadataRefused("Disposable registration-test database is required.")
    if getattr(settings, "TEST_RUNNER", None) != "config.test_runner.IsolatedMySQLRunner":
        raise TestMetadataRefused("Required isolated MySQL test runner is not configured.")
    if DEFAULT_DB_ALIAS != "default" or len(list(connections)) != 1:
        raise TestMetadataRefused("Fixture requires a single primary test database.")
    db = connections[DEFAULT_DB_ALIAS]
    config = db.settings_dict
    if (db.vendor != "mysql" or config.get("NAME") != name
            or config.get("TEST", {}).get("NAME") != name
            or str(config.get("HOST") or "").lower() not in ("127.0.0.1", "localhost", "::1")):
        raise TestMetadataRefused("Refusing a non-isolated or unexpected database configuration.")
    with db.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        selected = cursor.fetchone()[0]
    if selected != name:
        raise TestMetadataRefused("Connected database differs from the disposable test database.")


def _metadata_from_frozen_draft():
    try:
        contract, profile, source, raw = load_local()
        result = verify_contract(contract, profile, source, raw)
    except Exception as exc:
        raise TestMetadataRefused("Frozen, blocked registration-review draft is invalid.") from exc
    if (result.get("all_gates_blocked") is not True or result.get("execution_authorized") is not False
            or result.get("database_accessed") is not False):
        raise TestMetadataRefused("The draft's non-executable status was not preserved.")
    services = {row["service_code"]: row for row in source["services"] if row.get("service_code") in SERVICE_CODES}
    permissions = {row["permission_code"]: row for row in source["permissions"] if row.get("permission_code") in PERMISSION_CODES}
    if set(services) != set(SERVICE_CODES) or set(permissions) != set(PERMISSION_CODES):
        raise TestMetadataRefused("Exact metadata allowlist is unavailable.")
    return services, permissions


def _same_service(existing, expected):
    return (
        existing.service_code == expected["service_code"]
        and existing.service_name == expected["service_name"]
        and existing.description == expected["description"]
        and existing.is_active is False
    )


def _same_permission(existing, expected, service_id):
    return (
        existing.service_id == service_id
        and existing.permission_code == expected["permission_code"]
        and existing.permission_name == expected["permission_name"]
        and existing.module_name == expected["module_name"]
        and existing.action_name == expected["action_name"]
        and existing.description == expected["description"]
    )


def exercise_metadata_transaction_in_disposable_test(*, test_audit_actor):
    """Create *only* inactive metadata and bounded audits in disposable MySQL.

    A synthetic test actor is audit attribution, NOT governance approval.
    This function is forbidden for real databases even if imported manually.
    The role grants, service activation, APIs, and user assignments stay untouched.
    Duplicate runs with exactly matching metadata are audit-idempotent.
    """
    _assert_test_database()
    service_defs, permission_defs = _metadata_from_frozen_draft()
    if (not isinstance(test_audit_actor, Account)
            or test_audit_actor._state.adding
            or test_audit_actor._state.db != DEFAULT_DB_ALIAS
            or not isinstance(test_audit_actor.pk, int)
            or type(test_audit_actor.pk) is bool):
        raise TestMetadataRefused("A persisted synthetic test audit actor is required.")

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        # Lock order: canonical Admin row -> existing Services -> Permissions.
        # This serializes overlapping calls to THIS test-only fixture.
        try:
            admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
            raise TestMetadataRefused("A unique active Admin fixture role is required.") from exc
        if (RolePermission.objects.exists() or AccountPermission.objects.exists()):
            raise TestMetadataRefused("An isolated metadata test must not have grants or overrides.")
        if (Service.objects.exclude(service_code__in=SERVICE_CODES).exists()
                or Permission.objects.exclude(permission_code__in=PERMISSION_CODES).exists()):
            raise TestMetadataRefused("Unexpected catalogue records exist in the disposable database.")

        existing_services = {s.service_code: s for s in Service.objects.select_for_update().all()}
        existing_permissions = {p.permission_code: p for p in Permission.objects.select_for_update().all()}
        if len(existing_services) != Service.objects.count() or len(existing_permissions) != Permission.objects.count():
            raise TestMetadataRefused("Duplicate metadata records are not permitted.")

        # Verify every existing row *before* writing anything.
        for code, obj in existing_services.items():
            if not _same_service(obj, service_defs[code]):
                raise TestMetadataRefused("Existing service metadata differs from the frozen proposal.")
        for code, obj in existing_permissions.items():
            expected = permission_defs[code]
            owner = existing_services.get(expected["service_code"])
            if owner is None or not _same_permission(obj, expected, owner.pk):
                raise TestMetadataRefused("Existing permission metadata differs from the frozen proposal.")

        created_services = 0
        created_permissions = 0
        for code in SERVICE_CODES:
            if code in existing_services:
                continue
            row = service_defs[code]
            service = Service.objects.create(
                service_code=code,
                service_name=row["service_name"],
                description=row["description"],
                is_active=False,
            )
            record_access_audit_receipt(
                actor=test_audit_actor,
                action="test.catalogue.service.create",
                old_value=None,
                new_value={"service_id": service.pk, "is_active": False},
                reason="permission_change",
            )
            existing_services[code] = service
            created_services += 1

        for code in PERMISSION_CODES:
            if code in existing_permissions:
                continue
            row = permission_defs[code]
            service = existing_services[row["service_code"]]
            permission = Permission.objects.create(
                service=service,
                permission_code=code,
                permission_name=row["permission_name"],
                module_name=row["module_name"],
                action_name=row["action_name"],
                description=row["description"],
            )
            record_access_audit_receipt(
                actor=test_audit_actor,
                permission=permission,
                action="test.catalogue.permission.create",
                old_value=None,
                new_value={"service_id": service.pk, "permission_id": permission.pk},
                reason="permission_change",
            )
            created_permissions += 1

        if (RolePermission.objects.exists() or AccountPermission.objects.exists()
                or not Role.objects.filter(pk=admin.pk, is_active=True).exists()):
            raise TestMetadataRefused("The fixture changed protected authorization state.")

    return {"created_services": created_services, "created_permissions": created_permissions,
            "grants_created": 0, "services_activated": 0, "test_database_only": True}
