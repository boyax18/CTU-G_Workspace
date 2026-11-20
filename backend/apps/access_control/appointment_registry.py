"""WF-03.01 appointment evidence ledger, STAGED; no grants or release activation.

An appointment digest is NOT evidence by itself. A separate, exact-permission
reviewer must attest that they checked the external official record. Recording,
verification and role assignment must have three distinct accounts.

No School Admin role-title bypass, no self-review, no arbitrary proof checkbox,
no production route and no protected-writer bypass. The deployment policy deciding
which campus officer gets the exact review permission remains UNAPPROVED.
"""

import re
from datetime import datetime, timedelta

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.utils import timezone

from .audit import record_access_audit_receipt
from .models import AccountRole, OrdinaryAppointment
from .role_management import (
    ADMIN, INSTRUCTOR, SSG_ADVISOR, STUDENT, TREASURER,
    RoleChangeDenied, RoleChangeUnavailable, is_eligible_account,
    lock_state, refuse_while_protected_writer_enabled, require_mysql_read_committed,
    role_row,
)
from .services import has_permission
from .writer_boundary import writer_atomic

RECORD_PERMISSION = "access_control.appointments.record"
VERIFY_PERMISSION = "access_control.appointments.verify"
GATE_SETTING = "WORKSPACE_ORDINARY_APPOINTMENT_REGISTRY_ENABLED"
ROLE_BASE = {TREASURER: STUDENT, SSG_ADVISOR: INSTRUCTOR}
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class AppointmentConflict(Exception):
    """Conflict with a fixed, non-sensitive reason."""

    REASONS = frozenset({"state_changed", "not_eligible", "already_verified", "role_still_assigned"})

    def __init__(self, reason="state_changed"):
        self.reason = reason if reason in self.REASONS else "state_changed"
        super().__init__("Appointment could not be changed.")


def registry_gate_open():
    return getattr(settings, GATE_SETTING, False) is True


def _start(actor):
    if not registry_gate_open():
        raise RoleChangeUnavailable("Appointment registry is not activated.")
    refuse_while_protected_writer_enabled()
    if (not is_eligible_account(actor) or actor._state.adding
            or actor._state.db != DEFAULT_DB_ALIAS):
        raise RoleChangeDenied("A permitted school account is required.")


def _locked_authority(actor, target_id, code):
    _, accounts, assignments, held = lock_state([actor.pk, target_id], authority_for=actor.pk)
    actual_actor = accounts[actor.pk]
    target = accounts[target_id]
    if not is_eligible_account(actual_actor) or ADMIN not in held[actor.pk]:
        raise RoleChangeDenied("School administration eligibility is required.")
    if not has_permission(actual_actor, code):
        raise RoleChangeDenied("The exact appointment permission is required.")
    if not is_eligible_account(target):
        raise RoleChangeDenied("The proposed appointee is not eligible.")
    return actual_actor, target, assignments, held[target_id]


def _target_ok(target_roles, role_name):
    base = ROLE_BASE[role_name]
    # The role-assignment service rechecks every other combination when granting.
    return base in target_roles


def _valid_times(start, end):
    return (isinstance(start, datetime) and isinstance(end, datetime)
            and timezone.is_aware(start) and timezone.is_aware(end)
            and start < end and end > timezone.now()
            and end - start <= timedelta(days=366))


def record_appointment(*, actor, target_id, role_name, document_sha256, valid_from, valid_until):
    """Record a candidate document fingerprint. This does NOT verify it."""
    _start(actor)
    if (type(target_id) is not int or target_id <= 0 or actor.pk == target_id
            or type(role_name) is not str or role_name not in ROLE_BASE
            or type(document_sha256) is not str or not DIGEST_PATTERN.fullmatch(document_sha256)
            or not _valid_times(valid_from, valid_until)):
        raise RoleChangeDenied("An eligible appointment candidate is required.")
    with writer_atomic():
        require_mysql_read_committed()
        recorder, target, _, held = _locked_authority(actor, target_id, RECORD_PERMISSION)
        if not _target_ok(held, role_name):
            raise AppointmentConflict("not_eligible")
        role = role_row(role_name)
        if role is None or not role.is_active:
            raise RoleChangeUnavailable("The appointment role is unavailable.")
        # The digest is an identity/integrity marker only, not authorization.
        if OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).filter(
            account_id=target.pk, role_name=role_name, document_sha256=document_sha256,
        ).exists():
            raise AppointmentConflict("state_changed")
        row = OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).create(
            account=target, role_name=role_name, document_sha256=document_sha256,
            valid_from=valid_from, valid_until=valid_until,
            submitted_by=recorder, status="Submitted",
        )
        receipt_id = record_access_audit_receipt(
            actor=recorder, target=target, role=role, action="account.appointment.submit",
            old_value=None, new_value={"is_active": False},
            reason="assignment_change",
        )
        row.submission_receipt_id = receipt_id
        row.save(using=DEFAULT_DB_ALIAS, update_fields=["submission_receipt"])
    return {"appointment_id": row.pk, "status": "Submitted"}


