"""Previous-clearance eligibility for a Student and a semester (WF11-D15/16, WF-06.02 steps 1-2, WF-07.08).

The "prior applicable periods" are the semesters before the target (by school year, then term) that
were ever Active in the Workspace. A semester the Workspace never operated cannot require a Workspace
clearance. Rules, evaluated at onboarding entry and again inside finalization:

* No prior applicable period: eligible (first Workspace-operated period).
* The immediately previous applicable period has this Student's participation: its clearance must be
  Cleared (all signatures plus final approval); otherwise ``clearance_required``.
* No participation there, but an earlier participation exists: EVERY applicable period after it must
  have a School Admin-verified non-enrollment gap; otherwise ``gap_verification_required``. With all
  gaps verified the Student may proceed; the older clearance keeps its status and all past fees stay.
* No participation at all: official evidence for the target semester decides. A newcomer or transferee
  classification is first-time eligible. Without evidence the state is ``verification_required``
  (Draft allowed, finalization not). Continuing/returning evidence needs every prior applicable period
  covered by a verified gap (``history_unverified`` otherwise); missing records never prove anything.
* Newcomer/transferee evidence contradicted by an earlier participation: ``evidence_conflict``.

Read-only. Callers that finalize must hold the shared locks first.
"""

from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q

from .models import (
    EnrollmentGapException, EntryClassification, Semester, SemesterParticipation, VerificationStatus,
)

DB = DEFAULT_DB_ALIAS
ELIGIBLE = "eligible"
BLOCKING = frozenset({"clearance_required", "gap_verification_required", "history_unverified", "evidence_conflict"})
FIRST_TIME = (EntryClassification.NEWCOMER, EntryClassification.TRANSFEREE)


def prior_applicable_periods(semester):
    year = semester.school_year.start_year
    return list(Semester.objects.using(DB).select_related("school_year")
                .filter(activated_at__isnull=False)
                .filter(Q(school_year__start_year__lt=year) | Q(school_year__start_year=year, term__lt=semester.term))
                .order_by("school_year__start_year", "term"))


def _ref(semester):
    return {"semester_id": semester.pk, "label": semester.label, "school_year_label": semester.school_year.label,
            "status": semester.status}


def evaluate(student, semester, evidence=None):
    prior = prior_applicable_periods(semester)
    participations = {p.semester_id: p for p in SemesterParticipation.objects.using(DB)
                      .select_related("clearance").filter(student=student, semester__in=[s.pk for s in prior])}
    gaps = set(EnrollmentGapException.objects.using(DB).filter(
        student=student, status=VerificationStatus.VERIFIED, semester__in=[s.pk for s in prior])
        .values_list("semester_id", flat=True))
    classification = evidence.entry_classification if evidence is not None else None
    result = {"status": ELIGIBLE, "basis": "", "previous_semester": _ref(prior[-1]) if prior else None,
              "missing_gaps": [], "older_uncleared": []}
    if classification in FIRST_TIME and participations:
        return {**result, "status": "evidence_conflict", "basis": "first_time_evidence_with_history"}
    if not prior:
        return {**result, "basis": "no_prior_period"}
    previous = prior[-1]
    if previous.pk in participations:
        clearance = getattr(participations[previous.pk], "clearance", None)
        if clearance is not None and clearance.status == "Cleared":
            return {**result, "basis": "previous_cleared"}
        return {**result, "status": "clearance_required", "basis": "previous_uncleared"}
    participated = [s for s in prior if s.pk in participations]
    if participated:
        last = participated[-1]
        between = [s for s in prior if (s.school_year.start_year, s.term) > (last.school_year.start_year, last.term)]
        missing = [_ref(s) for s in between if s.pk not in gaps]
        if missing:
            return {**result, "status": "gap_verification_required", "basis": "unverified_gap", "missing_gaps": missing}
        clearance = getattr(participations[last.pk], "clearance", None)
        older = [_ref(last)] if clearance is None or clearance.status != "Cleared" else []
        return {**result, "basis": "verified_gap", "older_uncleared": older}
    if classification is None:
        return {**result, "status": "verification_required", "basis": "no_workspace_history"}
    if classification in FIRST_TIME:
        return {**result, "basis": "first_time_evidence"}
    missing = [_ref(s) for s in prior if s.pk not in gaps]
    if missing:
        return {**result, "status": "history_unverified", "basis": "continuing_without_history", "missing_gaps": missing}
    return {**result, "basis": "verified_gap"}
