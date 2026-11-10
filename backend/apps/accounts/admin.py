"""Safe, read-only framework-superuser inspection pages for account records."""

from django.contrib import admin

from .framework_admin_readonly import FrameworkSuperuserReadOnlyAdmin
from .models import Account, UserProfile


@admin.register(Account)
class AccountReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    # Deliberately omit password hashes, reset tokens, and other secrets.
    list_display = (
        "school_id", "request_status", "is_active", "is_staff",
        "is_superuser", "created_at",
    )
    list_filter = ("request_status", "is_active", "is_staff", "is_superuser")
    search_fields = ("school_id",)
    fields = (
        "school_id", "requested_role", "request_status", "is_active",
        "is_staff", "is_superuser", "created_at", "reviewed_by", "reviewed_at",
    )
    readonly_fields = fields


@admin.register(UserProfile)
class UserProfileReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("user_id", "account", "first_name", "last_name")
    search_fields = ("account__school_id", "first_name", "last_name")
    fields = ("account", "first_name", "middle_name", "last_name", "suffix")
    readonly_fields = fields
