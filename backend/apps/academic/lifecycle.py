"""WF-11.01 lifecycle foundation: activation, closure and archiving (NOT AVAILABLE AT RUNTIME).

Owner scope (25 Nov 2026): design and test the transition invariants only. Live activation,
closure and archiving are not authorized, so:

* No URL, view, management command or Django Admin action calls this module.
* ``WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED`` is defined by NO settings module; it reads as
  False everywhere outside a test's override, and every entry point refuses first.
* Activation preflight (WF11-D03) is fail-closed: the governed semester fee (pending the
  separately reviewed ``finance.fee_schedule.manage`` revision) and the curriculum/subject
  offerings do not exist yet, so ``DEFAULT_PREREQUISITES`` always reports them missing. Nothing
  here creates, assumes or fabricates a fee, offering, participation, clearance or obligation.
* A substitute prerequisites object is accepted ONLY on the verified disposable test database,
  so the atomic one-Active transition can be exercised in isolation without fake records.

Invariants (WF11-D02, D04, D11, D12): manual only (never date-triggered); at most one Active
semester campus-wide (UNIQUE ``active_slot`` + CHECK, plus serialization on the locked academic
service row); the previous Active semester is closed and the next activated in ONE transaction
with attributable audit, or nothing changes; Closed/Archived periods never return to Draft or
Active and keep all history; closing never clears or deletes outstanding obligations.
"""

import re

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, connections, transaction

from apps.accounts.fields import CurrentTimestamp

from . import services
from .models import Semester, SemesterStatus

TRANSITIONS_SETTING = "WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED"
ACTIVATE_ACTION = "academic.semester.activate"
CLOSE_ACTION = "academic.semester.close"
ARCHIVE_ACTION = "academic.semester.archive"
REASON_TRANSITION = "manual_transition"
_TEST_DATABASE = re.compile(r"test_ctug_registration_[0-9a-f]{16}")


class TransitionRefused(Exception):
    """A lifecycle rule refused the transition; nothing changed."""

    REASONS = frozenset({"not_draft", "not_active", "not_closed", "prerequisites_missing",
                         "active_changed", "confirmation_required", "transition_conflict"})

    def __init__(self, reason, missing=()):
        self.reason = reason if reason in self.REASONS else "transition_conflict"
        self.missing = tuple(missing)
        super().__init__("The academic-period transition was refused.")


class ActivationPrerequisites:
    """Fail-closed activation preflight. Never returns an empty list in this release."""

    def missing(self, semester):
        items = []
        start, end = semester.start_date, semester.end_date
        if start is None or end is None or not start < end:
            items.append("valid_dates")
        # No governed fee source exists (WF-11 fee-setting governance pending): never assumed.
        items.append("approved_fee")
        # No curriculum/subject offering model exists yet: never assumed.
        items.append("academic_offerings")
        return tuple(items)


DEFAULT_PREREQUISITES = ActivationPrerequisites()


def transitions_enabled():
    return getattr(settings, TRANSITIONS_SETTING, False) is True


def _isolated_test_database():
    name = getattr(settings, "REGISTRATION_TEST_DATABASE", "")
    if type(name) is not str or not _TEST_DATABASE.fullmatch(name):
        return False
    config = connections[DEFAULT_DB_ALIAS].settings_dict
    return config.get("NAME") == name and config.get("TEST", {}).get("NAME") == name


def _entry(prerequisites):
    if not transitions_enabled():
        raise services.AcademicPeriodUnavailable("Academic-period transitions are not available.")
    if prerequisites is None:
        return DEFAULT_PREREQUISITES
    if not _isolated_test_database():
        raise services.AcademicPeriodUnavailable("Substitute prerequisites are refused outside isolated tests.")
    return prerequisites


def preflight(semester, prerequisites=None):
    """Read-only list of missing activation prerequisites (empty only with an isolated substitute)."""
    checks = DEFAULT_PREREQUISITES if prerequisites is None else prerequisites
    return list(checks.missing(semester))


def _locked_semesters(semester_id):
    """Lock the target and every currently Active semester, in primary-key order."""
    db = Semester.objects.using(DEFAULT_DB_ALIAS)
    rows = list(db.select_for_update().filter(pk=semester_id).order_by("semester_id"))
    actives = list(db.select_for_update().filter(status=SemesterStatus.ACTIVE).order_by("semester_id"))
    if not rows:
        raise services.AcademicPeriodNotFound()
    return rows[0], actives


