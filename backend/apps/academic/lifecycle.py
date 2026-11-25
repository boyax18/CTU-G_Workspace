"""WF-11.01 semester lifecycle: activation (D02-D04, D10), closure (D11) and archiving (D12).

Every transition is a two-step, manual operation: a read-only *preview* (authorized, never
locking) and an explicit *confirmation*. Nothing is ever date-triggered.

The confirmation carries what the School Admin reviewed: the target's ``expected_version``, the
Active semester the preview showed (activation), and the exact set of warnings shown
(``acknowledged_warnings``). Inside ONE durable transaction the service locks, in the shared order,
the academic service row, the permission row, the actor, the target and every Active semester;
re-authorizes; re-evaluates prerequisites/obligations/warnings; and refuses if anything the admin
saw has changed. The state change and its audit rows commit together or not at all.

Gates: WORKSPACE_ACADEMIC_PERIODS_ENABLED (base) AND WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED
for confirmations (both default off; refused in the production profile). Previews need only the
base gate and report ``feature_enabled`` so the UI can show "Feature unavailable".

Preserved invariants: at most one Active semester (UNIQUE active_slot + CHECK, plus serialization
on the locked service row); Closed/Archived never return to Draft or Active; closing and archiving
change only the semester row: Student records, fee obligations, clearance signatures and audit
history are never touched, settled, cleared or deleted.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction

from apps.accounts.fields import CurrentTimestamp

from . import dependencies, services
from .models import SchoolYear, Semester, SemesterStatus

TRANSITIONS_SETTING = "WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED"
ACTIVATE_ACTION = "academic.semester.activate"
CLOSE_ACTION = "academic.semester.close"
ARCHIVE_ACTION = "academic.semester.archive"
REASON_TRANSITION = "manual_transition"
CAMPUS_TZ = ZoneInfo("Asia/Manila")
MAX_WARNINGS = 20


class TransitionRefused(Exception):
    """A lifecycle rule refused the transition; nothing changed."""

    REASONS = frozenset({"not_draft", "not_active", "not_closed", "prerequisites_missing", "active_changed",
                         "confirmation_required", "warnings_changed", "stale_version", "transition_conflict"})

    def __init__(self, reason, missing=()):
        self.reason = reason if reason in self.REASONS else "transition_conflict"
        self.missing = tuple(missing)
        super().__init__("The academic-period transition was refused.")


def transitions_enabled():
    return services.gate_open() and getattr(settings, TRANSITIONS_SETTING, False) is True


def campus_today():
    return datetime.now(CAMPUS_TZ).date()


# ---- Pure evaluation (shared by preview and confirmation) -----------------------------------

def _activation_warnings(target, current, today):
    warnings = []
    if current is not None:
        warnings.append("previous_active_will_close")
        if current.start_date and target.start_date and target.start_date < current.start_date:
            warnings.append("earlier_than_current_active")
    if target.start_date and target.end_date and not target.start_date <= today <= target.end_date:
        warnings.append("outside_semester_dates")
    return warnings


def _obligation_warnings(obligations):
    warnings = []
    for item in obligations:
        if item.status != dependencies.EVALUATED:
            warnings.append(f"{item.key}_unavailable")
        elif item.count:
            warnings.append(f"{item.key}_outstanding")
    return warnings


def _closure_warnings(semester, obligations, today):
    warnings = _obligation_warnings(obligations)
    if semester.end_date and today < semester.end_date:
        warnings.append("before_end_date")
    return warnings


def _ref(semester, year=None):
    year = year or semester.school_year
    return {**services.semester_snapshot(semester), "label": semester.label, "school_year_id": year.pk,
            "school_year_label": year.label}


def _load(semester_id):
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    semester = Semester.objects.using(DEFAULT_DB_ALIAS).select_related("school_year").filter(pk=semester_id).first()
    if semester is None:
        raise services.AcademicPeriodNotFound()
    return semester


def _current_active(exclude_id=None):
    qs = Semester.objects.using(DEFAULT_DB_ALIAS).select_related("school_year").filter(status=SemesterStatus.ACTIVE)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return list(qs.order_by("semester_id"))


# ---- Previews (read-only; base gate + HDAC) ---------------------------------------------------

def activation_preview(*, actor, semester_id):
    services.authorize(actor)
    semester = _load(semester_id)
    actives = _current_active(exclude_id=semester.pk)
    current = actives[0] if actives else None
    checks = dependencies.evaluate_prerequisites(semester)
    blockers = []
    if semester.status != SemesterStatus.DRAFT:
        blockers.append("not_draft")
    if any(c.status != dependencies.READY for c in checks):
        blockers.append("prerequisites_missing")
    enabled = transitions_enabled()
    if not enabled:
        blockers.append("feature_disabled")
    return {"semester": _ref(semester), "current_active": _ref(current) if current else None,
            "prerequisites": [c.as_dict() for c in checks],
            "warnings": _activation_warnings(semester, current, campus_today()),
            "blockers": blockers, "feature_enabled": enabled, "can_confirm": not blockers}


def _obligation_preview(semester, source_status, refusal, warnings):
    obligations = dependencies.evaluate_obligations(semester)
    blockers = [] if semester.status == source_status else [refusal]
    enabled = transitions_enabled()
    if not enabled:
        blockers.append("feature_disabled")
    return {"semester": _ref(semester), "obligations": [o.as_dict() for o in obligations],
            "warnings": warnings(semester, obligations, campus_today()),
            "blockers": blockers, "feature_enabled": enabled, "can_confirm": not blockers}


def closure_preview(*, actor, semester_id):
    services.authorize(actor)
    return _obligation_preview(_load(semester_id), SemesterStatus.ACTIVE, "not_active", _closure_warnings)


def archive_preview(*, actor, semester_id):
    services.authorize(actor)
    return _obligation_preview(_load(semester_id), SemesterStatus.CLOSED, "not_closed",
                               lambda s, o, _today: _obligation_warnings(o))


# ---- Confirmations --------------------------------------------------------------------------

def _validate_request(semester_id, expected_version, acknowledged_warnings, confirmed):
    if not transitions_enabled():
        raise services.AcademicPeriodFeatureDisabled("Academic-period transitions are not enabled.")
    if confirmed is not True:
        raise TransitionRefused("confirmation_required")
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    if type(expected_version) is not int or not 1 <= expected_version <= services.MAX_ID:
        raise services.AcademicPeriodInvalid({"expected_version": "invalid"})
    if (type(acknowledged_warnings) is not list or len(acknowledged_warnings) > MAX_WARNINGS
            or any(type(w) is not str or not 1 <= len(w) <= 60 for w in acknowledged_warnings)):
        raise services.AcademicPeriodInvalid({"acknowledged_warnings": "invalid"})
    return frozenset(acknowledged_warnings)


def _locked(semester_id):
    """Lock the target and every Active semester in primary-key order (after the shared locks)."""
    db = Semester.objects.using(DEFAULT_DB_ALIAS)
    ids = sorted({semester_id, *db.filter(status=SemesterStatus.ACTIVE).values_list("pk", flat=True)})
    rows = {row.pk: row for row in db.select_for_update().filter(pk__in=ids).order_by("semester_id")}
    target = rows.get(semester_id)
    if target is None:
        raise services.AcademicPeriodNotFound()
    actives = [row for row in rows.values() if row.status == SemesterStatus.ACTIVE and row.pk != semester_id]
    return target, actives


def _audit_snapshot(semester, **extra):
    return {**services.semester_snapshot(semester), **extra}


def activate_semester(*, actor, semester_id, expected_version, expected_active_semester_id,
                      acknowledged_warnings, confirmed):
    """Manually activate a Draft semester; atomically close the previously Active one, if any."""
    acknowledged = _validate_request(semester_id, expected_version, acknowledged_warnings, confirmed)
    if expected_active_semester_id is not None and (type(expected_active_semester_id) is not int
                                                    or expected_active_semester_id <= 0):
        raise TransitionRefused("active_changed")
    services.authorize(actor)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            auth = services.lock_and_authorize(actor)
            target, actives = _locked(semester_id)
            if target.status != SemesterStatus.DRAFT:
                raise TransitionRefused("not_draft")
            if target.version != expected_version:
                raise TransitionRefused("stale_version")
            current = actives[0] if actives else None
            if len(actives) > 1 or (current.pk if current else None) != expected_active_semester_id:
                raise TransitionRefused("active_changed")
            missing = [c.key for c in dependencies.evaluate_prerequisites(target) if c.status != dependencies.READY]
            if missing:
                raise TransitionRefused("prerequisites_missing", missing)
            warnings = _activation_warnings(target, current, campus_today())
            if frozenset(warnings) != acknowledged:
                raise TransitionRefused("warnings_changed")
            db = Semester.objects.using(DEFAULT_DB_ALIAS)
            if current is not None:
                before = services.semester_snapshot(current)
                # Free the single Active slot BEFORE taking it.
                db.filter(pk=current.pk, status=SemesterStatus.ACTIVE).update(
                    status=SemesterStatus.CLOSED, active_slot=None, closed_at=CurrentTimestamp(),
                    version=current.version + 1, updated_at=CurrentTimestamp())
                current.refresh_from_db()
                services.write_audit(auth, action=CLOSE_ACTION, school_year_id=current.school_year_id,
                                     semester_id=current.pk, old_value=before, reason=REASON_TRANSITION,
                                     new_value=_audit_snapshot(current, closed_by_activation_of=target.pk))
            before = services.semester_snapshot(target)
            changed = db.filter(pk=target.pk, status=SemesterStatus.DRAFT, version=expected_version).update(
                status=SemesterStatus.ACTIVE, active_slot=1, activated_at=CurrentTimestamp(),
                version=expected_version + 1, updated_at=CurrentTimestamp())
            if changed != 1:
                raise TransitionRefused("transition_conflict")
            target.refresh_from_db()
            services.write_audit(auth, action=ACTIVATE_ACTION, school_year_id=target.school_year_id,
                                 semester_id=target.pk, old_value=before, reason=REASON_TRANSITION,
                                 new_value=_audit_snapshot(target, acknowledged_warnings=sorted(warnings)))
            SchoolYear.objects.using(DEFAULT_DB_ALIAS).filter(
                pk__in={target.school_year_id, *(c.school_year_id for c in actives)}).update(updated_at=CurrentTimestamp())
    except IntegrityError as exc:
        # UNIQUE/CHECK backstop: never two Active semesters, never a half-applied transition.
        raise TransitionRefused("transition_conflict") from exc
    return _ref(Semester.objects.using(DEFAULT_DB_ALIAS).select_related("school_year").get(pk=target.pk))


def _obligation_transition(*, actor, semester_id, expected_version, acknowledged_warnings, confirmed,
                           source, target_status, stamp_field, action, refusal, warnings_for):
    acknowledged = _validate_request(semester_id, expected_version, acknowledged_warnings, confirmed)
    services.authorize(actor)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            auth = services.lock_and_authorize(actor)
            semester, _actives = _locked(semester_id)
            if semester.status != source:
                raise TransitionRefused(refusal)
            if semester.version != expected_version:
                raise TransitionRefused("stale_version")
            obligations = dependencies.evaluate_obligations(semester)
            warnings = warnings_for(semester, obligations, campus_today())
            if frozenset(warnings) != acknowledged:
                raise TransitionRefused("warnings_changed")
            before = services.semester_snapshot(semester)
            changes = {"status": target_status, stamp_field: CurrentTimestamp(),
                       "version": expected_version + 1, "updated_at": CurrentTimestamp()}
            if source == SemesterStatus.ACTIVE:
                changes["active_slot"] = None
            changed = Semester.objects.using(DEFAULT_DB_ALIAS).filter(
                pk=semester.pk, status=source, version=expected_version).update(**changes)
            if changed != 1:
                raise TransitionRefused("transition_conflict")
            semester.refresh_from_db()
            # Only the semester row changes. Obligations are recorded as reviewed, never resolved.
            services.write_audit(auth, action=action, school_year_id=semester.school_year_id,
                                 semester_id=semester.pk, old_value=before, reason=REASON_TRANSITION,
                                 new_value=_audit_snapshot(semester, acknowledged_warnings=sorted(warnings),
                                                           obligations=[o.as_dict() for o in obligations]))
            SchoolYear.objects.using(DEFAULT_DB_ALIAS).filter(pk=semester.school_year_id).update(
                updated_at=CurrentTimestamp())
    except IntegrityError as exc:
        raise TransitionRefused("transition_conflict") from exc
    return _ref(Semester.objects.using(DEFAULT_DB_ALIAS).select_related("school_year").get(pk=semester.pk))


def close_semester(*, actor, semester_id, expected_version, acknowledged_warnings, confirmed):
    """WF11-D11: warned manual closure. Outstanding signatures, fees and onboarding remain as they are."""
    return _obligation_transition(
        actor=actor, semester_id=semester_id, expected_version=expected_version,
        acknowledged_warnings=acknowledged_warnings, confirmed=confirmed, source=SemesterStatus.ACTIVE,
        target_status=SemesterStatus.CLOSED, stamp_field="closed_at", action=CLOSE_ACTION, refusal="not_active",
        warnings_for=_closure_warnings)


def archive_semester(*, actor, semester_id, expected_version, acknowledged_warnings, confirmed):
    """WF11-D12: manual archiving of a Closed semester; obligations need not be settled; never reopened."""
    return _obligation_transition(
        actor=actor, semester_id=semester_id, expected_version=expected_version,
        acknowledged_warnings=acknowledged_warnings, confirmed=confirmed, source=SemesterStatus.CLOSED,
        target_status=SemesterStatus.ARCHIVED, stamp_field="archived_at", action=ARCHIVE_ACTION,
        refusal="not_closed", warnings_for=lambda s, o, _today: _obligation_warnings(o))
