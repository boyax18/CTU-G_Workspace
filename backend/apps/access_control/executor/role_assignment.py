"""School Admin assignment of reviewed base roles; protected promotion excluded."""
from django.conf import settings
from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccountRole, Role, Service
from apps.access_control.services import has_permission
from apps.access_control.protected_requests import require, _id
from apps.access_control.writer_boundary import writer_atomic


def assign_ordinary_role(*, actor, target_id, role_id):
    from .client import LOCAL, remote_call
    remote = remote_call("role.assign", {"actor_id": getattr(actor, "pk", None), "target_id": target_id, "role_id": role_id})
    if remote is not LOCAL:
        return remote
    # This newly introduced operation has no unfenced local-development mode.
    from .runtime import active_operation
    require(active_operation() == "role.assign" and _id(target_id) and _id(role_id) and actor.pk != target_id)
    with writer_atomic():
        Service.objects.select_for_update().get(service_code="access_control", is_active=True)
        accounts = {a.pk: a for a in Account.objects.select_for_update().filter(pk__in=(actor.pk, target_id)).order_by("pk")}
        require(set(accounts) == {actor.pk, target_id})
        require(all(a.is_active and a.request_status == "Approved" and not a.is_staff and not a.is_superuser for a in accounts.values()))
        require(AccountRole.objects.filter(account=actor, role__role_name="Admin", role__is_active=True).exists()
                and has_permission(accounts[actor.pk], "accounts.role_assignments.manage"))
        role = Role.objects.select_for_update().get(pk=role_id, is_active=True)
        require(role.role_name in {"Student", "Instructor"})
        policy = getattr(settings, "WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_POLICY", {})
        require(type(policy) is dict and role.role_name in policy)
        eligible = policy[role.role_name]
        require(type(eligible) is list and eligible and all(n in {"Student", "Instructor"} for n in eligible))
        require(not AccountRole.objects.filter(account_id=target_id).exclude(role__role_name__in=eligible).exists())
        if AccountRole.objects.filter(account_id=target_id, role=role).exists():
            return False
        assignment = AccountRole.objects.create(account_id=target_id, role=role, assigned_by=accounts[actor.pk])
        record_access_audit(actor=accounts[actor.pk], target=accounts[target_id], role=role, action="account.role.assign",
            old_value=None, new_value={"account_id": target_id, "role_id": role.pk, "account_role_id": assignment.pk}, reason="assignment_change")
    return True
