"""WF-05.05 Student Semester Onboarding (Steps 1-4 and the one atomic finalization, WF11-D17-D24).

Owner-authorized restricted local development (26 Nov 2026). Default off:
WORKSPACE_STUDENT_ONBOARDING_ENABLED (status, Draft steps, review, own records) and
WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED (the finalization), both on top of the base
academic-period switch, both refused in production.

Authorization (apps.academic.student_access): genuine Student assignment, selected Student context
when enforced, exact effective permission (account-specific Deny wins). Reads use the pinned Student
default ``academic.profile.self.read``; Draft writes and finalization use the reviewed Student permission
``academic.semester_onboarding.self.submit`` (clearance creation is an internal consequence). The
Student is always the actor's own account: no student identifier is accepted from the client.

Steps (School Year, Semester and CTU-G ID are read-only from the Active semester and the account):
  1. Student type, Regular or Irregular.
  2. Subject confirmation. Regular: the complete prepared list of one section of the Student's course
     and year level (curriculum subjects offered this semester). Irregular: chosen valid offerings of
     the Student's course. Every offering must be valid for the semester and have an eligible
     assigned instructor; one offering per subject. Nothing here infers CTU enrollment.
  3. Course and year level confirmation. A change that makes the confirmed subjects inconsistent
     clears the subject confirmation, so Step 2 must be repeated before review.
  4. Final review and explicit confirmation (the approved semester fee shown is the one confirmed).

Missing or incorrect data is corrected IN PERSON by the School Admin (no online correction request:
WF11-D20/D21 stay skipped). Without matching Verified evidence (apps.academic.verification) the
confirmation records a recoverable Pending Verification and nothing else.

Finalization is ONE durable transaction with the shared lock order: services (academic, clearance,
finance by service_id) -> permission -> account -> Active semester -> fee schedule -> onboarding ->
evidence. Everything is revalidated under those locks; participation, subjects, the clearance with
its requirements, the fee obligation snapshot, the audit rows and the Completed state commit together
or not at all. A repeated or concurrent confirmation returns the existing records.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction

from apps.accounts.fields import CurrentTimestamp

from . import eligibility, services
from .models import (
    Course, MAX_YEAR_LEVEL, MIN_YEAR_LEVEL, OnboardingStatus, ParticipationSource, ParticipationSubject, Section,
    Semester, SemesterOnboarding, SemesterOnboardingSubject, SemesterParticipation, SemesterStatus, StudentType,
    SubjectOffering,
)
from .student_access import authorize_student, lock_and_authorize_student

DB = DEFAULT_DB_ALIAS
READ_CODE = "academic.profile.self.read"
WRITE_CODE = "academic.semester_onboarding.self.submit"
ONBOARDING_SETTING = "WORKSPACE_STUDENT_ONBOARDING_ENABLED"
FINALIZATION_SETTING = "WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED"
MAX_SUBJECTS = 20
FINALIZE_ACTION = "academic.onboarding.finalize"
CORRECTION_INSTRUCTIONS = (
    "If a subject, section, instructor, course or year level is missing or incorrect, visit the School Admin "
    "office in person with your official CTU enrollment record. The School Admin checks it against CTU records "
    "and corrects the Workspace records. Then return here and confirm again. There is no online correction request.")


class OnboardingConflict(Exception):
    REASONS = frozenset({
        "no_active_semester", "semester_changed", "already_completed", "stale_version", "type_required",
        "subjects_required", "course_required", "subjects_changed", "subject_unavailable", "instructor_unassigned",
        "duplicate_subject", "section_mismatch", "incomplete_section", "course_unavailable", "fee_unavailable",
        "fee_changed", "eligibility_blocked", "confirmation_required", "finalization_conflict", "instructor_conflict",
    })

    def __init__(self, reason, details=()):
        self.reason = reason if reason in self.REASONS else "finalization_conflict"
        self.details = tuple(details)
        super().__init__("The onboarding step could not be saved.")


class OnboardingRequired(Exception):
    """Backend dashboard gate: current-semester Student data needs a finalized onboarding."""

    def __init__(self, state):
        self.state = state
        self.route = dashboard_route(state)
        super().__init__("Complete Student Semester Onboarding first.")


def dashboard_route(state):
    """Server-decided Student dashboard routing (WF11-D17): where the dashboard must open."""
    return {"completed": "dashboard", "no_active_semester": "period_unavailable",
            "clearance_required": "clearance_required", "onboarding": "onboarding",
            "pending_verification": "onboarding"}.get(state, "verification_required")


def onboarding_enabled():
    return services.gate_open() and getattr(settings, ONBOARDING_SETTING, False) is True


def finalization_enabled():
    return onboarding_enabled() and getattr(settings, FINALIZATION_SETTING, False) is True


def _invalid(field, code="invalid"):
    raise services.AcademicPeriodInvalid({field: code})


def _id(raw, field):
    if type(raw) is not int or not 1 <= raw <= services.MAX_ID:
        _invalid(field)
    return raw


def _version(raw):
    if raw is None:
        return None
    return _id(raw, "expected_version")


def _year_level(raw):
    if type(raw) is not int or not MIN_YEAR_LEVEL <= raw <= MAX_YEAR_LEVEL:
        _invalid("year_level")
    return raw


def active_semester(lock=False):
    qs = Semester.objects.using(DB).select_related("school_year").filter(status=SemesterStatus.ACTIVE)
    return (qs.select_for_update() if lock else qs).first()


def semester_ref(semester):
    return {"semester_id": semester.pk, "label": semester.label, "status": semester.status,
            "school_year_label": semester.school_year.label,
            "start_date": semester.start_date.isoformat() if semester.start_date else None,
            "end_date": semester.end_date.isoformat() if semester.end_date else None}


def _student_ref(account):
    from .teaching import _full_name
    account = type(account).objects.using(DB).select_related("profile").get(pk=account.pk)
    return {"ctug_id": account.school_id, "full_name": _full_name(account)}


# ---- Offerings a Student may confirm -----------------------------------------------------------

def _valid(semester):
    from .configuration import valid_offerings
    return valid_offerings(semester.pk).select_related("subject", "section__course", "curriculum_subject__curriculum")


def _instructor(offering):
    """The eligible current instructor of the offering, or None (never a substitute)."""
    from .teaching import current_assignment, instructor_eligible
    assignment = current_assignment(offering)
    if assignment is None or not instructor_eligible(assignment.instructor_id):
        return None
    return assignment.instructor


def _offering_option(offering):
    from .teaching import _full_name
    instructor = _instructor(offering)
    subject = offering.subject
    return {"offering_id": offering.pk,
            "subject": {"subject_id": subject.pk, "code": subject.code, "title": subject.title,
                        "lecture_units": f"{subject.lecture_units}" if subject.lecture_units is not None else None,
                        "lab_units": f"{subject.lab_units}" if subject.lab_units is not None else None},
            "section": {"section_id": offering.section_id, "name": offering.section.name,
                        "year_level": offering.section.year_level, "course_code": offering.section.course.code},
            "instructor": _full_name(instructor) if instructor is not None else None,
            "instructor_assigned": instructor is not None,
            "ready_for_confirmation": instructor is not None}


def _regular_section_offerings(semester, section_id):
    return list(_valid(semester).filter(section_id=section_id).order_by("subject__code", "offering_id"))


def _context_options(semester):
    """Courses and year levels that have valid offerings this semester (for Steps 2 and 3)."""
    courses = {}
    for offering in _valid(semester).filter(section__course__status="Active").order_by(
            "section__course__code", "section__year_level", "section__name"):
        course = offering.section.course
        entry = courses.setdefault(course.pk, {"course_id": course.pk, "code": course.code, "name": course.name,
                                               "sections": {}})
        entry["sections"].setdefault(offering.section_id, {"section_id": offering.section_id,
                                                           "name": offering.section.name,
                                                           "year_level": offering.section.year_level})
    return [{**c, "year_levels": sorted({s["year_level"] for s in c["sections"].values()}),
             "sections": list(c["sections"].values())} for c in courses.values()]


# ---- State ----------------------------------------------------------------------------------------

def _evidence(student, semester, lock=False):
    from .verification import current_evidence
    return current_evidence(student.pk, semester.pk, lock=lock)


def _draft(student, semester, lock=False):
    qs = SemesterOnboarding.objects.using(DB).select_related("course").filter(student=student, semester=semester)
    return (qs.select_for_update() if lock else qs).first()


def _draft_subjects(onboarding):
    return list(SemesterOnboardingSubject.objects.using(DB)
                .select_related("offering__subject", "offering__section__course", "subject")
                .filter(onboarding=onboarding).order_by("subject__code"))


def _evidence_match(onboarding, evidence, subject_ids):
    """Fields where the Verified evidence differs from the Student's confirmed selections."""
    if evidence is None:
        return None
    mismatched = []
    if evidence.course_id != onboarding.course_id:
        mismatched.append("course")
    if evidence.year_level != onboarding.year_level:
        mismatched.append("year_level")
    verified = set(evidence.subjects.using(DB).values_list("subject_id", flat=True))
    if verified != set(subject_ids):
        mismatched.append("subjects")
    return mismatched


