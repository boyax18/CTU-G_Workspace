"""Student-context HDAC for WF-05.05 (own records only).

Every call, fresh: switch on; protected executor off; a persisted, active, Approved, non-framework
account with a GENUINE active Student assignment; when role context is enforced, the selected
context must be that Student role (a Treasurer, Instructor or Admin context of the same account never
reaches Student operations, and Student restrictions cannot be bypassed by switching); active
academic service; the exact effective permission (account-specific Deny wins). Objects are always
the actor's own: no student identifier is ever accepted from the client.

Mutations call ``lock_and_authorize_student`` inside the transaction. It locks, in the shared order,
the academic, clearance and finance service rows (service_id order), the permission row and the
account row, then re-authorizes.
"""

from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.models import AccountRole, Permission, Service
from apps.access_control.services import has_permission
from apps.accounts.active_role_context import allowed_role_ids, context_enabled, selected_scope
from apps.accounts.models import Account

from . import services

DB = DEFAULT_DB_ALIAS
LOCKED_SERVICES = ("academic", "clearance", "finance")


def authorize_student(actor, permission_code, gate):
    if not gate():
        raise services.AcademicPeriodUnavailable("Student Semester Onboarding is not activated.")
    if services._executor_enabled():
        raise services.AcademicPeriodUnavailable("The protected writer has no onboarding operation.")
    if (not isinstance(actor, Account) or actor._state.adding or actor._state.db != DB
            or type(actor.pk) is not int or not 1 <= actor.pk <= services.MAX_ID):
        raise services.AcademicPeriodDenied()
    account = Account.objects.using(DB).filter(pk=actor.pk).first()
    if (account is None or account.is_staff or account.is_superuser or not account.is_active
            or account.request_status != "Approved"):
        raise services.AcademicPeriodDenied()
    student_roles = frozenset(AccountRole.objects.using(DB).filter(
        account_id=account.pk, role__role_name="Student", role__is_active=True).values_list("role_id", flat=True))
    if not student_roles:
        raise services.AcademicPeriodDenied()
    acting = None
    if context_enabled():
        scope = selected_scope()
        if (scope is None or scope.account_id != account.pk or scope.role_id is None
                or not allowed_role_ids(account.pk, scope.role_id) & student_roles):
            raise services.AcademicPeriodDenied("student_context_required")
        acting = scope.role_id
    if not Service.objects.using(DB).filter(service_code=services.SERVICE_CODE, is_active=True).exists():
        raise services.AcademicPeriodUnavailable("The academic service is not active.")
    if type(permission_code) is not str or not has_permission(account, permission_code):
        raise services.AcademicPeriodDenied()
    return services.Authorization(account, acting)


def lock_shared_services():
    """Lock academic, clearance and finance service rows in service_id order (all must be active)."""
    rows = list(Service.objects.using(DB).select_for_update().filter(service_code__in=LOCKED_SERVICES).order_by("service_id"))
    if {r.service_code for r in rows} != set(LOCKED_SERVICES) or not all(r.is_active for r in rows):
        raise services.AcademicPeriodUnavailable("The academic, clearance and finance services must all be active.")
    return rows


def lock_and_authorize_student(actor, permission_code, gate):
    connection = transaction.get_connection(DB)
    if connection.vendor != "mysql" or not connection.in_atomic_block:
        raise services.AcademicPeriodUnavailable("Onboarding requires a primary MySQL transaction.")
    lock_shared_services()
    if len(list(Permission.objects.using(DB).select_for_update().filter(permission_code=permission_code))) != 1:
        raise services.AcademicPeriodUnavailable("Onboarding authority is not provisioned.")
    if isinstance(actor, Account) and type(actor.pk) is int:
        list(Account.objects.using(DB).select_for_update().filter(pk=actor.pk))
    return authorize_student(actor, permission_code, gate)


def genuine_student(account_id):
    """Eligibility of a TARGET account for School Admin operations (never authorizes the caller)."""
    if type(account_id) is not int or account_id <= 0:
        return None
    account = Account.objects.using(DB).filter(pk=account_id).first()
    if (account is None or account.is_staff or account.is_superuser or account.request_status != "Approved"
            or not AccountRole.objects.using(DB).filter(account_id=account.pk, role__role_name="Student",
                                                        role__is_active=True).exists()):
        return None
    return account
