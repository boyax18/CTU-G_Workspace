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
from apps.group_rating.views import (
    RatingLeaderNotificationView,
    RatingMemberView,
    RatingNotificationReadView,
    RatingPublishView,
    RatingReleaseView,
    RatingSessionView,
    RatingSubmissionView,
    RatingWorkspaceView,
)

from apps.accounts.registration_review_api import (
    PendingRegistrationDetailView,
    PendingRegistrationRequestsView,
)

urlpatterns = [
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.helpcenter.urls')),
    path('api/v1/', include('apps.finance.urls')),
    path('api/v1/', include('apps.announcements.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/group-rating/', RatingWorkspaceView.as_view()),
    path('api/v1/group-rating/sessions/', RatingSessionView.as_view()),
    path('api/v1/group-rating/sessions/<int:session_id>/members/', RatingMemberView.as_view()),
    path('api/v1/group-rating/sessions/<int:session_id>/publish/', RatingPublishView.as_view()),
    path('api/v1/group-rating/sessions/<int:session_id>/submit/', RatingSubmissionView.as_view()),
    path('api/v1/group-rating/sessions/<int:session_id>/release/', RatingReleaseView.as_view()),
    path('api/v1/group-rating/sessions/<int:session_id>/notify/', RatingLeaderNotificationView.as_view()),
    path('api/v1/group-rating/notifications/<int:notification_id>/read/', RatingNotificationReadView.as_view()),
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
    path('admin/', admin.site.urls),
]
