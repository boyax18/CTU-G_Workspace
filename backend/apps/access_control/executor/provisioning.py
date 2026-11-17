"""P4/P5 fixed protected workflows, usable only inside a verified writer lease."""
import hashlib
from apps.accounts.models import Account
from apps.access_control.audit import record_access_audit_receipt
from apps.access_control.delegation import is_reserved_role
from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.protected_requests import CORE_PERMISSIONS, digest, require, verify_request
from apps.access_control.technical_admin import has_technical_authority
from .protocol import now
from .runtime import active_operation


def before_hash():
    # Credential hashes are bound in memory, never stored as evidence fields.
    models = (Account, Role, Service, Permission, AccountRole, RolePermission, AccountPermission)
    from apps.access_control.protected_requests import canonical
    state = hashlib.sha256(b"CTUG:STATE:v1\x00")
    for model in models:
        fields = [f.attname for f in model._meta.fields if f.name not in {"created_at", "assigned_at", "granted_at", "updated_at", "reviewed_at", "password_reset_token_expires"}]
        state.update(canonical({"table": model._meta.db_table, "fields": fields}))
        for row in model.objects.order_by("pk").values_list(*fields).iterator():
            state.update(canonical(row) + b"\n")
    return state.hexdigest()


def execute_protected(bundle, trust, actor):
    request = verify_request(bundle, trust, now=now())
    require(active_operation() == request["operation"] and request["actor_id"] == actor.pk)
    require(actor.is_active and actor.request_status == "Approved" and not actor.is_staff and not actor.is_superuser)
    require(AccountRole.objects.filter(account=actor, role__role_name="Admin", role__is_active=True).exists())
    require(before_hash() == request["before_hash"])
    service = Service.objects.select_for_update().get(service_code="access_control", is_active=True)
    require(service.service_code == "access_control")
    if request["operation"] == "technical_role.provision":
        require(not any(is_reserved_role(name) and name != "Admin" for name in Role.objects.values_list("role_name", flat=True)))
        role = Role.objects.create(role_name="Technical Super Admin", is_active=False,
            description="Protected technical administration; explicit authority and reviewed bootstrap required.")
        for code in CORE_PERMISSIONS:
            module, action = code.split(".")[1:]
            permission = Permission.objects.filter(permission_code=code).first()
            if permission is None:
                permission = Permission.objects.create(service=service, permission_code=code,
                    permission_name=code.rsplit(".", 1)[1], module_name=module, action_name=action)
                record_access_audit_receipt(actor=actor, permission=permission, action="permission.catalogue.create",
                    new_value={"permission_id": permission.pk, "service_id": service.pk}, reason="permission_change")
            require(permission.permission_code == code and permission.service_id == service.pk
                    and permission.module_name == module and permission.action_name == action)
            RolePermission.objects.create(role=role, permission=permission, is_active=False, granted_by=actor)
        return record_access_audit_receipt(actor=actor, role=role, action="technical_role.provision",
            new_value={"role_id": role.pk, "is_active": False}, reason="permission_change")
    role = Role.objects.select_for_update().get(role_name="Technical Super Admin", is_active=False)
    require(role.role_name == "Technical Super Admin" and not AccountRole.objects.filter(role=role).exists())
    target = Account.objects.select_for_update().get(pk=request["target_id"])
    require(target.is_active and target.request_status == "Approved" and target.has_usable_password()
            and not target.is_staff and not target.is_superuser)
    require(AccountRole.objects.filter(account=target, role__role_name="Admin", role__is_active=True).exists())
    bindings = list(RolePermission.objects.select_for_update().filter(role=role).select_related("permission").order_by("permission__permission_code"))
    require(tuple(b.permission.permission_code for b in bindings) == CORE_PERMISSIONS
            and not any(b.is_active for b in bindings)
            and all(b.permission.service_id == service.pk for b in bindings))
    require(not AccountPermission.objects.filter(account=target, is_active=True, permission__permission_code__in=CORE_PERMISSIONS).exists())
    role.is_active = True
    role.save(update_fields=["is_active"])
    for binding in bindings:
        binding.is_active, binding.granted_by = True, actor
        binding.save(update_fields=["is_active", "granted_by"])
    AccountRole.objects.create(account=target, role=role, assigned_by=actor)
    require(all(has_technical_authority(target, code) for code in CORE_PERMISSIONS))
    return record_access_audit_receipt(actor=actor, target=target, role=role, action="technical_admin.bootstrap",
        new_value={"account_id": target.pk, "role_id": role.pk, "is_active": True}, reason="assignment_change")
