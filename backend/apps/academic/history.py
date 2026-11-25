"""WF-11.01 academic-period history (WF11-D13 School Admin scope): read-only, minimized.

Entries come from the append-only AcademicPeriodAuditLog of ONE existing School Year, newest
first. Each entry is rebuilt from an allowlist: a fixed event label, the time, a server-made actor
label ("You" / "An administrator"), the semester term, before/after values of dates and status,
the reason code and the correction note. Account IDs, acting roles and raw JSON are never returned.
"""

from django.db import DEFAULT_DB_ALIAS

from . import services
from .models import AcademicPeriodAuditLog, SchoolYear

PAGE_SIZE = 20
EVENTS = {
    "academic.school_year.create": "School year created",
    "academic.semester.dates.update": "Draft dates updated",
    "academic.semester.activate": "Semester activated",
    "academic.semester.close": "Semester closed",
    "academic.semester.archive": "Semester archived",
    "academic.semester.active_edit": "Active semester edited",
    "academic.semester.historical_correction": "Historical correction",
}
_FIELDS = ("start_date", "end_date", "status")
_TERMS = {"first": "first", "second": "second"}
_REASONS = frozenset({"period_setup", "draft_correction", "manual_transition", "calendar_change",
                      "data_entry_correction", "institutional_directive"})


def _value(snapshot, field):
    value = snapshot.get(field) if isinstance(snapshot, dict) else None
    return value if value is None or (type(value) is str and len(value) <= 20) else None


def _entry(row, viewer):
    old, new = row["old_value"], row["new_value"]
    changes = {}
    for field in _FIELDS:
        before, after = _value(old, field), _value(new, field)
        if before != after:
            changes[field] = {"before": before, "after": after}
    term = _value(new, "term") or _value(old, "term")
    return {
        "event": row["action"], "description": EVENTS[row["action"]],
        "occurred_at": row["created_at"].isoformat(),
        "actor": "You" if row["actor_account_id"] == viewer.pk else "An administrator",
        "semester": _TERMS.get(term), "changes": changes,
        "reason": row["reason"] if row["reason"] in _REASONS else None,
        "note": row["reason_note"] or None,
    }


def school_year_history(*, actor, school_year_id, page=1):
    auth = services.authorize(actor)
    if type(school_year_id) is not int or not 1 <= school_year_id <= services.MAX_ID:
        raise services.AcademicPeriodNotFound()
    if type(page) is not int or not 1 <= page <= services.MAX_PAGE:
        raise services.AcademicPeriodInvalid({"page": "invalid"})
    if not SchoolYear.objects.using(DEFAULT_DB_ALIAS).filter(pk=school_year_id).exists():
        raise services.AcademicPeriodNotFound()
    start = (page - 1) * PAGE_SIZE
    rows = list(AcademicPeriodAuditLog.objects.using(DEFAULT_DB_ALIAS)
                .filter(school_year_id=school_year_id, action__in=tuple(EVENTS))
                .order_by("-academic_period_audit_log_id")
                .values("action", "actor_account_id", "old_value", "new_value", "reason", "reason_note",
                        "created_at")[start:start + PAGE_SIZE + 1])
    return {"results": [_entry(row, auth.account) for row in rows[:PAGE_SIZE]],
            "page": page, "page_size": PAGE_SIZE, "has_next": len(rows) > PAGE_SIZE}
