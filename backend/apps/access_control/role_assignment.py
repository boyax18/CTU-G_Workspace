"""WF-03.01 Technical Super Admin role assignment (owner-approved D-79, D-82, D-97; 18 Nov 2026).

An effective Technical Super Admin (has_technical_authority for access_control.admin_assignments.manage:
active Admin AND Technical Super Admin roles plus the exact effective permission, account-level Deny
wins, services active) assigns or revokes School Admin (`Admin`) for ANOTHER eligible approved
Instructor. It can never grant or revoke Technical Super Admin (FR-ADM-03): that is the Django
Superuser's exclusive procedure (framework_roles). Ordinary responsibilities (Treasurer, SSG Advisor)
are not offered: catalogue v2 still binds their code to Admin, and the v2.1 revision is pending (D-89).

Default-off WORKSPACE_ROLE_ASSIGNMENT_ENABLED; refused while the protected writer is enabled.
"""

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from .audit import record_access_audit_receipt
from .models import AccountRole
from .role_management import (
    ADMIN, ADMIN_ASSIGNMENT_CODE, ASSIGN_ACTION, INSTRUCTOR, REVOKE_ACTION, ROLE_REASON, TECHNICAL,
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
    return {"account_id": target_id, "role": ADMIN, "assigned": assign}


def assign_school_admin(*, actor, target_id, expected_present=False):
    """Add `Admin` to another eligible approved Instructor; the Instructor role stays."""
    return _change(actor=actor, target_id=target_id, assign=True, expected_present=expected_present)


def revoke_school_admin(*, actor, target_id, expected_present=True):
    """Remove `Admin` from another account, never from a Technical Super Admin, the legacy operator or the last one."""
    return _change(actor=actor, target_id=target_id, assign=False, expected_present=expected_present)
