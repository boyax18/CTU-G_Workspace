"""Internal permission mutations; no endpoints, provisioning, or role assignment.

Every operation owns a durable primary-database transaction. The existing
access_control Service is a conservative management mutex; it is never created.
"""

from contextlib import contextmanager
from dataclasses import dataclass

from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.fields import CurrentTimestamp
from apps.accounts.models import Account

from . import audit
from .delegation import (
    ACCOUNT_PERMISSION_MANAGE, GOVERNANCE_SERVICE, ROLE_PERMISSION_MANAGE,
    DelegationPolicyUnavailable, PermissionManagementDenied,
    PermissionManagementValidationError, approved_scope, is_governance_permission,
    is_reserved_role, require_delegation, require_governance_authority,
)
from .models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service


def _pk(value, model):
    if (not isinstance(value, model) or value._state.adding or value._state.db != DEFAULT_DB_ALIAS
            or type(value.pk) is not int or not 1 <= value.pk <= 2_147_483_647):
        raise PermissionManagementValidationError("Use existing persisted primary-database references.")
    return value.pk


def _reason(value):
    if value is not None and (type(value) is not str or value not in audit.AUDIT_REASON_CODES):
        raise PermissionManagementValidationError("Use a supported non-sensitive audit reason code.")


@dataclass(frozen=True)
class _Context:
    actor: Account
    permission: Permission
    role: Role | None
    target: Account | None


@contextmanager
def _management_context(actor, permission, management_code, *, role=None, target=None):
    actor_id, permission_id = _pk(actor, Account), _pk(permission, Permission)
    role_id = _pk(role, Role) if role is not None else None
    target_id = _pk(target, Account) if target is not None else None
    if target_id == actor_id:
        raise PermissionManagementDenied("Self-targeted permission mutations are prohibited.")

    with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
        connection = transaction.get_connection(DEFAULT_DB_ALIAS)
        if connection.vendor != "mysql" or connection.isolation_level != "read committed":
            raise DelegationPolicyUnavailable("Trusted mutations require primary MySQL READ COMMITTED isolation.")
        initial = Permission.objects.using(DEFAULT_DB_ALIAS).select_related("service").filter(pk=permission_id).first()
        if initial is None:
            raise PermissionManagementValidationError("The referenced permission does not exist.")
        if is_governance_permission(initial):
            raise PermissionManagementDenied("Governance permissions cannot be changed through ordinary services.")
        scope = approved_scope(initial.service.service_code)
        governance = Service.objects.using(DEFAULT_DB_ALIAS).filter(service_code=GOVERNANCE_SERVICE).first()
        if governance is None or governance.service_code != GOVERNANCE_SERVICE:
            raise PermissionManagementDenied("The governance catalogue is unavailable.")

        # All service-managed writes share the governance mutex. Parent locks
        # also serialize absent-row creation; unique constraints remain the final
        # protection against writers that do not follow this protocol.
        service_ids = {initial.service_id, governance.pk}
        services = {row.pk: row for row in Service.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk__in=service_ids).order_by("service_id")}
        service = services.get(initial.service_id)
        if service is None or not service.is_active or not services[governance.pk].is_active or service.service_code != scope.service_code:
            raise PermissionManagementDenied("Active unchanged services are required.")
        permissions = list(Permission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            pk=permission_id,
        ).order_by("permission_id"))
        if not permissions or permissions[0].service_id != service.pk:
            raise PermissionManagementDenied("Permission scope changed; reevaluate the operation.")
        current_permission = permissions[0]
        current_permission.service = service
        if is_governance_permission(current_permission):
            raise PermissionManagementDenied("Governance permissions are protected.")
        # Lock catalogue definitions of both authority checks, not just their grants.
        list(Permission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            permission_code__in=[management_code, scope.authority_permission],
        ).order_by("permission_id").values_list("pk", flat=True))

        account_ids = {actor_id} | ({target_id} if target_id is not None else set())
        accounts = {row.pk: row for row in Account.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            pk__in=account_ids,
        ).only("account_id", "is_active", "request_status").order_by("account_id")}
        if set(accounts) != account_ids:
            raise PermissionManagementValidationError("An account reference no longer exists.")
        locked_actor = accounts[actor_id]
        assignments = list(AccountRole.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            account_id__in=account_ids,
        ).order_by("account_role_id"))
        role_ids = {row.role_id for row in assignments} | ({role_id} if role_id is not None else set())
        roles = {row.pk: row for row in Role.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk__in=role_ids).order_by("role_id")}
        actor_role_ids = {row.role_id for row in assignments if row.account_id == actor_id}
        list(RolePermission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            role_id__in=actor_role_ids,
        ).order_by("role_permission_id").values_list("pk", flat=True))
        list(AccountPermission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            account_id=actor_id,
        ).order_by("account_permission_id").values_list("pk", flat=True))

        require_governance_authority(locked_actor, management_code)
        checked_scope = require_delegation(locked_actor, current_permission)
        if checked_scope != scope:
            raise PermissionManagementDenied("Delegation policy changed; reevaluate the operation.")
        locked_role, locked_target = None, None
        if role_id is not None:
            locked_role = roles.get(role_id)
            if locked_role is None:
                raise PermissionManagementValidationError("The role reference no longer exists.")
            if (not locked_role.is_active or is_reserved_role(locked_role.role_name)
                    or locked_role.role_name not in scope.role_names or role_id in actor_role_ids):
                raise PermissionManagementDenied("The role is not an eligible independent delegation target.")
        if target_id is not None:
            locked_target = accounts[target_id]
            target_roles = [roles[row.role_id] for row in assignments if row.account_id == target_id]
            active_names = {row.role_name for row in target_roles if row.is_active}
            if (not locked_target.is_active or locked_target.request_status != "Approved" or not active_names
                    or not active_names <= scope.role_names or any(is_reserved_role(row.role_name) for row in target_roles)):
                raise PermissionManagementDenied("The account is not an eligible ordinary delegation target.")
        yield _Context(locked_actor, current_permission, locked_role, locked_target)


