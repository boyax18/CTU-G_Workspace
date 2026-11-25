from django.urls import path

from .views import NotificationListView, NotificationReadView, NotificationReadAllView


urlpatterns = [
    path("notifications/", NotificationListView.as_view()),
    path("notifications/<int:notification_id>/read/", NotificationReadView.as_view()),
    path("notifications/read-all/", NotificationReadAllView.as_view()),
]
