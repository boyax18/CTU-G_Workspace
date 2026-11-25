"""Semester organizational fee configuration: Draft, explicit approval, revisions and readiness.

Business rules (approved WF-11 decisions R-01): School Admin configures and approves the full
organizational fee for each semester; Treasurer collects cash. ₱0.00 is valid ONLY when entered and
approved explicitly; "not configured" and "approved zero" are different states. Fee obligations are
created later by Student Semester Onboarding, never here, and an approved rate already used to
assess obligations is never silently replaced.

Authorization (every operation, read or write): apps.academic.services.authorize with the exact
``finance.fee_schedule.manage`` code and ``admin_role_grant=True``: an active Approved account with
a genuine Admin assignment, the selected Admin context when role context is enforced, active academic
and finance services, account-specific Deny precedence, AND the code reaching the account through an
active grant of one of its Admin roles. The pinned v2.2 catalogue binds this code to Treasurer only,
so at runtime every fee operation is refused until a reviewed catalogue overlay exists (see
docs/security/WF11_FeeSchedulePermission_Overlay_Proposal_2026-11-25.md). Writes re-authorize under
the shared academic lock order (services -> permission -> account -> semester -> schedule) and commit
with an append-only FinanceAuditLog row.

Switches: WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED (reads + Draft) and, in addition,
WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED (approval). Neither enables academic-period transitions.
"""

import re
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, transaction
from django.db.models import Max

from apps.academic import dependencies, services
from apps.academic.models import Semester, SemesterStatus
from apps.access_control.models import Service
from apps.accounts.fields import CurrentTimestamp

from .models import CURRENCY, MAX_FEE_AMOUNT, FinanceAuditLog, RevisionStatus, SemesterFeeRevision, SemesterFeeSchedule

DB = DEFAULT_DB_ALIAS
PERMISSION_CODE = "finance.fee_schedule.manage"
FINANCE_SERVICE = "finance"
CONFIG_SETTING = "WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED"
APPROVAL_SETTING = "WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED"
EDITABLE_PERIODS = (SemesterStatus.DRAFT, SemesterStatus.ACTIVE)
REASON_MIN, REASON_MAX = 10, 500
MAX_WARNINGS = 10
_AMOUNT = re.compile(r"\d{1,6}(\.\d{1,2})?", re.ASCII)


class FeeConflict(Exception):
    """A fixed, non-sensitive refusal (409); nothing changed."""

    REASONS = frozenset({
        "period_closed", "draft_exists", "no_draft", "stale_version", "no_change", "reason_required",
        "approved_changed", "confirmation_required", "zero_confirmation_required", "warnings_changed",
        "impact_unavailable", "obligations_assessed", "transition_conflict",
    })

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "transition_conflict"
        super().__init__("The semester fee could not be changed.")


def configuration_enabled():
    return getattr(settings, CONFIG_SETTING, False) is True


def approval_enabled():
    return configuration_enabled() and getattr(settings, APPROVAL_SETTING, False) is True


def authorize(actor, gate=configuration_enabled):
    return services.authorize(actor, PERMISSION_CODE, gate=gate, admin_role_grant=True)


def _invalid(field, code="invalid"):
    raise services.AcademicPeriodInvalid({field: code})


def parse_amount(raw):
    """Exact PHP amount from a string ("1500", "1500.5", "0.00") or a JSON integer. Never a float,
    an empty value or null: "not configured" is never confused with zero."""
    if type(raw) is int:
        raw = str(raw)
    if type(raw) is not str:
        _invalid("amount", "required" if raw is None else "invalid")
    text = raw.strip()
    if not text:
        _invalid("amount", "required")
    if not _AMOUNT.fullmatch(text):
        _invalid("amount")
    try:
        value = Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        _invalid("amount")
    if not Decimal("0.00") <= value <= MAX_FEE_AMOUNT:
        _invalid("amount", "out_of_range")
    return value


def clean_reason(raw, required):
    if raw is None or (type(raw) is str and not raw.strip()):
        if required:
            raise FeeConflict("reason_required")
        return None
    if type(raw) is not str:
        _invalid("change_reason")
    text = " ".join(raw.split())
    if not REASON_MIN <= len(text) <= REASON_MAX or any(unicodedata.category(c).startswith("C") for c in text):
        _invalid("change_reason")
    return text


