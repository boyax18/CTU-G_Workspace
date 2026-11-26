"""Student Semester Onboarding and official-verification API (all default-off).

``api/v1/academic/onboarding/`` - the Student's own onboarding (WORKSPACE_STUDENT_ONBOARDING_ENABLED;
the finalization also needs WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED). No route accepts a
student identifier: every object is the signed-in Student's own.
``api/v1/academic/verification/`` - School Admin in-person verification records
(WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED) and the WF11-D14 historical participation correction
(WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED).

Same conventions as the academic API (session, explicit CSRF on POST, bounded duplicate-key-refusing
JSON, no-store, fixed error codes, per-account throttles). Authorization is decided only by the
service modules. Not a RegistrationReviewAPI subclass: the WF-02 release safeguard is unaffected.
"""

from rest_framework.response import Response

from apps.accounts.session_auth import WorkspaceSessionAPI

from . import historical_participation as hp
from . import onboarding, services, verification
from .api import AcademicPeriodsUnavailable, _AccountThrottle, _error
from .configuration_api import ConfigurationAPI

FIELD_MESSAGES = {
    "student_type": "Choose Regular or Irregular.",
    "course_id": "Choose your course.",
    "year_level": "Choose your year level.",
    "section_id": "Choose your section.",
    "offering_ids": "Choose 1 to 20 different offered subjects.",
    "expected_version": "Reload and try again.",
    "expected_fee_revision_id": "Review the semester fee again.",
    "confirmed": "Confirm to continue.",
    "student_account_id": "Choose a valid student.",
    "semester_id": "Choose a valid semester.",
    "entry_classification": "Choose the CTU entry classification.",
    "subject_ids": "Choose 1 to 20 different subjects.",
    "source_reference": "Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).",
    "source_as_of": "Enter a valid date that is not in the future.",
    "expected_evidence_id": "Reload the student record and try again.",
    "evidence_id": "Choose a valid record.",
    "gap_id": "Choose a valid record.",
    "reason_code": "Choose a reason.",
    "reason_note": "Explain the correction in 10 to 500 characters.",
    "q": "Use up to 50 plain characters.",
}
ONBOARDING_MESSAGES = {
    "no_active_semester": "There is no active semester right now.",
    "semester_changed": "The active semester changed. Start onboarding for the current semester.",
    "already_completed": "You already completed onboarding for this semester.",
    "stale_version": "Your onboarding changed in another window. Reload and try again.",
    "type_required": "Choose Regular or Irregular first.",
    "subjects_required": "Confirm your subjects and your course and year level first.",
    "course_required": "Confirm your course and year level first.",
    "subjects_changed": "Your subjects no longer match your course or year level. Confirm your subjects again.",
    "subject_unavailable": "A selected subject is no longer offered this semester. Confirm your subjects again.",
    "instructor_unassigned": "A selected subject has no assigned instructor yet. Visit the School Admin in person.",
    "duplicate_subject": "Choose each subject only once.",
    "section_mismatch": "The selected subjects do not belong to your course, year level or section.",
    "incomplete_section": "Regular students confirm every subject prepared for their section. Confirm the full list again.",
    "course_unavailable": "This course is not available. Visit the School Admin in person.",
    "fee_unavailable": "The semester fee is not approved yet. Try again later.",
    "fee_changed": "The semester fee changed. Review it again before confirming.",
    "eligibility_blocked": "Onboarding is not available until the previous requirement is resolved.",
    "confirmation_required": "Confirm your onboarding to continue.",
    "finalization_conflict": "Your onboarding could not be completed. Reload and try again.",
    "instructor_conflict": "You are the assigned instructor of a selected subject. Visit the School Admin in person.",
}
VERIFICATION_MESSAGES = {
    "period_not_open": "Records can be verified only for an Active, Closed or Archived semester.",
    "period_not_historical": "A non-enrollment gap can be recorded only for a Closed or Archived semester.",
    "evidence_changed": "The verified record changed. Reload and try again.",
    "participation_exists": "The student already has a finalized participation for this semester.",
    "evidence_in_use": "This record supports a finalized participation and cannot be revoked.",
    "gap_conflict": "A verified non-enrollment gap exists for this semester.",
    "evidence_conflict": "A verified enrollment record exists for this semester.",
    "stale_version": "This record was changed by someone else. Reload and try again.",
    "already_revoked": "This record is already revoked.",
    "not_found_student": "The student is unavailable.",
    "self_verification": "You cannot verify or change your own enrollment records.",
}
HISTORICAL_MESSAGES = {
    "period_not_historical": "Only a Closed or Archived semester can receive a historical correction.",
    "evidence_required": "Record the verified CTU enrollment for this semester first.",
    "evidence_changed": "The verified record changed. Review it again.",
    "participation_exists": "The student already has a participation for this semester.",
    "gap_conflict": "A verified non-enrollment gap exists for this semester.",
    "subjects_mismatch": "The offerings must match the verified subjects exactly.",
    "instructor_unassigned": "Every subject needs its real assigned instructor.",
    "historical_fee_unavailable": "The semester has no approved original fee, so no obligation can be created.",
    "confirmation_required": "Confirm the correction to continue.",
    "correction_conflict": "The correction could not be applied. Reload and try again.",
    "self_verification": "You cannot correct your own enrollment records.",
    "instructor_conflict": "The student is the assigned instructor of a selected subject; nobody signs their own clearance.",
}


