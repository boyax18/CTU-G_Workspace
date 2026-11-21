"""WF-03.03: gated account-specific Grant routes, isolated URLconfs only."""
from django.urls import path
from .account_grant_api import (
    AccountGrantChangeView, AccountGrantDetailView, AccountGrantSearchView,
)

urlpatterns = [
    path("accounts/", AccountGrantSearchView.as_view(), name="wf0303-accounts"),
    path("accounts/<int:account_id>/grants/", AccountGrantDetailView.as_view(), name="wf0303-grants"),
    path("accounts/<int:account_id>/grants/<int:permission_id>/",
         AccountGrantChangeView.as_view(), name="wf0303-grant-change"),
]
