"""WF-06.01 minimum: create the period clearance inside onboarding finalization (never on its own).

``create_semester_clearance`` is called ONLY from the atomic finalization in apps.academic.onboarding
or the evidenced WF11-D14 correction in apps.academic.historical_participation, after the caller has
taken the shared locks and created the participation. It writes, in the caller's transaction:

* one ``SemesterClearance`` (Uncleared) for the participation;
* one Pending ``subject_instructor`` requirement per confirmed subject, bound to the instructor of that
  subject's REAL current teaching assignment (re-validated here; an unassigned or ineligible instructor
  refuses the whole finalization - nobody is substituted);
* one Pending ``treasurer_fee`` and one Pending ``school_admin_final`` requirement (WF-06.02 step 4).
  They are role requirements: no Treasurer or School Admin person is invented as their signatory.

Nothing here signs, approves or clears. There is no public route and no write outside the caller's
transaction. Read helpers below are count-only adapters for the WF-11.01 dependency contract.
"""

from django.db import DEFAULT_DB_ALIAS, transaction

from .models import ClearanceRequirement, ClearanceStatus, RequirementKind, RequirementStatus, SemesterClearance

DB = DEFAULT_DB_ALIAS
ROLE_REQUIREMENTS = (RequirementKind.TREASURER_FEE, RequirementKind.SCHOOL_ADMIN_FINAL)


class ClearanceCreationRefused(Exception):
    REASONS = frozenset({"instructor_unassigned", "subject_mismatch", "no_subjects", "clearance_exists",
                         "transaction_required"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "subject_mismatch"
        super().__init__("The semester clearance could not be created.")


def create_semester_clearance(participation, subject_rows):
    """``subject_rows``: the participation's ParticipationSubject rows (subject, offering, instructor)."""
    from apps.academic.teaching import current_assignment, instructor_eligible
    if not transaction.get_connection(DB).in_atomic_block:
        raise ClearanceCreationRefused("transaction_required")
    if not subject_rows:
        raise ClearanceCreationRefused("no_subjects")
    if SemesterClearance.objects.using(DB).filter(student_id=participation.student_id,
                                                   semester_id=participation.semester_id).exists():
        raise ClearanceCreationRefused("clearance_exists")
    for row in subject_rows:
        if row.participation_id != participation.pk or row.offering.subject_id != row.subject_id:
            raise ClearanceCreationRefused("subject_mismatch")
        assignment = current_assignment(row.offering)
        if (assignment is None or assignment.instructor_id != row.instructor_id
                or not instructor_eligible(row.instructor_id)):
            raise ClearanceCreationRefused("instructor_unassigned")
    clearance = SemesterClearance.objects.using(DB).create(
        participation=participation, student_id=participation.student_id, semester_id=participation.semester_id,
        status=ClearanceStatus.UNCLEARED)
    requirements = [ClearanceRequirement(clearance=clearance, requirement_key=f"subject:{row.subject_id}",
                                         kind=RequirementKind.SUBJECT_INSTRUCTOR, subject_id=row.subject_id,
                                         offering_id=row.offering_id, signatory_id=row.instructor_id,
                                         status=RequirementStatus.PENDING)
                    for row in sorted(subject_rows, key=lambda r: r.subject_id)]
    requirements += [ClearanceRequirement(clearance=clearance, requirement_key=kind.value, kind=kind,
                                          status=RequirementStatus.PENDING) for kind in ROLE_REQUIREMENTS]
    for requirement in requirements:
        requirement.save(using=DB)  # one INSERT each: a constraint failure aborts the whole transaction
    return clearance


def clearance_summary(clearance):
    """Own-record presentation: requirement kinds and Pending/Signed state, never other Students' data."""
    if clearance is None:
        return None
    rows = list(ClearanceRequirement.objects.using(DB).select_related("subject", "signatory__profile")
                .filter(clearance=clearance).order_by("kind", "requirement_key"))
    from apps.academic.teaching import _full_name
    return {"clearance_id": clearance.pk, "status": clearance.status,
            "requirements": [{"kind": r.kind, "status": r.status,
                              "subject": {"subject_id": r.subject_id, "code": r.subject.code, "title": r.subject.title}
                              if r.subject_id else None,
                              "signatory": _full_name(r.signatory) if r.signatory_id else None}
                             for r in rows],
            "pending_count": sum(1 for r in rows if r.status == RequirementStatus.PENDING)}


# ---- WF-11.01 dependency adapters (read-only counts for one semester) -------------------------

def pending_requirement_count(semester):
    return ClearanceRequirement.objects.using(DB).filter(clearance__semester_id=semester.pk,
                                                         status=RequirementStatus.PENDING).count()


def clearance_count(semester):
    return SemesterClearance.objects.using(DB).filter(semester_id=semester.pk).count()