def _version(raw, field):
    if raw is None:
        return None
    if type(raw) is not int or not 1 <= raw <= services.MAX_ID:
        _invalid(field)
    return raw


def _amount_text(value):
    return None if value is None else f"{value:.2f}"


def _iso(value):
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


# ---- Read-only integration contracts --------------------------------------------------------

def _finance_service_active():
    return Service.objects.using(DB).filter(service_code=FINANCE_SERVICE, is_active=True).exists()


def _validated_current(schedule):
    """The current approved revision, or None when the persisted state is inconsistent."""
    current = schedule.current_approved_revision
    if current is None:
        return None
    approved = list(SemesterFeeRevision.objects.using(DB).filter(schedule=schedule, status=RevisionStatus.APPROVED))
    if (len(approved) != 1 or approved[0].pk != current.pk or current.schedule_id != schedule.pk
            or current.currency != CURRENCY or current.approved_slot != 1 or current.approved_at is None
            or current.approved_by_id is None or not Decimal("0.00") <= current.amount <= MAX_FEE_AMOUNT):
        return None
    return current


def fee_readiness(semester):
    """WF-11.01 activation contract (read-only; grants no fee-setting authority).

    Returns a dependencies.CheckResult for key ``approved_fee``:
      ready                                    - a genuinely approved rate exists (₱0.00 included)
      missing    no_fee_configured             - nothing configured for the semester
      missing    fee_awaiting_approval         - a Draft exists but no rate was approved
      unavailable fee_source_disabled          - the fee configuration switch is off
      unavailable finance_service_inactive     - the finance service is missing or inactive
      unavailable approved_fee_inconsistent    - persisted approval evidence does not validate
      unavailable fee_source_unavailable       - the fee tables cannot be read
    """
    key = "approved_fee"
    try:
        if not configuration_enabled():
            return dependencies.CheckResult(key, dependencies.UNAVAILABLE, "fee_source_disabled")
        if not _finance_service_active():
            return dependencies.CheckResult(key, dependencies.UNAVAILABLE, "finance_service_inactive")
        schedule = (SemesterFeeSchedule.objects.using(DB).select_related("current_approved_revision")
                    .filter(semester_id=semester.pk).first())
        if schedule is None:
            return dependencies.CheckResult(key, dependencies.MISSING, "no_fee_configured")
        if schedule.current_approved_revision_id is None:
            draft = SemesterFeeRevision.objects.using(DB).filter(schedule=schedule, status=RevisionStatus.DRAFT).exists()
            return dependencies.CheckResult(key, dependencies.MISSING, "fee_awaiting_approval" if draft else "no_fee_configured")
        if _validated_current(schedule) is None:
            return dependencies.CheckResult(key, dependencies.UNAVAILABLE, "approved_fee_inconsistent")
        return dependencies.CheckResult(key, dependencies.READY)
    except DatabaseError:
        return dependencies.CheckResult(key, dependencies.UNAVAILABLE, "fee_source_unavailable")


class ObligationImpact:
    """Would approving a new rate affect already assessed Student fee obligations?

    WF-07.02 obligations do not exist yet. Obligations can only be created by onboarding into the
    Active semester (dependencies.accepts_new_onboarding), so for a semester that was never
    activated there is nothing to affect ("not_applicable"), and with no previous approved rate
    there is nothing to replace. Otherwise the impact cannot be determined: "unavailable" (never 0).
    """

    def evaluate(self, semester, current_approved):
        if current_approved is None:
            return {"status": "not_applicable", "count": None, "reason": "no_previous_rate"}
        if semester.activated_at is None:
            return {"status": "not_applicable", "count": None, "reason": "semester_never_active"}
        return {"status": "unavailable", "count": None, "reason": "fee_obligations_not_implemented"}


DEFAULT_IMPACT = ObligationImpact()
_IMPACT_SUBSTITUTE = ContextVar("finance_obligation_impact_substitute", default=None)


@contextmanager
def isolated_impact(source):
    """TEST ONLY: substitute the impact source; refused outside the verified isolated database."""
    if not dependencies.isolated_test_database():
        raise dependencies.DependencyUnavailable("Substitute impact sources are refused outside isolated tests.")
    token = _IMPACT_SUBSTITUTE.set(source)
    try:
        yield
    finally:
        _IMPACT_SUBSTITUTE.reset(token)


