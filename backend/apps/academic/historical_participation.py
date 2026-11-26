"""WF11-D14: evidenced historical Student participation correction (late entry for a past semester).

For a Student who was officially enrolled in a Closed or Archived semester but has no Workspace
participation there. School Admin only (Admin path of services.authorize) with BOTH
``academic.periods.manage`` (WF-11.01 authority) and the proposed ``academic.profiles.manage``
(verification records), behind WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED (default off,
refused in production) on top of the base gate.

Required, re-checked under the shared locks (services -> permissions -> account -> semester -> fee
schedule -> evidence):
* the semester is Closed or Archived (it stays so: nothing is reopened or reactivated);
* a Verified evidence record for the Student and semester exists and is the one reviewed;
* no participation and no Verified non-enrollment gap for that Student and semester;
* the chosen offerings cover exactly the evidence subjects, are valid for that semester, belong to
  the evidence course, and each has its real eligible assigned instructor (never a substitute);
* the semester's ORIGINAL approved fee (its current approved revision, frozen once Closed) validates.
  Without it the correction is refused (``historical_fee_unavailable``): no amount is invented.

One transaction creates the participation (source ``historical_correction``), its subjects, one
Uncleared clearance with Pending requirements and one Unpaid obligation snapshot, with audit rows.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction

from . import services
from .models import (
    EnrollmentGapException, ParticipationSource, ParticipationSubject, Semester, SemesterParticipation, SemesterStatus,
    StudentType, VerificationStatus,
)
from .student_access import genuine_student, lock_shared_services

DB = DEFAULT_DB_ALIAS
SETTING = "WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED"
PERIOD_CODE = "academic.periods.manage"
PROFILE_CODE = "academic.profiles.manage"
ACTION = "academic.participation.historical_correction"
NOTE_MIN, NOTE_MAX = 10, 500


class HistoricalCorrectionRefused(Exception):
    REASONS = frozenset({"period_not_historical", "evidence_required", "evidence_changed", "participation_exists",
                         "gap_conflict", "subjects_mismatch", "instructor_unassigned", "historical_fee_unavailable",
                         "confirmation_required", "correction_conflict", "self_verification"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "correction_conflict"
        super().__init__("The historical participation could not be recorded.")


def correction_enabled():
    return services.gate_open() and getattr(settings, SETTING, False) is True


def _authorize(actor):
    services.authorize(actor, PROFILE_CODE, gate=correction_enabled)
    return services.authorize(actor, PERIOD_CODE, gate=correction_enabled)


def _invalid(field):
    raise services.AcademicPeriodInvalid({field: "invalid"})


def _id(raw, field):
    if type(raw) is not int or not 1 <= raw <= services.MAX_ID:
        _invalid(field)
    return raw


def _note(raw):
    if type(raw) is not str:
        _invalid("reason_note")
    text = " ".join(raw.split())
    if not NOTE_MIN <= len(text) <= NOTE_MAX:
        _invalid("reason_note")
    return text


def preview(*, actor, student_account_id, semester_id):
    """What the correction would create (read-only): evidence, candidate offerings, original fee."""
    from apps.finance.fees import _validated_current
    from apps.finance.models import SemesterFeeSchedule
    from .onboarding import _offering_option, _valid, semester_ref
    from .verification import current_evidence, evidence_payload
    _authorize(actor)
    student = genuine_student(_id(student_account_id, "student_account_id"))
    semester = Semester.objects.using(DB).select_related("school_year").filter(pk=_id(semester_id, "semester_id")).first()
    if student is None or semester is None:
        raise services.AcademicPeriodNotFound()
    evidence = current_evidence(student.pk, semester.pk)
    schedule = (SemesterFeeSchedule.objects.using(DB).select_related("current_approved_revision")
                .filter(semester_id=semester.pk).first())
    revision = _validated_current(schedule) if schedule else None
    blockers = []
    if semester.status not in (SemesterStatus.CLOSED, SemesterStatus.ARCHIVED):
        blockers.append("period_not_historical")
    if evidence is None:
        blockers.append("evidence_required")
    if SemesterParticipation.objects.using(DB).filter(student=student, semester=semester).exists():
        blockers.append("participation_exists")
    if EnrollmentGapException.objects.using(DB).filter(student=student, semester=semester,
                                                       status=VerificationStatus.VERIFIED).exists():
        blockers.append("gap_conflict")
    if revision is None:
        blockers.append("historical_fee_unavailable")
    if not correction_enabled():
        blockers.append("feature_disabled")
    options = []
    if evidence is not None:
        subject_ids = list(evidence.subjects.using(DB).values_list("subject_id", flat=True))
        options = [_offering_option(o) for o in _valid(semester).filter(
            subject_id__in=subject_ids, section__course_id=evidence.course_id).order_by("subject__code", "section__name")]
    return {"semester": semester_ref(semester), "evidence": evidence_payload(evidence), "options": options,
            "fee": {"revision_id": revision.pk, "amount": f"{revision.amount:.2f}"} if revision else None,
            "blockers": blockers, "can_confirm": not blockers}


def correct(*, actor, student_account_id, semester_id, expected_evidence_id, student_type, offering_ids,
            reason_note, confirmed):
    from apps.clearance.services import ClearanceCreationRefused, create_semester_clearance
    from apps.finance.fees import _audit as finance_audit
    from apps.finance.obligations import ObligationRefused, create_fee_obligation, locked_approved_revision
    from .onboarding import _instructor, _valid
    from .verification import current_evidence
    if not correction_enabled():
        raise services.AcademicPeriodUnavailable("Historical participation correction is not enabled.")
    if confirmed is not True:
        raise HistoricalCorrectionRefused("confirmation_required")
    student_id, semester_id = _id(student_account_id, "student_account_id"), _id(semester_id, "semester_id")
    expected_evidence_id = _id(expected_evidence_id, "expected_evidence_id")
    if type(student_type) is not str or student_type not in StudentType.values:
        _invalid("student_type")
    if (type(offering_ids) is not list or not 1 <= len(offering_ids) <= 20 or len(set(offering_ids)) != len(offering_ids)
            or any(type(i) is not int or i <= 0 for i in offering_ids)):
        _invalid("offering_ids")
    note = _note(reason_note)
    _authorize(actor)
    try:
        with transaction.atomic(using=DB, durable=True):
            lock_shared_services()  # the same service order as onboarding finalization
            services.lock_and_authorize(actor, PROFILE_CODE, gate=correction_enabled)
            auth = services.lock_and_authorize(actor, PERIOD_CODE, gate=correction_enabled)
            semester = Semester.objects.using(DB).select_for_update().filter(pk=semester_id).first()
            student = genuine_student(student_id)
            if semester is None or student is None:
                raise services.AcademicPeriodNotFound()
            if student.pk == auth.account.pk:
                raise HistoricalCorrectionRefused("self_verification")
            if semester.status not in (SemesterStatus.CLOSED, SemesterStatus.ARCHIVED):
                raise HistoricalCorrectionRefused("period_not_historical")
            revision = locked_approved_revision(semester)
            evidence = current_evidence(student.pk, semester.pk, lock=True)
            if evidence is None:
                raise HistoricalCorrectionRefused("evidence_required")
            if evidence.pk != expected_evidence_id:
                raise HistoricalCorrectionRefused("evidence_changed")
            if SemesterParticipation.objects.using(DB).filter(student=student, semester=semester).exists():
                raise HistoricalCorrectionRefused("participation_exists")
            if EnrollmentGapException.objects.using(DB).filter(student=student, semester=semester,
                                                               status=VerificationStatus.VERIFIED).exists():
                raise HistoricalCorrectionRefused("gap_conflict")
            offerings = list(_valid(semester).filter(pk__in=offering_ids, section__course_id=evidence.course_id))
            verified = set(evidence.subjects.using(DB).values_list("subject_id", flat=True))
            if (len(offerings) != len(offering_ids) or len({o.subject_id for o in offerings}) != len(offerings)
                    or {o.subject_id for o in offerings} != verified):
                raise HistoricalCorrectionRefused("subjects_mismatch")
            instructors = {o.pk: _instructor(o) for o in offerings}
            if any(i is None for i in instructors.values()):
                raise HistoricalCorrectionRefused("instructor_unassigned")
            if revision is None:
                raise HistoricalCorrectionRefused("historical_fee_unavailable")
            participation = SemesterParticipation.objects.using(DB).create(
                student=student, semester=semester, onboarding=None, evidence=evidence,
                source=ParticipationSource.HISTORICAL_CORRECTION, student_type=student_type,
                course_id=evidence.course_id, year_level=evidence.year_level, created_by=auth.account)
            rows = [ParticipationSubject.objects.using(DB).create(participation=participation, subject_id=o.subject_id,
                                                                  offering=o, instructor=instructors[o.pk])
                    for o in offerings]
            try:
                clearance = create_semester_clearance(participation, rows)
                obligation = create_fee_obligation(participation, revision)
            except (ClearanceCreationRefused, ObligationRefused) as exc:
                raise HistoricalCorrectionRefused("instructor_unassigned" if exc.reason == "instructor_unassigned"
                                                  else "correction_conflict") from exc
            services.write_audit(auth, action=ACTION, school_year_id=semester.school_year_id, semester_id=semester.pk,
                                 new_value={"participation_id": participation.pk, "student_account_id": student.pk,
                                            "evidence_id": evidence.pk, "student_type": student_type,
                                            "subject_ids": sorted(verified), "clearance_id": clearance.pk,
                                            "obligation_id": obligation.pk, "fee_revision_id": revision.pk,
                                            "semester_status": semester.status},
                                 reason="historical_participation", reason_note=note)
            finance_audit(auth, "finance.fee_obligation.create", "fee_obligation", obligation.pk, semester.pk,
                          new={"participation_id": participation.pk, "fee_revision_id": revision.pk,
                               "amount": f"{obligation.amount:.2f}", "currency": obligation.currency,
                               "status": obligation.status, "historical": True},
                          reason="historical_participation")
            participation_id = participation.pk
    except IntegrityError as exc:
        raise HistoricalCorrectionRefused("correction_conflict") from exc
    from .verification import student_record, verification_enabled
    body = {"participation_id": participation_id, "created": True}
    if verification_enabled():
        body["record"] = student_record(actor=actor, student_account_id=student_id)
    return body
