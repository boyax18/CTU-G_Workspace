"""WF-11.01 Draft academic-period management (owner-authorized restricted local development).

Every operation, read or write, is authorized afresh through Hybrid Dynamic Access Control:

1. ``WORKSPACE_ACADEMIC_PERIODS_ENABLED`` is exactly True (default off), and the protected
   executor is not enabled (it has no academic-period operation; refuse rather than bypass it).
2. The actor is a persisted, active, Approved Workspace account; never a framework
   ``is_staff``/``is_superuser`` account, a role name, a session claim or frontend visibility.
3. The actor holds a genuine active ``Admin`` assignment. A Technical Super Admin without one
   receives nothing; with one, the access comes from that stored Admin assignment only.
4. When role-context enforcement is in effect, the selected context must be Admin, or Technical
   Super Admin inheriting the actor's genuine Admin assignment (allowed_role_ids). Absent, stale
   or cross-account context fails closed.
5. The ``academic`` service is active and the exact ``academic.periods.manage`` permission is
   effective (apps.access_control.services.has_permission: account-specific Deny wins).

Mutations repeat steps 1-5 inside one durable transaction after locking, in the shared order,
the academic service row, the permission row and the actor's account row, so a concurrent Deny,
revocation or service deactivation is either seen or serialized. The change and its append-only
audit row commit together or not at all.

Scope exclusions (WF-11.01 restricted slice): no activation/closure/archiving here (see
lifecycle.py, unreachable at runtime), no fee or curriculum records, no Student participation,
clearance or fee obligations, and no ``finance.fee_schedule.manage`` use.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction
from django.db.models import ProtectedError, RestrictedError

from apps.access_control.models import AccountRole, Permission, RolePermission, Service
from apps.access_control.services import has_permission
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from apps.accounts.active_role_context import allowed_role_ids, context_enabled, selected_scope
from apps.accounts.fields import CurrentTimestamp
from apps.accounts.models import Account

from . import periods
from .models import AcademicPeriodAuditLog, SchoolYear, Semester, SemesterStatus, SemesterTerm

PERMISSION_CODE = "academic.periods.manage"
SERVICE_CODE = "academic"
GATE_SETTING = "WORKSPACE_ACADEMIC_PERIODS_ENABLED"
PAGE_SIZE = 20
MAX_PAGE = 500
MAX_ID = 2_147_483_647

CREATE_ACTION = "academic.school_year.create"
DATES_ACTION = "academic.semester.dates.update"
DELETE_ACTION = "academic.school_year.delete"
REASON_SETUP = "period_setup"
REASON_CORRECTION = "draft_correction"
REASON_DELETE = "unused_draft_deletion"


class AcademicPeriodUnavailable(Exception):
    """Gate off, executor enabled, service/permission rows missing or database unsuitable (503)."""


class AcademicPeriodFeatureDisabled(AcademicPeriodUnavailable):
    """A separately gated capability (transitions, corrections) is switched off (503 feature_disabled)."""


class AcademicPeriodDenied(Exception):
    """Not an eligible, authorized School Admin in a permitted role context (403)."""

    def __init__(self, reason="access_denied"):
        self.reason = reason if reason in {"access_denied", "admin_context_required"} else "access_denied"
        super().__init__("Academic-period management is not permitted.")


class AcademicPeriodNotFound(Exception):
    """Unknown School Year or semester (404); never distinguishes further."""


class AcademicPeriodConflict(Exception):
    """A fixed, non-sensitive business-rule refusal (409). The original state is retained."""

    REASONS = frozenset({
        "school_year_exists", "stale_version", "period_not_draft", "semesters_overlap",
        "cross_year_overlap", "period_in_use", "confirmation_mismatch",
        # WF11-D05/D06 controlled edits and historical corrections.
        "period_is_draft", "impact_unavailable", "impact_review_required", "no_change",
    })

    def __init__(self, reason, details=()):
        self.reason = reason if reason in self.REASONS else "stale_version"
        self.details = tuple(details)
        super().__init__("The academic period could not be changed.")


class AcademicPeriodInvalid(Exception):
    """Request values failed validation (400). ``fields`` maps a field to ONE fixed code."""

    def __init__(self, fields):
        self.fields = dict(fields)
        super().__init__("Check the submitted academic-period details.")


@dataclass(frozen=True)
class Authorization:
    account: Account
    acting_role_id: int | None


def gate_open():
    return getattr(settings, GATE_SETTING, False) is True


def _executor_enabled():
    from apps.access_control.executor.client import enabled
    try:
        return enabled()
    except WriterBoundaryUnavailable:
        return True  # an invalid writer configuration is never a reason to proceed


def authorize(actor, permission_code=PERMISSION_CODE, gate=None, admin_role_grant=False):
    """Steps 1-5 of the module docstring, from fresh database reads. Returns Authorization.

    ``permission_code`` is the operation's exact catalogue code (academic configuration reuses this
    evaluator with academic.courses.manage, clearance.subjects.manage, ...); ``gate`` is the
    operation's own default-off switch (the period gate when omitted). The code's own service must
    be active too (has_permission filters on it), in addition to the academic service.
    """
    if not (gate or gate_open)():
        raise AcademicPeriodUnavailable("Academic-period management is not activated.")
    if _executor_enabled():
        raise AcademicPeriodUnavailable("The protected writer has no academic-period operation.")
    if (not isinstance(actor, Account) or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS
            or type(actor.pk) is not int or not 1 <= actor.pk <= MAX_ID):
        raise AcademicPeriodDenied()
    account = Account.objects.using(DEFAULT_DB_ALIAS).filter(pk=actor.pk).first()
    if (account is None or account.is_staff or account.is_superuser or not account.is_active
            or account.request_status != "Approved"):
        raise AcademicPeriodDenied()
    admin_role_ids = frozenset(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
        account_id=account.pk, role__role_name="Admin", role__is_active=True,
    ).values_list("role_id", flat=True))
    if not admin_role_ids:
        raise AcademicPeriodDenied()
    acting_role_id = None
    if context_enabled():
        scope = selected_scope()
        if scope is None or scope.account_id != account.pk or scope.role_id is None:
            raise AcademicPeriodDenied("admin_context_required")
        # Admin selected, or Technical Super Admin inheriting THIS account's stored Admin role.
        if not allowed_role_ids(account.pk, scope.role_id) & admin_role_ids:
            raise AcademicPeriodDenied("admin_context_required")
        acting_role_id = scope.role_id
    service = Service.objects.using(DEFAULT_DB_ALIAS).filter(service_code=SERVICE_CODE).first()
    if service is None or not service.is_active:
        raise AcademicPeriodUnavailable("The academic service is not active.")
    if type(permission_code) is not str or not has_permission(account, permission_code):
        raise AcademicPeriodDenied()
    if admin_role_grant:
        # Narrowing only (semester fee setting): the code must reach this account through an active
        # grant of one of its genuine Admin roles. Another role's grant (e.g. the pinned Treasurer
        # default) or a direct account Grant alone never authorizes, even when role context is off.
        if not RolePermission.objects.using(DEFAULT_DB_ALIAS).filter(
                role_id__in=admin_role_ids, role__is_active=True, is_active=True,
                permission__permission_code=permission_code).exists():
            raise AcademicPeriodDenied()
    return Authorization(account, acting_role_id)


def _atomic():
    return transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True)


def lock_and_authorize(actor, permission_code=PERMISSION_CODE, gate=None, admin_role_grant=False):
    """Inside the caller's transaction: lock services -> permission -> account, then re-authorize.

    Every academic write locks the academic service row first, so all academic writes serialize
    in one order (the code's own service, e.g. clearance, is locked in the same service_id order).
    """
    connection = transaction.get_connection(DEFAULT_DB_ALIAS)
    if connection.vendor != "mysql" or not connection.in_atomic_block:
        raise AcademicPeriodUnavailable("Academic periods require a primary MySQL transaction.")
    owning = (Permission.objects.using(DEFAULT_DB_ALIAS).filter(permission_code=permission_code)
              .values_list("service__service_code", flat=True).first())
    codes = {SERVICE_CODE, owning} if owning else {SERVICE_CODE}
    services = list(Service.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                    .filter(service_code__in=codes).order_by("service_id"))
    by_code = {row.service_code: row for row in services}
    if set(by_code) != codes or not all(row.is_active for row in services) or owning is None:
        raise AcademicPeriodUnavailable("The academic service or the operation's service is not active.")
    permissions = list(Permission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                       .filter(permission_code=permission_code, service_id=by_code[owning].pk).order_by("permission_id"))
    if len(permissions) != 1:
        raise AcademicPeriodUnavailable("Academic authority is not provisioned.")
    if isinstance(actor, Account) and type(actor.pk) is int:
        list(Account.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk=actor.pk))
    if permission_code == PERMISSION_CODE and gate is None:
        return authorize(actor)
    return authorize(actor, permission_code, gate, admin_role_grant)


def write_audit(auth, *, action, school_year_id, semester_id=None, old_value=None, new_value=None, reason,
                reason_note=None):
    """Append-only audit inside the caller's transaction; a failure rolls the change back."""
    if not transaction.get_connection(DEFAULT_DB_ALIAS).in_atomic_block:
        raise AcademicPeriodUnavailable("Audit requires the change's transaction.")
    AcademicPeriodAuditLog.objects.using(DEFAULT_DB_ALIAS).create(
        actor_account=auth.account, acting_role_id=auth.acting_role_id, action=action,
        school_year_id=school_year_id, semester_id=semester_id,
        old_value=old_value, new_value=new_value, reason=reason, reason_note=reason_note,
    )


# ---- Presentation (minimized: no actor identities, audit contents or internal slots) ----------

def _iso(value):
    return value.isoformat() if value is not None else None


def activation_missing(semester):
    from .dependencies import missing_prerequisites
    return missing_prerequisites(semester)


def activation_readiness(semester):
    """Presentation only: the real prerequisite checks with fixed reason codes, so the UI can say what to
    do next. Activation re-evaluates everything under lock; ``available`` never authorizes anything."""
    from .dependencies import READY, evaluate_prerequisites
    from .lifecycle import transitions_enabled
    checks = evaluate_prerequisites(semester)
    missing = [c.key for c in checks if c.status != READY]
    return {"available": semester.status == SemesterStatus.DRAFT and not missing and transitions_enabled(),
            "missing": missing, "checks": [c.as_dict() for c in checks]}


def feature_flags():
    """Server-side switch state for the UI ("Feature unavailable"); never authorization."""
    from .corrections import corrections_enabled
    from .lifecycle import transitions_enabled
    return {"transitions": transitions_enabled(), "corrections": corrections_enabled()}


def semester_snapshot(semester):
    return {"semester_id": semester.pk, "term": periods.term_key(semester.term), "status": semester.status,
            "start_date": _iso(semester.start_date), "end_date": _iso(semester.end_date), "version": semester.version}


def semester_payload(semester):
    payload = semester_snapshot(semester)
    payload.update(
        label=semester.label,
        can_edit_dates=semester.status == SemesterStatus.DRAFT,
        # Read-only readiness from the real dependency contract; "available" never authorizes.
        activation=activation_readiness(semester),
        updated_at=_iso(semester.updated_at),
    )
    return payload


def _dependents_exist(instance, skip_models=()):
    for relation in instance._meta.related_objects:
        if relation.related_model in skip_models:
            continue
        manager = relation.related_model._default_manager.using(DEFAULT_DB_ALIAS)
        if manager.filter(**{relation.field.name: instance}).exists():
            return True
    return False


def deletion_blocker(school_year, semesters):
    """None when the year is a genuinely unused Draft; otherwise a fixed reason code."""
    if len(semesters) != 2:
        return "period_in_use"
    for semester in semesters:
        if (semester.status != SemesterStatus.DRAFT or semester.activated_at is not None
                or semester.closed_at is not None or semester.archived_at is not None):
            return "period_not_draft"
    if _dependents_exist(school_year, skip_models=(Semester,)) or any(_dependents_exist(s) for s in semesters):
        return "period_in_use"
    return None


def school_year_payload(school_year, semesters=None):
    semesters = sorted(semesters if semesters is not None else school_year.semesters.all(), key=lambda s: s.term)
    return {
        "school_year_id": school_year.pk, "start_year": school_year.start_year, "end_year": school_year.end_year,
        "label": school_year.label,
        "status": periods.derive_school_year_status([s.status for s in semesters]),
        "semesters": [semester_payload(s) for s in semesters],
        "can_delete": deletion_blocker(school_year, semesters) is None,
        "created_at": _iso(school_year.created_at), "updated_at": _iso(school_year.updated_at),
    }


# ---- Reads -------------------------------------------------------------------------------------

def list_school_years(*, actor, page=1):
    authorize(actor)
    if type(page) is not int or not 1 <= page <= MAX_PAGE:
        raise AcademicPeriodInvalid({"page": "invalid"})
    start = (page - 1) * PAGE_SIZE
    rows = list(SchoolYear.objects.using(DEFAULT_DB_ALIAS).prefetch_related("semesters")
                .order_by("-start_year", "-school_year_id")[start:start + PAGE_SIZE + 1])
    return {"results": [school_year_payload(row) for row in rows[:PAGE_SIZE]],
            "page": page, "page_size": PAGE_SIZE, "has_next": len(rows) > PAGE_SIZE,
            "features": feature_flags()}


# ---- Writes ------------------------------------------------------------------------------------

def create_school_year(*, actor, start_year):
    """WF11-D01/D08: one School Year plus exactly two Draft semesters, atomically.

    A duplicate (including a concurrent duplicate that loses the lock race or the UNIQUE index)
    changes nothing and is reported as ``school_year_exists``.
    """
    if not periods.valid_start_year(start_year):
        raise AcademicPeriodInvalid({"start_year": "invalid"})
    authorize(actor)  # fail fast without taking locks
    try:
        with _atomic():
            auth = lock_and_authorize(actor)
            db = SchoolYear.objects.using(DEFAULT_DB_ALIAS)
            if db.filter(start_year=start_year).exists():
                raise AcademicPeriodConflict("school_year_exists")
            school_year = db.create(start_year=start_year, created_by=auth.account)
            semesters = [Semester.objects.using(DEFAULT_DB_ALIAS).create(school_year=school_year, term=term)
                         for term in (SemesterTerm.FIRST, SemesterTerm.SECOND)]
            write_audit(auth, action=CREATE_ACTION, school_year_id=school_year.pk, reason=REASON_SETUP,
                        new_value={"start_year": start_year,
                                   "semesters": [{"semester_id": s.pk, "term": periods.term_key(s.term),
                                                  "status": SemesterStatus.DRAFT} for s in semesters]})
    except IntegrityError as exc:
        raise AcademicPeriodConflict("school_year_exists") from exc
    created = SchoolYear.objects.using(DEFAULT_DB_ALIAS).prefetch_related("semesters").get(pk=school_year.pk)
    return school_year_payload(created)


def _date_fields(start_date, end_date):
    parsed, errors = {}, {}
    for name, raw in (("start_date", start_date), ("end_date", end_date)):
        try:
            parsed[name] = periods.parse_iso_date(raw)
        except ValueError:
            errors[name] = "invalid"
    if errors:
        raise AcademicPeriodInvalid(errors)
    return parsed["start_date"], parsed["end_date"]


def update_semester_dates(*, actor, semester_id, start_date, end_date, expected_version,
                          acknowledge_cross_year_overlap=False):
    """Configure a Draft semester's dates (WF11-D10). Dates may be cleared or left incomplete.

    Rules: start strictly before end; both within the School Year's two calendar years; the First
    semester ends before the Second starts (a break is allowed); only Draft periods; the caller's
    confirmed ``expected_version`` must still hold. A complete range that overlaps a semester of
    another School Year is a reviewed warning: refused until explicitly acknowledged, then audited.
    """
    if type(semester_id) is not int or not 1 <= semester_id <= MAX_ID:
        raise AcademicPeriodNotFound()
    if type(expected_version) is not int or not 1 <= expected_version <= MAX_ID:
        raise AcademicPeriodInvalid({"expected_version": "invalid"})
    if type(acknowledge_cross_year_overlap) is not bool:
        raise AcademicPeriodInvalid({"acknowledge_cross_year_overlap": "invalid"})
    start, end = _date_fields(start_date, end_date)
    authorize(actor)
    with _atomic():
        auth = lock_and_authorize(actor)
        semester_db = Semester.objects.using(DEFAULT_DB_ALIAS)
        year_id = semester_db.filter(pk=semester_id).values_list("school_year_id", flat=True).first()
        if year_id is None:
            raise AcademicPeriodNotFound()
        school_year = SchoolYear.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk=year_id).first()
        pair = {s.term: s for s in semester_db.select_for_update().filter(school_year_id=year_id).order_by("semester_id")}
        target = next((s for s in pair.values() if s.pk == semester_id), None)
        if school_year is None or target is None or set(pair) != {SemesterTerm.FIRST, SemesterTerm.SECOND}:
            raise AcademicPeriodNotFound()
        if target.status != SemesterStatus.DRAFT:
            raise AcademicPeriodConflict("period_not_draft")
        if target.version != expected_version:
            raise AcademicPeriodConflict("stale_version")
        problem = periods.range_problem(start, end, school_year.start_year)
        if problem is not None:
            raise AcademicPeriodInvalid({"end_date" if problem == "start_not_before_end" else "start_date": problem})
        if (target.start_date, target.end_date) == (start, end):
            return school_year_payload(school_year, list(pair.values()))  # nothing to change, nothing audited
        sibling = pair[SemesterTerm.SECOND if target.term == SemesterTerm.FIRST else SemesterTerm.FIRST]
        first = (start, end) if target.term == SemesterTerm.FIRST else (sibling.start_date, sibling.end_date)
        second = (start, end) if target.term == SemesterTerm.SECOND else (sibling.start_date, sibling.end_date)
        if periods.terms_overlap(first, second):
            raise AcademicPeriodConflict("semesters_overlap")
        cross_year = start is not None and end is not None and any(
            periods.ranges_intersect(start, end, other.start_date, other.end_date)
            for other in semester_db.exclude(school_year_id=year_id).filter(
                start_date__isnull=False, end_date__isnull=False, start_date__lte=end, end_date__gte=start)
        )
        if cross_year and not acknowledge_cross_year_overlap:
            raise AcademicPeriodConflict("cross_year_overlap")
        before = semester_snapshot(target)
        semester_db.filter(pk=target.pk, version=expected_version).update(
            start_date=start, end_date=end, version=expected_version + 1, updated_at=CurrentTimestamp())
        SchoolYear.objects.using(DEFAULT_DB_ALIAS).filter(pk=year_id).update(updated_at=CurrentTimestamp())
        target.refresh_from_db()
        after = semester_snapshot(target)
        if cross_year:
            after["cross_year_overlap_acknowledged"] = True
        write_audit(auth, action=DATES_ACTION, school_year_id=year_id, semester_id=target.pk,
                    old_value=before, new_value=after, reason=REASON_CORRECTION)
    refreshed = SchoolYear.objects.using(DEFAULT_DB_ALIAS).prefetch_related("semesters").get(pk=year_id)
    return school_year_payload(refreshed)