def obligation_impact(semester, current_approved):
    source = _IMPACT_SUBSTITUTE.get()
    if source is None or not dependencies.isolated_test_database():
        source = DEFAULT_IMPACT
    try:
        result = source.evaluate(semester, current_approved)
    except Exception:  # an unknown is never "no impact"
        return {"status": "unavailable", "count": None, "reason": "source_unavailable"}
    if result.get("status") not in ("not_applicable", "evaluated", "unavailable"):
        return {"status": "unavailable", "count": None, "reason": "source_unavailable"}
    return result


# ---- Presentation (minimized: actor labels only) ---------------------------------------------

def _actor(account_id, viewer):
    if account_id is None:
        return None
    return "You" if account_id == viewer.pk else "An administrator"


def revision_payload(revision, viewer):
    return {"revision_id": revision.pk, "revision_number": revision.revision_number, "currency": revision.currency,
            "amount": _amount_text(revision.amount), "status": revision.status, "version": revision.version,
            "change_reason": revision.change_reason,
            "configured_by": _actor(revision.configured_by_id, viewer), "configured_at": _iso(revision.configured_at),
            "approved_by": _actor(revision.approved_by_id, viewer), "approved_at": _iso(revision.approved_at),
            "superseded_at": _iso(revision.superseded_at), "withdrawn_at": _iso(revision.withdrawn_at)}


def semester_ref(semester):
    return {"semester_id": semester.pk, "term": "first" if semester.term == 1 else "second", "label": semester.label,
            "status": semester.status, "school_year_id": semester.school_year_id,
            "school_year_label": semester.school_year.label}


def _state(schedule):
    if schedule is None:
        return "not_configured"
    has_draft = SemesterFeeRevision.objects.using(DB).filter(schedule=schedule, status=RevisionStatus.DRAFT).exists()
    if schedule.current_approved_revision_id is None:
        return "draft" if has_draft else "not_configured"
    return "approved_with_draft" if has_draft else "approved"


def feature_flags():
    return {"configuration": configuration_enabled(), "approval": approval_enabled()}


def _load_semester(semester_id):
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    semester = Semester.objects.using(DB).select_related("school_year").filter(pk=semester_id).first()
    if semester is None:
        raise services.AcademicPeriodNotFound()
    return semester


def _schedule_of(semester):
    return (SemesterFeeSchedule.objects.using(DB).select_related("current_approved_revision")
            .filter(semester=semester).first())


def semester_fee_payload(semester, viewer):
    schedule = _schedule_of(semester)
    revisions = (list(SemesterFeeRevision.objects.using(DB).filter(schedule=schedule).order_by("-revision_number"))
                 if schedule else [])
    current = next((r for r in revisions if r.status == RevisionStatus.APPROVED), None)
    draft = next((r for r in revisions if r.status == RevisionStatus.DRAFT), None)
    return {"semester": semester_ref(semester), "schedule_id": schedule.pk if schedule else None,
            "schedule_version": schedule.version if schedule else None, "state": _state(schedule),
            "current_approved": revision_payload(current, viewer) if current else None,
            "draft": revision_payload(draft, viewer) if draft else None,
            "revisions": [revision_payload(r, viewer) for r in revisions[:50]],
            "editable": semester.status in EDITABLE_PERIODS,
            "reason_required": current is not None,
            "readiness": fee_readiness(semester).as_dict(), "features": feature_flags()}


# ---- Reads ------------------------------------------------------------------------------------

def list_semester_fees(*, actor):
    auth = authorize(actor)
    rows = Semester.objects.using(DB).select_related("school_year").order_by("-school_year__start_year", "term")[:40]
    results = []
    for semester in rows:
        schedule = _schedule_of(semester)
        current = schedule.current_approved_revision if schedule else None
        results.append({"semester": semester_ref(semester), "state": _state(schedule),
                        "approved_amount": _amount_text(current.amount) if current else None,
                        "current_revision_number": current.revision_number if current else None})
    return {"results": results, "features": feature_flags(), "viewer": _actor(auth.account.pk, auth.account)}


