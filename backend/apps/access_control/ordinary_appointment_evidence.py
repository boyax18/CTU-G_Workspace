"""WF-03.01 D-110: server-side reviewed-appointment verifier (default deny).

A submitted fingerprint has no privilege. Positive verification additionally needs
an enabled, separately authorized evidence source, a current Verified record,
three distinct humans across submit/review/assign, and a live assignment lock.
The policy for the campus appointment-verifier permission is not yet adopted;
no setting module enables this source. Older D-100 tests may patch this adapter
in isolated test settings, never in a deployed server.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.db.models import F
from django.utils import timezone

from .models import OrdinaryAppointment

ROLE_NAMES = frozenset(("Treasurer", "SSG Advisor"))
EVIDENCE_GATE = "WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED"


def appointment_verified_for(*, target_account_id: int, role_name: str,
                             assigning_account_id=None, for_grant=False) -> bool:
    if getattr(settings, EVIDENCE_GATE, False) is not True:
        return False
    if (type(target_account_id) is not int or target_account_id <= 0
            or type(role_name) is not str or role_name not in ROLE_NAMES):
        return False
    if for_grant and (type(assigning_account_id) is not int or assigning_account_id <= 0
                      or not connections[DEFAULT_DB_ALIAS].in_atomic_block):
        return False
    try:
        now = timezone.now()
        qs = OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=target_account_id, role_name=role_name, status="Verified",
            reviewed_by__isnull=False, valid_from__lte=now, valid_until__gt=now,
            submission_receipt__action="account.appointment.submit",
            submission_receipt__actor_account_id=F("submitted_by_id"),
            submission_receipt__target_account_id=F("account_id"),
            review_receipt__action="account.appointment.verify",
            review_receipt__actor_account_id=F("reviewed_by_id"),
            review_receipt__target_account_id=F("account_id"),
            review_receipt__role__role_name=F("role_name"),
        ).exclude(submitted_by_id=F("reviewed_by_id"))
        if assigning_account_id is not None:
            qs = qs.exclude(submitted_by_id=assigning_account_id).exclude(
                reviewed_by_id=assigning_account_id)
        if for_grant:
            qs = qs.select_for_update()
        # A duplicate verified record is a policy/data-integrity anomaly, not
        # another way to bypass the independent approval ceremony.
        return len(list(qs.order_by("appointment_id")[:2])) == 1
    except DatabaseError:
        # A missing migration or storage outage must never unlock grants.
        return False
