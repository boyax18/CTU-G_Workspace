# ratings/result_services.py
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework.exceptions import ValidationError

from groups.models import GroupMembership
from notifications.services import notify
from .models import RatingPeriod, RatingResult, RatingScore

TWO_PLACES = Decimal("0.01")


def close_period(period):
    if period.status != RatingPeriod.Status.OPEN:
        raise ValidationError("Only an open session can be closed.")
    period.status = RatingPeriod.Status.CLOSED
    period.save(update_fields=["status"])
    return period


@transaction.atomic
def release_period(period):
    """
    Computes each student's weighted score once and stores it.
    Score = sum(criterion_average * weight) / sum(weights), per student.
    """
    period = RatingPeriod.objects.select_for_update().get(pk=period.pk)
    if period.status != RatingPeriod.Status.CLOSED:
        raise ValidationError("Close the session before releasing results.")

    criteria = list(period.criteria.all())
    weights = {c.id: Decimal(c.weight) for c in criteria}
    total_weight = sum(weights.values(), Decimal("0"))
    if not criteria or total_weight <= 0:
        raise ValidationError("The session needs criteria with positive weights.")

    # target -> criterion -> [values]; target -> set of rater ids
    values = defaultdict(lambda: defaultdict(list))
    raters = defaultdict(set)
    scores = RatingScore.objects.filter(submission__period=period).select_related("submission")
    for score in scores:
        values[score.target_id][score.criterion_id].append(score.value)
        raters[score.target_id].add(score.submission.rater_id)

    member_ids = set(
        GroupMembership.objects.filter(period=period).values_list("student_id", flat=True)
    )
    for student_id in member_ids:
        by_criterion = values.get(student_id)
        final = None
        if by_criterion:
            weighted = sum(
                (Decimal(sum(vals)) / Decimal(len(vals))) * weights[cid]
                for cid, vals in by_criterion.items()
            )
            final = (weighted / total_weight).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        RatingResult.objects.create(
            period=period,
            student_id=student_id,
            final_score=final,
            rater_count=len(raters.get(student_id, set())),
        )

    period.status = RatingPeriod.Status.RELEASED
    period.save(update_fields=["status"])

    # The notification says results exist, but does not include the score.
    notify(
        list(member_ids),
        f"Results for '{period.title}' are now available.",
        link=f"/rate/{period.id}/result",
    )
    return period