# ratings/services.py
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from groups.models import GroupMembership
from .models import RatingPeriod, RatingScore, RatingSubmission


def membership_for(period, student):
    return (
        GroupMembership.objects.select_related("group")
        .filter(period=period, student=student)
        .first()
    )


def open_period(period):
    if period.status != RatingPeriod.Status.DRAFT:
        raise ValidationError("Only a draft session can be opened.")
    if not period.criteria.exists():
        raise ValidationError("Add at least one criterion before opening.")
    if not period.groups.exists():
        raise ValidationError("Create groups before opening.")
    period.status = RatingPeriod.Status.OPEN
    period.save(update_fields=["status"])
    return period


@transaction.atomic
def submit_ratings(period, rater, scores):
    """
    scores: list of {"target_id": int, "criterion_id": int, "value": int}
    Values are range-checked by the serializer (1 to 5).
    """
    if period.status != RatingPeriod.Status.OPEN:
        raise ValidationError("This rating session is not open.")
    if timezone.now() > period.deadline:
        raise ValidationError("The deadline has passed.")

    membership = membership_for(period, rater)
    if membership is None:
        raise PermissionDenied("You are not in a group for this session.")

    teammates = set(
        GroupMembership.objects.filter(group=membership.group)
        .exclude(student=rater)
        .values_list("student_id", flat=True)
    )
    if not teammates:
        raise ValidationError("You have no teammates to rate.")

    criteria = set(period.criteria.values_list("id", flat=True))
    expected = {(t, c) for t in teammates for c in criteria}

    received = set()
    for item in scores:
        key = (item["target_id"], item["criterion_id"])
        if key not in expected:
            raise ValidationError(
                "Scores must cover only your teammates and this session's criteria."
            )
        if key in received:
            raise ValidationError("Duplicate score in submission.")
        received.add(key)

    if received != expected:
        raise ValidationError("Every teammate must be rated on every criterion.")

    # Lock the submission row so two simultaneous requests can't both submit.
    submission, _ = RatingSubmission.objects.select_for_update().get_or_create(
        period=period, rater=rater
    )
    if submission.is_locked:
        raise ValidationError("You have already submitted your ratings.")

    RatingScore.objects.bulk_create([
        RatingScore(
            submission=submission,
            target_id=item["target_id"],
            criterion_id=item["criterion_id"],
            value=item["value"],
        )
        for item in scores
    ])

    submission.submitted_at = timezone.now()
    submission.save(update_fields=["submitted_at"])
    return submission