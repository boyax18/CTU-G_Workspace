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

from apps.accounts.registration_review_api import PendingRegistrationRequestsView

urlpatterns = [
    path('api/v1/auth/', include('apps.accounts.urls')),
    # WF-02.01 (D-31): ONLY the read-only list is mounted, behind its own gate (default off).
    # Approve/reject (WF-02.03/02.04) remain unmounted; never include the isolated review URLconf here.
    path(
        'api/v1/admin/registration-requests/',
        PendingRegistrationRequestsView.as_view(),
        name='registration-review-pending',
    ),
    path('admin/', admin.site.urls),
]
