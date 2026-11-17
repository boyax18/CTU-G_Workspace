# ratings/scope.py
from classes.scope import visible_classes
from .models import RatingPeriod


def visible_periods(user):
    """Instructors see sessions for their own classes. Admins see all."""
    return RatingPeriod.objects.filter(classroom__in=visible_classes(user))


def student_periods(user):
    """Students see sessions only for classes they are enrolled in."""
    return RatingPeriod.objects.filter(classroom__enrollments__student=user)
    