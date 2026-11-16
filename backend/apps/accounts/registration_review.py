"""Guarded CTU-G Workspace Student/Instructor registration decisions.

NOT exposed by a URL or command. Disabled by default until the first-operator,
permission-catalogue, audit and governance approvals are completed.

This service does NOT provision an Admin or a Django Superuser; it never seeds
services, permission definitions, roles, or role-permission defaults.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, transaction
from django.utils import timezone

from apps.access_control.audit import record_access_audit, record_access_audit_receipt
from apps.access_control.models import (
    AccountPermission,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)
from apps.access_control.services import has_permission

from .models import Account
from .registration_notifications import schedule_registration_decision_email_after_commit
from .registration_outbox import record_registration_decision_outbox


APPROVE_CODE = "accounts.registration_requests.approve"
REJECT_CODE = "accounts.registration_requests.reject"
ELIGIBLE_BASE_ROLES = frozenset({"Student", "Instructor"})
REJECTION_CODES = frozenset({
    "incomplete_submission",
    "ineligible_registration",
    "identity_mismatch",
    "duplicate_request",
})


class RegistrationReviewDenied(Exception):
    """An account request cannot be decided by this actor under this policy."""


class RegistrationReviewUnavailable(Exception):
    """Required approved catalogue or transaction conditions are unavailable."""


def _account_id(value):
    if (
        not isinstance(value, Account)
        or value._state.adding
        or value._state.db != DEFAULT_DB_ALIAS
        or type(value.pk) is not int
        or not 1 <= value.pk <= 2_147_483_647
    ):
        raise RegistrationReviewDenied("An existing Workspace actor is required.")
    return value.pk


def _target_id(value):
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise RegistrationReviewDenied("An existing pending account is required.")
    return value


def _decide(*, actor, target_id, approve, rejection_code=None):
    """Return the decided account ID only AFTER its transaction commits.

    A future protected API must independently enforce CSRF, session eligibility,
    object scope, request validation and rate limits. Do not wire this into a
    route until its owner-approved governance/assignment lock policy is complete.
    """
    if not getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False):
        raise RegistrationReviewUnavailable("Registration review is not activated.")

    actor_id = _account_id(actor)
    target_id = _target_id(target_id)
    if actor_id == target_id:
        raise RegistrationReviewDenied("Self-approval or rejection is prohibited.")
    if approve:
        if rejection_code is not None:
            raise RegistrationReviewDenied("Do not supply a rejection code for approval.")
    elif type(rejection_code) is not str or rejection_code not in REJECTION_CODES:
        raise RegistrationReviewDenied("Use an approved non-sensitive rejection code.")

    code = APPROVE_CODE if approve else REJECT_CODE
    with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
        connection = transaction.get_connection(DEFAULT_DB_ALIAS)
        if connection.vendor != "mysql" or connection.isolation_level != "read committed":
            raise RegistrationReviewUnavailable("Trusted review requires primary MySQL READ COMMITTED.")

        # Coordinate with existing permission-management writers by locking
        # the same governance Service plus accounts Service in ID order.
        service_rows = list(
            Service.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(service_code__in=["access_control", "accounts"])
            .order_by("service_id")
        )
        services = {row.service_code: row for row in service_rows}
        if set(services) != {"access_control", "accounts"} or not all(
            row.is_active for row in services.values()
        ):
            raise RegistrationReviewUnavailable("Active approved service definitions are required.")

        permissions = list(
            Permission.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(permission_code=code, service_id=services["accounts"].pk)
            .order_by("permission_id")
        )
        if len(permissions) != 1:
            raise RegistrationReviewUnavailable("Registration authority is not available.")

        accounts = {
            row.pk: row
            for row in Account.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(pk__in=[actor_id, target_id])
            .order_by("account_id")
        }
        if set(accounts) != {actor_id, target_id}:
            raise RegistrationReviewDenied("The reviewer or target no longer exists.")
        reviewer, target = accounts[actor_id], accounts[target_id]

        # Framework administrators are not application administrators.
        if (
            reviewer.is_staff
            or reviewer.is_superuser
            or not reviewer.is_active
            or reviewer.request_status != "Approved"
        ):
            raise RegistrationReviewDenied("An eligible Workspace administrator is required.")

        assignments = list(
            AccountRole.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(account_id__in=[actor_id, target_id])
            .order_by("account_role_id")
        )
        reviewer_role_ids = {
            row.role_id for row in assignments if row.account_id == actor_id
        }
        if any(row.account_id == target_id for row in assignments):
            raise RegistrationReviewDenied("The registration already has assigned roles.")

        # No requested role, inactive role or reserved role may be assigned.
        roles = {
            row.pk: row
            for row in Role.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(pk__in=reviewer_role_ids | {target.requested_role_id})
            .order_by("role_id")
        }
        if not any(
            roles.get(row.role_id) is not None
            and roles[row.role_id].role_name == "Admin"
            and roles[row.role_id].is_active
            for row in assignments if row.account_id == actor_id
        ):
            raise RegistrationReviewDenied("The actor needs an active Admin assignment.")

        list(
            RolePermission.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(role_id__in=reviewer_role_ids)
            .order_by("role_permission_id")
            .values_list("pk", flat=True)
        )
        list(
            AccountPermission.objects.using(DEFAULT_DB_ALIAS)
            .select_for_update()
            .filter(account_id=actor_id)
            .order_by("account_permission_id")
            .values_list("pk", flat=True)
        )
        if not has_permission(reviewer, code):
            raise RegistrationReviewDenied("The actor lacks this exact effective permission.")

        requested_role = roles.get(target.requested_role_id)
        if (
            target.request_status != "Pending"
            or target.is_active
            or target.is_staff
            or target.is_superuser
            or target.reviewed_by_id is not None
            or target.reviewed_at is not None
            or requested_role is None
            or not requested_role.is_active
            or requested_role.role_name not in ELIGIBLE_BASE_ROLES
        ):
            raise RegistrationReviewDenied("The request is not an eligible pending registration.")

        old = {
            "account_id": target.pk,
            "request_status": "Pending",
            "is_active": False,
        }
        target.request_status = "Approved" if approve else "Rejected"
        target.is_active = bool(approve)
        target.reviewed_by = reviewer
        target.reviewed_at = timezone.now()
        target.rejection_reason = None if approve else rejection_code
        target.save(using=DEFAULT_DB_ALIAS, update_fields=[
            "request_status", "is_active", "reviewed_by", "reviewed_at",
            "rejection_reason",
        ])

        if approve:
            AccountRole.objects.using(DEFAULT_DB_ALIAS).create(
                account=target,
                role=requested_role,
                assigned_by=reviewer,
            )

        new = {
            "account_id": target.pk,
            "request_status": target.request_status,
            "is_active": target.is_active,
        }
        if approve:
            new["role_id"] = requested_role.pk
        else:
            # Immutable, bounded decision snapshot; required for delayed v2 emails.
            new["rejection_code"] = rejection_code
        audit_values = {
            "actor": reviewer,
            "target": target,
            "role": requested_role if approve else None,
            "action": "account.registration.approve" if approve else "account.registration.reject",
            "old_value": old,
            "new_value": new,
            "reason": "account_status_change",
        }
        if getattr(settings, "WORKSPACE_REGISTRATION_OUTBOX_ENABLED", False):
            # The audit receipt and encrypted outbox row are one transaction;
            # both roll back if encryption, validation or insertion fails.
            receipt_id = record_access_audit_receipt(**audit_values)
            record_registration_decision_outbox(
                audit_log_id=receipt_id,
                target_account_id=target.pk,
                approved=approve,
                recipient_email=target.email,
            )
        else:
            # Existing audit and best-effort callback path remains unchanged.
            record_access_audit(**audit_values)
            if getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED", False):
                schedule_registration_decision_email_after_commit(
                    recipient_email=target.email,
                    approved=approve,
                    rejection_code=rejection_code,
                )
    return target_id


def approve_registration(*, actor, target_id):
    """Approve one pending Student/Instructor and attach ONLY its base role."""
    return _decide(actor=actor, target_id=target_id, approve=True)


def reject_registration(*, actor, target_id, rejection_code):
    """Reject one pending Student/Instructor with a non-sensitive reason code."""
    return _decide(
        actor=actor,
        target_id=target_id,
        approve=False,
        rejection_code=rejection_code,
    )
