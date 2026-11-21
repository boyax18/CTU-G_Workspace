"""WF-03.05 read-only inspector routes: isolated review configurations only."""
from django.urls import path
from .effective_access_api import (
    EffectiveAccessSearchView, EffectiveAccessRolesView, EffectiveAccessDetailView,
)

urlpatterns = [
    path("accounts/", EffectiveAccessSearchView.as_view(), name="wf0305-search"),
    path("accounts/<int:account_id>/roles/", EffectiveAccessRolesView.as_view(), name="wf0305-roles"),
    path("accounts/<int:account_id>/roles/<int:role_id>/", EffectiveAccessDetailView.as_view(), name="wf0305-detail"),
]
