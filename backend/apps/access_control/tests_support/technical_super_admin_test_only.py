"""Test-only reference gate for the D1 dual-role profile contract.

NOT an application authorization service. No operational endpoint imports it.
A future production governance boundary must revalidate and lock the state
inside its own independently approved transaction and audit workflow.
"""

from django.db import DEFAULT_DB_ALIAS

from apps.accounts.models import Account
from apps.access_control.models import AccountRole
from apps.access_control.services import has_permission


REQUIRED_ROLES = frozenset({"Admin", "Technical Super Admin"})


def composed_profile_test_only(account):
    """Read-only fixture check: both active roles and approved active account."""
    if (
        not isinstance(account, Account)
        or account._state.adding
        or account._state.db != DEFAULT_DB_ALIAS
        or type(account.pk) is not int
        or account.pk <= 0
    ):
        return False
    try:
        names = set(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=account.pk,
            account__request_status="Approved",
            account__is_active=True,
            role__is_active=True,
        ).values_list("role__role_name", flat=True))
        # Exact Python string equality (independent of MySQL collation).
        return REQUIRED_ROLES.issubset(names)
    except Exception:
        return False


def simulated_governance_boundary_test_only(account, permission_code):
    """No real authority; verifies composition plus existing evaluator in tests."""
    return (
        type(permission_code) is str
        and permission_code.startswith("access_control.")
        and composed_profile_test_only(account)
        and has_permission(account, permission_code)
    )
