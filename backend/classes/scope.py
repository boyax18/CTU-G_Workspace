from .models import Class


def visible_classes(user):
    """Admins see every class. Instructors see only the classes they teach."""
    if user.is_admin_role:
        return Class.objects.all()
    return Class.objects.filter(instructor=user)