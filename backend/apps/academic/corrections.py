"""WF-11.01 controlled Active-semester edits (WF11-D06) and historical corrections (WF11-D05).

Scope: the start and end dates of an Active, Closed or Archived semester. Status never changes
(a correction never reopens or reactivates a period); Draft semesters use the Draft endpoint.
Fee amounts are out of scope (separately governed financial workflow); no Student, fee or
clearance record is ever written.

Every change needs an explicit reason code and note, a confirmed ``expected_version`` and a
downstream impact evaluation (dependencies.evaluate_impact) re-run under lock:

* any impact source ``unavailable`` -> refused (``impact_unavailable``): the effect on Student
  records, fee obligations or clearance cannot be evaluated safely, so it is never guessed;
* evaluated records that would be affected -> refused until the School Admin acknowledges exactly
  those categories (``impact_review_required``); the records themselves are never rewritten;
* identical dates -> refused (``no_change``) so a repeated submission cannot duplicate history.

The audit row keeps the original and new values, the actor, the acting role, the reason code and
note, and the impact summary. Gate: WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED (default off,
refused in production) in addition to the base gate. With today's dependency bundle every impact
source is unavailable, so these edits are refused at runtime until the dependent modules exist.
"""

import unicodedata

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.fields import CurrentTimestamp

from . import dependencies, periods, services
from .models import SchoolYear, Semester, SemesterStatus, SemesterTerm

CORRECTIONS_SETTING = "WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED"
ACTIVE_EDIT_ACTION = "academic.semester.active_edit"
HISTORICAL_CORRECTION_ACTION = "academic.semester.historical_correction"
REASON_CODES = frozenset({"calendar_change", "data_entry_correction", "institutional_directive"})
NOTE_MIN, NOTE_MAX = 10, 500
EDITABLE = (SemesterStatus.ACTIVE, SemesterStatus.CLOSED, SemesterStatus.ARCHIVED)


def corrections_enabled():
    return services.gate_open() and getattr(settings, CORRECTIONS_SETTING, False) is True


def _kind(semester):
    return "active_edit" if semester.status == SemesterStatus.ACTIVE else "historical_correction"


def _impact_state(impact):
    unavailable = [i.key for i in impact if i.status != dependencies.EVALUATED]
    affected = [i.key for i in impact if i.status == dependencies.EVALUATED and i.count]
    return unavailable, affected


def correction_preview(*, actor, semester_id):
    services.authorize(actor)
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    semester = Semester.objects.using(DEFAULT_DB_ALIAS).select_related("school_year").filter(pk=semester_id).first()
    if semester is None:
        raise services.AcademicPeriodNotFound()
    impact = dependencies.evaluate_impact(semester)
    unavailable, affected = _impact_state(impact)
    blockers = []
    if semester.status not in EDITABLE:
        blockers.append("period_is_draft")
    if unavailable:
        blockers.append("impact_unavailable")
    enabled = corrections_enabled()
    if not enabled:
        blockers.append("feature_disabled")
    return {"semester": {**services.semester_snapshot(semester), "label": semester.label,
                         "school_year_id": semester.school_year_id, "school_year_label": semester.school_year.label},
            "kind": _kind(semester), "impact": [i.as_dict() for i in impact], "affected": affected,
            "reason_codes": sorted(REASON_CODES), "blockers": blockers, "feature_enabled": enabled,
            "can_confirm": not blockers}


def _clean_note(raw):
    if type(raw) is not str:
        return None
    note = " ".join(raw.split())
    if not NOTE_MIN <= len(note) <= NOTE_MAX:
        return None
    if any(unicodedata.category(ch).startswith("C") for ch in note):
        return None
    return note


