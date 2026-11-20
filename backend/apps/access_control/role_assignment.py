"""WF-03.01 Technical Super Admin role assignment (owner-approved D-79, D-82, D-97; 18 Nov 2026).

An effective Technical Super Admin (has_technical_authority for access_control.admin_assignments.manage:
active Admin AND Technical Super Admin roles plus the exact effective permission, account-level Deny
wins, services active) assigns or revokes School Admin (`Admin`) for ANOTHER eligible approved
Instructor. It can never grant or revoke Technical Super Admin (FR-ADM-03): that is the Django
Superuser's exclusive procedure (framework_roles). D-100 ordinary responsibilities are separately staged and default off: an effective
S1 Technical Super Admin plus independently verified appointment evidence are required.
No ordinary role grant is usable until that evidence source and governance adoption exist.

Default-off WORKSPACE_ROLE_ASSIGNMENT_ENABLED; refused while the protected writer is enabled.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from apps.accounts import session_revocation

from .audit import record_access_audit_receipt
from .ordinary_appointment_evidence import appointment_verified_for
from .ordinary_role_runtime import runtime_enforcement_enabled
from .models import AccountRole, Role
from .role_management import (
    ADMIN, ADMIN_ASSIGNMENT_CODE, ASSIGN_ACTION, INSTRUCTOR, REVOKE_ACTION, ROLE_REASON, TECHNICAL,
    STUDENT, TREASURER, SSG_ADVISOR, ORDINARY_ASSIGNMENT_CODE,
    RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable, admin_revocation_refusal, is_eligible_account,
    lock_state, refuse_while_protected_writer_enabled, require_mysql_read_committed, role_row, snapshot,
)
from .technical_admin import has_technical_authority
from .writer_boundary import writer_atomic

GATE_SETTING = "WORKSPACE_ROLE_ASSIGNMENT_ENABLED"


def gate_open():
    return getattr(settings, GATE_SETTING, False) is True


def _change(*, actor, target_id, assign, expected_present):
    if not gate_open():
        raise RoleChangeUnavailable("Role assignment is not activated.")
    refuse_while_protected_writer_enabled()
    if type(expected_present) is not bool or expected_present is assign:
        # Assigning confirms the role is absent; revoking confirms it is present.
        raise RoleChangeConflict("state_changed")
    if not is_eligible_account(actor) or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS:
        raise RoleChangeDenied("An eligible Workspace administrator is required.")
    if type(target_id) is not int or not 1 <= target_id <= 2_147_483_647:
        raise RoleChangeDenied("An existing account is required.")
    if actor.pk == target_id:
        raise RoleChangeConflict("protected_account")  # never the actor's own roles

    with writer_atomic():
        require_mysql_read_committed()
        _, accounts, assignments, held = lock_state([actor.pk, target_id], authority_for=actor.pk)
        reviewer, target = accounts[actor.pk], accounts[target_id]
        if not is_eligible_account(reviewer) or not {ADMIN, TECHNICAL} <= held[actor.pk]:
            raise RoleChangeDenied("The composite Technical Super Admin profile is required.")
        if not has_technical_authority(reviewer, ADMIN_ASSIGNMENT_CODE):
            raise RoleChangeDenied("The exact effective governance permission is required.")
        if not is_eligible_account(target):
            raise RoleChangeDenied("The account is not an eligible school account.")
        admin = role_row(ADMIN)
        if admin is None or not admin.is_active:
            raise RoleChangeUnavailable("The School Admin role is unavailable.")
        target_roles = held[target_id]
        current = next((a for a in assignments if a.account_id == target_id and a.role_id == admin.pk), None)
        if (current is not None) is not expected_present:
            raise RoleChangeConflict("state_changed")
        if assign:
            if INSTRUCTOR not in target_roles:
                raise RoleChangeConflict("not_eligible")  # FR-ADM-02: only approved Instructors become School Admin
            row = AccountRole.objects.using(DEFAULT_DB_ALIAS).create(account=target, role=admin, assigned_by=reviewer)
            record_access_audit_receipt(actor=reviewer, target=target, role=admin, action=ASSIGN_ACTION,
                                        old_value=None, new_value=snapshot(target_id, admin, row.pk), reason=ROLE_REASON)
        else:
            refusal = admin_revocation_refusal(target, target_roles)
            if refusal:
                raise RoleChangeConflict(refusal)
            removed = current.pk
            deleted, _ = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(pk=removed, account_id=target_id,
                                                                         role_id=admin.pk).delete()
            if deleted != 1:
                raise RoleChangeUnavailable("The role assignment could not be changed.")
            record_access_audit_receipt(actor=reviewer, target=target, role=admin, action=REVOKE_ACTION,
                                        old_value=snapshot(target_id, admin, removed), new_value=None, reason=ROLE_REASON)
        # D-83 / SR-1: exactly one advance per successful change; lock_state already holds the target's row lock.
        session_revocation.advance(target_id)
    return {"account_id": target_id, "role": ADMIN, "assigned": assign}


def assign_school_admin(*, actor, target_id, expected_present=False):
    """Add `Admin` to another eligible approved Instructor; the Instructor role stays."""
    return _change(actor=actor, target_id=target_id, assign=True, expected_present=expected_present)


def revoke_school_admin(*, actor, target_id, expected_present=True):
    """Remove `Admin` from another account, never from a Technical Super Admin, the legacy operator or the last one."""
    return _change(actor=actor, target_id=target_id, assign=False, expected_present=expected_present)


# D-100: a separate, independently default-off gate from the School Admin path.
# No production URL mounts these endpoints, even when a switch is accidentally set.
ORDINARY_GATE_SETTING = "WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED"
ORDINARY_ALLOWED = frozenset((TREASURER, SSG_ADVISOR))


def ordinary_gate_open():
    return gate_open() and getattr(settings, ORDINARY_GATE_SETTING, False) is True


def _ordinary_change(*, actor, target_id, role_name, assign, expected_present):
    """Modify one ordinary responsibility, never base, Admin or governance roles.

    D-100 evidence is verified server-side against an independent source ONLY;
    the caller cannot send an appointment ID or checkbox that serves as proof.
    Until that source is integrated, every assignment fails closed. Revocation
    of pre-existing ordinary roles remains supported when separately enabled.
    """
    if not ordinary_gate_open():
        raise RoleChangeUnavailable("Ordinary role assignments are not activated.")
    refuse_while_protected_writer_enabled()
    if type(role_name) is not str or role_name not in ORDINARY_ALLOWED:
        raise RoleChangeDenied("Only listed ordinary responsibilities may be changed.")
    if type(expected_present) is not bool or expected_present is assign:
        raise RoleChangeConflict("state_changed")
    if not is_eligible_account(actor) or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS:
        raise RoleChangeDenied("An eligible Workspace administrator is required.")
    if type(target_id) is not int or not 1 <= target_id <= 2_147_483_647:
        raise RoleChangeDenied("An existing account is required.")
    if actor.pk == target_id:
        raise RoleChangeConflict("protected_account")

    with writer_atomic():
        require_mysql_read_committed()
        _, accounts, assignments, held = lock_state([actor.pk, target_id], authority_for=actor.pk)
        reviewer, target = accounts[actor.pk], accounts[target_id]
        if not is_eligible_account(reviewer) or not {ADMIN, TECHNICAL} <= held[actor.pk]:
            raise RoleChangeDenied("The composite Technical Super Admin profile is required.")
        if not has_technical_authority(reviewer, ORDINARY_ASSIGNMENT_CODE):
            raise RoleChangeDenied("The exact ordinary-role management permission is required.")
        if not is_eligible_account(target):
            raise RoleChangeDenied("The account is not an eligible school account.")

        role = role_row(role_name)
        if role is None or not role.is_active:
            raise RoleChangeUnavailable("The requested ordinary role is unavailable.")
        target_roles = held[target_id]
        # Do not use ordinary assignment as a route to cross-base, privileged or
        # unsupported multi-role compositions. Admin and governance are never touched.
        base_role = STUDENT if role_name == TREASURER else INSTRUCTOR
        excluded = {STUDENT, INSTRUCTOR, TREASURER, SSG_ADVISOR, ADMIN, TECHNICAL} - {base_role, role_name}
        # Include dormant assignments in the conflict check: a disabled Admin or
        # Technical Super Admin role must not become a latent mixed-role bypass.
        assigned_role_ids = {a.role_id for a in assignments if a.account_id == target_id}
        persisted_roles = set(Role.objects.using(DEFAULT_DB_ALIAS).filter(
            pk__in=assigned_role_ids).values_list("role_name", flat=True))
        if base_role not in target_roles or (persisted_roles & excluded):
            raise RoleChangeConflict("not_eligible")
        current = next((a for a in assignments if a.account_id == target_id and a.role_id == role.pk), None)
        if (current is not None) is not expected_present:
            raise RoleChangeConflict("state_changed")
        if assign:
            # Never issue a NEW privileged role while its continuous per-request
            # access guard is disabled. Existing role revocation remains possible.
            if not runtime_enforcement_enabled():
                raise RoleChangeUnavailable("Appointment runtime enforcement is required.")
            # The verifier is intentionally default-deny until an independent
            # approved appointment source exists. No caller-provided proof.
            if appointment_verified_for(
                target_account_id=target_id, role_name=role_name,
                assigning_account_id=reviewer.pk, for_grant=True,
            ) is not True:
                raise RoleChangeUnavailable("An independently verified appointment is required.")
            row = AccountRole.objects.using(DEFAULT_DB_ALIAS).create(account=target, role=role, assigned_by=reviewer)
            record_access_audit_receipt(actor=reviewer, target=target, role=role, action=ASSIGN_ACTION,
                                        old_value=None, new_value=snapshot(target_id, role, row.pk), reason=ROLE_REASON)
        else:
            if len(target_roles) <= 1:  # never remove the last active role
                raise RoleChangeConflict("last_role")
            removed = current.pk
            deleted, _ = AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
                pk=removed, account_id=target_id, role_id=role.pk).delete()
            if deleted != 1:
                raise RoleChangeUnavailable("The role assignment could not be changed.")
            record_access_audit_receipt(actor=reviewer, target=target, role=role, action=REVOKE_ACTION,
                                        old_value=snapshot(target_id, role, removed), new_value=None, reason=ROLE_REASON)
        # D-83: all earlier sessions end on privilege changes, including ordinary grants.
        session_revocation.advance(target_id)
    return {"account_id": target_id, "role": role_name, "assigned": assign}


def assign_ordinary_role(*, actor, target_id, role_name, expected_present=False):
    return _ordinary_change(actor=actor, target_id=target_id, role_name=role_name,
                            assign=True, expected_present=expected_present)


def revoke_ordinary_role(*, actor, target_id, role_name, expected_present=True):
    return _ordinary_change(actor=actor, target_id=target_id, role_name=role_name,
                            assign=False, expected_present=expected_present)
