"""Read-only academic catalogue for every role holding ``academic.catalogue.read`` (FR-ACA-03/07).

Pinned v2.0 binds academic.catalogue.read to Student, Instructor, Treasurer and Admin: "Read
courses, school years, periods and section definitions without student rosters." This module
serves the server-provided current academic period (FR-ACA-07: "The server SHALL provide School
Year and Semester as read-only current-period values"), used by the dashboard header and, later, by
Student Semester Onboarding. It never writes and never returns rosters, fees, versions, audit data
or management fields.

Authorization (fresh on every request): a persisted, active, Approved, non-framework account with at
least one eligible role assignment; the active academic service; and the exact effective
academic.catalogue.read through the existing HDAC evaluator (account-specific Deny wins; under
role-context enforcement only the selected role's grants count, and an absent or stale context
denies). No Admin assignment is required: this is the catalogue, not management.

Switch: WORKSPACE_ACADEMIC_CATALOGUE_ENABLED (default off; refused in the production profile).
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from apps.access_control.models import AccountRole, Service
from apps.access_control.services import has_permission
from apps.accounts.models import Account

from . import services
from .models import Semester, SemesterStatus

CATALOGUE_CODE = "academic.catalogue.read"
CATALOGUE_SETTING = "WORKSPACE_ACADEMIC_CATALOGUE_ENABLED"
DB = DEFAULT_DB_ALIAS


def catalogue_enabled():
    return getattr(settings, CATALOGUE_SETTING, False) is True


def authorize_reader(actor):
    if not catalogue_enabled():
        raise services.AcademicPeriodUnavailable("The academic catalogue is not activated.")
    if (not isinstance(actor, Account) or actor._state.adding or actor._state.db != DB
            or type(actor.pk) is not int or not 1 <= actor.pk <= services.MAX_ID):
        raise services.AcademicPeriodDenied()
    account = Account.objects.using(DB).filter(pk=actor.pk).first()
    if (account is None or account.is_staff or account.is_superuser or not account.is_active
            or account.request_status != "Approved"):
        raise services.AcademicPeriodDenied()
    if not AccountRole.objects.using(DB).filter(account_id=account.pk, role__is_active=True).exists():
        raise services.AcademicPeriodDenied()
    if not Service.objects.using(DB).filter(service_code=services.SERVICE_CODE, is_active=True).exists():
        raise services.AcademicPeriodUnavailable("The academic service is not active.")
    if not has_permission(account, CATALOGUE_CODE):
        raise services.AcademicPeriodDenied()
    return account


def _period(semester):
    return {"semester_id": semester.pk, "term": "first" if semester.term == 1 else "second", "label": semester.label,
            "school_year_id": semester.school_year_id, "school_year_label": semester.school_year.label,
            "start_date": semester.start_date.isoformat() if semester.start_date else None,
            "end_date": semester.end_date.isoformat() if semester.end_date else None}


def current_period(*, actor):
    """The single Active semester (at most one by database constraint), or null. Read-only."""
    authorize_reader(actor)
    actives = list(Semester.objects.using(DB).select_related("school_year")
                   .filter(status=SemesterStatus.ACTIVE).order_by("semester_id")[:2])
    if len(actives) > 1:  # impossible under the UNIQUE active_slot; never guess which one is current
        raise services.AcademicPeriodUnavailable("The current academic period is inconsistent.")
    return {"active": _period(actives[0]) if actives else None}
