from django.urls import path
from . import views

urlpatterns = [
    path("finance/summary/", views.FinanceSummaryView.as_view()),
    path("finance/payments/", views.PaymentCreateView.as_view()),
]