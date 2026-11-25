"""WF-11.01 pure period rules (no database access, no authorization).

Kept separate so the derivation and date rules can be unit-tested and reused by both the Draft
service and the lifecycle foundation without importing either.
"""

import re
from datetime import date

from .models import MAX_START_YEAR, MIN_START_YEAR, SemesterStatus, SemesterTerm

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


class SchoolYearStatus:
    """WF11-D09: derived only; a School Year has no independently editable status."""

    DRAFT = "Draft"
    ACTIVE = "Active"
    BETWEEN_SEMESTERS = "Between semesters"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


_FINISHED = frozenset({SemesterStatus.CLOSED, SemesterStatus.ARCHIVED})


def derive_school_year_status(statuses):
    """Return the School Year status from its semester statuses (any order).

    Any Active semester makes the year Active; all Draft is Draft; all Archived is Archived; all
    Closed or Archived is Completed; any other mix (some finished, some Draft) is Between semesters.
    An empty or unknown input fails closed to Draft, which grants nothing.
    """
    values = [str(s) for s in statuses]
    known = {choice.value for choice in SemesterStatus}
    if not values or any(v not in known for v in values):
        return SchoolYearStatus.DRAFT
    if SemesterStatus.ACTIVE in values:
        return SchoolYearStatus.ACTIVE
    if all(v == SemesterStatus.DRAFT for v in values):
        return SchoolYearStatus.DRAFT
    if all(v == SemesterStatus.ARCHIVED for v in values):
        return SchoolYearStatus.ARCHIVED
    if all(v in _FINISHED for v in values):
        return SchoolYearStatus.COMPLETED
    return SchoolYearStatus.BETWEEN_SEMESTERS


def valid_start_year(value):
    return type(value) is int and MIN_START_YEAR <= value <= MAX_START_YEAR


def parse_iso_date(value):
    """Strict YYYY-MM-DD or None. Raises ValueError for anything else (never echoes input)."""
    if value is None:
        return None
    if type(value) is not str or len(value) != 10 or not _ISO_DATE.fullmatch(value):
        raise ValueError("invalid date")
    return date.fromisoformat(value)


def school_year_bounds(start_year):
    """Sanity window for semester dates: the two calendar years the School Year names."""
    return date(start_year, 1, 1), date(start_year + 1, 12, 31)


def range_problem(start, end, start_year):
    """Return a fixed field-error code for one semester's own range, or None."""
    low, high = school_year_bounds(start_year)
    for value in (start, end):
        if value is not None and not low <= value <= high:
            return "outside_school_year"
    if start is not None and end is not None and not start < end:
        return "start_not_before_end"
    return None


def terms_overlap(first, second):
    """True unless every known First-semester date precedes every known Second-semester date.

    ``first`` and ``second`` are (start, end) pairs whose items may be None (an incomplete Draft).
    A break between the semesters is allowed; sharing or crossing a day is not.
    """
    first_known = [d for d in first if d is not None]
    second_known = [d for d in second if d is not None]
    if not first_known or not second_known:
        return False
    return not max(first_known) < min(second_known)


def ranges_intersect(a_start, a_end, b_start, b_end):
    """Complete ranges only; incomplete ranges never count as a cross-year overlap."""
    if None in (a_start, a_end, b_start, b_end):
        return False
    return a_start <= b_end and b_start <= a_end


def term_key(term):
    return "first" if term == SemesterTerm.FIRST else "second"
