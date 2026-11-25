import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class Assessment(models.Model):
    """What a student owes for a semester. Set by the Accounting Office."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="assessments")
    semester = models.CharField(max_length=40)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("student", "semester")

    def __str__(self):
        return f"{self.student} - {self.semester}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="payments")
    reference = models.CharField(max_length=20, unique=True, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = "PAY-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} ({self.amount})"