def _next_step(onboarding):
    if onboarding is None or onboarding.student_type is None:
        return 1
    if not onboarding.subjects_confirmed:
        return 2
    if not onboarding.course_confirmed:
        return 3
    return 4


def _onboarding_payload(onboarding):
    if onboarding is None:
        return {"status": None, "student_type": None, "course": None, "year_level": None, "subjects": [],
                "subjects_confirmed": False, "course_confirmed": False, "version": None, "next_step": 1}
    return {"status": onboarding.status, "student_type": onboarding.student_type,
            "course": {"course_id": onboarding.course_id, "code": onboarding.course.code, "name": onboarding.course.name}
            if onboarding.course_id else None,
            "year_level": onboarding.year_level,
            "subjects": [_offering_option(row.offering) for row in _draft_subjects(onboarding)],
            "subjects_confirmed": onboarding.subjects_confirmed, "course_confirmed": onboarding.course_confirmed,
            "version": onboarding.version, "next_step": _next_step(onboarding)}


def _prefill(student, semester, evidence):
    """Course/year context the Student starts Step 2 from: Verified evidence, else last participation."""
    if evidence is not None:
        return {"course_id": evidence.course_id, "year_level": evidence.year_level, "source": "verified_record"}
    last = (SemesterParticipation.objects.using(DB).filter(student=student).exclude(semester=semester)
            .order_by("-semester__school_year__start_year", "-semester__term").first())
    if last is not None:
        return {"course_id": last.course_id, "year_level": last.year_level, "source": "previous_semester"}
    return None


