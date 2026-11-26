"""v2.3 Deny-only transition guard. Old Grants never authorize replacement codes."""
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Exists, Q

from .models import AccountPermission

DENY_PREDECESSORS = {
    "academic.enrollment_verifications.record": ("academic.profiles.manage",),
    "academic.semester_onboarding.self.submit": ("clearance.requests.self.submit",),
    "academic.historical_participation.correct": ("academic.periods.manage", "academic.profiles.manage"),
}


def preserve_transition_denies(permissions, account_id):
    """Narrow the normal resolver, including its session hints and locked re-evaluations.

    Account Denies are global restrictions. Role scopes and old-service activation cannot
    exempt them. Database errors propagate to the resolver's existing fail-closed boundary.
    """
    for replacement, predecessors in DENY_PREDECESSORS.items():
        denied = AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=account_id, is_active=True, effect="Deny",
            permission__permission_code__in=predecessors,
        )
        permissions = permissions.exclude(Q(permission_code=replacement) & Q(Exists(denied)))
    return permissions
