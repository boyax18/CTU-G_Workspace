"""Academic configuration API under ``api/v1/academic/config/`` (all default-off).

Reuses the academic API conventions (session, explicit CSRF on POST, bounded duplicate-key-
refusing JSON, no-store, fixed error codes). Every view answers 503 unless
WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED is exactly True; curriculum, offering and teaching
writes additionally answer 503 ``feature_disabled`` unless their own switch is on. Authorization is
decided only by apps.academic.configuration / teaching (exact code per area, HDAC, locked re-check).
Not a RegistrationReviewAPI subclass: the WF-02 release safeguard is unaffected.
"""

from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.session_auth import WorkspaceSessionAPI

from . import configuration as cfg
from . import services, teaching
from .api import AcademicPeriodAPI, AcademicPeriodsUnavailable, _AccountThrottle, _error

FIELD_MESSAGES = {
    "code": "Use 1 to 20 letters, digits, spaces, dots, hyphens or slashes.",
    "name": "Enter a name of up to 150 characters.",
    "title": "Enter a title of up to 200 characters.",
    "classification": "Use up to 60 characters.",
    "lecture_units": "Enter units from 0 to 30 in steps of 0.1, or leave blank.",
    "lab_units": "Enter units from 0 to 30 in steps of 0.1, or leave blank.",
    "label": "Enter a label of up to 40 characters.",
    "effective_start_year": "Enter a year from 2000 to 2100, or leave blank.",
    "year_level": "Choose a year level from 1 to 6.",
    "term": "Choose the First or Second semester.",
    "status": "Choose a valid status.",
    "expected_version": "Reload and try again.",
    "confirmed": "Confirm the change to continue.",
    "reason_code": "Choose a reason.",
    "q": "Use up to 50 plain characters.",
    "page": "Invalid page.",
}
for _ref in ("course_id", "subject_id", "section_id", "semester_id", "curriculum_id", "curriculum_subject_id",
             "offering_id", "instructor_account_id", "expected_assignment_id"):
    FIELD_MESSAGES[_ref] = "Choose a valid item."
REQUIRED = {"name": "Enter a name.", "title": "Enter a title.", "label": "Enter a label.",
            "confirmed": "Confirm the change to continue."}
CONFLICT_MESSAGES = {
    "code_exists": "This code is already used.",
    "label_exists": "This course already has a curriculum with that label.",
    "section_exists": "This section already exists for the course and year level.",
    "entry_exists": "This subject is already in the curriculum.",
    "offering_exists": "This subject is already offered to the section this semester.",
    "stale_version": "This record was changed by someone else. Reload and try again.",
    "in_use": "This record is already used by curricula or offerings, so this change is not allowed.",
    "invalid_transition": "This status change is not allowed.",
    "not_available": "An inactive or retired definition cannot be used here.",
    "not_draft": "Only a Draft curriculum can be changed.",
    "not_published": "Only a Published curriculum can be used for this.",
    "curriculum_empty": "Add at least one subject before publishing.",
    "period_closed": "Closed and Archived semesters cannot be changed.",
    "period_not_draft": "Offerings can be removed only while the semester is Draft.",
    "reference_mismatch": "The curriculum subject does not match the section's course, year level or the semester.",
    "offering_in_use": "This offering has teaching assignment history and cannot be removed.",
    "assignment_changed": "The instructor assignment changed. Reload and try again.",
    "no_change": "Nothing changed.",
    "instructor_ineligible": "This account is not an eligible Instructor.",
    "constraint_conflict": "The change conflicts with existing records. Reload and try again.",
}


class ConfigReadThrottle(_AccountThrottle):
    scope = "workspace_academic_config_read"
    rate = "120/min"


class ConfigWriteThrottle(_AccountThrottle):
    scope = "workspace_academic_config_write"
    rate = "60/min"


