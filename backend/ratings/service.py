from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from groups.models import GroupMembership
from .models import RatingSubmission, RatingScore
from decimal import Decimal
from django.db.models import Avg, Sum, F
@transaction.atomic
def submit_ratings(period, rater, scores):
    """
    scores: list of {"target_id": int, "criterion_id": int, "value": int}
    """
    if period.status != RatingPeriod.Status.OPEN:
        raise ValidationError("This rating session is not open.")
    if timezone.now() > period.deadline:
        raise ValidationError("The deadline has passed.")

    # The rater must belong to a group in this session.
    rater_membership = (
        GroupMembership.objects
        .select_related("group")
        .filter(group__period=period, student=rater)
        .first()
    )
    if rater_membership is None:
        raise PermissionDenied("You are not in a group for this session.")

    group = rater_membership.group
    teammate_ids = set(
        group.memberships.exclude(student=rater).values_list("student_id", flat=True)
    )
    criterion_ids = set(period.criteria.values_list("id", flat=True))

    # Lock the submission row so a double-click can't create two submissions.
    submission, _ = (
        RatingSubmission.objects.select_for_update()
        .get_or_create(period=period, rater=rater)
    )
    if submission.is_locked:
        raise ValidationError("You have already submitted your ratings.")

    expected = {(t, c) for t in teammate_ids for c in criterion_ids}
    received = set()
    for s in scores:
        key = (s["target_id"], s["criterion_id"])
        if key not in expected:
            raise ValidationError("Invalid target or criterion.")
        if key in received:
            raise ValidationError("Duplicate score in submission.")
        received.add(key)

    if received != expected:
        raise ValidationError("Every teammate must be rated on every criterion.")

    RatingScore.objects.bulk_create([
        RatingScore(submission=submission, target_id=s["target_id"],
                    criterion_id=s["criterion_id"], value=s["value"])
        for s in scores
    ])

    submission.submitted_at = timezone.now()
    submission.save(update_fields=["submitted_at"])
    return submission
@transaction.atomic
def release_results(period, released_by):
    if period.status != RatingPeriod.Status.CLOSED:
        raise ValidationError("Close the session before releasing results.")

    weights = {c.id: c.weight for c in period.criteria.all()}
    total_weight = sum(weights.values())
    scores = RatingScore.objects.filter(submission__period=period)

    # Average per (target, criterion) across raters, then weight across criteria.
    per_target = {}
    for row in scores.values("target_id", "criterion_id").annotate(avg=Avg("value")):
        t = row["target_id"]
        per_target.setdefault(t, Decimal("0"))
        per_target[t] += Decimal(str(row["avg"])) * weights[row["criterion_id"]]

    for student_id, weighted in per_target.items():
        RatingResult.objects.update_or_create(
            period=period, student_id=student_id,
            defaults={"final_score": round(weighted / total_weight, 2)},
        )

    period.status = RatingPeriod.Status.RELEASED
    period.save(update_fields=["status"])
    ActivityLog.objects.create(actor=released_by, action="release_results",
                               target=f"period:{period.id}")