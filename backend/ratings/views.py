# ratings/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsInstructorOrAdmin, IsStudent
from classes.scope import visible_classes
from groups.models import GroupMembership
from groups.services import create_group
from .models import RatingCriterion, RatingPeriod, RatingSubmission
from .scope import student_periods, visible_periods
from .serializers import (
    GroupCreateSerializer,
    RatingCriterionSerializer,
    RatingPeriodSerializer,
    SubmitRatingsSerializer,
)
from .services import membership_for, open_period, submit_ratings


def display_name(user):
    return user.get_full_name() or user.username


class RatingPeriodListCreateView(generics.ListCreateAPIView):
    serializer_class = RatingPeriodSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        return visible_periods(self.request.user)

    def perform_create(self, serializer):
        classroom = serializer.validated_data["classroom"]
        if not visible_classes(self.request.user).filter(pk=classroom.pk).exists():
            raise NotFound()
        serializer.save()


class GroupCreateView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, period_id):
        period = get_object_or_404(visible_periods(request.user), pk=period_id)
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = create_group(period, **serializer.validated_data)
        return Response({"id": group.id, "name": group.name}, status=201)


class CriterionListCreateView(generics.ListCreateAPIView):
    serializer_class = RatingCriterionSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_period(self):
        return get_object_or_404(visible_periods(self.request.user), pk=self.kwargs["period_id"])

    def get_queryset(self):
        return self.get_period().criteria.all()

    def perform_create(self, serializer):
        period = self.get_period()
        if period.status != RatingPeriod.Status.DRAFT:
            raise ValidationError("Criteria can only be changed while the session is in draft.")
        serializer.save(period=period)


class OpenPeriodView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, period_id):
        period = get_object_or_404(visible_periods(request.user), pk=period_id)
        open_period(period)
        return Response({"status": period.status})


class RatingFormView(APIView):
    """The student's own form: teammates and criteria. Never includes scores."""
    permission_classes = [IsStudent]

    def get(self, request, period_id):
        period = get_object_or_404(student_periods(request.user), pk=period_id)
        membership = membership_for(period, request.user)
        if membership is None:
            raise NotFound()

        teammates = (
            GroupMembership.objects.filter(group=membership.group)
            .exclude(student=request.user)
            .select_related("student")
        )
        submitted = RatingSubmission.objects.filter(
            period=period, rater=request.user, submitted_at__isnull=False
        ).exists()

        return Response({
            "period": {
                "id": period.id,
                "title": period.title,
                "deadline": period.deadline,
                "status": period.status,
            },
            "criteria": [
                {"id": c.id, "name": c.name, "description": c.description}
                for c in period.criteria.all()
            ],
            "teammates": [
                {"id": m.student_id, "name": display_name(m.student)} for m in teammates
            ],
            "submitted": submitted,
        })


class SubmitRatingsView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, period_id):
        period = get_object_or_404(student_periods(request.user), pk=period_id)
        serializer = SubmitRatingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submit_ratings(period, request.user, serializer.validated_data["scores"])
        return Response({"detail": "Submitted."}, status=201)


class GroupStatusView(APIView):
    """Leader-only. Shows who has submitted, never what they gave."""
    permission_classes = [IsStudent]

    def get(self, request, period_id):
        period = get_object_or_404(student_periods(request.user), pk=period_id)
        membership = membership_for(period, request.user)
        if membership is None:
            raise NotFound()
        if not membership.is_group_leader:
            raise PermissionDenied("Only the group leader can view submission status.")

        members = list(
            GroupMembership.objects.filter(group=membership.group).select_related("student")
        )
        submitted_ids = set(
            RatingSubmission.objects.filter(
                period=period,
                rater_id__in=[m.student_id for m in members],
                submitted_at__isnull=False,
            ).values_list("rater_id", flat=True)
        )
        return Response([
            {
                "id": m.student_id,
                "name": display_name(m.student),
                "submitted": m.student_id in submitted_ids,
            }
            for m in members
        ])