def get_semester_fee(*, actor, semester_id):
    auth = authorize(actor)
    return semester_fee_payload(_load_semester(semester_id), auth.account)


def fee_history(*, actor, semester_id):
    auth = authorize(actor)
    semester = _load_semester(semester_id)
    rows = (FinanceAuditLog.objects.using(DB).filter(semester_id=semester.pk)
            .order_by("-finance_audit_log_id")
            .values("action", "actor_account_id", "old_value", "new_value", "created_at")[:50])
    return {"semester": semester_ref(semester),
            "results": [{"event": r["action"], "occurred_at": _iso(r["created_at"]),
                         "actor": _actor(r["actor_account_id"], auth.account),
                         "before": r["old_value"], "after": r["new_value"]} for r in rows]}


def readiness_for_activation(*, actor, semester_id):
    """Read-only readiness for the academic activation actor (academic.periods.manage); this
    deliberately does NOT require, or grant, finance.fee_schedule.manage."""
    services.authorize(actor, services.PERMISSION_CODE, gate=configuration_enabled)
    semester = _load_semester(semester_id)
    return {"semester": semester_ref(semester), "readiness": fee_readiness(semester).as_dict()}


# ---- Writes -----------------------------------------------------------------------------------

def _audit(auth, action, entity_type, entity_id, semester_id, old=None, new=None, reason="fee_configuration"):
    if not transaction.get_connection(DB).in_atomic_block:
        raise services.AcademicPeriodUnavailable("Audit requires the change's transaction.")
    FinanceAuditLog.objects.using(DB).create(
        actor_account=auth.account, acting_role_id=auth.acting_role_id, action=action, entity_type=entity_type,
        entity_id=entity_id, semester_id=semester_id, old_value=old, new_value=new, reason=reason)


def _write(actor, gate, fn):
    if not configuration_enabled():
        raise services.AcademicPeriodUnavailable("Semester fee configuration is not activated.")
    if not gate():
        raise services.AcademicPeriodFeatureDisabled("Semester fee approval is not enabled.")
    authorize(actor, gate=gate)
    try:
        with transaction.atomic(using=DB, durable=True):
            auth = services.lock_and_authorize(actor, PERMISSION_CODE, gate=gate, admin_role_grant=True)
            return fn(auth)
    except IntegrityError as exc:
        raise FeeConflict("transition_conflict") from exc


def _locked_period(semester_id):
    semester = Semester.objects.using(DB).select_for_update().filter(pk=semester_id).first()
    if semester is None:
        raise services.AcademicPeriodNotFound()
    if semester.status not in EDITABLE_PERIODS:
        raise FeeConflict("period_closed")  # Closed/Archived fee history is never amended here
    schedule = SemesterFeeSchedule.objects.using(DB).select_for_update().filter(semester=semester).first()
    revisions = (list(SemesterFeeRevision.objects.using(DB).select_for_update().filter(schedule=schedule)
                      .order_by("revision_id")) if schedule else [])
    return semester, schedule, revisions


