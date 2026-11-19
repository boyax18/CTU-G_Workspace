# ratings/pdf_views.py
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from accounts.permissions import IsInstructorOrAdmin, IsStudent
from .models import RatingPeriod, RatingResult
from .pdf_reports import build_student_pdf, build_summary_pdf
from .result_views import instructor_period_with_results


def pdf_response(content, filename):
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class MyResultPdfView(APIView):
    """A student's own released result as PDF. Same visibility rule as the JSON endpoint."""
    permission_classes = [IsStudent]

    def get(self, request, period_id):
        result = get_object_or_404(
            RatingResult.objects.select_related("period", "student"),
            period_id=period_id,
            student=request.user,
            period__status=RatingPeriod.Status.RELEASED,
        )
        return pdf_response(build_student_pdf(result), f"my-result-period-{period_id}.pdf")


class PeriodSummaryPdfView(APIView):
    """Instructor/admin class summary. Refused until the session is closed."""
    permission_classes = [IsInstructorOrAdmin]

    def get(self, request, period_id):
        period = instructor_period_with_results(request.user, period_id)
        results = (
            RatingResult.objects.filter(period=period)
            .select_related("student")
            .order_by("student__last_name", "student__username")
        )
        return pdf_response(
            build_summary_pdf(period, results), f"summary-period-{period.id}.pdf"
        )