def _participation_result(participation):
    from apps.clearance.services import clearance_summary
    from apps.finance.obligations import obligation_summary
    from .teaching import _full_name
    rows = (ParticipationSubject.objects.using(DB).select_related("subject", "offering__section", "instructor__profile")
            .filter(participation=participation).order_by("subject__code"))
    return {"participation_id": participation.pk, "source": participation.source,
            "student_type": participation.student_type,
            "course": {"course_id": participation.course_id, "code": participation.course.code,
                       "name": participation.course.name},
            "year_level": participation.year_level,
            "subjects": [{"subject_id": r.subject_id, "code": r.subject.code, "title": r.subject.title,
                          "section": r.offering.section.name, "instructor": _full_name(r.instructor)} for r in rows],
            "clearance": clearance_summary(getattr(participation, "clearance", None)),
            "fee": obligation_summary(getattr(participation, "fee_obligation", None)),
            "completed_at": participation.created_at.isoformat() if hasattr(participation.created_at, "isoformat") else None}


def _participation(student, semester):
    return (SemesterParticipation.objects.using(DB).select_related("course", "clearance", "fee_obligation")
            .filter(student=student, semester=semester).first())


def _previous_clearance(student, eligible):
    from apps.clearance.services import clearance_summary
    previous = eligible.get("previous_semester")
    if previous is None:
        return None
    participation = _participation(student, Semester.objects.using(DB).get(pk=previous["semester_id"]))
    if participation is None:
        return None
    from apps.finance.obligations import obligation_summary
    return {"semester": previous, "clearance": clearance_summary(getattr(participation, "clearance", None)),
            "fee": obligation_summary(getattr(participation, "fee_obligation", None))}


