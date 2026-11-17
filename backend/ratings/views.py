# ratings/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsStudent
from .models import RatingPeriod, RatingResult
from .services import submit_ratings
from .serializers import SubmitRatingsSerializer, ResultSerializer

class SubmitRatingsView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, period_id):
        # Students can only rate sessions they are enrolled in.
        period = get_object_or_404(
            RatingPeriod.objects.filter(
                classroom__enrollments__student=request.user
            ),
            pk=period_id,
        )
        ser = SubmitRatingsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        submit_ratings(period, request.user, ser.validated_data["scores"])
        return Response({"detail": "Submitted."}, status=status.HTTP_201_CREATED)

class MyResultView(generics.RetrieveAPIView):
    """A student sees only their own result, and only after release."""
    serializer_class = ResultSerializer
    permission_classes = [IsStudent]

    def get_object(self):
        return get_object_or_404(
            RatingResult.objects.select_related("period"),
            period_id=self.kwargs["period_id"],
            student=self.request.user,
            period__status=RatingPeriod.Status.RELEASED,
        )