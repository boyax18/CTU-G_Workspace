from django.conf import settings
from django.db import models

from apps.announcements.models import Announcement


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="workspace_notifications",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    announcement = models.ForeignKey(
        Announcement,
        related_name="notifications",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.recipient.school_id})"
