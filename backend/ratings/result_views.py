# ratings/result_views.py
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsInstructorOrAdmin, IsStudent
from .models import RatingPeriod, RatingResult
from .result_serializers import InstructorResultSerializer, MyResultSerializer
from .result_services import close_period, release_period
from .scope import visible_periods

REVEALABLE = (RatingPeriod.Status.CLOSED, RatingPeriod.Status.RELEASED)


def instructor_period_with_results(user, period_id):
    period = get_object_or_404(visible_periods(user), pk=period_id)
    if period.status not in REVEALABLE:
        raise ValidationError("Results are available once the session is closed.")
    return period


class ClosePeriodView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, period_id):
        period = get_object_or_404(visible_periods(request.user), pk=period_id)
        close_period(period)
        return Response({"status": period.status})


class ReleasePeriodView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, period_id):
        period = get_object_or_404(visible_periods(request.user), pk=period_id)
        release_period(period)
        return Response({"status": "released"})


class MyResultView(APIView):
    """A student's own released result. Other students' rows can't be addressed here."""
    permission_classes = [IsStudent]

    def get(self, request, period_id):
        result = get_object_or_404(
            RatingResult.objects.select_related("period"),
            period_id=period_id,
            student=request.user,
            period__status=RatingPeriod.Status.RELEASED,
        )
        return Response(MyResultSerializer(result).data)


class PeriodResultsView(generics.ListAPIView):
    """Instructor view of all results for their session. Available after close."""
    serializer_class = InstructorResultSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        period = instructor_period_with_results(self.request.user, self.kwargs["period_id"])
        return (
            RatingResult.objects.filter(period=period)
            .select_related("student")
            .order_by("student__last_name", "student__username")
        )


class ExportResultsView(APIView):
    permission_classes = [IsInstructorOrAdmin]

    def get(self, request, period_id):
        period = instructor_period_with_results(request.user, period_id)
        results = (
            RatingResult.objects.filter(period=period)
            .select_related("student")
            .order_by("student__last_name", "student__username")
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Results"
        ws.append(["Student ID", "Name", "Final score", "Raters"])
        for r in results:
            name = r.student.get_full_name() or r.student.username
            ws.append([
                r.student.student_id or r.student.username,
                name,
                float(r.final_score) if r.final_score is not None else None,
                r.rater_count,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="results-period-{period.id}.xlsx"'
        wb.save(response)
        return response