class ConfigurationAPI(AcademicPeriodAPI):
    def initial(self, request, *args, **kwargs):
        if not cfg.configuration_enabled():
            raise AcademicPeriodsUnavailable()
        WorkspaceSessionAPI.initial(self, request, *args, **kwargs)  # skip the period gate, keep CSRF/throttles

    def get_throttles(self):
        return [ConfigReadThrottle()] if self.request.method in ("GET", "HEAD", "OPTIONS") else [ConfigWriteThrottle()]

    @staticmethod
    def respond(payload, status=200):
        return Response(payload, status=status)

    def handle_exception(self, exc):
        if isinstance(exc, cfg.ConfigurationConflict):
            return _error("configuration_conflict", CONFLICT_MESSAGES[exc.reason], 409, reason=exc.reason)
        if isinstance(exc, services.AcademicPeriodInvalid):
            fields = {name: [REQUIRED.get(name) if code == "required" and name in REQUIRED else FIELD_MESSAGES[name]]
                      for name, code in exc.fields.items() if name in FIELD_MESSAGES}
            return _error("invalid_request", "Check the submitted details.", 400, fields=fields)
        if isinstance(exc, services.AcademicPeriodFeatureDisabled):
            return _error("feature_disabled", "This academic-configuration change is not enabled.", 503)
        if isinstance(exc, services.AcademicPeriodUnavailable) or isinstance(exc, AcademicPeriodsUnavailable):
            return _error("academic_configuration_unavailable", "Academic configuration is unavailable.", 503)
        if isinstance(exc, services.AcademicPeriodNotFound):
            return _error("not_found", "The requested record is unavailable.", 404)
        return super().handle_exception(exc)

    @staticmethod
    def query(request, allowed, ints=()):
        params = request.query_params
        if set(params) - set(allowed) or any(len(params.getlist(k)) > 1 for k in params):
            raise exceptions.ValidationError("Unsupported query fields.")
        values = {}
        for key in allowed:
            if key not in params:
                continue
            raw = params[key]
            if key in ints:
                if not raw.isascii() or not raw.isdecimal() or len(raw) > 10:
                    raise services.AcademicPeriodInvalid({key: "invalid"})
                values[key] = int(raw)
            else:
                values[key] = raw
        return values


def _view(name, methods, get=None, post=None, fields=(), required=None, query=(), ints=()):
    """Build a small view class: ``get(actor, **url_kwargs, **query)`` / ``post(actor, data, **url_kwargs)``."""
    fields, required = frozenset(fields), frozenset(fields if required is None else required)

    def do_get(self, request, **kwargs):
        actor = self.actor(request)
        return self.respond(get(actor, **kwargs, **self.query(request, query, ints)))

    def do_post(self, request, **kwargs):
        actor = self.actor(request)
        data = self.body(request, fields, required)
        return self.respond(post(actor, data, **kwargs), status=201 if name.endswith("Collection") else 200)

    attrs = {"http_method_names": methods, "__module__": __name__}
    if get is not None:
        attrs["get"] = do_get
    if post is not None:
        attrs["post"] = do_post
    return type(name, (ConfigurationAPI,), attrs)


READ = ["get", "head", "options"]
WRITE = ["post", "options"]
BOTH = ["get", "post", "head", "options"]
STATUS_FIELDS = ("status", "expected_version")

CourseCollection = _view(
    "CourseCollection", BOTH,
    get=lambda a, **q: cfg.list_courses(actor=a, **q), query=("q", "status", "page"), ints=("page",),
    post=lambda a, d: cfg.create_course(actor=a, code=d["code"], name=d["name"]), fields=("code", "name"))
CourseDetail = _view(
    "CourseDetail", WRITE, fields=("code", "name", "expected_version"),
    post=lambda a, d, course_id: cfg.update_course(actor=a, course_id=course_id, code=d["code"], name=d["name"],
                                                   expected_version=d["expected_version"]))
CourseStatus = _view(
    "CourseStatus", WRITE, fields=STATUS_FIELDS,
    post=lambda a, d, course_id: cfg.set_course_status(actor=a, course_id=course_id, status=d["status"],
                                                       expected_version=d["expected_version"]))

