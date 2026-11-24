"""Loopback-only WF-02 decision routes plus normal read-only application routes."""

from django.urls import include, path

from .urls import urlpatterns as normal_patterns

urlpatterns = [
    path(
        "api/v1/admin/registration-requests/",
        include("apps.accounts.registration_review_urls"),
    ),
    *normal_patterns,
]
