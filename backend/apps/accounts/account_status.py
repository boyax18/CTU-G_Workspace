"""WF-02.05 Activate or deactivate an existing account (stage 1, owner-authorized 18 Nov 2026).

Governance-sensitive. Changes ONLY accounts.is_active (D-65) for an eligible Approved school
account (D-63), plus the session-revocation counter that SR-1 Stage A requires (security state), never request_status, review fields, roles, direct permissions, identity,
credentials or profile. One locked transaction reuses the WF-02.03/02.04 lock order and re-checks
the exact effective permission inside the lock; the caller's confirmed state must still hold
(D-68); one append-only audit event is written in the same transaction (D-67).

Sessions (D-66; SR-1 Stage A, owner-authorized 19 Nov 2026): suspension and reactivation each
advance the account's persistent session-revocation counter (session_revocation.advance) in the
same transaction, so every session signed in before the change fails Django's per-request
session-hash check and a reactivation can never revive it. The counter is not derived from the
audit row, so deleting or changing that row cannot revive a session either. Administrators, governance and framework accounts and the
actor are protected (D-71). Disabled by default; refused while the protected writer is enabled,
because the executor protocol has no account-status operation (D-69). NOT mounted in config.urls.
"""

import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models import Max

from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccessAuditLog, AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.access_control.writer_boundary import WriterBoundaryUnavailable, writer_atomic

from . import session_revocation
from .models import Account
from .registration_review import RegistrationReviewDenied, RegistrationReviewUnavailable

READ_CODE = "accounts.school_accounts.read"
SUSPEND_CODE = "accounts.school_accounts.suspend"
ACTIVATE_CODE = "accounts.school_accounts.activate"
SUSPEND_ACTION = "account.status.suspend"
ACTIVATE_ACTION = "account.status.activate"
GATE_SETTING = "WORKSPACE_ACCOUNT_STATUS_ENABLED"
# Same normalization as the executor's wex_reserved(): administrator and governance roles.
_RESERVED = frozenset({"admin", "superadmin", "technicalsuperadmin"})


class AccountStatusDenied(RegistrationReviewDenied):
    """Unknown, ineligible or unauthorized target: the shared non-enumerating 404/denial."""


class AccountStatusUnavailable(RegistrationReviewUnavailable):
    """Gate off, catalogue rows missing or transaction conditions unavailable (503)."""


