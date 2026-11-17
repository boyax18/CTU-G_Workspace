from django.conf import settings
from django.db import models

class Class(models.Model):
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="classes_taught"
    )
    created_at = models.DateTimeField(auto_now_add=True)

class Enrollment(models.Model):
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="enrollments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["classroom", "student"], name="unique_enrollment")
        ]