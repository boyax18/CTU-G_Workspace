from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        # Same check as finance/permissions.py. Update both if your roles differ.
        return request.user.is_authenticated and getattr(request.user, "role", None) == "student"