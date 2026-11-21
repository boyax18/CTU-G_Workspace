"""WF-03.06: isolated, read-only audit history routes."""
from django.urls import path
from .access_audit_api import AuditHistoryListView, AuditHistoryDetailView

urlpatterns = [
    path("events/", AuditHistoryListView.as_view(), name="wf0306-audit-events"),
    path("events/<int:audit_id>/", AuditHistoryDetailView.as_view(), name="wf0306-audit-detail"),
]