def save_draft(*, actor, semester_id, amount, expected_draft_version, change_reason=None):
    """Create (expected_draft_version None) or edit the semester's single open Draft revision.
    Saving NEVER approves. After a rate is approved, every new revision needs a change reason."""
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    value = parse_amount(amount)
    expected = _version(expected_draft_version, "expected_draft_version")

    def apply(auth):
        semester, schedule, revisions = _locked_period(semester_id)
        current = next((r for r in revisions if r.status == RevisionStatus.APPROVED), None)
        draft = next((r for r in revisions if r.status == RevisionStatus.DRAFT), None)
        reason = clean_reason(change_reason, required=current is not None)
        if schedule is None:
            schedule = SemesterFeeSchedule.objects.using(DB).create(semester=semester, created_by=auth.account)
        if expected is None:
            if draft is not None:
                raise FeeConflict("draft_exists")
            if current is not None and current.amount == value:
                raise FeeConflict("no_change")
            number = (SemesterFeeRevision.objects.using(DB).filter(schedule=schedule)
                      .aggregate(n=Max("revision_number"))["n"] or 0) + 1
            draft = SemesterFeeRevision.objects.using(DB).create(
                schedule=schedule, revision_number=number, amount=value, draft_slot=1, change_reason=reason,
                configured_by=auth.account)
            old, action = None, "finance.semester_fee.draft.create"
        else:
            if draft is None:
                raise FeeConflict("no_draft")
            if draft.version != expected:
                raise FeeConflict("stale_version")
            if (draft.amount, draft.change_reason) == (value, reason):
                raise FeeConflict("no_change")
            old = {"amount": _amount_text(draft.amount), "version": draft.version}
            SemesterFeeRevision.objects.using(DB).filter(pk=draft.pk, version=expected, status=RevisionStatus.DRAFT).update(
                amount=value, change_reason=reason, version=expected + 1, updated_at=CurrentTimestamp())
            draft.refresh_from_db()
            action = "finance.semester_fee.draft.update"
        SemesterFeeSchedule.objects.using(DB).filter(pk=schedule.pk).update(
            version=schedule.version + 1, updated_at=CurrentTimestamp())
        _audit(auth, action, "fee_revision", draft.pk, semester.pk, old,
               {"revision_number": draft.revision_number, "amount": _amount_text(draft.amount), "currency": CURRENCY,
                "version": draft.version, "change_reason_recorded": reason is not None}, reason="fee_draft")
        return semester.pk
    return get_semester_fee(actor=actor, semester_id=_write(actor, configuration_enabled, apply))


def withdraw_draft(*, actor, semester_id, expected_draft_version):
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    expected = _version(expected_draft_version, "expected_draft_version")
    if expected is None:
        _invalid("expected_draft_version", "required")

    def apply(auth):
        semester, _schedule, revisions = _locked_period(semester_id)
        draft = next((r for r in revisions if r.status == RevisionStatus.DRAFT), None)
        if draft is None:
            raise FeeConflict("no_draft")
        if draft.version != expected:
            raise FeeConflict("stale_version")
        SemesterFeeRevision.objects.using(DB).filter(pk=draft.pk, status=RevisionStatus.DRAFT).update(
            status=RevisionStatus.WITHDRAWN, draft_slot=None, withdrawn_at=CurrentTimestamp(),
            version=expected + 1, updated_at=CurrentTimestamp())
        _audit(auth, "finance.semester_fee.draft.withdraw", "fee_revision", draft.pk, semester.pk,
               {"status": "Draft", "amount": _amount_text(draft.amount)}, {"status": "Withdrawn"}, reason="fee_draft")
        return semester.pk
    pk = _write(actor, configuration_enabled, apply)
    return get_semester_fee(actor=actor, semester_id=pk)


def _warnings(semester, draft, current):
    warnings = []
    if draft.amount == Decimal("0.00"):
        warnings.append("zero_amount")
    if current is not None:
        warnings.append("replaces_approved_rate")
    if semester.status == SemesterStatus.ACTIVE:
        warnings.append("semester_is_active")
    return warnings


def _impact_blocker(impact):
    if impact["status"] == "unavailable":
        return "impact_unavailable"
    if impact["status"] == "evaluated" and impact.get("count"):
        return "obligations_assessed"  # a controlled financial adjustment workflow is required (not built)
    return None


def approval_preview(*, actor, semester_id):
    auth = authorize(actor)
    semester = _load_semester(semester_id)
    schedule = _schedule_of(semester)
    revisions = list(SemesterFeeRevision.objects.using(DB).filter(schedule=schedule)) if schedule else []
    draft = next((r for r in revisions if r.status == RevisionStatus.DRAFT), None)
    current = next((r for r in revisions if r.status == RevisionStatus.APPROVED), None)
    impact = obligation_impact(semester, current)
    blockers = []
    if semester.status not in EDITABLE_PERIODS:
        blockers.append("period_closed")
    if draft is None:
        blockers.append("no_draft")
    blocker = _impact_blocker(impact)
    if blocker:
        blockers.append(blocker)
    enabled = approval_enabled()
    if not enabled:
        blockers.append("feature_disabled")
    return {"semester": semester_ref(semester),
            "proposed": revision_payload(draft, auth.account) if draft else None,
            "current_approved": revision_payload(current, auth.account) if current else None,
            "impact": impact, "warnings": _warnings(semester, draft, current) if draft else [],
            "blockers": blockers, "feature_enabled": enabled, "can_confirm": not blockers}