SUBJECT_FIELDS = ("code", "title", "classification", "lecture_units", "lab_units")
SubjectCollection = _view(
    "SubjectCollection", BOTH,
    get=lambda a, **q: cfg.list_subjects(actor=a, **q), query=("q", "status", "page"), ints=("page",),
    fields=SUBJECT_FIELDS, required=("code", "title"),
    post=lambda a, d: cfg.create_subject(actor=a, code=d["code"], title=d["title"],
                                         classification=d.get("classification"),
                                         lecture_units=d.get("lecture_units"), lab_units=d.get("lab_units")))
SubjectDetail = _view(
    "SubjectDetail", WRITE, fields=SUBJECT_FIELDS + ("expected_version",), required=("code", "title", "expected_version"),
    post=lambda a, d, subject_id: cfg.update_subject(
        actor=a, subject_id=subject_id, code=d["code"], title=d["title"], classification=d.get("classification"),
        lecture_units=d.get("lecture_units"), lab_units=d.get("lab_units"), expected_version=d["expected_version"]))
SubjectStatus = _view(
    "SubjectStatus", WRITE, fields=STATUS_FIELDS,
    post=lambda a, d, subject_id: cfg.set_subject_status(actor=a, subject_id=subject_id, status=d["status"],
                                                         expected_version=d["expected_version"]))

SectionCollection = _view(
    "SectionCollection", BOTH,
    get=lambda a, **q: cfg.list_sections(actor=a, **q), query=("course_id", "year_level", "status", "page"),
    ints=("course_id", "year_level", "page"), fields=("course_id", "year_level", "name"),
    post=lambda a, d: cfg.create_section(actor=a, course_id=d["course_id"], year_level=d["year_level"], name=d["name"]))
SectionDetail = _view(
    "SectionDetail", WRITE, fields=("year_level", "name", "expected_version"),
    post=lambda a, d, section_id: cfg.update_section(actor=a, section_id=section_id, year_level=d["year_level"],
                                                     name=d["name"], expected_version=d["expected_version"]))
SectionStatus = _view(
    "SectionStatus", WRITE, fields=STATUS_FIELDS,
    post=lambda a, d, section_id: cfg.set_section_status(actor=a, section_id=section_id, status=d["status"],
                                                         expected_version=d["expected_version"]))

CurriculumCollection = _view(
    "CurriculumCollection", BOTH,
    get=lambda a, **q: cfg.list_curricula(actor=a, **q), query=("course_id", "status", "page"),
    ints=("course_id", "page"), fields=("course_id", "label", "effective_start_year"), required=("course_id", "label"),
    post=lambda a, d: cfg.create_curriculum(actor=a, course_id=d["course_id"], label=d["label"],
                                            effective_start_year=d.get("effective_start_year")))
CurriculumDetail = _view(
    "CurriculumDetail", BOTH, get=lambda a, curriculum_id: cfg.get_curriculum(actor=a, curriculum_id=curriculum_id),
    fields=("label", "effective_start_year", "expected_version"), required=("label", "expected_version"),
    post=lambda a, d, curriculum_id: cfg.update_curriculum(
        actor=a, curriculum_id=curriculum_id, label=d["label"], effective_start_year=d.get("effective_start_year"),
        expected_version=d["expected_version"]))
CurriculumEntries = _view(
    "CurriculumEntries", WRITE, fields=("subject_id", "year_level", "term", "expected_version"),
    post=lambda a, d, curriculum_id: cfg.add_curriculum_entry(
        actor=a, curriculum_id=curriculum_id, subject_id=d["subject_id"], year_level=d["year_level"], term=d["term"],
        expected_version=d["expected_version"]))
