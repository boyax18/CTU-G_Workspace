"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from apps.accounts.active_role_context_api import RoleContextSwitchView
from apps.accounts.account_status_api import (
    SchoolAccountDetailView, SchoolAccountHistoryView, SchoolAccountListView,
)

from apps.accounts.registration_review_api import (
    PendingRegistrationDetailView,
    PendingRegistrationRequestsView,
)

urlpatterns = [
    path('api/v1/auth/', include('apps.accounts.urls')),
    # D-116: normal development route; view denies with 503 unless the
    # explicit local role-context gate is on, and refuses protected executor.
    path('api/v1/auth/role-context/', RoleContextSwitchView.as_view(),
         name='workspace-role-context-switch-normal'),
    # WF-02.01 (D-31) list and WF-02.02 (D-37) detail: the ONLY two review routes, both GET-only and
    # behind the same read switch (default off). Approve/reject (WF-02.03/02.04) remain unmounted;
    # never include the isolated review URLconf here.
    path(
        'api/v1/admin/registration-requests/',
        PendingRegistrationRequestsView.as_view(),
        name='registration-review-pending',
    ),
    path(
        'api/v1/admin/registration-requests/<int:account_id>/',
        PendingRegistrationDetailView.as_view(),
        name='registration-review-detail',
    ),
    # WF-02 read-only integration. Never include account_status_urls here: it also mounts writes.
    path('api/v1/admin/school-accounts/', SchoolAccountListView.as_view(), name='school-accounts-list'),
    path('api/v1/admin/school-accounts/<int:account_id>/', SchoolAccountDetailView.as_view(), name='school-accounts-detail'),
    path('api/v1/admin/school-accounts/<int:account_id>/history/', SchoolAccountHistoryView.as_view(), name='school-accounts-history'),
    # WF-11.01 Draft academic periods: every view answers 503 unless WORKSPACE_ACADEMIC_PERIODS_ENABLED
    # is on; HDAC (academic.periods.manage, Admin assignment/context, Deny precedence) on every request.
    # No activation, closure, archiving, fee or curriculum route exists.
    path('api/v1/academic/', include('apps.academic.urls')),
    path('admin/', admin.site.urls),
]
