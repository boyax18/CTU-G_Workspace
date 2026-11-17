# accounts/permissions.py
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)


class IsInstructor(BasePermission):
    message = "Instructor access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_instructor)


class IsStudent(BasePermission):
    message = "Student access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_student)

class IsInstructorOrAdmin(BasePermission):
    message = "Instructor or admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_instructor or user.is_admin_role)
        )