def approve(*, actor, semester_id, revision_id, expected_version, expected_current_approved_revision_id,
            acknowledged_warnings, confirmed, confirm_zero_amount=False):
    """Explicit, attributable approval of the semester's open Draft as the ONE current rate.

    The previous approved revision (if any) becomes Superseded and stays as history. Re-validated
    under lock: the exact Draft and version reviewed, the current approved rate shown, the warnings
    shown, the obligation impact, and an explicit zero-amount confirmation for ₱0.00.
    """
    if not approval_enabled():
        if not configuration_enabled():
            raise services.AcademicPeriodUnavailable("Semester fee configuration is not activated.")
        raise services.AcademicPeriodFeatureDisabled("Semester fee approval is not enabled.")
    if confirmed is not True:
        raise FeeConflict("confirmation_required")
    if type(semester_id) is not int or not 1 <= semester_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    revision_id = _version(revision_id, "revision_id")
    expected_version = _version(expected_version, "expected_version")
    if revision_id is None or expected_version is None:
        _invalid("revision_id" if revision_id is None else "expected_version", "required")
    expected_current = _version(expected_current_approved_revision_id, "expected_current_approved_revision_id")
    if (type(acknowledged_warnings) is not list or len(acknowledged_warnings) > MAX_WARNINGS
            or any(type(w) is not str or len(w) > 40 for w in acknowledged_warnings)):
        _invalid("acknowledged_warnings")
    if type(confirm_zero_amount) is not bool:
        _invalid("confirm_zero_amount")

    def apply(auth):
        semester, schedule, revisions = _locked_period(semester_id)
        draft = next((r for r in revisions if r.status == RevisionStatus.DRAFT), None)
        current = next((r for r in revisions if r.status == RevisionStatus.APPROVED), None)
        if draft is None or draft.pk != revision_id:
            raise FeeConflict("no_draft")
        if draft.version != expected_version:
            raise FeeConflict("stale_version")
        if (current.pk if current else None) != expected_current or schedule.current_approved_revision_id != (
                current.pk if current else None):
            raise FeeConflict("approved_changed")
        blocker = _impact_blocker(obligation_impact(semester, current))
        if blocker:
            raise FeeConflict(blocker)
        warnings = _warnings(semester, draft, current)
        if frozenset(warnings) != frozenset(acknowledged_warnings):
            raise FeeConflict("warnings_changed")
        if draft.amount == Decimal("0.00") and confirm_zero_amount is not True:
            raise FeeConflict("zero_confirmation_required")
        db = SemesterFeeRevision.objects.using(DB)
        if current is not None:
            # Free the single approved slot BEFORE taking it; the old rate stays as history.
            db.filter(pk=current.pk, status=RevisionStatus.APPROVED).update(
                status=RevisionStatus.SUPERSEDED, approved_slot=None, superseded_at=CurrentTimestamp(),
                version=current.version + 1, updated_at=CurrentTimestamp())
        changed = db.filter(pk=draft.pk, status=RevisionStatus.DRAFT, version=expected_version).update(
            status=RevisionStatus.APPROVED, draft_slot=None, approved_slot=1, approved_by=auth.account,
            approved_at=CurrentTimestamp(), version=expected_version + 1, updated_at=CurrentTimestamp())
        if changed != 1:
            raise FeeConflict("transition_conflict")
        SemesterFeeSchedule.objects.using(DB).filter(pk=schedule.pk).update(
            current_approved_revision=draft.pk, version=schedule.version + 1, updated_at=CurrentTimestamp())
        _audit(auth, "finance.semester_fee.approve", "fee_revision", draft.pk, semester.pk,
               {"current_approved_revision_id": current.pk if current else None,
                "amount": _amount_text(current.amount) if current else None},
               {"revision_id": draft.pk, "revision_number": draft.revision_number, "amount": _amount_text(draft.amount),
                "currency": CURRENCY, "zero_amount_confirmed": draft.amount == Decimal("0.00"),
                "acknowledged_warnings": sorted(warnings)}, reason="fee_approval")
        return semester.pk
    pk = _write(actor, approval_enabled, apply)
    return get_semester_fee(actor=actor, semester_id=pk)