def delete_school_year(*, actor, school_year_id, expected_start_year):
    """WF11-D07: permanently delete ONLY a genuinely unused Draft year with its two Draft semesters.

    Never-activated, no dependent records, and the caller must confirm the year it saw. History of
    the year (its audit rows) is kept; the deletion itself is audited in the same transaction.
    """
    if type(school_year_id) is not int or not 1 <= school_year_id <= MAX_ID:
        raise AcademicPeriodNotFound()
    if not periods.valid_start_year(expected_start_year):
        raise AcademicPeriodInvalid({"expected_start_year": "invalid"})
    authorize(actor)
    try:
        with _atomic():
            auth = lock_and_authorize(actor)
            school_year = SchoolYear.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(pk=school_year_id).first()
            if school_year is None:
                raise AcademicPeriodNotFound()
            semesters = list(Semester.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                             .filter(school_year_id=school_year.pk).order_by("semester_id"))
            if school_year.start_year != expected_start_year:
                raise AcademicPeriodConflict("confirmation_mismatch")
            blocker = deletion_blocker(school_year, semesters)
            if blocker is not None:
                raise AcademicPeriodConflict(blocker)
            snapshot = {"start_year": school_year.start_year,
                        "semesters": [semester_snapshot(s) for s in sorted(semesters, key=lambda s: s.term)]}
            Semester.objects.using(DEFAULT_DB_ALIAS).filter(pk__in=[s.pk for s in semesters]).delete()
            school_year.delete(using=DEFAULT_DB_ALIAS)
            write_audit(auth, action=DELETE_ACTION, school_year_id=school_year_id, old_value=snapshot,
                        reason=REASON_DELETE)
    except (ProtectedError, RestrictedError, IntegrityError) as exc:
        raise AcademicPeriodConflict("period_in_use") from exc
    return {"deleted": True, "school_year_id": school_year_id}
