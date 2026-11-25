"""Period-scoped subject teaching assignments (clearance.teaching_assignments.manage).

Eligibility is evaluated from the existing role-assignment services every time, never cached:
an instructor must be a persisted, active, Approved, non-framework account whose CURRENT eligible
roles (apps.accounts.active_role_context.available_roles, which applies the ordinary-appointment
runtime rules) include Instructor. Instructor is a base role: it has no OrdinaryAppointment record,
so a "revoked appointment" means a removed/inactive Instructor assignment or a suspended account.
Such an assignment is never auto-ended; it is reported ``eligible: false`` and its offering is not
ready for Student subject confirmation (WF-05.05 contract) until a School Admin reassigns it.

Changing the instructor ends the current row and creates a new one in the same transaction; rows
are never overwritten or deleted. Assignments are refused for Closed/Archived semesters. This is
NOT a section adviser appointment (academic.advisers.manage) and creates no clearance signatory.
Writes need WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED in addition to the base switch.
"""

from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q

from apps.access_control.models import AccountRole
from apps.accounts.active_role_context import available_roles
from apps.accounts.fields import CurrentTimestamp
from apps.accounts.models import Account

from . import configuration, services
from .configuration import ConfigurationConflict, parse_id, parse_search
from .models import AssignmentStatus, SemesterStatus, SubjectOffering, TeachingAssignment

DB = DEFAULT_DB_ALIAS
END_REASONS = frozenset({"instructor_unavailable", "assignment_error", "schedule_change"})
MAX_RESULTS = 20


def _full_name(account):
    profile = getattr(account, "profile", None)
    if profile is None:
        return None
    parts = [getattr(profile, f, None) for f in ("first_name", "middle_name", "last_name", "suffix")]
    name = " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
    return name or None


def instructor_eligible(account_id):
    if type(account_id) is not int or account_id <= 0:
        return False
    account = Account.objects.using(DB).filter(pk=account_id).first()
    if (account is None or account.is_staff or account.is_superuser or not account.is_active
            or account.request_status != "Approved"):
        return False
    return any(role["role_name"] == "Instructor" for role in available_roles(account_id))


def instructor_ref(account):
    return {"account_id": account.pk, "ctug_id": account.school_id, "full_name": _full_name(account)}


def current_assignment(offering):
    return (TeachingAssignment.objects.using(DB).select_related("instructor__profile")
            .filter(offering=offering, status=AssignmentStatus.ACTIVE).first())


def assignment_payload(assignment, eligible=None):
    if eligible is None:
        eligible = instructor_eligible(assignment.instructor_id)
    return {"assignment_id": assignment.pk, "status": assignment.status,
            "instructor": instructor_ref(assignment.instructor), "eligible": eligible,
            "assigned_at": configuration._iso(assignment.assigned_at), "ended_at": configuration._iso(assignment.ended_at),
            "end_reason": assignment.end_reason}


def offering_ready_for_confirmation(offering):
    """WF-05.05 contract: True only with a current assignment whose instructor is eligible NOW."""
    assignment = current_assignment(offering)
    return assignment is not None and instructor_eligible(assignment.instructor_id)


def eligible_instructors(*, actor, q=None):
    configuration.authorize_read(actor, "teaching")
    q = parse_search(q)
    qs = (Account.objects.using(DB).select_related("profile")
          .filter(is_active=True, request_status="Approved", is_staff=False, is_superuser=False,
                  pk__in=AccountRole.objects.using(DB).filter(role__role_name="Instructor", role__is_active=True)
                  .values("account_id"))
          .order_by("school_id", "pk"))
    if q:
        qs = qs.filter(Q(school_id__istartswith=q) | Q(profile__first_name__icontains=q)
                       | Q(profile__last_name__icontains=q))
    results = [instructor_ref(a) for a in qs[:MAX_RESULTS * 2] if instructor_eligible(a.pk)][:MAX_RESULTS]
    return {"results": results}


