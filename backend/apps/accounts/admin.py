"""Safe, read-only framework-superuser inspection pages for account records."""

from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm

from .framework_admin_readonly import FrameworkSuperuserReadOnlyAdmin
from .models import Account, UserProfile


class WorkspaceAdminAuthenticationForm(AdminAuthenticationForm):
    """Use the Workspace identifier label with Django's existing authentication."""

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": AdminAuthenticationForm.error_messages["invalid_login"] % {"username": "CTU-G ID"},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "CTU-G ID"


admin.site.login_form = WorkspaceAdminAuthenticationForm


@admin.register(Account)
class AccountReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    # Deliberately omit password hashes, reset tokens, and other secrets.
    list_display = (
        "account_identifier", "request_status", "is_active", "is_staff",
        "is_superuser", "created_at",
    )
    list_filter = ("request_status", "is_active", "is_staff", "is_superuser")
    search_fields = ("school_id",)
    fields = (
        "account_identifier", "requested_role", "request_status", "is_active",
        "is_staff", "is_superuser", "created_at", "reviewed_by", "reviewed_at",
    )
    readonly_fields = fields

    @admin.display(description="CTU-G ID", ordering="school_id")
    def account_identifier(self, obj):
        return obj.school_id


@admin.register(UserProfile)
class UserProfileReadOnlyAdmin(FrameworkSuperuserReadOnlyAdmin):
    list_display = ("user_id", "account", "first_name", "last_name")
    search_fields = ("account__school_id", "first_name", "last_name")
    fields = ("account", "first_name", "middle_name", "last_name", "suffix")
    readonly_fields = fields
