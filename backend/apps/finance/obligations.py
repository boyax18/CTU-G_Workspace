"""WF-07.02 minimum: the full semester organizational-fee obligation created at onboarding finalization.

``create_fee_obligation`` is called ONLY from the atomic finalization in apps.academic.onboarding (or
the evidenced WF11-D14 correction), after the caller has locked the shared services, the semester and
the semester's fee schedule. It re-reads the CURRENT approved revision from the locked schedule,
re-validates it (apps.finance.fees._validated_current) and snapshots its amount. The amount is never
taken from the client and a later revision never changes an existing obligation.

No payment, receipt, balance settlement or paid status is created: payment is the separate Treasurer
cash workflow (later WF-07 slices). Count helpers are the WF-11.01 dependency adapters.
"""

from django.db import DEFAULT_DB_ALIAS, transaction

from .fees import _finance_service_active, _validated_current, configuration_enabled
from .models import FeeObligation, ObligationStatus, SemesterFeeSchedule

DB = DEFAULT_DB_ALIAS


class ObligationRefused(Exception):
    REASONS = frozenset({"fee_unavailable", "obligation_exists", "transaction_required", "fee_changed"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "fee_unavailable"
        super().__init__("The organizational fee obligation could not be created.")


def locked_approved_revision(semester):
    """Lock the semester's schedule and return its validated current approved revision (or None).

    None as well when the fee source itself is unavailable (configuration switch off or finance
    service inactive): an obligation is never assessed from a source the Workspace has switched off.
    """
    if not configuration_enabled() or not _finance_service_active():
        return None
    schedule = (SemesterFeeSchedule.objects.using(DB).select_for_update()
                .select_related("current_approved_revision").filter(semester_id=semester.pk).first())
    if schedule is None:
        return None
    return _validated_current(schedule)


def create_fee_obligation(participation, revision):
    """Snapshot ``revision`` (already validated under the schedule lock) for this participation."""
    if not transaction.get_connection(DB).in_atomic_block:
        raise ObligationRefused("transaction_required")
    if revision is None:
        raise ObligationRefused("fee_unavailable")
    if revision.schedule.semester_id != participation.semester_id:
        raise ObligationRefused("fee_changed")
    if FeeObligation.objects.using(DB).filter(student_id=participation.student_id,
                                               semester_id=participation.semester_id).exists():
        raise ObligationRefused("obligation_exists")
    return FeeObligation.objects.using(DB).create(
        participation=participation, student_id=participation.student_id, semester_id=participation.semester_id,
        fee_revision=revision, currency=revision.currency, amount=revision.amount, status=ObligationStatus.UNPAID)


def obligation_summary(obligation):
    if obligation is None:
        return None
    return {"obligation_id": obligation.pk, "amount": f"{obligation.amount:.2f}", "currency": obligation.currency,
            "status": obligation.status}


# ---- WF-11.01 dependency adapters (read-only counts for one semester) -------------------------

def unpaid_obligation_count(semester):
    return FeeObligation.objects.using(DB).filter(semester_id=semester.pk, status=ObligationStatus.UNPAID).count()


def obligation_count(semester):
    return FeeObligation.objects.using(DB).filter(semester_id=semester.pk).count()