def state_for(student, semester):
    """The Student's onboarding state for the Active semester (read-only), with its dashboard route.

    Always evaluated against the CURRENT Active semester: a participation in an earlier semester never
    counts as completion for a newly activated one (WF11-D17).
    """
    body = _state_for(student, semester)
    body["dashboard_route"] = dashboard_route(body["state"])
    return body


def _state_for(student, semester):
    if semester is None:
        return {"state": "no_active_semester", "semester": None, "dashboard_unlocked": False}
    participation = _participation(student, semester)
    if participation is not None:
        return {"state": "completed", "semester": semester_ref(semester), "dashboard_unlocked": True,
                "result": _participation_result(participation)}
    evidence = _evidence(student, semester)
    eligible = eligibility.evaluate(student, semester, evidence)
    body = {"semester": semester_ref(semester), "dashboard_unlocked": False, "eligibility": eligible,
            "correction_instructions": CORRECTION_INSTRUCTIONS}
    if eligible["status"] in eligibility.BLOCKING:
        if eligible["status"] == "clearance_required":
            body["previous_clearance"] = _previous_clearance(student, eligible)
        return {"state": eligible["status"], **body}
    onboarding = _draft(student, semester)
    state = ("pending_verification" if onboarding is not None and onboarding.status == OnboardingStatus.PENDING_VERIFICATION
             else "onboarding")
    return {"state": state, **body, "onboarding": _onboarding_payload(onboarding),
            "prefill": _prefill(student, semester, evidence),
            "verified_record_available": evidence is not None}


def _read(actor):
    return authorize_student(actor, READ_CODE, onboarding_enabled)


def status(*, actor):
    auth = _read(actor)
    body = state_for(auth.account, active_semester())
    body["student"] = _student_ref(auth.account)
    body["features"] = {"finalization_enabled": finalization_enabled()}
    return body


def context_options(*, actor):
    _read(actor)
    semester = active_semester()
    if semester is None:
        raise OnboardingConflict("no_active_semester")
    return {"semester": semester_ref(semester), "courses": _context_options(semester)}


def subject_options(*, actor, course_id, year_level=None, section_id=None):
    """Step 2 choices. Regular: the complete prepared list of ``section_id`` (course and year level).
    Irregular: every valid offering of the course. Reads only; the Draft's type decides."""
    auth = _read(actor)
    semester = active_semester()
    if semester is None:
        raise OnboardingConflict("no_active_semester")
    onboarding = _draft(auth.account, semester)
    if onboarding is None or onboarding.student_type is None:
        raise OnboardingConflict("type_required")
    course_id = _id(course_id, "course_id")
    if onboarding.student_type == StudentType.REGULAR:
        year_level, section_id = _year_level(year_level), _id(section_id, "section_id")
        section = Section.objects.using(DB).filter(pk=section_id, course_id=course_id, year_level=year_level,
                                                   status="Active").first()
        if section is None:
            raise OnboardingConflict("section_mismatch")
        rows = _regular_section_offerings(semester, section.pk)
    else:
        rows = list(_valid(semester).filter(section__course_id=course_id)
                    .order_by("section__year_level", "subject__code", "section__name", "offering_id"))
    options = [_offering_option(o) for o in rows]
    return {"semester": semester_ref(semester), "student_type": onboarding.student_type, "options": options,
            "complete": bool(options) and all(o["ready_for_confirmation"] for o in options),
            "correction_instructions": CORRECTION_INSTRUCTIONS}


# ---- Draft writes ---------------------------------------------------------------------------------

def _draft_write(actor, fn):
    if not onboarding_enabled():
        raise services.AcademicPeriodUnavailable("Student Semester Onboarding is not activated.")
    authorize_student(actor, WRITE_CODE, onboarding_enabled)
    try:
        with transaction.atomic(using=DB, durable=True):
            auth = lock_and_authorize_student(actor, WRITE_CODE, onboarding_enabled)
            semester = active_semester(lock=True)
            if semester is None:
                raise OnboardingConflict("no_active_semester")
            student = auth.account
            if _participation(student, semester) is not None:
                raise OnboardingConflict("already_completed")
            eligible = eligibility.evaluate(student, semester, _evidence(student, semester))
            if eligible["status"] in eligibility.BLOCKING:
                raise OnboardingConflict("eligibility_blocked", [eligible["status"]])
            onboarding = _draft(student, semester, lock=True)
            fn(student, semester, onboarding)
    except IntegrityError as exc:
        raise OnboardingConflict("stale_version") from exc
    return status(actor=actor)


