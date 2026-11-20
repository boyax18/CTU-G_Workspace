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
# Keep the ordinary-role runtime in lockstep with D-100 grant eligibility.
# This is a constraint, never a new role grant or role-name permission bypass.
ORDINARY_BASE_ROLES = {"Treasurer": "Student", "SSG Advisor": "Instructor"}
ORDINARY_CONFLICT_ROLES = frozenset((
    "Student", "Instructor", "Treasurer", "SSG Advisor", "Admin", "Technical Super Admin",
))
RUNTIME_GATE_SETTING = "WORKSPACE_ORDINARY_APPOINTMENT_RUNTIME_ENFORCEMENT_ENABLED"


def runtime_enforcement_enabled():
    return getattr(settings, RUNTIME_GATE_SETTING, False) is True


def verified_ordinary_roles_for(account_id):
    """Recheck each ordinary appointment AND role eligibility on every evaluation.

    A verified document alone is insufficient: the account must still hold its
    current active Student/Instructor base role and no conflicting protected or
    ordinary assignment, even if the conflicting role has since been disabled.
    The persisted assignment is not deleted by this read-only guard. Any
    database/evidence failure denies *all ordinary* roles, leaving other base
    permissions to the ordinary effective-permission evaluator.
    """
    if type(account_id) is not int or account_id <= 0:
        return frozenset()
    try:
        # Include disabled role assignments solely to detect dormant conflicts.
        # Only active assignments are eligible to supply the required base role.
        assignments = tuple(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=account_id, account__is_active=True,
            account__request_status="Approved", account__is_staff=False,
            account__is_superuser=False,
        ).values_list("role__role_name", "role__is_active", "assigned_by_id"))
        assigned_names = {name for name, _, _ in assignments}
        active_names = {name for name, active, _ in assignments if active is True}
        verified = set()
        for role_name, active, assigner_id in assignments:
            if role_name not in ORDINARY_ROLE_NAMES or active is not True:
                continue
            base_role = ORDINARY_BASE_ROLES[role_name]
            if base_role not in active_names:
                continue
            forbidden = ORDINARY_CONFLICT_ROLES - {base_role, role_name}
            if assigned_names.intersection(forbidden):
                continue
            if (type(assigner_id) is int and assigner_id > 0
                    and appointment_verified_for(
                        target_account_id=account_id, role_name=role_name,
                        assigning_account_id=assigner_id,
                    ) is True):
                verified.add(role_name)
        return frozenset(verified)
    except DatabaseError:
        # Missing appointment migration, unavailable DB or corrupted ledger:
        # deny ordinary privileges; never fall back to an unverified role.
        return frozenset()
