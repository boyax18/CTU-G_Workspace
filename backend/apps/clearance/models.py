from django.conf import settings
from django.db import models


class ClearanceItem(models.Model):
    class Status(models.TextChoices):
        CLEARED = "cleared", "Cleared"
        PENDING = "pending", "Pending"
        FOR_REVIEW = "for_review", "For Review"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="clearance_items")
    office = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    remarks = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["office"]
        unique_together = ("student", "office")

    def __str__(self):
        return f"{self.office} - {self.student} ({self.get_status_display()})"