def _check_version(onboarding, expected_version):
    if (onboarding.version if onboarding else None) != expected_version:
        raise OnboardingConflict("stale_version")


def _touch(onboarding, **changes):
    """Every Draft change returns a Pending Verification draft to Draft (it must be reviewed again)."""
    changed = SemesterOnboarding.objects.using(DB).filter(pk=onboarding.pk, version=onboarding.version).update(
        status=OnboardingStatus.DRAFT, version=onboarding.version + 1, updated_at=CurrentTimestamp(), **changes)
    if changed != 1:
        raise OnboardingConflict("stale_version")


def save_student_type(*, actor, student_type, expected_version=None):
    """Step 1. Changing the type clears the confirmed subjects (their meaning differs)."""
    if type(student_type) is not str or student_type not in StudentType.values:
        _invalid("student_type")
    expected_version = _version(expected_version)

    def apply(student, semester, onboarding):
        _check_version(onboarding, expected_version)
        if onboarding is None:
            SemesterOnboarding.objects.using(DB).create(student=student, semester=semester, student_type=student_type)
            return
        if onboarding.student_type == student_type:
            return _touch(onboarding)
        SemesterOnboardingSubject.objects.using(DB).filter(onboarding=onboarding).delete()
        _touch(onboarding, student_type=student_type, subjects_confirmed=False)
    return _draft_write(actor, apply)


def _parse_offering_ids(raw):
    if (type(raw) is not list or not 1 <= len(raw) <= MAX_SUBJECTS or len(set(raw)) != len(raw)
            or any(type(i) is not int or not 1 <= i <= services.MAX_ID for i in raw)):
        _invalid("offering_ids")
    return raw


def _validated_selection(semester, student_type, course_id, year_level, offering_ids, student):
    """The offerings, revalidated for THIS semester, or OnboardingConflict. Returns (offerings, instructors).

    A Student who is also the assigned instructor of a selected offering is refused (``instructor_conflict``):
    nobody signs their own clearance requirement, and no substitute signatory is chosen here.
    """
    offerings = {o.pk: o for o in _valid(semester).filter(pk__in=offering_ids)}
    if len(offerings) != len(offering_ids):
        raise OnboardingConflict("subject_unavailable")
    rows = [offerings[i] for i in offering_ids]
    if len({o.subject_id for o in rows}) != len(rows):
        raise OnboardingConflict("duplicate_subject")
    if any(o.section.course_id != course_id for o in rows):
        raise OnboardingConflict("section_mismatch")
    if student_type == StudentType.REGULAR:
        sections = {o.section_id for o in rows}
        if len(sections) != 1 or rows[0].section.year_level != year_level:
            raise OnboardingConflict("section_mismatch")
        prepared = {o.pk for o in _regular_section_offerings(semester, rows[0].section_id)}
        if prepared != set(offering_ids):
            raise OnboardingConflict("incomplete_section")  # a Regular Student confirms the whole prepared list
    instructors = {}
    for offering in rows:
        instructor = _instructor(offering)
        if instructor is None:
            raise OnboardingConflict("instructor_unassigned", [offering.subject.code])
        if instructor.pk == student.pk:
            raise OnboardingConflict("instructor_conflict", [offering.subject.code])
        instructors[offering.pk] = instructor
    return rows, instructors


def _course(course_id):
    course = Course.objects.using(DB).filter(pk=course_id, status="Active").first()
    if course is None:
        raise OnboardingConflict("course_unavailable")
    return course


