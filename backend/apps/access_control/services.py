"""Read-only, fail-closed Hybrid Dynamic Access Control evaluation.

Only persisted accounts from the primary/default database are accepted. Every
call rechecks database state in one SELECT; caller attributes, related-object
caches, requested roles, role names, and Django auth flags confer no authority.
"""

import logging

from django.db import DEFAULT_DB_ALIAS
from django.db.models import Exists, OuterRef, Q

from apps.accounts.models import Account

from .models import AccountPermission, AccountRole, Permission, RolePermission

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
    overrides = AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(
        account_id=account_id, permission_id=OuterRef("pk"), is_active=True,
    )
    role_grants = RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
        permission_id=OuterRef("pk"),
        is_active=True,
        role__is_active=True,
        role__account_assignments__account_id=account_id,
    )
    return (
        Permission.objects.using(DEFAULT_DB_ALIAS)
        .filter(service__is_active=True)
        .filter(Exists(eligible_assignments))
        .filter(~Exists(overrides.filter(effect="Deny")))
        .filter(Q(Exists(overrides.filter(effect="Grant"))) | Q(Exists(role_grants)))
    )


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