def activate_semester(*, actor, semester_id, expected_active_semester_id, confirmed, prerequisites=None):
    """Manually activate one Draft semester; atomically close the previously Active one, if any.

    ``expected_active_semester_id`` is the Active semester the School Admin's preview showed (None
    when none); if it changed, nothing happens. ``confirmed`` must be exactly True.
    """
    checks = _entry(prerequisites)
    if confirmed is not True:
        raise TransitionRefused("confirmation_required")
    if type(semester_id) is not int or semester_id <= 0:
        raise services.AcademicPeriodNotFound()
    if expected_active_semester_id is not None and type(expected_active_semester_id) is not int:
        raise TransitionRefused("active_changed")
    services.authorize(actor)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            auth = services.lock_and_authorize(actor)
            target, actives = _locked_semesters(semester_id)
            if target.status != SemesterStatus.DRAFT:
                raise TransitionRefused("not_draft")
            current = actives[0] if actives else None
            if len(actives) > 1 or (current.pk if current else None) != expected_active_semester_id:
                raise TransitionRefused("active_changed")
            missing = checks.missing(target)
            if missing:
                raise TransitionRefused("prerequisites_missing", missing)
            db = Semester.objects.using(DEFAULT_DB_ALIAS)
            if current is not None:
                before = services.semester_snapshot(current)
                # Free the single Active slot BEFORE taking it; one statement per row.
                db.filter(pk=current.pk, status=SemesterStatus.ACTIVE).update(
                    status=SemesterStatus.CLOSED, active_slot=None, closed_at=CurrentTimestamp(),
                    version=current.version + 1, updated_at=CurrentTimestamp())
                current.refresh_from_db()
                services.write_audit(auth, action=CLOSE_ACTION, school_year_id=current.school_year_id,
                                     semester_id=current.pk, old_value=before,
                                     new_value=services.semester_snapshot(current), reason=REASON_TRANSITION)
            before = services.semester_snapshot(target)
            changed = db.filter(pk=target.pk, status=SemesterStatus.DRAFT).update(
                status=SemesterStatus.ACTIVE, active_slot=1, activated_at=CurrentTimestamp(),
                version=target.version + 1, updated_at=CurrentTimestamp())
            if changed != 1:
                raise TransitionRefused("transition_conflict")
            target.refresh_from_db()
            services.write_audit(auth, action=ACTIVATE_ACTION, school_year_id=target.school_year_id,
                                 semester_id=target.pk, old_value=before,
                                 new_value=services.semester_snapshot(target), reason=REASON_TRANSITION)
    except IntegrityError as exc:
        # The UNIQUE/CHECK backstop: never two Active semesters, never a half-applied transition.
        raise TransitionRefused("transition_conflict") from exc
    return services.semester_snapshot(target)


def _simple_transition(*, actor, semester_id, confirmed, prerequisites, source, target_status, action,
                       stamp_field, refusal):
    _entry(prerequisites)
    if confirmed is not True:
        raise TransitionRefused("confirmation_required")
    if type(semester_id) is not int or semester_id <= 0:
        raise services.AcademicPeriodNotFound()
    services.authorize(actor)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            auth = services.lock_and_authorize(actor)
            semester, _actives = _locked_semesters(semester_id)
            if semester.status != source:
                raise TransitionRefused(refusal)
            before = services.semester_snapshot(semester)
            changes = {"status": target_status, stamp_field: CurrentTimestamp(),
                       "version": semester.version + 1, "updated_at": CurrentTimestamp()}
            if source == SemesterStatus.ACTIVE:
                changes["active_slot"] = None
            Semester.objects.using(DEFAULT_DB_ALIAS).filter(pk=semester.pk, status=source).update(**changes)
            semester.refresh_from_db()
            services.write_audit(auth, action=action, school_year_id=semester.school_year_id,
                                 semester_id=semester.pk, old_value=before,
                                 new_value=services.semester_snapshot(semester), reason=REASON_TRANSITION)
    except IntegrityError as exc:
        raise TransitionRefused("transition_conflict") from exc
    return services.semester_snapshot(semester)


def close_semester(*, actor, semester_id, confirmed, prerequisites=None):
    """WF11-D11: warned manual closure. Outstanding signatures and fees are untouched and remain."""
    return _simple_transition(actor=actor, semester_id=semester_id, confirmed=confirmed,
                              prerequisites=prerequisites, source=SemesterStatus.ACTIVE,
                              target_status=SemesterStatus.CLOSED, action=CLOSE_ACTION,
                              stamp_field="closed_at", refusal="not_active")


def archive_semester(*, actor, semester_id, confirmed, prerequisites=None):
    """WF11-D12: manual archiving of a Closed semester; history is retained, never reopened."""
    return _simple_transition(actor=actor, semester_id=semester_id, confirmed=confirmed,
                              prerequisites=prerequisites, source=SemesterStatus.CLOSED,
                              target_status=SemesterStatus.ARCHIVED, action=ARCHIVE_ACTION,
                              stamp_field="archived_at", refusal="not_closed")