def confirm_subjects(*, actor, course_id, year_level, offering_ids, expected_version):
    """Step 2: store the explicitly confirmed offerings and the course/year context they were chosen in."""
    course_id, year_level = _id(course_id, "course_id"), _year_level(year_level)
    offering_ids, expected_version = _parse_offering_ids(offering_ids), _id(expected_version, "expected_version")

    def apply(student, semester, onboarding):
        if onboarding is None or onboarding.student_type is None:
            raise OnboardingConflict("type_required")
        _check_version(onboarding, expected_version)
        _course(course_id)
        rows, _instructors = _validated_selection(semester, onboarding.student_type, course_id, year_level, offering_ids,
                                                  student)
        SemesterOnboardingSubject.objects.using(DB).filter(onboarding=onboarding).delete()
        for offering in rows:
            SemesterOnboardingSubject.objects.using(DB).create(onboarding=onboarding, offering=offering,
                                                               subject_id=offering.subject_id)
        same_context = onboarding.course_id == course_id and onboarding.year_level == year_level
        _touch(onboarding, course_id=course_id, year_level=year_level, subjects_confirmed=True,
               course_confirmed=onboarding.course_confirmed and same_context)
    return _draft_write(actor, apply)


def _subjects_consistent(onboarding, course_id, year_level, rows):
    if not rows:
        return False
    if any(r.offering.section.course_id != course_id for r in rows):
        return False
    if onboarding.student_type == StudentType.REGULAR:
        return all(r.offering.section.year_level == year_level for r in rows)
    return True


def confirm_course(*, actor, course_id, year_level, expected_version):
    """Step 3: confirm course and year level; inconsistent confirmed subjects must be re-confirmed."""
    course_id, year_level = _id(course_id, "course_id"), _year_level(year_level)
    expected_version = _id(expected_version, "expected_version")

    def apply(student, semester, onboarding):
        if onboarding is None or onboarding.student_type is None:
            raise OnboardingConflict("type_required")
        _check_version(onboarding, expected_version)
        _course(course_id)
        consistent = _subjects_consistent(onboarding, course_id, year_level, _draft_subjects(onboarding))
        _touch(onboarding, course_id=course_id, year_level=year_level, course_confirmed=True,
               subjects_confirmed=onboarding.subjects_confirmed and consistent)
    return _draft_write(actor, apply)


# ---- Step 4: review and finalization ----------------------------------------------------------------

def _fee(semester):
    """(approved revision, readiness result) from the real fee contract; no client amount is ever used."""
    from apps.finance.fees import _validated_current, fee_readiness
    from apps.finance.models import SemesterFeeSchedule
    readiness = fee_readiness(semester)
    if readiness.status != "ready":
        return None, readiness
    schedule = (SemesterFeeSchedule.objects.using(DB).select_related("current_approved_revision")
                .filter(semester_id=semester.pk).first())
    return (_validated_current(schedule) if schedule else None), readiness


def review(*, actor):
    auth = _read(actor)
    semester = active_semester()
    if semester is None:
        raise OnboardingConflict("no_active_semester")
    student = auth.account
    participation = _participation(student, semester)
    if participation is not None:
        return {"state": "completed", "semester": semester_ref(semester), "result": _participation_result(participation)}
    onboarding = _draft(student, semester)
    if onboarding is None or _next_step(onboarding) != 4:
        raise OnboardingConflict("subjects_required" if onboarding and onboarding.student_type else "type_required")
    rows = _draft_subjects(onboarding)
    evidence = _evidence(student, semester)
    eligible = eligibility.evaluate(student, semester, evidence)
    revision, readiness = _fee(semester)
    mismatched = _evidence_match(onboarding, evidence, [r.subject_id for r in rows])
    blockers = []
    if eligible["status"] in eligibility.BLOCKING:
        blockers.append("eligibility_blocked")
    if revision is None:
        blockers.append("fee_unavailable")
    if any(not _offering_option(r.offering)["ready_for_confirmation"] for r in rows):
        blockers.append("instructor_unassigned")
    if not finalization_enabled():
        blockers.append("feature_disabled")
    verification = ("verified" if mismatched == [] else "mismatch" if mismatched else "not_recorded")
    return {"state": "review", "semester": semester_ref(semester), "student": _student_ref(student),
            "onboarding": _onboarding_payload(onboarding),
            "fee": {"revision_id": revision.pk, "amount": f"{revision.amount:.2f}", "currency": revision.currency}
            if revision else None,
            "fee_status": readiness.reason or readiness.status,
            "verification": verification, "mismatched": mismatched or [],
            "eligibility": eligible, "blockers": blockers, "can_confirm": not blockers,
            "correction_instructions": CORRECTION_INSTRUCTIONS}


