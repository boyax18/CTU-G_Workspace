"""Read-only Django Admin views; governance mutations stay in trusted services."""

from django.contrib import admin

from apps.accounts.framework_admin_readonly import FrameworkSuperuserReadOnlyAdmin

from .models import (
    AccessAuditLog,
    AccountPermission,
    AccountRole,
    Permission,
    Role,
    RolePermission,
    Service,
)


@admin.register(Role)
class RoleReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("role_id", "role_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("role_name",)
    fields = ("role_id", "role_name", "description", "is_active")
    readonly_fields = fields


@admin.register(AccountRole)
class AccountRoleReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("account_role_id", "account", "role", "assigned_at")
    search_fields = ("account__school_id", "role__role_name")
    fields = ("account", "role", "assigned_by", "assigned_at")
    readonly_fields = fields


@admin.register(Service)
class ServiceReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("service_id", "service_code", "service_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("service_code", "service_name")
    fields = ("service_id", "service_code", "service_name", "description", "is_active")
    readonly_fields = fields


@admin.register(Permission)
class PermissionReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("permission_id", "permission_code", "service", "module_name", "action_name")
    search_fields = ("permission_code", "permission_name")
    fields = (
        "permission_id", "permission_code", "permission_name", "service",
        "module_name", "action_name", "description", "created_at",
    )
    readonly_fields = fields


@admin.register(RolePermission)
class RolePermissionReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("role_permission_id", "role", "permission", "is_active")
    list_filter = ("is_active",)
    search_fields = ("role__role_name", "permission__permission_code")
    fields = ("role", "permission", "is_active", "granted_by", "granted_at")
    readonly_fields = fields


@admin.register(AccountPermission)
class AccountPermissionReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("account_permission_id", "account", "permission", "effect", "is_active")
    list_filter = ("effect", "is_active")
    search_fields = ("account__school_id", "permission__permission_code")
    fields = (
        "account", "permission", "effect", "is_active",
        "assigned_by", "created_at", "updated_at",
    )
    readonly_fields = fields


@admin.register(AccessAuditLog)
class AccessAuditLogReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    # Omit JSON old_value/new_value and free-form reason from Admin UI.
    list_display = ("access_audit_log_id", "action", "actor_account", "target_account", "created_at")
    search_fields = ("action", "actor_account__school_id", "target_account__school_id")
    fields = (
        "access_audit_log_id", "action", "actor_account", "target_account",
        "role", "permission", "created_at",
    )
    readonly_fields = fields
