# classes/views.py
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsInstructorOrAdmin
from .models import Enrollment
from .scope import visible_classes
from .serializers import ClassSerializer, EnrollSerializer


class ClassListCreateView(generics.ListCreateAPIView):
    serializer_class = ClassSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        return visible_classes(self.request.user)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)


class ClassDetailView(generics.RetrieveAPIView):
    serializer_class = ClassSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        # Another instructor's class returns 404, not 403, so it isn't revealed.
        return visible_classes(self.request.user)


class EnrollStudentsView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, pk):
        classroom = get_object_or_404(visible_classes(request.user), pk=pk)
        serializer = EnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = set(serializer.validated_data["student_ids"])
        students = list(
            User.objects.filter(pk__in=ids, role=User.Role.STUDENT)
        )
        if len(students) != len(ids):
            raise ValidationError("Every ID must belong to a student account.")

        with transaction.atomic():
            Enrollment.objects.bulk_create(
                [Enrollment(classroom=classroom, student=s) for s in students],
                ignore_conflicts=True,  # already-enrolled students are skipped
            )
        return Response({"enrolled": len(students)}, status=201)