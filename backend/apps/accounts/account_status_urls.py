"""WF-02.05 isolated URLconf, mounted at api/v1/admin/school-accounts/ ONLY by the owner-authorized
local-review and sandbox URLconfs (config.review_local_urls, config.review_sandbox_urls; D-69).

It is NOT included by config.urls, so normal production routes never expose it; the release
safeguard refuses it there, and WORKSPACE_ACCOUNT_STATUS_ENABLED stays off in config.settings.
"""

from django.urls import path

from .account_status_api import (
    ActivateSchoolAccountView, SchoolAccountDetailView, SchoolAccountHistoryView, SchoolAccountListView,
    SuspendSchoolAccountView,
)

urlpatterns = [
    path("", SchoolAccountListView.as_view(), name="school-accounts-list"),
    path("<int:account_id>/", SchoolAccountDetailView.as_view(), name="school-accounts-detail"),
    # WF-02.06 D-76: the only history route; read-only (GET/HEAD/OPTIONS).
    path("<int:account_id>/history/", SchoolAccountHistoryView.as_view(), name="school-accounts-history"),
    path("<int:account_id>/suspend/", SuspendSchoolAccountView.as_view(), name="school-accounts-suspend"),
    path("<int:account_id>/activate/", ActivateSchoolAccountView.as_view(), name="school-accounts-activate"),
]