def correct_semester_dates(*, actor, semester_id, start_date, end_date, expected_version, reason_code, reason_note,
                           acknowledged_impacts=(), acknowledge_cross_year_overlap=False):
    if not corrections_enabled():
        raise services.AcademicPeriodFeatureDisabled("Academic-period corrections are not enabled.")
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    errors = {}
    if type(expected_version) is not int or not 1 <= expected_version <= services.MAX_ID:
        errors["expected_version"] = "invalid"
    if type(reason_code) is not str or reason_code not in REASON_CODES:
        errors["reason_code"] = "invalid"
    note = _clean_note(reason_note)
    if note is None:
        errors["reason_note"] = "invalid"
    if type(acknowledge_cross_year_overlap) is not bool:
        errors["acknowledge_cross_year_overlap"] = "invalid"
    if (not isinstance(acknowledged_impacts, (list, tuple)) or len(acknowledged_impacts) > 10
            or any(type(k) is not str or k not in dependencies.IMPACT_RECORDS for k in acknowledged_impacts)):
        errors["acknowledged_impacts"] = "invalid"
    try:
        start = periods.parse_iso_date(start_date)
    except ValueError:
        start, errors["start_date"] = None, "invalid"
    try:
        end = periods.parse_iso_date(end_date)
    except ValueError:
        end, errors["end_date"] = None, "invalid"
    if "start_date" not in errors and start is None:
        errors["start_date"] = "required"  # a non-Draft period always keeps a complete range
    if "end_date" not in errors and end is None:
        errors["end_date"] = "required"
    if errors:
        raise services.AcademicPeriodInvalid(errors)
    services.authorize(actor)
    with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
        auth = services.lock_and_authorize(actor)
        semester_db = Semester.objects.using(DEFAULT_DB_ALIAS)
        year_id = semester_db.filter(pk=semester_id).values_list("school_year_id", flat=True).first()
        if year_id is None:
            raise services.AcademicPeriodNotFound()
        school_year = SchoolYear.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk=year_id).first()
        pair = {s.term: s for s in semester_db.select_for_update().filter(school_year_id=year_id).order_by("semester_id")}
        target = next((s for s in pair.values() if s.pk == semester_id), None)
        if school_year is None or target is None or set(pair) != {SemesterTerm.FIRST, SemesterTerm.SECOND}:
            raise services.AcademicPeriodNotFound()
        if target.status not in EDITABLE:
            raise services.AcademicPeriodConflict("period_is_draft")
        if target.version != expected_version:
            raise services.AcademicPeriodConflict("stale_version")
        problem = periods.range_problem(start, end, school_year.start_year)
        if problem is not None:
            raise services.AcademicPeriodInvalid({"end_date" if problem == "start_not_before_end" else "start_date": problem})
        if (target.start_date, target.end_date) == (start, end):
            raise services.AcademicPeriodConflict("no_change")
        sibling = pair[SemesterTerm.SECOND if target.term == SemesterTerm.FIRST else SemesterTerm.FIRST]
        first = (start, end) if target.term == SemesterTerm.FIRST else (sibling.start_date, sibling.end_date)
        second = (start, end) if target.term == SemesterTerm.SECOND else (sibling.start_date, sibling.end_date)
        if periods.terms_overlap(first, second):
            raise services.AcademicPeriodConflict("semesters_overlap")
        impact = dependencies.evaluate_impact(target)
        unavailable, affected = _impact_state(impact)
        if unavailable:
            raise services.AcademicPeriodConflict("impact_unavailable", unavailable)
        if frozenset(affected) != frozenset(acknowledged_impacts):
            raise services.AcademicPeriodConflict("impact_review_required", affected)
        cross_year = any(periods.ranges_intersect(start, end, other.start_date, other.end_date)
                         for other in semester_db.exclude(school_year_id=year_id).filter(
                             start_date__isnull=False, end_date__isnull=False, start_date__lte=end, end_date__gte=start))
        if cross_year and not acknowledge_cross_year_overlap:
            raise services.AcademicPeriodConflict("cross_year_overlap")
        kind = _kind(target)
        before = services.semester_snapshot(target)
        changed = semester_db.filter(pk=target.pk, version=expected_version, status=target.status).update(
            start_date=start, end_date=end, version=expected_version + 1, updated_at=CurrentTimestamp())
        if changed != 1:
            raise services.AcademicPeriodConflict("stale_version")
        SchoolYear.objects.using(DEFAULT_DB_ALIAS).filter(pk=year_id).update(updated_at=CurrentTimestamp())
        target.refresh_from_db()
        after = {**services.semester_snapshot(target), "impact": [i.as_dict() for i in impact]}
        if cross_year:
            after["cross_year_overlap_acknowledged"] = True
        services.write_audit(auth, action=ACTIVE_EDIT_ACTION if kind == "active_edit" else HISTORICAL_CORRECTION_ACTION,
                             school_year_id=year_id, semester_id=target.pk, old_value=before, new_value=after,
                             reason=reason_code, reason_note=note)
    refreshed = SchoolYear.objects.using(DEFAULT_DB_ALIAS).prefetch_related("semesters").get(pk=year_id)
    return services.school_year_payload(refreshed)