class StudentReadThrottle(_AccountThrottle):
    scope = "workspace_student_onboarding_read"
    rate = "120/min"


class StudentWriteThrottle(_AccountThrottle):
    scope = "workspace_student_onboarding_write"
    rate = "30/min"


class _BaseAPI(ConfigurationAPI):
    gate = staticmethod(lambda: False)
    unavailable = ("student_onboarding_unavailable", "Student Semester Onboarding is unavailable.")

    def initial(self, request, *args, **kwargs):
        if not self.gate():
            raise AcademicPeriodsUnavailable()
        WorkspaceSessionAPI.initial(self, request, *args, **kwargs)

    def get_throttles(self):
        return [StudentReadThrottle()] if self.request.method in ("GET", "HEAD", "OPTIONS") else [StudentWriteThrottle()]

    def handle_exception(self, exc):
        if isinstance(exc, onboarding.OnboardingConflict):
            return _error("onboarding_conflict", ONBOARDING_MESSAGES[exc.reason], 409, reason=exc.reason,
                          details=[d for d in exc.details if isinstance(d, str) and len(d) <= 40][:20])
        if isinstance(exc, onboarding.OnboardingRequired):
            return _error("onboarding_required", "Complete Student Semester Onboarding first.", 409, state=exc.state,
                          route=exc.route)
        if isinstance(exc, verification.VerificationConflict):
            return _error("verification_conflict", VERIFICATION_MESSAGES[exc.reason], 409, reason=exc.reason)
        if isinstance(exc, hp.HistoricalCorrectionRefused):
            return _error("historical_correction_conflict", HISTORICAL_MESSAGES[exc.reason], 409, reason=exc.reason)
        if isinstance(exc, services.AcademicPeriodInvalid):
            fields = {name: [FIELD_MESSAGES[name]] for name in exc.fields if name in FIELD_MESSAGES}
            return _error("invalid_request", "Check the submitted details.", 400, fields=fields)
        if isinstance(exc, services.AcademicPeriodFeatureDisabled):
            return _error("feature_disabled", "This action is not enabled.", 503)
        if isinstance(exc, (services.AcademicPeriodUnavailable, AcademicPeriodsUnavailable)):
            return _error(*self.unavailable, 503)
        if isinstance(exc, services.AcademicPeriodDenied):
            return _error("access_denied", "You cannot use this feature in your current role.", 403, reason=exc.reason)
        return super().handle_exception(exc)


class OnboardingAPI(_BaseAPI):
    gate = staticmethod(onboarding.onboarding_enabled)


class VerificationAPI(_BaseAPI):
    gate = staticmethod(verification.verification_enabled)
    unavailable = ("verification_unavailable", "Official verification recording is unavailable.")


class HistoricalAPI(_BaseAPI):
    gate = staticmethod(hp.correction_enabled)
    unavailable = ("historical_correction_unavailable", "Historical participation correction is unavailable.")


def _view(base, name, methods, get=None, post=None, fields=(), required=None, query=(), ints=()):
    fields, required = frozenset(fields), frozenset(fields if required is None else required)

    def do_get(self, request, **kwargs):
        return Response(get(self.actor(request), **kwargs, **self.query(request, query, ints)))

    def do_post(self, request, **kwargs):
        actor = self.actor(request)
        return Response(post(actor, self.body(request, fields, required), **kwargs))

    attrs = {"http_method_names": methods, "__module__": __name__}
    if get is not None:
        attrs["get"] = do_get
    if post is not None:
        attrs["post"] = do_post
    return type(name, (base,), attrs)


READ = ["get", "head", "options"]
WRITE = ["post", "options"]

# ---- Student (own records only) ------------------------------------------------------------------
OnboardingStatusView = _view(OnboardingAPI, "OnboardingStatusView", READ, get=lambda a: onboarding.status(actor=a))
OnboardingContextView = _view(OnboardingAPI, "OnboardingContextView", READ,
                              get=lambda a: onboarding.context_options(actor=a))
OnboardingSubjectOptionsView = _view(
    OnboardingAPI, "OnboardingSubjectOptionsView", READ, query=("course_id", "year_level", "section_id"),
    ints=("course_id", "year_level", "section_id"),
    get=lambda a, **q: onboarding.subject_options(actor=a, course_id=q.get("course_id"), year_level=q.get("year_level"),
                                                  section_id=q.get("section_id")))
