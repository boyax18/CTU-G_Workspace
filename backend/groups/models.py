# groups/models.py
from django.conf import settings
from django.db import models
from ratings.models import RatingPeriod

class Group(models.Model):
    period = models.ForeignKey(RatingPeriod, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=100)

class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="group_memberships")
    is_group_leader = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "student"], name="unique_member"),
        ]