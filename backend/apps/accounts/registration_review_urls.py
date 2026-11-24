"""Isolated decision URLconf. Never include these mutation routes in config.urls."""

from django.urls import path

from .registration_bulk_api import BulkRegistrationReviewView
from .registration_review_api import (
    PendingRegistrationRequestsView,
    ApproveRegistrationRequestView,
    RejectRegistrationRequestView,
)

urlpatterns = [
    path("", PendingRegistrationRequestsView.as_view(), name="registration-review-pending"),
    path("<int:account_id>/approve/", ApproveRegistrationRequestView.as_view(), name="registration-review-approve"),
    path("<int:account_id>/reject/", RejectRegistrationRequestView.as_view(), name="registration-review-reject"),
    path("bulk/", BulkRegistrationReviewView.as_view(), name="bulk-registration-review"),
]