OnboardingTypeView = _view(
    OnboardingAPI, "OnboardingTypeView", WRITE, fields=("student_type", "expected_version"), required=("student_type",),
    post=lambda a, d: onboarding.save_student_type(actor=a, student_type=d["student_type"],
                                                   expected_version=d.get("expected_version")))
OnboardingSubjectsView = _view(
    OnboardingAPI, "OnboardingSubjectsView", WRITE, fields=("course_id", "year_level", "offering_ids", "expected_version"),
    post=lambda a, d: onboarding.confirm_subjects(actor=a, course_id=d["course_id"], year_level=d["year_level"],
                                                  offering_ids=d["offering_ids"], expected_version=d["expected_version"]))
OnboardingCourseView = _view(
    OnboardingAPI, "OnboardingCourseView", WRITE, fields=("course_id", "year_level", "expected_version"),
    post=lambda a, d: onboarding.confirm_course(actor=a, course_id=d["course_id"], year_level=d["year_level"],
                                                expected_version=d["expected_version"]))
OnboardingReviewView = _view(OnboardingAPI, "OnboardingReviewView", READ, get=lambda a: onboarding.review(actor=a))
OnboardingFinalizeView = _view(
    OnboardingAPI, "OnboardingFinalizeView", WRITE, fields=("expected_version", "expected_fee_revision_id", "confirmed"),
    post=lambda a, d: onboarding.finalize(actor=a, expected_version=d["expected_version"],
                                          expected_fee_revision_id=d["expected_fee_revision_id"],
                                          confirmed=d["confirmed"]))
MySemesterView = _view(OnboardingAPI, "MySemesterView", READ, get=lambda a: onboarding.my_semester(actor=a))
MyHistoryView = _view(OnboardingAPI, "MyHistoryView", READ, get=lambda a: onboarding.my_history(actor=a))

# ---- School Admin: in-person verification records --------------------------------------------------
EVIDENCE_FIELDS = ("student_account_id", "semester_id", "entry_classification", "course_id", "year_level", "subject_ids",
                   "source_reference", "source_as_of", "expected_evidence_id")
StudentSearchView = _view(VerificationAPI, "StudentSearchView", READ, query=("q",),
                          get=lambda a, **q: verification.search_students(actor=a, q=q.get("q")))
StudentRecordView = _view(VerificationAPI, "StudentRecordView", READ,
                          get=lambda a, student_account_id: verification.student_record(
                              actor=a, student_account_id=student_account_id))
EvidenceRecordView = _view(
    VerificationAPI, "EvidenceRecordView", WRITE, fields=EVIDENCE_FIELDS,
    required=("student_account_id", "semester_id", "entry_classification", "course_id", "year_level", "subject_ids",
              "source_reference", "expected_evidence_id"),
    post=lambda a, d: verification.record_evidence(actor=a, **{k: d.get(k) for k in EVIDENCE_FIELDS}))
EvidenceRevokeView = _view(
    VerificationAPI, "EvidenceRevokeView", WRITE, fields=("expected_version", "reason_code"),
    post=lambda a, d, evidence_id: verification.revoke_evidence(actor=a, evidence_id=evidence_id,
                                                                expected_version=d["expected_version"],
                                                                reason_code=d["reason_code"]))
GapRecordView = _view(
    VerificationAPI, "GapRecordView", WRITE, fields=("student_account_id", "semester_id", "source_reference"),
    post=lambda a, d: verification.record_gap(actor=a, student_account_id=d["student_account_id"],
                                              semester_id=d["semester_id"], source_reference=d["source_reference"]))
GapRevokeView = _view(
    VerificationAPI, "GapRevokeView", WRITE, fields=("expected_version",),
    post=lambda a, d, gap_id: verification.revoke_gap(actor=a, gap_id=gap_id, expected_version=d["expected_version"]))

# ---- School Admin: WF11-D14 historical participation correction --------------------------------------
HISTORICAL_FIELDS = ("student_account_id", "semester_id", "expected_evidence_id", "student_type", "offering_ids",
                     "reason_note", "confirmed")
HistoricalPreviewView = _view(
    HistoricalAPI, "HistoricalPreviewView", READ, query=("student_account_id", "semester_id"),
    ints=("student_account_id", "semester_id"),
    get=lambda a, **q: hp.preview(actor=a, student_account_id=q.get("student_account_id"),
                                  semester_id=q.get("semester_id")))
HistoricalCorrectView = _view(
    HistoricalAPI, "HistoricalCorrectView", WRITE, fields=HISTORICAL_FIELDS,
    post=lambda a, d: hp.correct(actor=a, **{k: d[k] for k in HISTORICAL_FIELDS}))
