"""WF-03.01 D-111: per-request ordinary-role appointment gate (STAGED).

This is not a separate role grant. It validates persisted assignment provenance
against independently reviewed appointment receipts at the permission boundary.
If storage, evidence or reviewer provenance is unavailable, ordinary-role
privileges are excluded while unrelated base-role privileges remain usable.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError

from .models import AccountRole
from .ordinary_appointment_evidence import appointment_verified_for

ORDINARY_ROLE_NAMES = frozenset(("Treasurer", "SSG Advisor"))
RUNTIME_GATE_SETTING = "WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED"


def runtime_enforcement_enabled():
    return getattr(settings, RUNTIME_GATE_SETTING, False) is True


def verified_ordinary_roles_for(account_id):
    """Current authorized ordinary assignments, never from a request or cache.

    A previously assigned role without a known independent assigner is unsafe.
    The verified document must also be independent of the stored assigner.
    Errors deliberately discard the entire ordinary-role set.
    """
    if type(account_id) is not int or account_id <= 0:
        return frozenset()
    try:
        assignments = tuple(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=account_id, account__is_active=True,
            account__request_status="Approved", role__is_active=True,
            role__role_name__in=ORDINARY_ROLE_NAMES,
        ).values_list("role__role_name", "assigned_by_id"))
        verified = set()
        for role_name, assigner_id in assignments:
            if (type(assigner_id) is int and assigner_id > 0
                    and appointment_verified_for(
                        target_account_id=account_id, role_name=role_name,
                        assigning_account_id=assigner_id,
                    ) is True):
                verified.add(role_name)
        return frozenset(verified)
    except DatabaseError:
        # Migration not applied, unavailable primary database or corrupt ledger:
        # no ordinary-role access, rather than treating the grant as valid.
        return frozenset()
