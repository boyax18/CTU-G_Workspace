"""WF-03.01 Assign or revoke account roles: shared, governance-sensitive core (owner-approved 18 Nov 2026).

Two separate entry points share these rules; neither is an is_superuser shortcut in a Workspace API:
- apps.access_control.role_assignment: an effective Technical Super Admin (Instructor + Admin +
  Technical Super Admin with access_control.admin_assignments.manage, has_technical_authority)
  assigns or revokes School Admin (`Admin`) for OTHER eligible approved Instructors (D-82, D-97).
- apps.access_control.framework_roles: the protected Django-Superuser-exclusive procedure (D-91 to
  D-93) that also grants or revokes Technical Super Admin; nobody else can (FR-ADM-03).

Every change: one writer_atomic READ COMMITTED transaction with the WF-02.03/02.05 lock order, the
eligibility rechecked inside the lock, exactly one account_roles insert or delete (the table has no
active flag), one append-only audit receipt in the same transaction, and a session-epoch bump for the
target (D-83; apps.accounts.account_status.status_epoch). No schema change, no audit.py change.
"""

from django.db import DEFAULT_DB_ALIAS, transaction

from apps.accounts.models import Account

from .models import AccountPermission, AccountRole, Role, RolePermission, Service
from .writer_boundary import WriterBoundaryUnavailable, writer_atomic

INSTRUCTOR = "Instructor"
ADMIN = "Admin"
TECHNICAL = "Technical Super Admin"
ADMIN_ASSIGNMENT_CODE = "access_control.admin_assignments.manage"

# Audit actions (all also advance the target's session epoch, D-83).
ASSIGN_ACTION = "account.role.assign"            # Technical Super Admin path
REVOKE_ACTION = "account.role.revoke"
FRAMEWORK_ASSIGN_ACTION = "framework.role.assign"   # Django Superuser procedure
FRAMEWORK_REVOKE_ACTION = "framework.role.revoke"
ROLE_CHANGE_ACTIONS = (ASSIGN_ACTION, REVOKE_ACTION, FRAMEWORK_ASSIGN_ACTION, FRAMEWORK_REVOKE_ACTION)
ROLE_REASON = "assignment_change"


class RoleChangeDenied(Exception):
    """Unknown, ineligible or unauthorized target or actor (non-enumerating)."""


class RoleChangeUnavailable(Exception):
    """Gate off, prerequisites or governance state unavailable (fail closed)."""


class RoleChangeConflict(Exception):
    """A fixed, data-free reason for a target the actor may manage."""

    REASONS = frozenset({"state_changed", "not_eligible", "protected_account", "last_school_admin",
                         "last_technical_super_admin"})

    def __init__(self, reason):
        self.reason = reason if reason in self.REASONS else "state_changed"
        super().__init__("The role assignment could not be changed.")


def require_mysql_read_committed():
    connection = transaction.get_connection(DEFAULT_DB_ALIAS)
    if connection.vendor != "mysql" or connection.isolation_level != "read committed":
        raise RoleChangeUnavailable("Role changes require primary MySQL READ COMMITTED.")


def refuse_while_protected_writer_enabled():
    from apps.access_control.executor.client import enabled as executor_enabled
    if executor_enabled():
        # The protected executor has no operation for these changes; refuse rather than bypass it.
        raise WriterBoundaryUnavailable("Role changes are not supported by the protected writer.")


def lock_state(account_ids, *, authority_for=None):
    """WF-02.03/02.05 lock order: services, accounts (by id), their role rows, those roles and, for
    the acting account, its role bindings and account-level overrides (so a Deny, a revoked binding
    or a disabled role committed meanwhile is seen by the in-lock authority check)."""
    services = {row.service_code: row for row in Service.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                .filter(service_code__in=["access_control", "accounts"]).order_by("service_id")}
    if set(services) != {"access_control", "accounts"} or not all(s.is_active for s in services.values()):
        raise RoleChangeUnavailable("Active approved service definitions are required.")
    ids = sorted(set(account_ids))
    accounts = {row.pk: row for row in Account.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                .filter(pk__in=ids).order_by("account_id")}
    if set(accounts) != set(ids):
        raise RoleChangeDenied("An account no longer exists.")
    assignments = list(AccountRole.objects.using(DEFAULT_DB_ALIAS).select_for_update()
                       .filter(account_id__in=ids).order_by("account_role_id"))
    roles = {row.pk: row for row in Role.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(pk__in={a.role_id for a in assignments}).order_by("role_id")}
    held = {pk: set() for pk in ids}
    for a in assignments:
        role = roles.get(a.role_id)
        if role is not None and role.is_active:
            held[a.account_id].add(role.role_name)
    if authority_for is not None:
        actor_role_ids = {a.role_id for a in assignments if a.account_id == authority_for}
        list(RolePermission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(role_id__in=actor_role_ids).order_by("role_permission_id").values_list("pk", flat=True))
        list(AccountPermission.objects.using(DEFAULT_DB_ALIAS).select_for_update()
             .filter(account_id=authority_for).order_by("account_permission_id").values_list("pk", flat=True))
    return services, accounts, assignments, held


def is_eligible_account(account):
    return (isinstance(account, Account) and account.is_active and account.request_status == "Approved"
            and not account.is_staff and not account.is_superuser)


def role_row(role_name):
    try:
        return Role.objects.using(DEFAULT_DB_ALIAS).select_for_update().get(role_name=role_name)
    except Role.DoesNotExist:
        return None


def effective_holders(role_names, *, excluding=None):
    """Accounts that are currently usable holders of ALL the given active roles (people, not rows).

    Locks every assignment of those roles first (in primary-key order), so two concurrent removals
    serialize and the second one sees the first one's committed result (READ COMMITTED).
    """
    list(AccountRole.objects.using(DEFAULT_DB_ALIAS).select_for_update()
         .filter(role__role_name__in=list(role_names)).order_by("account_role_id").values_list("pk", flat=True))
    qs = Account.objects.using(DEFAULT_DB_ALIAS).filter(
        is_active=True, request_status="Approved", is_staff=False, is_superuser=False)
    for name in role_names:
        qs = qs.filter(pk__in=AccountRole.objects.using(DEFAULT_DB_ALIAS)
                       .filter(role__role_name=name, role__is_active=True).values("account_id"))
    if excluding is not None:
        qs = qs.exclude(pk=excluding)
    return qs


def admin_revocation_refusal(target, target_roles):
    """D-94/D-97: rules shared by both entry points for removing School Admin (`Admin`)."""
    if TECHNICAL in target_roles:
        return "protected_account"  # removing Admin would demote a Technical Super Admin (superuser only, revoke it first)
    if INSTRUCTOR not in target_roles:
        return "protected_account"  # legacy Admin-only operator (D-94), e.g. the first-Admin bootstrap account
    if not effective_holders([ADMIN], excluding=target.pk).exists():
        return "last_school_admin"
    return None


def snapshot(account_id, role, assignment_id):
    return {"account_id": account_id, "role_id": role.pk, "account_role_id": assignment_id}