def _locked_offering(offering_id):
    offering = SubjectOffering.objects.using(DB).select_for_update().filter(pk=offering_id).first()
    if offering is None:
        raise services.AcademicPeriodNotFound()
    if offering.semester.status not in (SemesterStatus.DRAFT, SemesterStatus.ACTIVE):
        raise ConfigurationConflict("period_closed")  # historical teaching history is preserved as is
    active = list(TeachingAssignment.objects.using(DB).select_for_update()
                  .filter(offering=offering, status=AssignmentStatus.ACTIVE).order_by("assignment_id"))
    return offering, (active[0] if active else None)


def _end(auth, assignment, reason):
    TeachingAssignment.objects.using(DB).filter(pk=assignment.pk, status=AssignmentStatus.ACTIVE).update(
        status=AssignmentStatus.ENDED, active_slot=None, ended_at=CurrentTimestamp(), ended_by=auth.account,
        end_reason=reason)


def assign_instructor(*, actor, offering_id, instructor_account_id, expected_assignment_id):
    """Assign (or replace) the offering's instructor. ``expected_assignment_id`` is the current
    assignment the School Admin saw (None when none); if it changed, nothing happens."""
    offering_id = parse_id(offering_id, "offering_id")
    instructor_id = parse_id(instructor_account_id, "instructor_account_id")
    if expected_assignment_id is not None:
        expected_assignment_id = parse_id(expected_assignment_id, "expected_assignment_id")

    def apply(auth):
        offering, current = _locked_offering(offering_id)
        if (current.pk if current else None) != expected_assignment_id:
            raise ConfigurationConflict("assignment_changed")
        if current is not None and current.instructor_id == instructor_id:
            raise ConfigurationConflict("no_change")
        # Lock the instructor account row, then evaluate eligibility from current role data.
        if not Account.objects.using(DB).select_for_update().filter(pk=instructor_id).exists():
            raise services.AcademicPeriodNotFound()
        if not instructor_eligible(instructor_id):
            raise ConfigurationConflict("instructor_ineligible")
        if current is not None:
            _end(auth, current, "replaced")
        created = TeachingAssignment.objects.using(DB).create(
            offering=offering, instructor_id=instructor_id, active_slot=1, assigned_by=auth.account)
        configuration.audit(auth, "academic.teaching.assign", "offering", offering.pk,
                            {"assignment_id": current.pk, "instructor_account_id": current.instructor_id}
                            if current else None,
                            {"assignment_id": created.pk, "instructor_account_id": instructor_id})
        return offering.pk
    pk = configuration.write(actor, "teaching", apply)
    return configuration.offering_payload(configuration._offerings_qs().get(pk=pk))


def end_assignment(*, actor, offering_id, expected_assignment_id, reason_code):
    offering_id = parse_id(offering_id, "offering_id")
    expected_assignment_id = parse_id(expected_assignment_id, "expected_assignment_id")
    if type(reason_code) is not str or reason_code not in END_REASONS:
        raise services.AcademicPeriodInvalid({"reason_code": "invalid"})

    def apply(auth):
        offering, current = _locked_offering(offering_id)
        if current is None or current.pk != expected_assignment_id:
            raise ConfigurationConflict("assignment_changed")
        _end(auth, current, reason_code)
        configuration.audit(auth, "academic.teaching.end", "offering", offering.pk,
                            {"assignment_id": current.pk, "instructor_account_id": current.instructor_id},
                            {"assignment_id": current.pk, "status": "Ended", "end_reason": reason_code})
        return offering.pk
    pk = configuration.write(actor, "teaching", apply)
    return configuration.offering_payload(configuration._offerings_qs().get(pk=pk))


def assignment_history(*, actor, offering_id):
    configuration.authorize_read(actor, "teaching")
    offering = SubjectOffering.objects.using(DB).filter(pk=parse_id(offering_id, "offering_id")).first()
    if offering is None:
        raise services.AcademicPeriodNotFound()
    rows = (TeachingAssignment.objects.using(DB).select_related("instructor__profile")
            .filter(offering=offering).order_by("-assignment_id")[:50])
    return {"offering_id": offering.pk, "results": [assignment_payload(a) for a in rows]}
