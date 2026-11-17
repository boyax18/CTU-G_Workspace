# notifications/urls.py
from django.urls import path
from .views import MarkReadView, NotificationListView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", MarkReadView.as_view(), name="notification-read"),
]