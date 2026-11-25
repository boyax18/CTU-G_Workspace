from django.conf import settings
from django.db import models


class HelpArticle(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class HelpRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="help_requests",
        on_delete=models.CASCADE,
    )
    subject = models.CharField(max_length=150)
    message = models.CharField(max_length=2000)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.student}"
