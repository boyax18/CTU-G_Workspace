"""Guarded CTU-G Workspace Student/Instructor registration decisions.

NOT exposed by a URL or command. Disabled by default until the first-operator,
permission-catalogue, audit and governance approvals are completed.

This service does NOT provision an Admin or a Django Superuser; it never seeds
services, permission definitions, roles, or role-permission defaults.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction
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
from apps.access_control.writer_boundary import (
    WriterBoundaryUnavailable,
    require_verified_writer,
    writer_atomic,
)

from .models import Account
from .outbox_models import RegistrationNotificationOutbox
from .registration_notifications import schedule_registration_decision_email_after_commit
from .registration_outbox import _recipient_valid, record_registration_decision_outbox


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


# WF-02.03 (D-44, D-45; owner-approved 17 Nov 2026). Approval requires verified email ownership
# for the CURRENT address and the reviewer's attestation that institutional eligibility was
# checked against the one fixed source for the requested role. Workspace does not verify
# enrollment or employment itself; the attestation records the reviewer's own check.
ELIGIBILITY_SOURCES = {
    "Student": "ctu_main_system_records",
    "Instructor": "institutional_employment_records",
}
ELIGIBILITY_SUBJECTS = {"Student": "enrollment", "Instructor": "employment"}


class RegistrationApprovalNotAllowed(RegistrationReviewDenied):
    """Approval policy refusal (D-47): a fixed reason code, never applicant data.

    Subclasses RegistrationReviewDenied so callers that only know the generic denial
    (for example the test-only bulk service) still treat the refusal as "not decided".
    """

    REASONS = frozenset({"email_unverified", "eligibility_unconfirmed"})

    def __init__(self, reason):
        if reason not in self.REASONS:
            reason = "eligibility_unconfirmed"
        self.reason = reason
        super().__init__("Approval is not allowed by policy.")


class RegistrationRejectionNotAllowed(RegistrationReviewDenied):
    """WF-02.04 rejection policy conflict (D-58): a fixed reason code, never applicant data.

    Raised only after the reviewer's authorization and the application's eligibility were
    confirmed inside the lock, so it reveals nothing to a caller who cannot read the
    application. Subclasses RegistrationReviewDenied so bulk and executor callers fail closed.
    """

    REASONS = frozenset({"recipient_unverified", "direct_permissions", "protected_history"})

    def __init__(self, reason):
        if reason not in self.REASONS:
            reason = "protected_history"
        self.reason = reason
        super().__init__("Rejection is not allowed by policy.")


def rejection_notification_ready():
    """D-54: a completed rejection needs the durable outbox and the v2 (reason-bearing) template."""
    return bool(
        getattr(settings, "WORKSPACE_REGISTRATION_OUTBOX_ENABLED", False)
        and getattr(settings, "WORKSPACE_REGISTRATION_EMAIL_TEMPLATE_V2_ENABLED", False)
    )


def email_ownership_verified(account):
    """D-44: proof recorded for the address now on file (same rule as WF-02.01/02.02)."""
    email = (account.email or "").strip()
    proof = (account.email_verified_address or "").strip()
    return bool(email) and account.email_verified_at is not None and bool(proof) and proof.lower() == email.lower()


def _attested_source(attestation):
    """D-45: exactly {"confirmed": True, "source": <str>}; anything else is unconfirmed."""
    if (
        type(attestation) is not dict
        or set(attestation) != {"confirmed", "source"}
        or attestation["confirmed"] is not True
        or type(attestation["source"]) is not str
    ):
        raise RegistrationApprovalNotAllowed("eligibility_unconfirmed")
    return attestation["source"]


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


def _delete_rejected_registration(target_id):
    # A fixed two-table delete avoids Django's CASCADE collector issuing
    # DELETEs against unrelated history tables. Database foreign keys and the
    # executor's rejection-only triggers remain authoritative and fail closed.
    with transaction.get_connection(DEFAULT_DB_ALIAS).cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE account_id=%s", [target_id])
        cursor.execute(
            "DELETE FROM accounts WHERE account_id=%s AND request_status='Rejected' "
            "AND is_active=0 AND is_staff=0 AND is_superuser=0", [target_id],
        )
        if cursor.rowcount != 1:
            raise RegistrationReviewUnavailable("The rejected registration could not be removed.")


def _decide(*, actor, target_id, approve, rejection_code=None, attestation=None):
    """Return the decided account ID only AFTER its transaction commits.

    A future protected API must independently enforce CSRF, session eligibility,
    object scope, request validation and rate limits. Do not wire this into a
    route until its owner-approved governance/assignment lock policy is complete.
    """
    if not getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False):
        raise RegistrationReviewUnavailable("Registration review is not activated.")

    from apps.access_control.executor.client import LOCAL, enabled as executor_enabled, remote_call
    if approve:
        # D-51: the protected executor protocol cannot carry the eligibility attestation, so
        # approval is refused (before any transaction) whenever the protected writer is enabled,
        # instead of being executed without it. Rejection is unchanged.
        if executor_enabled():
            raise WriterBoundaryUnavailable("Approval needs the eligibility attestation; the protected executor cannot carry it.")
        attested_source = _attested_source(attestation)
    remote = remote_call("registration.approve" if approve else "registration.reject", {
        "actor_id": getattr(actor, "pk", None), "target_id": target_id, "rejection_code": rejection_code,
    })
    if remote is not LOCAL:
        return remote

    # P3C6A: when enforcement is enabled, stop BEFORE any primary-DB read/write.
    require_verified_writer("registration.approve" if approve else "registration.reject")
    if not approve and not rejection_notification_ready():
        # WF-02.04 D-54: never delete an applicant without the durable notification record.
        # Checked where the writes happen (here, or inside the executor), before any read or write.
        raise RegistrationReviewUnavailable("Rejection requires the durable notification outbox.")

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
    with writer_atomic():
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
        if approve:
            # D-44 / D-45 inside the locked transaction: nothing has been written yet.
            if not email_ownership_verified(target):
                raise RegistrationApprovalNotAllowed("email_unverified")
            if attested_source != ELIGIBILITY_SOURCES[requested_role.role_name]:
                raise RegistrationApprovalNotAllowed("eligibility_unconfirmed")
        else:
            # WF-02.04, inside the locked transaction and before any write.
            if AccountPermission.objects.using(DEFAULT_DB_ALIAS).filter(account=target).exists():
                raise RegistrationRejectionNotAllowed("direct_permissions")
            # D-55 (revised): the rejection email needs a verified, deliverable current address.
            if not email_ownership_verified(target) or not _recipient_valid(target.email):
                raise RegistrationRejectionNotAllowed("recipient_unverified")

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
            # D-45: the reviewer's attestation in the existing audit JSON, as the four flat fields
            # the audit writer accepts for this event only. Every value is derived here, server-side:
            # the reviewer is the audit actor, the applicant its target, created_at its time.
            new["email_evidence"] = "verified"
            new["eligibility_confirmed"] = True
            new["eligibility_subject"] = ELIGIBILITY_SUBJECTS[requested_role.role_name]
            new["eligibility_source"] = attested_source
        else:
            # Immutable, bounded decision snapshot; required for delayed v2 emails.
            new["rejection_code"] = rejection_code
            new["account_deleted"] = True
        audit_values = {
            "actor": reviewer,
            # Rejection retains the immutable account ID in the snapshot, not
            # a foreign key that would prevent removal of this applicant.
            "target": target if approve else None,
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
            outbox_id = record_registration_decision_outbox(
                audit_log_id=receipt_id,
                target_account_id=target.pk,
                approved=approve,
                recipient_email=target.email,
            )
            if not approve and not RegistrationNotificationOutbox.objects.using(DEFAULT_DB_ALIAS).filter(
                    pk=outbox_id, delivery_status="Pending").exists():
                # D-54/D-55: a rejection completes only with a deliverable, queued notification.
                raise RegistrationReviewUnavailable("The rejection notification could not be queued.")
        else:
            # Existing audit and best-effort callback path remains unchanged.
            record_access_audit(**audit_values)
            if getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_NOTIFICATIONS_ENABLED", False):
                schedule_registration_decision_email_after_commit(
                    recipient_email=target.email,
                    approved=approve,
                    rejection_code=rejection_code,
                )
        if not approve:
            # Delete only the locked, eligible applicant after its audit and
            # notification intent exist. Existing protected references refuse
            # deletion and roll back the entire decision; never rewrite audits.
            try:
                _delete_rejected_registration(target_id)
            except IntegrityError as exc:
                if not exc.args or exc.args[0] != 1451:
                    raise
                # D-58: a fixed policy conflict; the whole decision (audit, outbox) rolls back.
                raise RegistrationRejectionNotAllowed("protected_history") from exc
    return target_id


def approve_registration(*, actor, target_id, attestation=None):
    """Approve one pending Student/Instructor and attach ONLY its base role.

    WF-02.03: requires verified email ownership (D-44) and the reviewer's eligibility
    attestation {"confirmed": True, "source": ELIGIBILITY_SOURCES[role]} (D-45).
    Without them the call is refused and the applicant stays Pending.
    """
    return _decide(actor=actor, target_id=target_id, approve=True, attestation=attestation)


def reject_registration(*, actor, target_id, rejection_code):
    """Audit rejection, queue its email and remove the applicant's account and profile.

    WF-02.04: one of the four fixed codes (D-56); requires the durable outbox with the v2
    template (D-54) and a verified, deliverable current address (D-55 revised). Audit,
    encrypted outbox row and deletion commit together or not at all. Policy conflicts raise
    RegistrationRejectionNotAllowed (D-58); the notification is queued, never "delivered".
    """
    return _decide(
        actor=actor,
        target_id=target_id,
        approve=False,
        rejection_code=rejection_code,
    )
