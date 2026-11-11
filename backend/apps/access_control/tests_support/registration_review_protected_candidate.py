"""AR-6C7D.4: disposable-MySQL-only integration candidate for protected review grants.

TEST SUPPORT ONLY. No URL, management command, task, or production service may
import or call this module. It cannot create active grants, enable services,
mount review routes, approve registrations, or authorize real initialization.
The user's scoped approval is NOT independent security/operator signoff.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.models import Account
from apps.access_control.models import (
    AccessAuditLog, AccountPermission, AccountRole, Permission, Role,
    RolePermission, Service,
)
from apps.access_control.tests_support import (
    registration_review_inactive_grants as inactive,
    registration_review_metadata as metadata,
)


class ProtectedCandidateRefused(RuntimeError):
    """A disposable-test precondition or exact audit invariant failed."""


_ACTIONS = (
    "test.catalogue.service.create",
    "test.catalogue.permission.create",
    "test.role_permission.stage_inactive",
)


def _require(condition, message):
    if not condition:
        raise ProtectedCandidateRefused(message)


def _verify_exact_audit_receipts(*, actor, admin):
    """Require one attributed, exact-state receipt for each of the eight rows.

    This is a test-fixture consistency proof, NOT independent approval evidence.
    Existing rows with missing/foreign/modified audit receipts fail closed.
    """
    services = {r.service_code: r for r in Service.objects.select_for_update().all()}
    permissions = {r.permission_code: r for r in Permission.objects.select_for_update().all()}
    grants = list(RolePermission.objects.select_for_update().all())
    _require(set(services) == set(metadata.SERVICE_CODES) and len(services) == 2,
             "Exact two service definitions required.")
    _require(set(permissions) == set(metadata.PERMISSION_CODES) and len(permissions) == 3,
             "Exact three permission definitions required.")
    _require(len(grants) == 3 and {g.permission_id for g in grants} ==
             {p.pk for p in permissions.values()}, "Exact three bindings required.")
    _require(not AccountPermission.objects.exists() and
             not Service.objects.filter(is_active=True).exists() and
             not RolePermission.objects.filter(is_active=True).exists(),
             "No active services, grants, or overrides may exist.")

    expected = set()
    def marker(action, role_id, permission_id, snapshot):
        return (action, role_id, permission_id, json.dumps(snapshot, sort_keys=True))

    for service in services.values():
        expected.add(marker("test.catalogue.service.create", None, None,
                            {"service_id": service.pk, "is_active": False}))
    for permission in permissions.values():
        expected.add(marker("test.catalogue.permission.create", None, permission.pk,
                            {"service_id": permission.service_id,
                             "permission_id": permission.pk}))
    for grant in grants:
        _require(grant.role_id == admin.pk and grant.is_active is False and
                 grant.granted_by_id == actor.pk, "Grant attribution or inactive scope differs.")
        expected.add(marker("test.role_permission.stage_inactive", admin.pk,
                            grant.permission_id,
                            {"role_id": admin.pk, "permission_id": grant.permission_id,
                             "role_permission_id": grant.pk, "is_active": False}))

    # Check ALL receipts for these exact action codes, including a foreign actor's.
    # A duplicate, wrong actor or altered snapshot cannot be silently ignored.
    rows = list(AccessAuditLog.objects.select_for_update()
                .filter(action__in=_ACTIONS).order_by("access_audit_log_id"))
    _require(len(rows) == 8 and len(expected) == 8,
             "Exactly eight unique test audit receipts are required.")
    actual = set()
    for row in rows:
        _require(row.actor_account_id == actor.pk and
                 row.target_account_id is None and
                 row.old_value is None and
                 row.reason == "permission_change" and
                 type(row.new_value) is dict,
                 "Test audit attribution, reason or state differs.")
        actual.add(marker(row.action, row.role_id, row.permission_id, row.new_value))
    _require(actual == expected, "Test audit receipts do not match all eight records.")
    return len(rows)


def exercise_protected_initialization_candidate_in_disposable_test(*, test_audit_actor):
    """Atomically stage 2 inactive services, 3 permissions, 3 INACTIVE grants.

    Guarded by pinned DRAFT catalogue and disposable MySQL settings. On failure,
    the entire transaction—including both nested fixtures' audits—rolls back.
    Repeated calls require the original eight exact audit receipts and add zero
    new records. This function NEVER activates access or asserts real approval.
    """
    try:
        metadata._assert_test_database()
        metadata._metadata_from_frozen_draft()
    except Exception as exc:
        raise ProtectedCandidateRefused("Disposable MySQL and pinned blocked draft required.") from exc

    _require(getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False) is False and
             getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False) is False,
             "Registration-review activation gates must remain false.")
    _require(isinstance(test_audit_actor, Account) and
             test_audit_actor._state.adding is False and
             test_audit_actor._state.db == DEFAULT_DB_ALIAS and
             type(test_audit_actor.pk) is int and 1 <= test_audit_actor.pk <= 2_147_483_647,
             "A persisted synthetic test audit actor is required.")

    with transaction.atomic(using=DEFAULT_DB_ALIAS):
        try:
            admin = Role.objects.select_for_update().get(role_name="Admin", is_active=True)
        except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
            raise ProtectedCandidateRefused("Exactly one active Admin fixture role required.") from exc
        _require(Account.objects.filter(pk=test_audit_actor.pk).exists(),
                 "Synthetic test actor is missing.")
        assignment_ids_before = list(AccountRole.objects.order_by("account_role_id")
                                     .values_list("account_role_id", flat=True))
        existing = RolePermission.objects.count()
        _require(existing in (0, 3), "Partial/foreign preexisting bindings are not accepted.")
        if existing == 0:
            metadata_report = metadata.exercise_metadata_transaction_in_disposable_test(
                test_audit_actor=test_audit_actor)
        else:
            # The original metadata fixture correctly refuses any existing
            # bindings. A complete repeat run must verify, not recreate, them.
            metadata_report = {"created_services": 0, "created_permissions": 0}
        grant_report = inactive.exercise_inactive_admin_bindings_in_disposable_test(
            test_audit_actor=test_audit_actor)
        _require(grant_report == {
            "inactive_bindings_created": 3 if existing == 0 else 0,
            "active_grants": 0, "services_activated": 0, "test_database_only": True,
        }, "Inactive-grant fixture returned an unexpected result.")
        receipt_count = _verify_exact_audit_receipts(actor=test_audit_actor, admin=admin)
        _require(assignment_ids_before == list(AccountRole.objects.order_by("account_role_id")
                                              .values_list("account_role_id", flat=True)),
                 "Account role assignments must remain unchanged.")

    return {
        "created_services": metadata_report["created_services"],
        "created_permissions": metadata_report["created_permissions"],
        "inactive_bindings_created": grant_report["inactive_bindings_created"],
        "audit_receipts_verified": receipt_count,
        "active_grants": 0,
        "services_activated": 0,
        "api_activated": False,
        "test_database_only": True,
        "live_execution_authorized": False,
    }
