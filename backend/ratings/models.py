# ratings/models.py
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RatingPeriod(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        RELEASED = "released", "Released"

    classroom = models.ForeignKey(
        "classes.Class", on_delete=models.CASCADE, related_name="rating_periods"
    )
    title = models.CharField(max_length=200)
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RatingCriterion(models.Model):
    period = models.ForeignKey(RatingPeriod, on_delete=models.CASCADE, related_name="criteria")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    order = models.PositiveSmallIntegerField(default=0)


class RatingSubmission(models.Model):
    period = models.ForeignKey(RatingPeriod, on_delete=models.CASCADE, related_name="submissions")
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="submissions")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["period", "rater"], name="one_submission_per_rater"),
        ]

    @property
    def is_locked(self):
        return self.submitted_at is not None


class RatingScore(models.Model):
    submission = models.ForeignKey(RatingSubmission, on_delete=models.CASCADE,
                                   related_name="scores")
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="received_scores")
    criterion = models.ForeignKey(RatingCriterion, on_delete=models.CASCADE)
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["submission", "target", "criterion"],
                                    name="unique_score"),
        ]