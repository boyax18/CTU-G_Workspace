# groups/services.py
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from classes.models import Enrollment
from notifications.services import notify
from ratings.models import RatingPeriod
from .models import Group, GroupMembership


@transaction.atomic
def create_group(period, name, member_ids, leader_id):
    if period.status != RatingPeriod.Status.DRAFT:
        raise ValidationError("Groups can only be changed while the session is in draft.")

    members = set(member_ids)
    if leader_id not in members:
        raise ValidationError("The leader must be one of the group members.")

    enrolled = set(
        Enrollment.objects.filter(classroom=period.classroom, student_id__in=members)
        .values_list("student_id", flat=True)
    )
    if enrolled != members:
        raise ValidationError("Every member must be enrolled in this class.")

    if GroupMembership.objects.filter(period=period, student_id__in=members).exists():
        raise ValidationError("A student is already in a group for this session.")

    group = Group.objects.create(period=period, name=name)
    try:
        GroupMembership.objects.bulk_create([
            GroupMembership(
                period=period,
                group=group,
                student_id=sid,
                is_group_leader=(sid == leader_id),
            )
            for sid in members
        ])
    except IntegrityError:
        raise ValidationError("A student was just added to another group.")

    notify(
        [leader_id],
        f"You are the leader of {name} for '{period.title}'.",
        link=f"/rate/{period.id}/group",
    )
    return group