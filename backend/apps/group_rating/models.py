from django.db import models
from django.conf import settings


class RatingSession(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("closed", "Closed"),
        ("released", "Released"),
    ]

    title = models.CharField(max_length=200)
    deadline = models.DateTimeField()
    criteria = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_rating_sessions",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RatingGroup(models.Model):
    session = models.ForeignKey(
        RatingSession, related_name="groups", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="led_rating_groups",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "leader"], name="rating_session_leader_unique"
            )
        ]


class RatingMember(models.Model):
    group = models.ForeignKey(
        RatingGroup, related_name="members", on_delete=models.CASCADE
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rating_memberships",
        on_delete=models.PROTECT,
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "account"], name="rating_group_member_unique"
            )
        ]


class RatingSubmission(models.Model):
    session = models.ForeignKey(
        RatingSession, related_name="submissions", on_delete=models.CASCADE
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rating_submissions",
        on_delete=models.PROTECT,
    )
    group = models.ForeignKey(
        RatingGroup, related_name="submissions", on_delete=models.CASCADE
    )
    ratings = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "rater", "group"],
                name="rating_submission_unique",
            )
        ]


class IndividualResult(models.Model):
    session = models.ForeignKey(
        RatingSession, related_name="results", on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="individual_rating_results",
        on_delete=models.PROTECT,
    )
    group = models.ForeignKey(
        RatingGroup, related_name="results", on_delete=models.CASCADE
    )
    scores = models.JSONField(default=dict)
    final_score = models.DecimalField(max_digits=7, decimal_places=2)
    released_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student", "group"],
                name="individual_rating_result_unique",
            )
        ]


class RatingActivity(models.Model):
    session = models.ForeignKey(
        RatingSession, related_name="activity", on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rating_activity",
        on_delete=models.PROTECT,
    )
    action = models.CharField(max_length=100)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
