# ratings/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsInstructorOrAdmin
from classes.scope import visible_classes
from groups.services import create_group
from .models import RatingPeriod
from .serializers import GroupCreateSerializer, RatingPeriodSerializer


def visible_periods(user):
    return RatingPeriod.objects.filter(classroom__in=visible_classes(user))


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