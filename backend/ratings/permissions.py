
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """
    Only students can access student peer-rating actions.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'STUDENT'
        )


class IsInstructorOrAdmin(BasePermission):
    """
    Only instructors and admins can access detailed rating results.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ['INSTRUCTOR', 'ADMIN']
        )


class IsAdmin(BasePermission):
    """
    Only admins can manage global rating criteria.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == 'ADMIN'
        )
