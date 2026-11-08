"""Isolated first Workspace Admin bootstrap; NEVER a general role-assignment API.

An authenticated framework superuser is used solely as the one-time console
operator / audit actor. The framework account never acquires Workspace roles.
No catalogue, services, permissions, or role defaults are created here.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DEFAULT_DB_ALIAS, IntegrityError, connections, transaction
from django.utils import timezone

from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccessAuditLog, AccountRole, Role
from .models import Account


BOOTSTRAP_ACTION = "workspace.bootstrap.initial_admin"


class BootstrapRefused(Exception):
    """The one-time bootstrap was not authorized or conditions changed."""


def _require_local_primary_mysql():
    connection = connections[DEFAULT_DB_ALIAS]
    host = str(connection.settings_dict.get("HOST") or "").lower()
    if connection.vendor != "mysql" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise BootstrapRefused("Bootstrap requires the local primary MySQL database.")
    if connection.isolation_level != "read committed":
        raise BootstrapRefused("Bootstrap requires MySQL READ COMMITTED isolation.")
    return connection


def bootstrap_preflight():
    """Read only. Does not authenticate an operator or authorize a live write."""
    _require_local_primary_mysql()
    roles = list(Role.objects.using(DEFAULT_DB_ALIAS).filter(role_name="Admin"))
    return {
        "admin_role_exists_and_active": len(roles) == 1 and roles[0].is_active,
        "existing_admin_assignments": AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
            role__role_name="Admin"
        ).count(),
        "previous_bootstrap_events": AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).filter(
            action=BOOTSTRAP_ACTION
        ).count(),
        "framework_operators": Account.objects.using(DEFAULT_DB_ALIAS).filter(
            is_staff=True, is_superuser=True, is_active=True,
            request_status="Approved",
        ).count(),
    }


def provision_first_workspace_admin(*, operator_school_id, operator_password,
                                   new_school_id, new_email, new_password):
    """Create exactly one new approved Admin and its audit atomically.

    This is not an alternative to governance approval. Disabled by default,
    and deliberately excludes registration applicants or pre-existing accounts.
    Do not expose it via views, API, tasks, or a background worker.
    """
    if not getattr(settings, "WORKSPACE_FIRST_ADMIN_BOOTSTRAP_ENABLED", False):
        raise BootstrapRefused("One-time Workspace Admin bootstrap is disabled.")
    _require_local_primary_mysql()
    if not all(type(v) is str and v.strip() for v in (
        operator_school_id, operator_password, new_school_id,
        new_email, new_password,
    )):
        raise BootstrapRefused("All operator and new Admin fields are required.")
    operator_school_id = operator_school_id.strip()
    new_school_id = new_school_id.strip()
    new_email = new_email.strip()
    try:
        validate_email(new_email)
    except ValidationError as exc:
        raise BootstrapRefused("Provide a valid new Admin email address.") from exc
    if operator_school_id == new_school_id:
        raise BootstrapRefused("The operator and new Admin must be different accounts.")

    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            # Locks the canonical Admin row; concurrent runs of THIS bootstrap
            # serialize here, then re-check assignments and prior events.
            try:
                admin_role = Role.objects.using(DEFAULT_DB_ALIAS).select_for_update().get(
                    role_name="Admin", is_active=True
                )
            except (Role.DoesNotExist, Role.MultipleObjectsReturned) as exc:
                raise BootstrapRefused("The canonical active Admin role is unavailable.") from exc

            if AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(role_id=admin_role.pk).exists():
                raise BootstrapRefused("An Admin role assignment already exists. Bootstrap refused.")
            if AccessAuditLog.objects.using(DEFAULT_DB_ALIAS).filter(
                action=BOOTSTRAP_ACTION
            ).exists():
                raise BootstrapRefused("This one-time bootstrap was already recorded.")
            if Account.objects.using(DEFAULT_DB_ALIAS).filter(school_id=new_school_id).exists():
                raise BootstrapRefused("A new, unused school ID is required. Existing applicants cannot be promoted.")

            try:
                operator = Account.objects.using(DEFAULT_DB_ALIAS).select_for_update().get(
                    school_id=operator_school_id,
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                    request_status="Approved",
                )
            except (Account.DoesNotExist, Account.MultipleObjectsReturned) as exc:
                raise BootstrapRefused("A valid framework operator is required.") from exc
            if not operator.check_password(operator_password):
                raise BootstrapRefused("Operator authentication failed.")
            if AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(account=operator).exists():
                raise BootstrapRefused("The framework operator must have no Workspace roles.")

            # AccountManager's validated pathway hashes the password and creates
            # a pending/inactive account. It rejects requested Admin roles.
            try:
                account = Account.objects.db_manager(DEFAULT_DB_ALIAS).create_user(
                    school_id=new_school_id, email=new_email, password=new_password
                )
            except (ValidationError, ValueError) as exc:
                raise BootstrapRefused(
                    "New Admin school ID, email or password did not pass validation."
                ) from exc
            if account.requested_role_id is not None or account.is_staff or account.is_superuser:
                raise BootstrapRefused("The created Admin is not an eligible Workspace account.")
            account.request_status = "Approved"
            account.is_active = True
            account.reviewed_by = operator
            account.reviewed_at = timezone.now()
            account.save(using=DEFAULT_DB_ALIAS, update_fields=[
                "request_status", "is_active", "reviewed_by", "reviewed_at",
            ])
            AccountRole.objects.using(DEFAULT_DB_ALIAS).create(
                account=account, role=admin_role, assigned_by=operator
            )
            record_access_audit(
                actor=operator,
                target=account,
                role=admin_role,
                action=BOOTSTRAP_ACTION,
                old_value=None,
                new_value={
                    "account_id": account.pk,
                    "role_id": admin_role.pk,
                    "request_status": "Approved",
                    "is_active": True,
                },
                reason="assignment_change",
            )
        return account.pk
    except IntegrityError as exc:
        raise BootstrapRefused("Bootstrap database integrity check failed; no change committed.") from exc
