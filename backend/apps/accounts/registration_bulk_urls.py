"""Isolated test-only URLconf. NOT included by backend/config/urls.py."""

from django.urls import path

from .registration_bulk_api import BulkRegistrationReviewView
from .registration_review_api import PendingRegistrationRequestsView

urlpatterns = [
    path("", PendingRegistrationRequestsView.as_view(), name="bulk-review-pending-preview"),
    path("bulk/", BulkRegistrationReviewView.as_view(), name="bulk-registration-review"),
]
