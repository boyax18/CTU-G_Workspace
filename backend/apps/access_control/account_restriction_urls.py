"""WF-03.04 restriction routes: isolated profiles only, not config.urls."""
from django.urls import path
from .account_restriction_api import (
    RestrictionSearchView, RestrictionDetailView, RestrictionChangeView,
)

urlpatterns = [
    path("accounts/", RestrictionSearchView.as_view(), name="wf0304-accounts"),
    path("accounts/<int:account_id>/overrides/", RestrictionDetailView.as_view(), name="wf0304-overrides"),
    path("accounts/<int:account_id>/overrides/<int:permission_id>/",
         RestrictionChangeView.as_view(), name="wf0304-change"),
]
