from rest_framework.permissions import BasePermission

from apps.access_control.models import AccountRole


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and AccountRole.objects.filter(
            account=request.user,
            account__is_active=True,
            account__request_status="Approved",
            role__role_name="Student",
            role__is_active=True,
        ).exists()
