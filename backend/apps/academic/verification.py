"""Official CTU verification records (R-02; WF-05.04 minimum for onboarding; WF11-D15/16 gaps).

Lane 1 - previously verified evidence: an existing Verified ``EnrollmentEvidence`` for the Student and
semester. Source ``ctu_integration`` has NO runtime writer: no CTU API or accepted integration exists,
so only isolated tests create such rows. Lane 2 - in-person School Admin verification, recorded here.

School Admin operations: services.authorize with the exact ``academic.enrollment_verifications.record`` code behind WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED (default off). Every write locks the shared
order (services -> permission -> account -> semester -> evidence) and commits with an audit row.

Privacy: only a controlled reference (e.g. a document control number, at most 80 characters) is
stored; never a scan, file or document contents, and the reference itself is not written to audit.
School Admin records evidence only; the Student still confirms onboarding personally afterwards.
"""

import re
from datetime import date

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction

from apps.accounts.fields import CurrentTimestamp

from . import services
from .models import (
    Course, EnrollmentEvidence, EnrollmentEvidenceSubject, EnrollmentGapException, EntryClassification, EvidenceSource,
    MAX_YEAR_LEVEL, MIN_YEAR_LEVEL, Semester, SemesterOnboarding, SemesterParticipation, SemesterStatus, Subject,
    VerificationStatus,
)
from .student_access import genuine_student

DB = DEFAULT_DB_ALIAS
VERIFY_CODE = "academic.enrollment_verifications.record"
VERIFY_SETTING = "WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED"
REVOKE_REASONS = frozenset({"recorded_in_error", "superseded_by_ctu_record", "identity_mismatch"})
OPEN_PERIODS = (SemesterStatus.ACTIVE, SemesterStatus.CLOSED, SemesterStatus.ARCHIVED)
HISTORICAL = (SemesterStatus.CLOSED, SemesterStatus.ARCHIVED)
_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .\-/#]{2,79}", re.ASCII)