def _role_snapshot(row):
    return {"role_permission_id": row.pk, "role_id": row.role_id,
            "permission_id": row.permission_id, "is_active": row.is_active}


def _change_role_permission(*, actor, role, permission, enable, reason):
    with _management_context(actor, permission, ROLE_PERMISSION_MANAGE, role=role) as context:
        _reason(reason)
        row = RolePermission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(role=context.role, permission=context.permission).first()
        if row is None and not enable or row is not None and row.is_active == enable:
            changed = False
        else:
            old = _role_snapshot(row) if row is not None else None
            if row is None:
                row = RolePermission.objects.using(DEFAULT_DB_ALIAS).create(
                    role=context.role, permission=context.permission, is_active=True, granted_by=context.actor,
                )
            else:
                row.is_active = enable
                fields = ["is_active"]
                if enable:
                    row.granted_by, row.granted_at = context.actor, CurrentTimestamp()
                    fields += ["granted_by", "granted_at"]
                row.save(using=DEFAULT_DB_ALIAS, update_fields=fields)
            audit.record_access_audit(actor=context.actor, role=context.role, permission=context.permission,
                action="role_permission.grant" if enable else "role_permission.revoke",
                old_value=old, new_value=_role_snapshot(row), reason=reason)
            changed = True
    return changed


def grant_role_permission(*, actor, role, permission, reason="permission_change"):
    """Create/enable one approved ordinary role grant; return changed after commit."""
    _pk(role, Role)
    return _change_role_permission(actor=actor, role=role, permission=permission, enable=True, reason=reason)


def revoke_role_permission(*, actor, role, permission, reason="permission_change"):
    """Disable an existing role grant; never insert an inactive placeholder."""
    _pk(role, Role)
    return _change_role_permission(actor=actor, role=role, permission=permission, enable=False, reason=reason)


def _override_snapshot(row):
    return {"account_permission_id": row.pk, "account_id": row.account_id,
            "permission_id": row.permission_id, "effect": row.effect, "is_active": row.is_active}


def _change_account_override(*, actor, target, permission, effect, deactivate, reason):
    if effect not in {"Grant", "Deny", None} or (not deactivate and effect is None):
        raise PermissionManagementValidationError("Use the Grant or Deny operation.")
    with _management_context(actor, permission, ACCOUNT_PERMISSION_MANAGE, target=target) as context:
        _reason(reason)
        row = AccountPermission.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(account=context.target, permission=context.permission).first()
        if (deactivate and (row is None or not row.is_active)) or (not deactivate and row is not None and row.is_active and row.effect == effect):
            changed = False
        else:
            old = _override_snapshot(row) if row is not None else None
            if row is None:
                row = AccountPermission.objects.using(DEFAULT_DB_ALIAS).create(
                    account=context.target, permission=context.permission, effect=effect, is_active=True, assigned_by=context.actor,
                )
            else:
                row.is_active = not deactivate
                row.updated_at = CurrentTimestamp()
                fields = ["is_active", "updated_at"]
                if not deactivate:
                    row.effect, row.assigned_by = effect, context.actor
                    fields += ["effect", "assigned_by"]
                row.save(using=DEFAULT_DB_ALIAS, update_fields=fields)
            action = (f"account_permission.{row.effect.lower()}.deactivate" if deactivate else f"account_permission.{effect.lower()}")
            audit.record_access_audit(actor=context.actor, target=context.target, permission=context.permission,
                action=action, old_value=old, new_value=_override_snapshot(row), reason=reason)
            changed = True
    return changed


def grant_account_permission(*, actor, target, permission, reason="permission_change"):
    """Create/enable Grant, including a reviewed change from Deny to Grant."""
    _pk(target, Account)
    return _change_account_override(actor=actor, target=target, permission=permission, effect="Grant", deactivate=False, reason=reason)


def deny_account_permission(*, actor, target, permission, reason="permission_change"):
    """Create/enable an explicit Deny; this is distinct from revoking a role grant."""
    _pk(target, Account)
    return _change_account_override(actor=actor, target=target, permission=permission, effect="Deny", deactivate=False, reason=reason)


def deactivate_account_override(*, actor, target, permission, reason="permission_change"):
    """Disable Grant or Deny. Disabling Deny can increase access and is fully gated."""
    _pk(target, Account)
    return _change_account_override(actor=actor, target=target, permission=permission, effect=None, deactivate=True, reason=reason)