def _review(*, actor, appointment_id, action, confirmed_digest=None):
    """Two-person independent review or revocation; no blind approval."""
    _start(actor)
    if type(appointment_id) is not int or appointment_id <= 0 or action not in {"verify", "reject", "revoke"}:
        raise RoleChangeDenied("An existing appointment is required.")
    if action == "verify" and (type(confirmed_digest) is not str or not DIGEST_PATTERN.fullmatch(confirmed_digest)):
        raise RoleChangeDenied("A separately checked document digest is required.")
    if action != "verify" and confirmed_digest is not None:
        raise RoleChangeDenied("Unexpected verification input.")
    with writer_atomic():
        require_mysql_read_committed()
        # Determine target before acquiring locks; recheck once row-locked.
        target_id = OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).filter(
            pk=appointment_id).values_list("account_id", flat=True).first()
        if type(target_id) is not int or actor.pk == target_id:
            raise RoleChangeDenied("Appointment unavailable.")
        verifier, target, assignments, held = _locked_authority(actor, target_id, VERIFY_PERMISSION)
        appointment = OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).select_for_update().filter(
            pk=appointment_id, account_id=target.pk).first()
        if appointment is None or verifier.pk == appointment.submitted_by_id:
            raise RoleChangeDenied("Independent review is required.")
        if appointment.role_name not in ROLE_BASE or not _target_ok(held, appointment.role_name):
            raise AppointmentConflict("not_eligible")
        role = role_row(appointment.role_name)
        if role is None or not role.is_active:
            raise RoleChangeUnavailable("The appointment role is unavailable.")
        old_status = appointment.status
        if action in {"verify", "reject"}:
            if old_status != "Submitted":
                raise AppointmentConflict()
            if action == "verify":
                if (confirmed_digest != appointment.document_sha256
                        or not _valid_times(appointment.valid_from, appointment.valid_until)):
                    raise AppointmentConflict("not_eligible")
                # All reviewers serialize on the target account row, including
                # reviews of different document records for the same target.
                if OrdinaryAppointment.objects.using(DEFAULT_DB_ALIAS).filter(
                    account_id=target.pk, role_name=appointment.role_name, status="Verified",
                    valid_until__gt=timezone.now()).exclude(pk=appointment.pk).exists():
                    raise AppointmentConflict("already_verified")
                appointment.status = "Verified"
            else:
                appointment.status = "Rejected"
            appointment.reviewed_by = verifier
            appointment.reviewed_at = timezone.now()
            appointment.save(using=DEFAULT_DB_ALIAS, update_fields=["status", "reviewed_by", "reviewed_at"])
        else:
            if old_status != "Verified":
                raise AppointmentConflict()
            # Evidence cannot be revoked while it still supports a role. Revoke
            # the role first to prevent a stale privileged role from remaining.
            if any(a.account_id == target.pk and a.role.role_name == appointment.role_name
                   for a in assignments):
                raise AppointmentConflict("role_still_assigned")
            appointment.status = "Revoked"
            appointment.revoked_by = verifier
            appointment.revoked_at = timezone.now()
            appointment.save(using=DEFAULT_DB_ALIAS, update_fields=["status", "revoked_by", "revoked_at"])
        receipt_id = record_access_audit_receipt(
            actor=verifier, target=target, role=role,
            action="account.appointment." + action,
            old_value={"is_active": old_status == "Verified"},
            new_value={"is_active": appointment.status == "Verified"},
            reason="assignment_change",
        )
        receipt_field = "revocation_receipt" if action == "revoke" else "review_receipt"
        setattr(appointment, receipt_field + "_id", receipt_id)
        appointment.save(using=DEFAULT_DB_ALIAS, update_fields=[receipt_field])
    return {"appointment_id": appointment.pk, "status": appointment.status}


def verify_appointment(*, actor, appointment_id, confirmed_digest):
    return _review(actor=actor, appointment_id=appointment_id, action="verify", confirmed_digest=confirmed_digest)


def reject_appointment(*, actor, appointment_id):
    return _review(actor=actor, appointment_id=appointment_id, action="reject")


def revoke_appointment(*, actor, appointment_id):
    return _review(actor=actor, appointment_id=appointment_id, action="revoke")
