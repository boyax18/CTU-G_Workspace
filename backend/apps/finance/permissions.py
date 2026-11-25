from rest_framework.permissions import BasePermission
from apps.access_control.models import AccountRole
from apps.access_control.services import has_permission


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        has_student_role = AccountRole.objects.filter(
            account=request.user,
            account__is_active=True,
            account__request_status="Approved",
            role__role_name="Student",
            role__is_active=True,
        ).exists()
        if not has_student_role:
            return False
        return (
            has_permission(request.user, "finance.payments.self.read")
            or has_permission(request.user, "finance.receipts.self.read")
        )