"""Protected profile eligibility plus fresh hybrid permission evaluation.

This read-only predicate grants nothing and is not a transaction boundary.
Writers must serialize and recheck all contributing authorization state.
"""

from django.db import DEFAULT_DB_ALIAS

from apps.accounts.models import Account
from .models import AccountRole
from .services import has_permission


ADMIN_ROLE = "Admin"  # School Admin's existing persisted name.
TECHNICAL_ROLE = "Technical Super Admin"


def has_technical_authority(account, permission_code):
    """Require both administrative responsibilities AND an explicit permission.

    Framework flags, requested roles, a role title, and a direct Grant on an
    ordinary School Admin never substitute for the protected composite profile.
    Database errors and noncanonical permission names deny access.
    """
    if (not isinstance(account, Account) or account._state.adding
            or account._state.db != DEFAULT_DB_ALIAS or type(account.pk) is not int
            or account.pk <= 0 or type(permission_code) is not str
            or not permission_code.startswith("access_control.")):
        return False
    try:
        roles = set(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=account.pk, account__is_active=True,
            account__request_status="Approved", role__is_active=True,
            role__role_name__in=(ADMIN_ROLE, TECHNICAL_ROLE),
        ).values_list("role__role_name", flat=True))
        return roles == {ADMIN_ROLE, TECHNICAL_ROLE} and has_permission(account, permission_code)
    except Exception:
        return False