CurriculumEntryRemove = _view(
    "CurriculumEntryRemove", WRITE, fields=("expected_version",),
    post=lambda a, d, curriculum_id, entry_id: cfg.remove_curriculum_entry(
        actor=a, curriculum_id=curriculum_id, curriculum_subject_id=entry_id, expected_version=d["expected_version"]))
CurriculumPublish = _view(
    "CurriculumPublish", WRITE, fields=("expected_version", "confirmed"),
    post=lambda a, d, curriculum_id: cfg.publish_curriculum(
        actor=a, curriculum_id=curriculum_id, expected_version=d["expected_version"], confirmed=d["confirmed"]))
CurriculumSupersede = _view(
    "CurriculumSupersede", WRITE, fields=("expected_version", "confirmed"),
    post=lambda a, d, curriculum_id: cfg.supersede_curriculum(
        actor=a, curriculum_id=curriculum_id, expected_version=d["expected_version"], confirmed=d["confirmed"]))
CurriculumDelete = _view(
    "CurriculumDelete", WRITE, fields=("expected_version",),
    post=lambda a, d, curriculum_id: cfg.delete_draft_curriculum(
        actor=a, curriculum_id=curriculum_id, expected_version=d["expected_version"]))

SemesterLookup = _view("SemesterLookup", READ, get=lambda a: cfg.list_semesters(actor=a))
OfferingCollection = _view(
    "OfferingCollection", BOTH,
    get=lambda a, **q: cfg.list_offerings(actor=a, semester_id=q.get("semester_id"), page=q.get("page", 1)),
    query=("semester_id", "page"), ints=("semester_id", "page"),
    fields=("semester_id", "section_id", "curriculum_subject_id"),
    post=lambda a, d: cfg.create_offering(actor=a, semester_id=d["semester_id"], section_id=d["section_id"],
                                          curriculum_subject_id=d["curriculum_subject_id"]))
OfferingCandidates = _view(
    "OfferingCandidates", READ, query=("semester_id", "section_id"), ints=("semester_id", "section_id"),
    get=lambda a, **q: cfg.offering_candidates(actor=a, semester_id=q.get("semester_id"), section_id=q.get("section_id")))
OfferingRemove = _view(
    "OfferingRemove", WRITE, fields=(),
    post=lambda a, d, offering_id: cfg.remove_offering(actor=a, offering_id=offering_id))

InstructorLookup = _view("InstructorLookup", READ, query=("q",),
                         get=lambda a, **q: teaching.eligible_instructors(actor=a, q=q.get("q")))
OfferingInstructor = _view(
    "OfferingInstructor", WRITE, fields=("instructor_account_id", "expected_assignment_id"),
    post=lambda a, d, offering_id: teaching.assign_instructor(
        actor=a, offering_id=offering_id, instructor_account_id=d["instructor_account_id"],
        expected_assignment_id=d["expected_assignment_id"]))
OfferingInstructorEnd = _view(
    "OfferingInstructorEnd", WRITE, fields=("expected_assignment_id", "reason_code"),
    post=lambda a, d, offering_id: teaching.end_assignment(
        actor=a, offering_id=offering_id, expected_assignment_id=d["expected_assignment_id"],
        reason_code=d["reason_code"]))
OfferingInstructorHistory = _view(
    "OfferingInstructorHistory", READ, get=lambda a, offering_id: teaching.assignment_history(actor=a, offering_id=offering_id))

_HISTORY_AREAS = {"courses": ("courses", "course"), "subjects": ("subjects", "subject"),
                  "sections": ("sections", "section"), "curricula": ("curricula", "curriculum"),
                  "offerings": ("offerings", "offering")}


def _history(actor, kind, entity_id):
    if kind not in _HISTORY_AREAS:
        raise services.AcademicPeriodNotFound()
    area, entity = _HISTORY_AREAS[kind]
    return cfg.configuration_history(actor=actor, area_key=area, entity_type=entity, entity_id=entity_id)


RecordHistory = _view("RecordHistory", READ, get=lambda a, kind, entity_id: _history(a, kind, entity_id))
