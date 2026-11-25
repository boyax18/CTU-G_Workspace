"""Academic configuration foundation: courses, subjects, sections, curricula and semester offerings.

Owner-authorized restricted local development (25 Nov 2026). These are CTU-G Workspace's own
configuration records used by WF-11.01 activation and the future WF-05.05 onboarding. They never
claim to change, or to prove, institutional CTU enrollment.

Authorization: every call goes through apps.academic.services.authorize with the area's EXACT
catalogue code (pinned v2.0; the v2.1/v2.2 overlays do not change these codes):

=========  ========================================  =====================================
Area       Code                                      Scope basis
=========  ========================================  =====================================
courses    academic.courses.manage                   "Maintain approved course definitions"
subjects   clearance.subjects.manage                 "Maintain subjects and lecture/lab units"
sections   academic.sections.manage                  "course/year/section definitions"
curricula  academic.courses.manage  (PROPOSED)       no approved curriculum-specific code
offerings  academic.periods.manage  (PROPOSED)       WF-11.01 step 2 only; no exact code
teaching   clearance.teaching_assignments.manage     "subject/period/section" instructors
=========  ========================================  =====================================

Areas with a PROPOSED mapping, and teaching assignments, have their own default-off write switch
(``write_setting``); the governance dependency is reported in docs. academic.advisers.manage
(section advisers) is never used here. Writes re-authorize under the shared academic locks and
commit with an append-only AcademicConfigurationAuditLog row.
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction
from django.db.models import F, Q

from apps.accounts.fields import CurrentTimestamp

from . import services
from .models import (
    MAX_START_YEAR, MAX_UNITS, MAX_YEAR_LEVEL, MIN_START_YEAR, MIN_YEAR_LEVEL, AcademicConfigurationAuditLog, Course,
    CurriculumStatus, CurriculumSubject, CurriculumVersion, DefinitionStatus, Section, Semester, SemesterStatus,
    SemesterTerm, Subject, SubjectOffering,
)
from .periods import term_key

CONFIG_SETTING = "WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED"
PAGE_SIZE = 50
MAX_ID = services.MAX_ID
DB = DEFAULT_DB_ALIAS


@dataclass(frozen=True)
class Area:
    key: str
    permission_code: str
    write_setting: str | None
    exact_scope: bool


AREAS = {
    "courses": Area("courses", "academic.courses.manage", None, True),
    "subjects": Area("subjects", "clearance.subjects.manage", None, True),
    "sections": Area("sections", "academic.sections.manage", None, True),
    "curricula": Area("curricula", "academic.courses.manage", "WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED", False),
    "offerings": Area("offerings", "academic.periods.manage", "WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED", False),
    "teaching": Area("teaching", "clearance.teaching_assignments.manage",
                     "WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED", True),
}


class ConfigurationConflict(Exception):
    """A fixed, non-sensitive refusal (409); nothing changed."""

    REASONS = frozenset({
        "code_exists", "label_exists", "section_exists", "entry_exists", "offering_exists", "stale_version",
        "in_use", "invalid_transition", "not_available", "not_draft", "not_published", "curriculum_empty",
        "period_closed", "period_not_draft", "reference_mismatch", "offering_in_use", "assignment_changed",
        "no_change", "instructor_ineligible", "constraint_conflict",
    })

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "constraint_conflict"
        super().__init__("The academic configuration could not be changed.")


# ---- Gates and authorization ----------------------------------------------------------------

def configuration_enabled():
    return getattr(settings, CONFIG_SETTING, False) is True


def write_enabled(area):
    return configuration_enabled() and (area.write_setting is None or getattr(settings, area.write_setting, False) is True)


def feature_flags():
    """Server switch state for the UI (never authorization)."""
    return {"curriculum_writes": write_enabled(AREAS["curricula"]), "offering_writes": write_enabled(AREAS["offerings"]),
            "teaching_assignments": write_enabled(AREAS["teaching"])}


def authorize_read(actor, area_key):
    return services.authorize(actor, AREAS[area_key].permission_code, gate=configuration_enabled)


def write(actor, area_key, fn):
    """Pre-check, then lock + re-authorize + run ``fn(auth)`` + audit in ONE durable transaction."""
    area = AREAS[area_key]
    if not configuration_enabled():
        raise services.AcademicPeriodUnavailable("Academic configuration is not activated.")
    if not write_enabled(area):
        raise services.AcademicPeriodFeatureDisabled("This academic-configuration change is not enabled.")
    def gate():
        return write_enabled(area)
    services.authorize(actor, area.permission_code, gate=gate)
    try:
        with transaction.atomic(using=DB, durable=True):
            auth = services.lock_and_authorize(actor, area.permission_code, gate=gate)
            return fn(auth)
    except IntegrityError as exc:
        # Natural keys are checked under the lock first; this is the database backstop.
        raise ConfigurationConflict("constraint_conflict") from exc


def audit(auth, action, entity_type, entity_id, old=None, new=None, reason="configuration_change"):
    if not transaction.get_connection(DB).in_atomic_block:
        raise services.AcademicPeriodUnavailable("Audit requires the change's transaction.")
    AcademicConfigurationAuditLog.objects.using(DB).create(
        actor_account=auth.account, acting_role_id=auth.acting_role_id, action=action, entity_type=entity_type,
        entity_id=entity_id, old_value=old, new_value=new, reason=reason)


# ---- Input normalization (fixed field codes; submitted values are never echoed) ----------------

_CODE = re.compile(r"[A-Z0-9](?:[A-Z0-9 .\-/]{0,18}[A-Z0-9])?", re.ASCII)


def _invalid(field, code="invalid"):
    raise services.AcademicPeriodInvalid({field: code})


def normalize_code(raw, field):
    if type(raw) is not str:
        _invalid(field)
    text = " ".join(unicodedata.normalize("NFKC", raw).split()).upper()
    if not _CODE.fullmatch(text):
        _invalid(field)
    return text


def clean_text(raw, field, max_len, required=True):
    if raw is None and not required:
        return None
    if type(raw) is not str:
        _invalid(field)
    text = " ".join(unicodedata.normalize("NFKC", raw).split())
    if not text:
        if required:
            _invalid(field, "required")
        return None
    if len(text) > max_len or any(unicodedata.category(ch).startswith("C") for ch in text):
        _invalid(field)
    return text


def parse_units(raw, field):
    if raw is None:
        return None
    if type(raw) not in (int, float, str):
        _invalid(field)
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        _invalid(field)
    if not value.is_finite() or value != value.quantize(Decimal("0.1")) or not 0 <= value <= MAX_UNITS:
        _invalid(field)
    return value.quantize(Decimal("0.1"))


def parse_year_level(raw, field="year_level"):
    if type(raw) is not int or not MIN_YEAR_LEVEL <= raw <= MAX_YEAR_LEVEL:
        _invalid(field)
    return raw


def parse_term(raw):
    terms = {"first": SemesterTerm.FIRST, "second": SemesterTerm.SECOND}
    if type(raw) is not str or raw not in terms:
        _invalid("term")
    return terms[raw]


def parse_id(raw, field):
    if type(raw) is not int or not 1 <= raw <= MAX_ID:
        _invalid(field)
    return raw


def parse_version(raw):
    return parse_id(raw, "expected_version")


def parse_status(raw):
    if type(raw) is not str or raw not in DefinitionStatus.values:
        _invalid("status")
    return raw


def parse_page(raw):
    if type(raw) is not int or not 1 <= raw <= 500:
        _invalid("page")
    return raw


def parse_search(raw):
    if raw is None:
        return None
    if type(raw) is not str:
        _invalid("q")
    text = " ".join(raw.split())
    if not text:
        return None
    if len(text) > 50 or not all(" " <= ch <= "~" for ch in text):
        _invalid("q")
    return text


def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _units(value):
    return None if value is None else str(value)


def _page(qs, page):
    start = (page - 1) * PAGE_SIZE
    rows = list(qs[start:start + PAGE_SIZE + 1])
    return rows[:PAGE_SIZE], len(rows) > PAGE_SIZE


def _locked(model, pk):
    row = model.objects.using(DB).select_for_update().filter(pk=pk).first()
    if row is None:
        raise services.AcademicPeriodNotFound()
    return row


def _check_version(row, expected):
    if row.version != expected:
        raise ConfigurationConflict("stale_version")


_STATUS_TRANSITIONS = {
    DefinitionStatus.ACTIVE: {DefinitionStatus.INACTIVE, DefinitionStatus.RETIRED},
    DefinitionStatus.INACTIVE: {DefinitionStatus.ACTIVE, DefinitionStatus.RETIRED},
    DefinitionStatus.RETIRED: set(),  # terminal: retired definitions are preserved, never reused
}


def _bump(model, row, **changes):
    model.objects.using(DB).filter(pk=row.pk, version=row.version).update(
        version=row.version + 1, updated_at=CurrentTimestamp(), **changes)
    row.refresh_from_db()
    return row


def _set_status(auth, model, row, status, expected_version, entity_type):
    _check_version(row, expected_version)
    if status == row.status:
        raise ConfigurationConflict("no_change")
    if status not in _STATUS_TRANSITIONS[row.status]:
        raise ConfigurationConflict("invalid_transition")
    before = row.status
    _bump(model, row, status=status)
    audit(auth, f"academic.{entity_type}.status", entity_type, row.pk, {"status": before, "version": expected_version},
          {"status": status, "version": row.version})
    return row


# ---- Courses (academic.courses.manage) --------------------------------------------------------

def course_in_use(course):
    return (CurriculumVersion.objects.using(DB).filter(course=course).exclude(status=CurriculumStatus.DRAFT).exists()
            or SubjectOffering.objects.using(DB).filter(section__course=course).exists())


def course_payload(course):
    references = {"curricula": CurriculumVersion.objects.using(DB).filter(course=course).count(),
                  "sections": Section.objects.using(DB).filter(course=course).count(),
                  "offerings": SubjectOffering.objects.using(DB).filter(section__course=course).count()}
    return {"course_id": course.pk, "code": course.code, "name": course.name, "status": course.status,
            "version": course.version, "in_use": course_in_use(course), "references": references,
            "created_at": _iso(course.created_at), "updated_at": _iso(course.updated_at)}


def list_courses(*, actor, q=None, status=None, page=1):
    authorize_read(actor, "courses")
    q, page = parse_search(q), parse_page(page)
    qs = Course.objects.using(DB).order_by("code", "course_id")
    if status is not None:
        qs = qs.filter(status=parse_status(status))
    if q:
        qs = qs.filter(Q(code__istartswith=q) | Q(name__icontains=q))
    rows, has_next = _page(qs, page)
    return {"results": [course_payload(c) for c in rows], "page": page, "page_size": PAGE_SIZE, "has_next": has_next}


def create_course(*, actor, code, name):
    code, name = normalize_code(code, "code"), clean_text(name, "name", 150)

    def apply(auth):
        if Course.objects.using(DB).filter(code=code).exists():
            raise ConfigurationConflict("code_exists")
        course = Course.objects.using(DB).create(code=code, name=name, created_by=auth.account)
        audit(auth, "academic.course.create", "course", course.pk, None, {"code": code, "name": name})
        return course.pk
    return course_payload(Course.objects.using(DB).get(pk=write(actor, "courses", apply)))


def update_course(*, actor, course_id, code, name, expected_version):
    course_id, expected_version = parse_id(course_id, "course_id"), parse_version(expected_version)
    code, name = normalize_code(code, "code"), clean_text(name, "name", 150)

    def apply(auth):
        course = _locked(Course, course_id)
        _check_version(course, expected_version)
        if (course.code, course.name) == (code, name):
            raise ConfigurationConflict("no_change")
        if code != course.code:
            if course_in_use(course):
                raise ConfigurationConflict("in_use")  # historical records keep their course code
            if Course.objects.using(DB).filter(code=code).exclude(pk=course.pk).exists():
                raise ConfigurationConflict("code_exists")
        before = {"code": course.code, "name": course.name, "version": course.version}
        _bump(Course, course, code=code, name=name)
        audit(auth, "academic.course.update", "course", course.pk, before,
              {"code": code, "name": name, "version": course.version})
        return course.pk
    return course_payload(Course.objects.using(DB).get(pk=write(actor, "courses", apply)))


def set_course_status(*, actor, course_id, status, expected_version):
    course_id, status, expected_version = parse_id(course_id, "course_id"), parse_status(status), parse_version(expected_version)

    def apply(auth):
        return _set_status(auth, Course, _locked(Course, course_id), status, expected_version, "course").pk
    return course_payload(Course.objects.using(DB).get(pk=write(actor, "courses", apply)))


# ---- Subjects (clearance.subjects.manage) -----------------------------------------------------

def subject_in_use(subject):
    return (CurriculumSubject.objects.using(DB).filter(subject=subject).exists()
            or SubjectOffering.objects.using(DB).filter(subject=subject).exists())


def subject_payload(subject):
    references = {"curriculum_entries": CurriculumSubject.objects.using(DB).filter(subject=subject).count(),
                  "offerings": SubjectOffering.objects.using(DB).filter(subject=subject).count()}
    return {"subject_id": subject.pk, "code": subject.code, "title": subject.title,
            "classification": subject.classification, "lecture_units": _units(subject.lecture_units),
            "lab_units": _units(subject.lab_units), "status": subject.status, "version": subject.version,
            "in_use": references["curriculum_entries"] > 0 or references["offerings"] > 0, "references": references,
            "created_at": _iso(subject.created_at), "updated_at": _iso(subject.updated_at)}


def list_subjects(*, actor, q=None, status=None, page=1):
    authorize_read(actor, "subjects")
    q, page = parse_search(q), parse_page(page)
    qs = Subject.objects.using(DB).order_by("code", "subject_id")
    if status is not None:
        qs = qs.filter(status=parse_status(status))
    if q:
        qs = qs.filter(Q(code__istartswith=q) | Q(title__icontains=q))
    rows, has_next = _page(qs, page)
    return {"results": [subject_payload(s) for s in rows], "page": page, "page_size": PAGE_SIZE, "has_next": has_next}


def _subject_fields(code, title, classification, lecture_units, lab_units):
    return (normalize_code(code, "code"), clean_text(title, "title", 200),
            clean_text(classification, "classification", 60, required=False),
            parse_units(lecture_units, "lecture_units"), parse_units(lab_units, "lab_units"))


def create_subject(*, actor, code, title, classification=None, lecture_units=None, lab_units=None):
    code, title, classification, lecture, lab = _subject_fields(code, title, classification, lecture_units, lab_units)

    def apply(auth):
        if Subject.objects.using(DB).filter(code=code).exists():
            raise ConfigurationConflict("code_exists")
        subject = Subject.objects.using(DB).create(code=code, title=title, classification=classification,
                                                   lecture_units=lecture, lab_units=lab, created_by=auth.account)
        audit(auth, "academic.subject.create", "subject", subject.pk, None,
              {"code": code, "title": title, "classification": classification,
               "lecture_units": _units(lecture), "lab_units": _units(lab)})
        return subject.pk
    return subject_payload(Subject.objects.using(DB).get(pk=write(actor, "subjects", apply)))


def update_subject(*, actor, subject_id, code, title, classification=None, lecture_units=None, lab_units=None,
                   expected_version):
    subject_id, expected_version = parse_id(subject_id, "subject_id"), parse_version(expected_version)
    code, title, classification, lecture, lab = _subject_fields(code, title, classification, lecture_units, lab_units)

    def apply(auth):
        subject = _locked(Subject, subject_id)
        _check_version(subject, expected_version)
        current = (subject.code, subject.title, subject.classification, subject.lecture_units, subject.lab_units)
        if current == (code, title, classification, lecture, lab):
            raise ConfigurationConflict("no_change")
        # Version-safe references: a referenced subject keeps its code, title and units.
        if subject_in_use(subject) and current[:2] + current[3:] != (code, title, lecture, lab):
            raise ConfigurationConflict("in_use")
        if code != subject.code and Subject.objects.using(DB).filter(code=code).exclude(pk=subject.pk).exists():
            raise ConfigurationConflict("code_exists")
        before = {"code": subject.code, "title": subject.title, "classification": subject.classification,
                  "lecture_units": _units(subject.lecture_units), "lab_units": _units(subject.lab_units),
                  "version": subject.version}
        _bump(Subject, subject, code=code, title=title, classification=classification, lecture_units=lecture,
              lab_units=lab)
        audit(auth, "academic.subject.update", "subject", subject.pk, before,
              {"code": code, "title": title, "classification": classification, "lecture_units": _units(lecture),
               "lab_units": _units(lab), "version": subject.version})
        return subject.pk
    return subject_payload(Subject.objects.using(DB).get(pk=write(actor, "subjects", apply)))


def set_subject_status(*, actor, subject_id, status, expected_version):
    subject_id, status, expected_version = parse_id(subject_id, "subject_id"), parse_status(status), parse_version(expected_version)

    def apply(auth):
        return _set_status(auth, Subject, _locked(Subject, subject_id), status, expected_version, "subject").pk
    return subject_payload(Subject.objects.using(DB).get(pk=write(actor, "subjects", apply)))


# ---- Sections (academic.sections.manage) ------------------------------------------------------

def section_payload(section):
    offerings = SubjectOffering.objects.using(DB).filter(section=section).count()
    return {"section_id": section.pk, "course": {"course_id": section.course_id, "code": section.course.code},
            "year_level": section.year_level, "name": section.name, "status": section.status,
            "version": section.version, "in_use": offerings > 0, "references": {"offerings": offerings},
            "created_at": _iso(section.created_at), "updated_at": _iso(section.updated_at)}


def list_sections(*, actor, course_id=None, year_level=None, status=None, page=1):
    authorize_read(actor, "sections")
    page = parse_page(page)
    qs = Section.objects.using(DB).select_related("course").order_by("course__code", "year_level", "name", "section_id")
    if course_id is not None:
        qs = qs.filter(course_id=parse_id(course_id, "course_id"))
    if year_level is not None:
        qs = qs.filter(year_level=parse_year_level(year_level))
    if status is not None:
        qs = qs.filter(status=parse_status(status))
    rows, has_next = _page(qs, page)
    return {"results": [section_payload(s) for s in rows], "page": page, "page_size": PAGE_SIZE, "has_next": has_next}


def create_section(*, actor, course_id, year_level, name):
    course_id, year_level = parse_id(course_id, "course_id"), parse_year_level(year_level)
    name = normalize_code(name, "name")

    def apply(auth):
        course = Course.objects.using(DB).select_for_update().filter(pk=course_id).first()
        if course is None:
            raise services.AcademicPeriodNotFound()
        if course.status != DefinitionStatus.ACTIVE:
            raise ConfigurationConflict("not_available")
        if Section.objects.using(DB).filter(course=course, year_level=year_level, name=name).exists():
            raise ConfigurationConflict("section_exists")
        section = Section.objects.using(DB).create(course=course, year_level=year_level, name=name,
                                                   created_by=auth.account)
        audit(auth, "academic.section.create", "section", section.pk, None,
              {"course_id": course.pk, "year_level": year_level, "name": name})
        return section.pk
    return section_payload(Section.objects.using(DB).select_related("course").get(pk=write(actor, "sections", apply)))


def update_section(*, actor, section_id, year_level, name, expected_version):
    section_id, expected_version = parse_id(section_id, "section_id"), parse_version(expected_version)
    year_level, name = parse_year_level(year_level), normalize_code(name, "name")

    def apply(auth):
        section = _locked(Section, section_id)
        _check_version(section, expected_version)
        if (section.year_level, section.name) == (year_level, name):
            raise ConfigurationConflict("no_change")
        if SubjectOffering.objects.using(DB).filter(section=section).exists():
            raise ConfigurationConflict("in_use")  # never silently moves historical offerings
        if Section.objects.using(DB).filter(course_id=section.course_id, year_level=year_level, name=name).exclude(
                pk=section.pk).exists():
            raise ConfigurationConflict("section_exists")
        before = {"year_level": section.year_level, "name": section.name, "version": section.version}
        _bump(Section, section, year_level=year_level, name=name)
        audit(auth, "academic.section.update", "section", section.pk, before,
              {"year_level": year_level, "name": name, "version": section.version})
        return section.pk
    return section_payload(Section.objects.using(DB).select_related("course").get(pk=write(actor, "sections", apply)))


def set_section_status(*, actor, section_id, status, expected_version):
    section_id, status, expected_version = parse_id(section_id, "section_id"), parse_status(status), parse_version(expected_version)

    def apply(auth):
        return _set_status(auth, Section, _locked(Section, section_id), status, expected_version, "section").pk
    return section_payload(Section.objects.using(DB).select_related("course").get(pk=write(actor, "sections", apply)))


# ---- Curriculum versions (PROPOSED academic.courses.manage; separate write switch) -------------

def entry_payload(entry):
    subject = entry.subject
    return {"curriculum_subject_id": entry.pk, "year_level": entry.year_level, "term": term_key(entry.term),
            "subject": {"subject_id": subject.pk, "code": subject.code, "title": subject.title,
                        "lecture_units": _units(subject.lecture_units), "lab_units": _units(subject.lab_units),
                        "status": subject.status}}


def curriculum_payload(curriculum, entries=False):
    offerings = SubjectOffering.objects.using(DB).filter(curriculum_subject__curriculum=curriculum).count()
    payload = {"curriculum_id": curriculum.pk,
               "course": {"course_id": curriculum.course_id, "code": curriculum.course.code,
                          "name": curriculum.course.name},
               "label": curriculum.label, "effective_start_year": curriculum.effective_start_year,
               "status": curriculum.status, "version": curriculum.version,
               "entry_count": CurriculumSubject.objects.using(DB).filter(curriculum=curriculum).count(),
               "offering_count": offerings, "can_edit": curriculum.status == CurriculumStatus.DRAFT,
               "published_at": _iso(curriculum.published_at), "superseded_at": _iso(curriculum.superseded_at),
               "created_at": _iso(curriculum.created_at), "updated_at": _iso(curriculum.updated_at)}
    if entries:
        rows = (CurriculumSubject.objects.using(DB).filter(curriculum=curriculum).select_related("subject")
                .order_by("year_level", "term", "subject__code"))
        payload["entries"] = [entry_payload(e) for e in rows]
    return payload


def _load_curriculum(pk):
    return CurriculumVersion.objects.using(DB).select_related("course").get(pk=pk)


def list_curricula(*, actor, course_id=None, status=None, page=1):
    authorize_read(actor, "curricula")
    page = parse_page(page)
    qs = CurriculumVersion.objects.using(DB).select_related("course").order_by("course__code", "-curriculum_id")
    if course_id is not None:
        qs = qs.filter(course_id=parse_id(course_id, "course_id"))
    if status is not None:
        if type(status) is not str or status not in CurriculumStatus.values:
            _invalid("status")
        qs = qs.filter(status=status)
    rows, has_next = _page(qs, page)
    return {"results": [curriculum_payload(c) for c in rows], "page": page, "page_size": PAGE_SIZE,
            "has_next": has_next, "features": feature_flags()}


def get_curriculum(*, actor, curriculum_id):
    authorize_read(actor, "curricula")
    curriculum = CurriculumVersion.objects.using(DB).select_related("course").filter(
        pk=parse_id(curriculum_id, "curriculum_id")).first()
    if curriculum is None:
        raise services.AcademicPeriodNotFound()
    return {**curriculum_payload(curriculum, entries=True), "features": feature_flags()}


def _parse_start_year(raw):
    if raw is None:
        return None
    if type(raw) is not int or not MIN_START_YEAR <= raw <= MAX_START_YEAR:
        _invalid("effective_start_year")
    return raw


def create_curriculum(*, actor, course_id, label, effective_start_year=None):
    course_id = parse_id(course_id, "course_id")
    label, start = clean_text(label, "label", 40), _parse_start_year(effective_start_year)

    def apply(auth):
        course = Course.objects.using(DB).select_for_update().filter(pk=course_id).first()
        if course is None:
            raise services.AcademicPeriodNotFound()
        if course.status != DefinitionStatus.ACTIVE:
            raise ConfigurationConflict("not_available")
        if CurriculumVersion.objects.using(DB).filter(course=course, label__iexact=label).exists():
            raise ConfigurationConflict("label_exists")
        curriculum = CurriculumVersion.objects.using(DB).create(course=course, label=label, effective_start_year=start,
                                                                created_by=auth.account)
        audit(auth, "academic.curriculum.create", "curriculum", curriculum.pk, None,
              {"course_id": course.pk, "label": label, "effective_start_year": start, "status": "Draft"})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def _draft(curriculum_id, expected_version):
    curriculum = _locked(CurriculumVersion, curriculum_id)
    _check_version(curriculum, expected_version)
    if curriculum.status != CurriculumStatus.DRAFT:
        raise ConfigurationConflict("not_draft")  # Published/Superseded definitions are never edited silently
    return curriculum


def update_curriculum(*, actor, curriculum_id, label, effective_start_year, expected_version):
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)
    label, start = clean_text(label, "label", 40), _parse_start_year(effective_start_year)

    def apply(auth):
        curriculum = _draft(curriculum_id, expected_version)
        if (curriculum.label, curriculum.effective_start_year) == (label, start):
            raise ConfigurationConflict("no_change")
        if CurriculumVersion.objects.using(DB).filter(course_id=curriculum.course_id, label__iexact=label).exclude(
                pk=curriculum.pk).exists():
            raise ConfigurationConflict("label_exists")
        before = {"label": curriculum.label, "effective_start_year": curriculum.effective_start_year,
                  "version": curriculum.version}
        _bump(CurriculumVersion, curriculum, label=label, effective_start_year=start)
        audit(auth, "academic.curriculum.update", "curriculum", curriculum.pk, before,
              {"label": label, "effective_start_year": start, "version": curriculum.version})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def add_curriculum_entry(*, actor, curriculum_id, subject_id, year_level, term, expected_version):
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)
    subject_id, year_level, term = parse_id(subject_id, "subject_id"), parse_year_level(year_level), parse_term(term)

    def apply(auth):
        curriculum = _draft(curriculum_id, expected_version)
        subject = Subject.objects.using(DB).select_for_update().filter(pk=subject_id).first()
        if subject is None:
            raise services.AcademicPeriodNotFound()
        if subject.status != DefinitionStatus.ACTIVE:
            raise ConfigurationConflict("not_available")
        if CurriculumSubject.objects.using(DB).filter(curriculum=curriculum, subject=subject).exists():
            raise ConfigurationConflict("entry_exists")
        entry = CurriculumSubject.objects.using(DB).create(curriculum=curriculum, subject=subject,
                                                           year_level=year_level, term=term)
        _bump(CurriculumVersion, curriculum)
        audit(auth, "academic.curriculum.entry.add", "curriculum", curriculum.pk, None,
              {"curriculum_subject_id": entry.pk, "subject_id": subject.pk, "year_level": year_level,
               "term": term_key(term), "version": curriculum.version})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def remove_curriculum_entry(*, actor, curriculum_id, curriculum_subject_id, expected_version):
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)
    entry_id = parse_id(curriculum_subject_id, "curriculum_subject_id")

    def apply(auth):
        curriculum = _draft(curriculum_id, expected_version)
        entry = CurriculumSubject.objects.using(DB).select_for_update().filter(pk=entry_id, curriculum=curriculum).first()
        if entry is None:
            raise services.AcademicPeriodNotFound()
        before = {"curriculum_subject_id": entry.pk, "subject_id": entry.subject_id, "year_level": entry.year_level,
                  "term": term_key(entry.term), "version": curriculum.version}
        entry.delete(using=DB)  # Draft entries are never referenced by offerings (Published only)
        _bump(CurriculumVersion, curriculum)
        audit(auth, "academic.curriculum.entry.remove", "curriculum", curriculum.pk, before,
              {"version": curriculum.version})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def _confirm(confirmed):
    if confirmed is not True:
        _invalid("confirmed", "required")


def publish_curriculum(*, actor, curriculum_id, expected_version, confirmed):
    """Explicit, audited publication. The definition is immutable afterwards; nothing is auto-superseded
    and no Student record is changed (existing student-confirmed records keep their own version)."""
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)
    _confirm(confirmed)

    def apply(auth):
        curriculum = _draft(curriculum_id, expected_version)
        course = Course.objects.using(DB).select_for_update().get(pk=curriculum.course_id)
        if course.status != DefinitionStatus.ACTIVE:
            raise ConfigurationConflict("not_available")
        entries = CurriculumSubject.objects.using(DB).filter(curriculum=curriculum)
        if not entries.exists():
            raise ConfigurationConflict("curriculum_empty")
        if entries.exclude(subject__status=DefinitionStatus.ACTIVE).exists():
            raise ConfigurationConflict("not_available")
        _bump(CurriculumVersion, curriculum, status=CurriculumStatus.PUBLISHED, published_at=CurrentTimestamp())
        audit(auth, "academic.curriculum.publish", "curriculum", curriculum.pk,
              {"status": "Draft", "version": expected_version},
              {"status": "Published", "version": curriculum.version, "entry_count": entries.count()})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def supersede_curriculum(*, actor, curriculum_id, expected_version, confirmed):
    """Published -> Superseded: preserved for history, no new offerings. Existing offerings stay."""
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)
    _confirm(confirmed)

    def apply(auth):
        curriculum = _locked(CurriculumVersion, curriculum_id)
        _check_version(curriculum, expected_version)
        if curriculum.status != CurriculumStatus.PUBLISHED:
            raise ConfigurationConflict("not_published")
        _bump(CurriculumVersion, curriculum, status=CurriculumStatus.SUPERSEDED, superseded_at=CurrentTimestamp())
        audit(auth, "academic.curriculum.supersede", "curriculum", curriculum.pk,
              {"status": "Published", "version": expected_version},
              {"status": "Superseded", "version": curriculum.version})
        return curriculum.pk
    return curriculum_payload(_load_curriculum(write(actor, "curricula", apply)), entries=True)


def delete_draft_curriculum(*, actor, curriculum_id, expected_version):
    curriculum_id, expected_version = parse_id(curriculum_id, "curriculum_id"), parse_version(expected_version)

    def apply(auth):
        curriculum = _draft(curriculum_id, expected_version)
        entries = list(CurriculumSubject.objects.using(DB).filter(curriculum=curriculum).values_list("subject_id", flat=True))
        snapshot = {"course_id": curriculum.course_id, "label": curriculum.label, "status": "Draft",
                    "subject_ids": entries[:100], "version": curriculum.version}
        CurriculumSubject.objects.using(DB).filter(curriculum=curriculum).delete()
        curriculum.delete(using=DB)
        audit(auth, "academic.curriculum.delete_draft", "curriculum", curriculum_id, snapshot, None)
        return curriculum_id
    return {"deleted": True, "curriculum_id": write(actor, "curricula", apply)}


# ---- Semester subject offerings (PROPOSED academic.periods.manage; separate write switch) ------

OPEN_FOR_OFFERINGS = (SemesterStatus.DRAFT, SemesterStatus.ACTIVE)


def semester_ref(semester):
    return {"semester_id": semester.pk, "term": term_key(semester.term), "label": semester.label,
            "status": semester.status, "school_year_id": semester.school_year_id,
            "school_year_label": semester.school_year.label}


def list_semesters(*, actor):
    """Lookup for offerings: newest school years first (bounded)."""
    authorize_read(actor, "offerings")
    rows = (Semester.objects.using(DB).select_related("school_year")
            .order_by("-school_year__start_year", "term")[:40])
    return {"results": [semester_ref(s) for s in rows], "features": feature_flags()}


def valid_offerings(semester_id):
    """Offerings that are valid for THIS semester: every relationship re-validated (activation evidence)."""
    return (SubjectOffering.objects.using(DB)
            .filter(semester_id=semester_id, semester__term=F("curriculum_subject__term"),
                    subject_id=F("curriculum_subject__subject_id"),
                    section__course_id=F("curriculum_subject__curriculum__course_id"),
                    section__year_level=F("curriculum_subject__year_level"),
                    curriculum_subject__curriculum__status__in=(CurriculumStatus.PUBLISHED, CurriculumStatus.SUPERSEDED),
                    subject__status=DefinitionStatus.ACTIVE, section__status=DefinitionStatus.ACTIVE))


def offering_payload(offering, assignment=None, eligible=None):
    from . import teaching
    if assignment is None:
        assignment = teaching.current_assignment(offering)
    current = None
    if assignment is not None:
        current = teaching.assignment_payload(assignment, eligible)
    removable = (offering.semester.status == SemesterStatus.DRAFT
                 and not offering.teaching_assignments.using(DB).exists())
    return {"offering_id": offering.pk, "semester": semester_ref(offering.semester),
            "section": {"section_id": offering.section_id, "name": offering.section.name,
                        "year_level": offering.section.year_level, "course_code": offering.section.course.code},
            "subject": {"subject_id": offering.subject_id, "code": offering.subject.code,
                        "title": offering.subject.title},
            "curriculum": {"curriculum_id": offering.curriculum_subject.curriculum_id,
                           "label": offering.curriculum_subject.curriculum.label},
            "assignment": current,
            # WF-05.05 contract: a Student may confirm this subject only when this is true.
            "ready_for_confirmation": bool(current and current["eligible"]),
            "can_remove": removable, "created_at": _iso(offering.created_at)}


def _offerings_qs():
    return SubjectOffering.objects.using(DB).select_related(
        "semester__school_year", "section__course", "subject", "curriculum_subject__curriculum")


def list_offerings(*, actor, semester_id, page=1):
    authorize_read(actor, "offerings")
    semester_id, page = parse_id(semester_id, "semester_id"), parse_page(page)
    semester = Semester.objects.using(DB).select_related("school_year").filter(pk=semester_id).first()
    if semester is None:
        raise services.AcademicPeriodNotFound()
    qs = _offerings_qs().filter(semester=semester).order_by("section__course__code", "section__year_level",
                                                               "section__name", "subject__code", "offering_id")
    rows, has_next = _page(qs, page)
    return {"semester": semester_ref(semester), "results": [offering_payload(o) for o in rows],
            "valid_offering_count": valid_offerings(semester.pk).count(), "page": page, "page_size": PAGE_SIZE,
            "has_next": has_next, "features": feature_flags()}


def _candidate_entries(semester, section):
    return (CurriculumSubject.objects.using(DB).select_related("subject", "curriculum")
            .filter(curriculum__course_id=section.course_id, curriculum__status=CurriculumStatus.PUBLISHED,
                    year_level=section.year_level, term=semester.term, subject__status=DefinitionStatus.ACTIVE)
            .exclude(subject_id__in=SubjectOffering.objects.using(DB).filter(semester=semester, section=section)
                     .values("subject_id"))
            .order_by("subject__code", "curriculum_id"))


def offering_candidates(*, actor, semester_id, section_id):
    authorize_read(actor, "offerings")
    semester = Semester.objects.using(DB).select_related("school_year").filter(pk=parse_id(semester_id, "semester_id")).first()
    section = Section.objects.using(DB).select_related("course").filter(pk=parse_id(section_id, "section_id")).first()
    if semester is None or section is None:
        raise services.AcademicPeriodNotFound()
    return {"semester": semester_ref(semester), "section_id": section.pk,
            "results": [{"curriculum_subject_id": e.pk, "curriculum": {"curriculum_id": e.curriculum_id,
                                                                       "label": e.curriculum.label},
                         "subject": {"subject_id": e.subject_id, "code": e.subject.code, "title": e.subject.title}}
                        for e in _candidate_entries(semester, section)[:100]]}


def create_offering(*, actor, semester_id, section_id, curriculum_subject_id):
    semester_id, section_id = parse_id(semester_id, "semester_id"), parse_id(section_id, "section_id")
    entry_id = parse_id(curriculum_subject_id, "curriculum_subject_id")

    def apply(auth):
        semester = Semester.objects.using(DB).select_for_update().filter(pk=semester_id).first()
        section = Section.objects.using(DB).select_for_update().filter(pk=section_id).first()
        entry = (CurriculumSubject.objects.using(DB).select_related("curriculum", "subject")
                 .filter(pk=entry_id).first())
        if semester is None or section is None or entry is None:
            raise services.AcademicPeriodNotFound()
        if semester.status not in OPEN_FOR_OFFERINGS:
            raise ConfigurationConflict("period_closed")  # historical offerings are never added to
        if section.status != DefinitionStatus.ACTIVE or entry.subject.status != DefinitionStatus.ACTIVE:
            raise ConfigurationConflict("not_available")
        if entry.curriculum.status != CurriculumStatus.PUBLISHED:
            raise ConfigurationConflict("not_published")
        if (entry.curriculum.course_id != section.course_id or entry.year_level != section.year_level
                or entry.term != semester.term):
            raise ConfigurationConflict("reference_mismatch")  # the plan must fit this section and semester
        if SubjectOffering.objects.using(DB).filter(semester=semester, section=section, subject_id=entry.subject_id).exists():
            raise ConfigurationConflict("offering_exists")
        offering = SubjectOffering.objects.using(DB).create(semester=semester, section=section, curriculum_subject=entry,
                                                            subject_id=entry.subject_id, created_by=auth.account)
        audit(auth, "academic.offering.create", "offering", offering.pk, None,
              {"semester_id": semester.pk, "section_id": section.pk, "curriculum_subject_id": entry.pk,
               "subject_id": entry.subject_id, "semester_status": semester.status})
        return offering.pk
    return offering_payload(_offerings_qs().get(pk=write(actor, "offerings", apply)))


def remove_offering(*, actor, offering_id):
    offering_id = parse_id(offering_id, "offering_id")

    def apply(auth):
        offering = SubjectOffering.objects.using(DB).select_for_update().filter(pk=offering_id).first()
        if offering is None:
            raise services.AcademicPeriodNotFound()
        semester = Semester.objects.using(DB).select_for_update().get(pk=offering.semester_id)
        if semester.status != SemesterStatus.DRAFT:
            raise ConfigurationConflict("period_not_draft")
        if offering.teaching_assignments.using(DB).exists():
            raise ConfigurationConflict("offering_in_use")  # assignment history is never destroyed
        snapshot = {"semester_id": offering.semester_id, "section_id": offering.section_id,
                    "curriculum_subject_id": offering.curriculum_subject_id, "subject_id": offering.subject_id}
        offering.delete(using=DB)
        audit(auth, "academic.offering.remove", "offering", offering_id, snapshot, None)
        return offering_id
    return {"deleted": True, "offering_id": write(actor, "offerings", apply)}


def configuration_history(*, actor, area_key, entity_type, entity_id):
    """Minimized audit history of one configuration record (fixed fields; no account identifiers)."""
    auth = authorize_read(actor, area_key)
    rows = (AcademicConfigurationAuditLog.objects.using(DB)
            .filter(entity_type=entity_type, entity_id=parse_id(entity_id, "entity_id"))
            .order_by("-academic_configuration_audit_log_id")
            .values("action", "actor_account_id", "old_value", "new_value", "reason", "created_at")[:50])
    return {"results": [{"event": r["action"], "occurred_at": _iso(r["created_at"]),
                         "actor": "You" if r["actor_account_id"] == auth.account.pk else "An administrator",
                         "before": r["old_value"], "after": r["new_value"]} for r in rows]}