class VerificationConflict(Exception):
    REASONS = frozenset({"period_not_open", "period_not_historical", "evidence_changed", "participation_exists",
                         "evidence_in_use", "gap_conflict", "evidence_conflict", "not_found_student", "stale_version",
                         "already_revoked", "self_verification"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "evidence_changed"
        super().__init__("The verification record could not be changed.")


def verification_enabled():
    return getattr(settings, VERIFY_SETTING, False) is True


def authorize_verifier(actor):
    return services.authorize(actor, VERIFY_CODE, gate=verification_enabled)


def _invalid(field, code="invalid"):
    raise services.AcademicPeriodInvalid({field: code})


def _reference(raw):
    if type(raw) is not str or not _REFERENCE.fullmatch(" ".join(raw.split())):
        _invalid("source_reference")
    return " ".join(raw.split())


def _id(raw, field):
    if type(raw) is not int or not 1 <= raw <= services.MAX_ID:
        _invalid(field)
    return raw


def _as_of(raw):
    if raw is None:
        return None
    if type(raw) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        _invalid("source_as_of")
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        _invalid("source_as_of")
    if value > date.today():
        _invalid("source_as_of")
    return value


def evidence_payload(evidence):
    if evidence is None:
        return None
    return {"evidence_id": evidence.pk, "semester_id": evidence.semester_id, "source_type": evidence.source_type,
            "entry_classification": evidence.entry_classification,
            "course": {"course_id": evidence.course_id, "code": evidence.course.code},
            "year_level": evidence.year_level, "status": evidence.status, "version": evidence.version,
            "subjects": [{"subject_id": s.subject_id, "code": s.subject.code, "title": s.subject.title}
                         for s in evidence.subjects.select_related("subject").order_by("subject__code")],
            "verified_by": "A School Admin" if evidence.verified_by_id else "CTU integration",
            "verified_at": evidence.verified_at.isoformat() if hasattr(evidence.verified_at, "isoformat") else None}


def current_evidence(student_id, semester_id, lock=False):
    qs = EnrollmentEvidence.objects.using(DB).select_related("course").filter(
        student_id=student_id, semester_id=semester_id, status=VerificationStatus.VERIFIED)
    return (qs.select_for_update() if lock else qs).first()


def _audit(auth, action, semester, new=None, old=None, reason="official_verification"):
    services.write_audit(auth, action=action, school_year_id=semester.school_year_id, semester_id=semester.pk,
                         old_value=old, new_value=new, reason=reason)


def _write(actor, fn):
    if not services.gate_open():
        raise services.AcademicPeriodUnavailable("Academic-period management is not activated.")
    if not verification_enabled():
        raise services.AcademicPeriodFeatureDisabled("Official verification recording is not enabled.")
    authorize_verifier(actor)
    try:
        with transaction.atomic(using=DB, durable=True):
            auth = services.lock_and_authorize(actor, VERIFY_CODE, gate=verification_enabled)
            return fn(auth)
    except IntegrityError as exc:
        raise VerificationConflict("evidence_changed") from exc


def record_evidence(*, actor, student_account_id, semester_id, entry_classification, course_id, year_level, subject_ids,
                    source_reference, source_as_of=None, expected_evidence_id=None):
    """Record (or supersede) the in-person verified CTU enrollment evidence for a Student and semester."""
    student_id, semester_id, course_id = (_id(student_account_id, "student_account_id"), _id(semester_id, "semester_id"),
                                          _id(course_id, "course_id"))
    if type(entry_classification) is not str or entry_classification not in EntryClassification.values:
        _invalid("entry_classification")
    if type(year_level) is not int or not MIN_YEAR_LEVEL <= year_level <= MAX_YEAR_LEVEL:
        _invalid("year_level")
    if (type(subject_ids) is not list or not 1 <= len(subject_ids) <= 20 or len(set(subject_ids)) != len(subject_ids)
            or any(type(s) is not int or s <= 0 for s in subject_ids)):
        _invalid("subject_ids")
    reference, as_of = _reference(source_reference), _as_of(source_as_of)
    if expected_evidence_id is not None:
        _id(expected_evidence_id, "expected_evidence_id")

    def apply(auth):
        semester = Semester.objects.using(DB).select_for_update().filter(pk=semester_id).first()
        student = genuine_student(student_id)
        if semester is None or student is None:
            raise services.AcademicPeriodNotFound()
        if student.pk == auth.account.pk:
            raise VerificationConflict("self_verification")  # no one verifies their own enrollment
        if semester.status not in OPEN_PERIODS:
            raise VerificationConflict("period_not_open")  # Draft semesters have no enrollment yet
        if SemesterParticipation.objects.using(DB).filter(student=student, semester=semester).exists():
            raise VerificationConflict("participation_exists")  # the finalized basis is never rewritten
        if EnrollmentGapException.objects.using(DB).filter(student=student, semester=semester,
                                                           status=VerificationStatus.VERIFIED).exists():
            raise VerificationConflict("gap_conflict")  # enrolled and not enrolled cannot both be verified
        course = Course.objects.using(DB).filter(pk=course_id).first()
        subjects = list(Subject.objects.using(DB).filter(pk__in=subject_ids))
        if course is None or len(subjects) != len(subject_ids):
            raise services.AcademicPeriodNotFound()
        current = current_evidence(student.pk, semester.pk, lock=True)
        if (current.pk if current else None) != expected_evidence_id:
            raise VerificationConflict("evidence_changed")
        if current is not None:
            EnrollmentEvidence.objects.using(DB).filter(pk=current.pk, status=VerificationStatus.VERIFIED).update(
                status=VerificationStatus.REVOKED, active_slot=None, revoked_at=CurrentTimestamp(),
                revoked_by=auth.account, revoke_reason="superseded", version=current.version + 1)
        evidence = EnrollmentEvidence.objects.using(DB).create(
            student=student, semester=semester, source_type=EvidenceSource.IN_PERSON, source_reference=reference,
            source_as_of=as_of, entry_classification=entry_classification, course=course, year_level=year_level,
            active_slot=1, verified_by=auth.account)
        for subject in subjects:
            EnrollmentEvidenceSubject.objects.using(DB).create(evidence=evidence, subject=subject)
        _audit(auth, "academic.enrollment_evidence.record", semester,
               old={"evidence_id": current.pk} if current else None,
               new={"evidence_id": evidence.pk, "student_account_id": student.pk, "source_type": EvidenceSource.IN_PERSON,
                    "entry_classification": entry_classification, "course_id": course.pk, "year_level": year_level,
                    "subject_ids": sorted(subject_ids), "source_reference_recorded": True})
        return evidence.pk
    pk = _write(actor, apply)
    return evidence_payload(EnrollmentEvidence.objects.using(DB).select_related("course").get(pk=pk))


def revoke_evidence(*, actor, evidence_id, expected_version, reason_code):
    evidence_id, expected_version = _id(evidence_id, "evidence_id"), _id(expected_version, "expected_version")
    if type(reason_code) is not str or reason_code not in REVOKE_REASONS:
        _invalid("reason_code")

    def apply(auth):
        evidence = EnrollmentEvidence.objects.using(DB).select_for_update().filter(pk=evidence_id).first()
        if evidence is None:
            raise services.AcademicPeriodNotFound()
        semester = Semester.objects.using(DB).select_for_update().get(pk=evidence.semester_id)
        if evidence.student_id == auth.account.pk:
            raise VerificationConflict("self_verification")
        if evidence.status != VerificationStatus.VERIFIED:
            raise VerificationConflict("already_revoked")
        if evidence.version != expected_version:
            raise VerificationConflict("stale_version")
        if evidence.participations.using(DB).exists():
            raise VerificationConflict("evidence_in_use")
        EnrollmentEvidence.objects.using(DB).filter(pk=evidence.pk).update(
            status=VerificationStatus.REVOKED, active_slot=None, revoked_at=CurrentTimestamp(), revoked_by=auth.account,
            revoke_reason=reason_code, version=expected_version + 1)
        _audit(auth, "academic.enrollment_evidence.revoke", semester, old={"evidence_id": evidence.pk, "status": "Verified"},
               new={"evidence_id": evidence.pk, "status": "Revoked", "reason": reason_code})
        return evidence.pk
    return {"revoked": True, "evidence_id": _write(actor, apply)}


def gap_payload(gap):
    return {"gap_id": gap.pk, "semester_id": gap.semester_id, "status": gap.status, "version": gap.version,
            "verified_at": gap.verified_at.isoformat() if hasattr(gap.verified_at, "isoformat") else None}


def record_gap(*, actor, student_account_id, semester_id, source_reference):
    """Record a CTU-verified NON-enrollment of the Student in one past (Closed/Archived) semester."""
    student_id, semester_id = _id(student_account_id, "student_account_id"), _id(semester_id, "semester_id")
    reference = _reference(source_reference)

    def apply(auth):
        semester = Semester.objects.using(DB).select_for_update().filter(pk=semester_id).first()
        student = genuine_student(student_id)
        if semester is None or student is None:
            raise services.AcademicPeriodNotFound()
        if student.pk == auth.account.pk:
            raise VerificationConflict("self_verification")
        if semester.status not in HISTORICAL:
            raise VerificationConflict("period_not_historical")
        if SemesterParticipation.objects.using(DB).filter(student=student, semester=semester).exists():
            raise VerificationConflict("participation_exists")  # an enrolled period is never a gap
        if current_evidence(student.pk, semester.pk) is not None:
            raise VerificationConflict("evidence_conflict")
        gap = EnrollmentGapException.objects.using(DB).create(student=student, semester=semester, source_reference=reference,
                                                             active_slot=1, verified_by=auth.account)
        _audit(auth, "academic.enrollment_gap.record", semester,
               new={"gap_id": gap.pk, "student_account_id": student.pk, "source_reference_recorded": True},
               reason="verified_gap_exception")
        return gap.pk
    return gap_payload(EnrollmentGapException.objects.using(DB).get(pk=_write(actor, apply)))


def revoke_gap(*, actor, gap_id, expected_version):
    gap_id, expected_version = _id(gap_id, "gap_id"), _id(expected_version, "expected_version")

    def apply(auth):
        gap = EnrollmentGapException.objects.using(DB).select_for_update().filter(pk=gap_id).first()
        if gap is None:
            raise services.AcademicPeriodNotFound()
        semester = Semester.objects.using(DB).get(pk=gap.semester_id)
        if gap.student_id == auth.account.pk:
            raise VerificationConflict("self_verification")
        if gap.status != VerificationStatus.VERIFIED:
            raise VerificationConflict("already_revoked")
        if gap.version != expected_version:
            raise VerificationConflict("stale_version")
        EnrollmentGapException.objects.using(DB).filter(pk=gap.pk).update(
            status=VerificationStatus.REVOKED, active_slot=None, revoked_at=CurrentTimestamp(), revoked_by=auth.account,
            version=expected_version + 1)
        _audit(auth, "academic.enrollment_gap.revoke", semester, old={"gap_id": gap.pk, "status": "Verified"},
               new={"gap_id": gap.pk, "status": "Revoked"}, reason="verified_gap_exception")
        return gap.pk
    return {"revoked": True, "gap_id": _write(actor, apply)}


def _student_ref(account):
    from .teaching import _full_name
    return {"account_id": account.pk, "ctug_id": account.school_id, "full_name": _full_name(account)}


def search_students(*, actor, q=None):
    from apps.access_control.models import AccountRole
    from apps.accounts.models import Account
    from .configuration import parse_search
    authorize_verifier(actor)
    q = parse_search(q)
    qs = (Account.objects.using(DB).select_related("profile")
          .filter(is_active=True, request_status="Approved", is_staff=False, is_superuser=False,
                  pk__in=AccountRole.objects.using(DB).filter(role__role_name="Student", role__is_active=True)
                  .values("account_id")).order_by("school_id", "pk"))
    if q:
        qs = qs.filter(school_id__istartswith=q)
    return {"results": [_student_ref(a) for a in qs[:20]]}


def student_record(*, actor, student_account_id):
    """What School Admin needs at the counter: per-period evidence, gaps, participation and onboarding."""
    from apps.clearance.models import SemesterClearance
    from apps.finance.models import FeeObligation
    from apps.finance.obligations import obligation_summary
    authorize_verifier(actor)
    student = genuine_student(_id(student_account_id, "student_account_id"))
    if student is None:
        raise services.AcademicPeriodNotFound()
    periods = list(Semester.objects.using(DB).select_related("school_year").filter(activated_at__isnull=False)
                   .order_by("-school_year__start_year", "-term")[:20])
    rows = []
    for semester in periods:
        participation = SemesterParticipation.objects.using(DB).filter(student=student, semester=semester).first()
        clearance = SemesterClearance.objects.using(DB).filter(student=student, semester=semester).first()
        obligation = FeeObligation.objects.using(DB).filter(student=student, semester=semester).first()
        gap = EnrollmentGapException.objects.using(DB).filter(student=student, semester=semester,
                                                              status=VerificationStatus.VERIFIED).first()
        onboarding = SemesterOnboarding.objects.using(DB).filter(student=student, semester=semester).first()
        rows.append({"semester": {"semester_id": semester.pk, "label": semester.label, "status": semester.status,
                                  "school_year_label": semester.school_year.label},
                     "evidence": evidence_payload(current_evidence(student.pk, semester.pk)),
                     "gap": gap_payload(gap) if gap else None,
                     "participation": {"participation_id": participation.pk, "source": participation.source}
                     if participation else None,
                     "clearance_status": clearance.status if clearance else None,
                     "fee": obligation_summary(obligation),
                     "onboarding_status": onboarding.status if onboarding else None})
    return {"student": _student_ref(student), "periods": rows}