class AccountStatusConflict(Exception):
    """D-68 fixed conflict for an account the reviewer may read; never account data."""

    REASONS = frozenset({"state_changed", "protected_account", "no_operational_role"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "state_changed"
        super().__init__("The account status could not be changed.")


def is_reserved_role(role_name):
    return type(role_name) is str and re.sub(r"[\s\W_]+", "", role_name).lower() in _RESERVED


def status_epoch(account_id):
    """DIAGNOSTIC ONLY since SR-1 Stage A: primary key of the account's latest committed suspension OR
    role grant/revoke audit receipt (Technical Super Admin path and Django Superuser procedure), or 0.

    It is NOT a security control and is no longer part of the session hash: receipts can be deleted
    or changed by a database-privileged writer, which moves this value backwards (SR-1). Session
    revocation uses Account.session_revocation_version (apps.accounts.session_revocation).
    """
    if type(account_id) is not int:
        return 0
    from apps.access_control.role_management import ROLE_CHANGE_ACTIONS
    return (AccessAuditLog.objects.using(DEFAULT_DB_ALIAS)
            .filter(target_account_id=account_id, action__in=(SUSPEND_ACTION, *ROLE_CHANGE_ACTIONS))
            .aggregate(epoch=Max("pk"))["epoch"] or 0)


def gate_open():
    return getattr(settings, GATE_SETTING, False) is True


def _change(*, actor, target_id, activate, expected_active):
    if not gate_open():
        raise AccountStatusUnavailable("Account status changes are not activated.")
    from apps.access_control.executor.client import enabled as executor_enabled
    if executor_enabled():
        # D-69: the protected executor has no account-status operation; refuse rather than bypass it.
        raise WriterBoundaryUnavailable("Account status changes are not supported by the protected writer.")
    if type(expected_active) is not bool or expected_active is activate:
        # Suspension confirms an active account; reactivation confirms an inactive one.
        raise AccountStatusConflict("state_changed")
    if (not isinstance(actor, Account) or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS
            or type(actor.pk) is not int):
        raise AccountStatusDenied("An existing Workspace actor is required.")
    if type(target_id) is not int or not 1 <= target_id <= 2_147_483_647:
        raise AccountStatusDenied("An existing account is required.")
    if actor.pk == target_id:
        raise AccountStatusConflict("protected_account")  # D-71: never the actor's own account

    code = ACTIVATE_CODE if activate else SUSPEND_CODE
    with writer_atomic():
        connection = transaction.get_connection(DEFAULT_DB_ALIAS)
        if connection.vendor != "mysql" or connection.isolation_level != "read committed":
            raise AccountStatusUnavailable("Account status requires primary MySQL READ COMMITTED.")
        db = Account.objects.using(DEFAULT_DB_ALIAS)
        # Lock order shared with WF-02.03/02.04 and permission management.
        services = {row.service_code: row for row in Service.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                    .filter(service_code__in=["access_control", "accounts"]).order_by("service_id")}
        if set(services) != {"access_control", "accounts"} or not all(s.is_active for s in services.values()):
            raise AccountStatusUnavailable("Active approved service definitions are required.")
        permissions = list(Permission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                           .filter(permission_code=code, service_id=services["accounts"].pk).order_by("permission_id"))
        if len(permissions) != 1:
            raise AccountStatusUnavailable("Account status authority is not available.")
        accounts = {row.pk: row for row in db.select_for_update().filter(pk__in=[actor.pk, target_id]).order_by("account_id")}
        if set(accounts) != {actor.pk, target_id}:
            raise AccountStatusDenied("The reviewer or target no longer exists.")
        reviewer, target = accounts[actor.pk], accounts[target_id]
        if reviewer.is_staff or reviewer.is_superuser or not reviewer.is_active or reviewer.request_status != "Approved":
            raise AccountStatusDenied("An eligible Workspace administrator is required.")
        assignments = list(AccountRole.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                           .filter(account_id__in=[actor.pk, target_id]).order_by("account_role_id"))
        roles = {row.pk: row for row in Role.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                 .filter(pk__in={a.role_id for a in assignments}).order_by("role_id")}
        reviewer_roles = [roles[a.role_id] for a in assignments if a.account_id == actor.pk and a.role_id in roles]
        if not any(r.role_name == "Admin" and r.is_active for r in reviewer_roles):
            raise AccountStatusDenied("The actor needs an active Admin assignment.")
        list(RolePermission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(role_id__in={r.pk for r in reviewer_roles}).order_by("role_permission_id").values_list("pk", flat=True))
        list(AccountPermission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(account_id=actor.pk).order_by("account_permission_id").values_list("pk", flat=True))
        if not has_permission(reviewer, code):
            raise AccountStatusDenied("The actor lacks this exact effective permission.")

        # D-63 (revised): only Approved accounts; Pending and Rejected look like unknown ones.
        if target.request_status != "Approved":
            raise AccountStatusDenied("The account is not an eligible school account.")
        target_roles = [roles[a.role_id] for a in assignments if a.account_id == target_id and a.role_id in roles]
        if target.is_staff or target.is_superuser or any(is_reserved_role(r.role_name) for r in target_roles):
            raise AccountStatusConflict("protected_account")  # D-71
        if target.is_active is not expected_active:
            raise AccountStatusConflict("state_changed")  # D-68: never a second decision or audit
        if activate and not any(r.is_active for r in target_roles):
            # D-63: reactivate only into the existing login eligibility; never grant a role here.
            raise AccountStatusConflict("no_operational_role")

        changed = db.filter(pk=target_id, is_active=expected_active, request_status="Approved").update(is_active=activate)
        if changed != 1:
            raise AccountStatusUnavailable("The account status could not be changed.")
        record_access_audit(
            actor=reviewer, target=target,
            action=ACTIVATE_ACTION if activate else SUSPEND_ACTION,
            old_value={"account_id": target_id, "request_status": "Approved", "is_active": expected_active},
            new_value={"account_id": target_id, "request_status": "Approved", "is_active": activate},
            reason="account_status_change",
        )
        # D-66 / SR-1: end every earlier session in the same transaction (the target row is already locked).
        session_revocation.advance(target_id)
    return {"account_id": target_id, "is_active": activate}


def suspend_account(*, actor, target_id, expected_active=True):
    """Deactivate an eligible Approved school account; effective access ends on the next request."""
    return _change(actor=actor, target_id=target_id, activate=False, expected_active=expected_active)


def activate_account(*, actor, target_id, expected_active=False):
    """Reactivate an eligible Approved school account that still holds an active role."""
    return _change(actor=actor, target_id=target_id, activate=True, expected_active=expected_active)
