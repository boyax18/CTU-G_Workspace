"""Read-only, fail-closed Hybrid Dynamic Access Control evaluation.

Only persisted accounts from the primary/default database are accepted. Every
call rechecks database state in one SELECT; caller attributes, related-object
caches, requested roles, role names, and Django auth flags confer no authority.
"""

import logging

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Exists, OuterRef, Q

from apps.accounts.models import Account
from apps.accounts.active_role_context import context_enabled, selected_scope, allowed_role_ids

from .models import AccountPermission, AccountPermissionRoleScope, AccountRole, Permission, Role, RolePermission
from .permission_transitions import preserve_transition_denies
from .ordinary_role_runtime import (
    ORDINARY_ROLE_NAMES, runtime_enforcement_enabled, verified_ordinary_roles_for,
)

logger = logging.getLogger(__name__)


def _authorized_permissions(account_id):
    # This uncorrelated EXISTS gates both role grants and direct overrides. A
    # direct Grant never substitutes for an active assigned role or approval.
    eligible_assignments = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
        account_id=account_id,
        account__is_active=True,
        account__request_status="Approved",
        role__is_active=True,
    )
    # D-113: active context restricts the role sources themselves. An absent,
    # stale or cross-account context denies all access (not the union fallback).
    selected_ids = None
    if context_enabled():
        scope = selected_scope()
        if scope is None or scope.account_id != account_id:
            return Permission.objects.using(DEFAULT_DB_ALIAS).none()
        selected_ids = allowed_role_ids(account_id, scope.role_id)
        if not selected_ids:
            return Permission.objects.using(DEFAULT_DB_ALIAS).none()
        eligible_assignments = eligible_assignments.filter(role_id__in=selected_ids)

    overrides = AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(
        account_id=account_id, permission_id=OuterRef("pk"), is_active=True,
    )
    role_grants = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
        permission_id=OuterRef("pk"),
        is_active=True,
        role__is_active=True,
        role__account_assignments__account_id=account_id,
    )
    if selected_ids is not None:
        role_grants = role_grants.filter(role_id__in=selected_ids)
    # D-111: only independently verified, current ordinary assignments can
    # contribute role permissions. The mapping is fetched afresh on EVERY
    # evaluator invocation, never from session roles or cached request claims.
    # The gate is staged and default-off, but ordinary NEW grants are blocked
    # unless it is on (see role_assignment.py).
    if runtime_enforcement_enabled():
        verified = verified_ordinary_roles_for(account_id)
        blocked = ORDINARY_ROLE_NAMES.difference(verified)
        if blocked:
            role_grants = role_grants.exclude(role__role_name__in=blocked)
        # An account-specific Grant must not be a backdoor around an invalid
        # Treasurer/Advisor appointment. Any code bound to an ordinary role is
        # guarded. A distinct, independently granted non-ordinary role can still
        # confer a shared code through role_grants, with Deny precedence intact.
        ordinary_bound_code = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
            permission_id=OuterRef("pk"), role__role_name__in=ORDINARY_ROLE_NAMES,
        )
        grant_source = (Q(Exists(role_grants)) |
                        (Q(Exists(overrides.filter(effect="Grant"))) &
                         ~Q(Exists(ordinary_bound_code))))
    else:
        grant_source = Q(Exists(overrides.filter(effect="Grant"))) | Q(Exists(role_grants))

    # WF-03.03: new direct Grants are explicitly bound to ONE persisted role
    # context in a separate, opt-in table. Without a completed migration and
    # activation this code performs no new queries, preserving D-117 behavior.
    scoped_grants_enabled = (
        getattr(settings, "WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED", False) is True
    )
    if selected_ids is not None:
        if scoped_grants_enabled:
            chosen = selected_scope()
            scoped_rows = AccountPermissionRoleScope.objects.using(DEFAULT_DB_ALIAS).filter(
                account_permission_id=OuterRef("pk"), role_id=chosen.role_id,
            )
            scoped_source = overrides.filter(effect="Grant").filter(Exists(scoped_rows))
            # A scoped grant cannot bypass an unverified ordinary appointment
            # or an ordinary-role-bound permission guard.
            chosen_ordinary = Role.objects.using(DEFAULT_DB_ALIAS).filter(
                pk=chosen.role_id, role_name__in=ORDINARY_ROLE_NAMES,
            ).exists()
            if chosen_ordinary and not runtime_enforcement_enabled():
                scoped_source = scoped_source.none()
            if runtime_enforcement_enabled():
                bound_ordinary = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
                    permission_id=OuterRef("pk"), role__role_name__in=ORDINARY_ROLE_NAMES,
                )
                grant_source = Q(Exists(role_grants)) | (
                    Q(Exists(scoped_source)) & ~Q(Exists(bound_ordinary))
                )
            else:
                grant_source = Q(Exists(role_grants)) | Q(Exists(scoped_source))
        else:
            grant_source = Q(Exists(role_grants))
    elif scoped_grants_enabled:
        # Legacy unscoped grants retain legacy semantics in non-context mode;
        # new role-scoped grants must NEVER leak into the union evaluator.
        scoped_any = AccountPermissionRoleScope.objects.using(DEFAULT_DB_ALIAS).filter(
            account_permission_id=OuterRef("pk"),
        )
        legacy_unscoped = overrides.filter(effect="Grant").filter(~Exists(scoped_any))
        grant_source = Q(Exists(role_grants)) | Q(Exists(legacy_unscoped))

    permissions = (
        Permission.objects.using(DEFAULT_DB_ALIAS)
        .filter(service__is_active=True)
        .filter(Exists(eligible_assignments))
        .filter(~Exists(overrides.filter(effect="Deny")))
        .filter(grant_source)
    )
    return preserve_transition_denies(permissions, account_id)


def _effective_codes(account, permission_code=None):
    try:
        if (
            not isinstance(account, Account)
            or account._state.adding
            or account._state.db != DEFAULT_DB_ALIAS
            or type(account.pk) is not int
            or account.pk <= 0
        ):
            return frozenset()

        permissions = _authorized_permissions(account.pk)
        if permission_code is not None:
            permissions = permissions.filter(permission_code=permission_code)
        # Materialize completely before returning: even a mid-read failure
        # discards all potential grants. Empty/blank catalogue codes authorize
        # nothing. Never trust a cached QuerySet or cached account attributes.
        return frozenset(
            code for code in permissions.values_list("permission_code", flat=True)
            if code and code.strip()
        )
    except Exception as exc:
        # No SQL, identifiers, permission codes, request bodies, or traceback.
        logger.error("Permission evaluation failed (%s).", type(exc).__name__)
        return frozenset()


def has_permission(account, permission_code):
    """Return whether an eligible account has this exact stored permission code.

    Codes are case-sensitive Python strings, even when MySQL's lookup collation
    is case/accent insensitive. No trimming, aliases, wildcards, or name bypasses.
    """
    if type(permission_code) is not str or not permission_code.strip() or len(permission_code) > 150:
        return False
    return permission_code in _effective_codes(account, permission_code)


def get_effective_permissions(account):
    """Return a fresh immutable set of effective codes, or an empty set on failure.

    A returned set is a point-in-time result. Reevaluate at protected action
    boundaries; do not persist it in sessions or cache it across requests.
    """
    return _effective_codes(account)
