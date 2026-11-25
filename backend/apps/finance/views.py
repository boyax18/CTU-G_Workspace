from decimal import Decimal
from django.db.models import Sum
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assessment, Payment
from .permissions import IsStudent
from .serializers import PaymentSerializer


def get_balance(user):
    """Returns (total, paid, balance). Only verified payments reduce the balance."""
    assessment = Assessment.objects.filter(student=user).order_by("-id").first()
    total = assessment.total if assessment else Decimal("0.00")
    paid = (Payment.objects.filter(student=user, status=Payment.Status.VERIFIED)
            .aggregate(s=Sum("amount"))["s"] or Decimal("0.00"))
    return total, paid, total - paid


class FinanceSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        total, paid, balance = get_balance(request.user)
        payments = Payment.objects.filter(student=request.user)
        return Response({
            "total": total,
            "paid": paid,
            "balance": balance,
            "payments": PaymentSerializer(payments, many=True).data,
        })


class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def perform_create(self, serializer):
        amount = serializer.validated_data["amount"]
        _, _, balance = get_balance(self.request.user)
        if amount > balance:
            raise ValidationError({"amount": "Amount cannot be more than your balance."})
        serializer.save(student=self.request.user)