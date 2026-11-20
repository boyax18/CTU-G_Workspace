"""AR-6C1 isolated URLconf. NOT included by config.urls; no live routes."""

from django.urls import path

from .registration_review_api import (
    PendingRegistrationRequestsView,
    ApproveRegistrationRequestView,
    RejectRegistrationRequestView,
)

urlpatterns = [
    path("", PendingRegistrationRequestsView.as_view(), name="registration-review-pending"),
    path("<int:account_id>/approve/", ApproveRegistrationRequestView.as_view(), name="registration-review-approve"),
    path("<int:account_id>/reject/", RejectRegistrationRequestView.as_view(), name="registration-review-reject"),
]
