"""Read-only Django framework administration, separate from Workspace roles.

Framework superusers can inspect selected administrative records through /admin/.
This does NOT grant access to the Workspace dashboard or authorize governance
writes. All operational changes must use separately approved audited services.
"""

from django.contrib import admin


class FrameworkSuperuserReadOnlyAdmin(admin.ModelAdmin):
    """Require an active framework superuser for every model-level view."""

    actions = None
    list_per_page = 50
    show_full_result_count = False

    @staticmethod
    def _allowed(request):
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and user.is_staff
            and user.is_superuser
        )

    def has_module_permission(self, request):
        # Account.has_module_perms intentionally returns False for Workspace
        # permissions; Django Admin's model display uses this narrow override.
        return self._allowed(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}