def _fail(step):
    """Failure-injection seam for isolated tests (a no-op in normal operation)."""


def _finalize_locked(auth, expected_version, expected_fee_revision_id):
    from apps.clearance.services import ClearanceCreationRefused, create_semester_clearance
    from apps.finance.fees import _audit as finance_audit
    from apps.finance.obligations import ObligationRefused, create_fee_obligation, locked_approved_revision
    student = auth.account
    semester = active_semester(lock=True)
    if semester is None:
        raise OnboardingConflict("no_active_semester")
    revision = locked_approved_revision(semester)
    onboarding = _draft(student, semester, lock=True)
    existing = _participation(student, semester)
    if existing is not None:
        return "completed", existing  # A1: a repeated confirmation returns the existing records
    if onboarding is None:
        # Not started, or a Draft for a previous Active semester (the Active semester switched).
        if SemesterOnboarding.objects.using(DB).filter(student=student).exclude(
                status=OnboardingStatus.COMPLETED).exists():
            raise OnboardingConflict("semester_changed")
        raise OnboardingConflict("type_required")
    if onboarding.version != expected_version:
        raise OnboardingConflict("stale_version")
    if _next_step(onboarding) != 4:
        raise OnboardingConflict("subjects_required" if onboarding.student_type else "type_required")
    evidence = _evidence(student, semester, lock=True)
    eligible = eligibility.evaluate(student, semester, evidence)
    if eligible["status"] in eligibility.BLOCKING:
        raise OnboardingConflict("eligibility_blocked", [eligible["status"]])
    rows = _draft_subjects(onboarding)
    if not _subjects_consistent(onboarding, onboarding.course_id, onboarding.year_level, rows):
        raise OnboardingConflict("subjects_changed")
    offerings, instructors = _validated_selection(semester, onboarding.student_type, onboarding.course_id,
                                                  onboarding.year_level, [r.offering_id for r in rows], student)
    _course(onboarding.course_id)
    if revision is None:
        raise OnboardingConflict("fee_unavailable")
    if revision.pk != expected_fee_revision_id:
        raise OnboardingConflict("fee_changed")  # the Student confirms the amount shown, nothing else
    mismatched = _evidence_match(onboarding, evidence, [o.subject_id for o in offerings])
    if mismatched is None or mismatched or eligible["status"] == "verification_required":
        SemesterOnboarding.objects.using(DB).filter(pk=onboarding.pk).update(
            status=OnboardingStatus.PENDING_VERIFICATION, updated_at=CurrentTimestamp())
        return "pending_verification", None
    _fail("participation")
    participation = SemesterParticipation.objects.using(DB).create(
        student=student, semester=semester, onboarding=onboarding, evidence=evidence,
        source=ParticipationSource.ONBOARDING, student_type=onboarding.student_type, course_id=onboarding.course_id,
        year_level=onboarding.year_level, created_by=student)
    _fail("subjects")
    subject_rows = [ParticipationSubject.objects.using(DB).create(
        participation=participation, subject_id=o.subject_id, offering=o, instructor=instructors[o.pk]) for o in offerings]
    _fail("clearance")
    try:
        clearance = create_semester_clearance(participation, subject_rows)
        _fail("obligation")
        obligation = create_fee_obligation(participation, revision)
    except (ClearanceCreationRefused, ObligationRefused) as exc:
        raise OnboardingConflict("instructor_unassigned" if exc.reason == "instructor_unassigned"
                                 else "instructor_conflict" if exc.reason == "signatory_conflict"
                                 else "fee_unavailable" if exc.reason == "fee_unavailable" else "finalization_conflict") from exc
    _fail("audit")
    services.write_audit(auth, action=FINALIZE_ACTION, school_year_id=semester.school_year_id, semester_id=semester.pk,
                         new_value={"participation_id": participation.pk, "onboarding_id": onboarding.pk,
                                    "evidence_id": evidence.pk, "evidence_source": evidence.source_type,
                                    "student_type": onboarding.student_type, "course_id": onboarding.course_id,
                                    "year_level": onboarding.year_level,
                                    "subject_ids": sorted(o.subject_id for o in offerings),
                                    "clearance_id": clearance.pk, "obligation_id": obligation.pk,
                                    "eligibility_basis": eligible["basis"],
                                    "older_uncleared": [s["semester_id"] for s in eligible["older_uncleared"]]},
                         reason="student_semester_onboarding")
    finance_audit(auth, "finance.fee_obligation.create", "fee_obligation", obligation.pk, semester.pk,
                  new={"participation_id": participation.pk, "fee_revision_id": revision.pk,
                       "amount": f"{obligation.amount:.2f}", "currency": obligation.currency, "status": obligation.status},
                  reason="onboarding_finalization")
    _fail("completion")
    changed = SemesterOnboarding.objects.using(DB).filter(pk=onboarding.pk, version=expected_version).update(
        status=OnboardingStatus.COMPLETED, completed_at=CurrentTimestamp(), version=expected_version + 1,
        updated_at=CurrentTimestamp())
    if changed != 1:
        raise OnboardingConflict("finalization_conflict")
    return "completed", participation


