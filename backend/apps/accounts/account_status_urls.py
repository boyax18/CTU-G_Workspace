"""WF-02.05 isolated URLconf. NOT included by config.urls, review_local_urls or review_sandbox_urls.

Mounting it in the local review or sandbox URLconfs is a protected change that needs separate
owner authorization (D-69); the proposed mount point is api/v1/admin/school-accounts/.
"""

from django.urls import path

from .account_status_api import (
    ActivateSchoolAccountView, SchoolAccountDetailView, SchoolAccountListView, SuspendSchoolAccountView,
)

urlpatterns = [
    path("", SchoolAccountListView.as_view(), name="school-accounts-list"),
    path("<int:account_id>/", SchoolAccountDetailView.as_view(), name="school-accounts-detail"),
    path("<int:account_id>/suspend/", SuspendSchoolAccountView.as_view(), name="school-accounts-suspend"),
    path("<int:account_id>/activate/", ActivateSchoolAccountView.as_view(), name="school-accounts-activate"),
]