def finalize(*, actor, expected_version, expected_fee_revision_id, confirmed):
    """Step 4 confirmation. Returns the completed records, or the recorded Pending Verification state."""
    if not finalization_enabled():
        if not onboarding_enabled():
            raise services.AcademicPeriodUnavailable("Student Semester Onboarding is not activated.")
        raise services.AcademicPeriodFeatureDisabled("Onboarding finalization is not enabled.")
    if confirmed is not True:
        raise OnboardingConflict("confirmation_required")
    expected_version = _id(expected_version, "expected_version")
    expected_fee_revision_id = _id(expected_fee_revision_id, "expected_fee_revision_id")
    authorize_student(actor, WRITE_CODE, finalization_enabled)
    try:
        with transaction.atomic(using=DB, durable=True):
            auth = lock_and_authorize_student(actor, WRITE_CODE, finalization_enabled)
            outcome, participation = _finalize_locked(auth, expected_version, expected_fee_revision_id)
    except IntegrityError as exc:
        # A concurrent confirmation that won the unique constraints: return its records, never a duplicate.
        semester = active_semester()
        existing = _participation(actor, semester) if semester is not None else None
        if existing is None:
            raise OnboardingConflict("finalization_conflict") from exc
        outcome, participation = "completed", existing
    if outcome == "pending_verification":
        body = status(actor=actor)
        body["outcome"] = "pending_verification"
        return body
    participation = _participation(participation.student, participation.semester)
    return {"outcome": "completed", "state": "completed", "semester": semester_ref(participation.semester),
            "result": _participation_result(participation), "dashboard_unlocked": True, "dashboard_route": "dashboard"}


# ---- Own records (backend dashboard gate) -------------------------------------------------------------

def require_completed(student, semester):
    """Raise OnboardingRequired unless the Student finalized onboarding for the Active semester."""
    if semester is None or _participation(student, semester) is None:
        state = state_for(student, semester)["state"] if semester is not None else "no_active_semester"
        raise OnboardingRequired(state)


def my_semester(*, actor):
    """Current-semester Student dashboard data: available ONLY after a committed finalization."""
    auth = _read(actor)
    semester = active_semester()
    require_completed(auth.account, semester)
    participation = _participation(auth.account, semester)
    return {"semester": semester_ref(semester), "student": _student_ref(auth.account),
            "result": _participation_result(participation)}


def my_history(*, actor):
    """Own historical clearance and fee status (WF11-D17: available even while onboarding is required)."""
    auth = _read(actor)
    rows = (SemesterParticipation.objects.using(DB).select_related("semester__school_year", "course", "clearance",
                                                                    "fee_obligation")
            .filter(student=auth.account).order_by("-semester__school_year__start_year", "-semester__term")[:20])
    from apps.clearance.services import clearance_summary
    from apps.finance.obligations import obligation_summary
    return {"results": [{"semester": semester_ref(p.semester), "source": p.source, "year_level": p.year_level,
                         "course_code": p.course.code,
                         "clearance": clearance_summary(getattr(p, "clearance", None)),
                         "fee": obligation_summary(getattr(p, "fee_obligation", None))} for p in rows]}
