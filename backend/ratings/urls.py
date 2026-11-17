# ratings/urls.py
from django.urls import path
from .views import GroupCreateView, RatingPeriodListCreateView

urlpatterns = [
    path("periods/", RatingPeriodListCreateView.as_view(), name="period-list"),
    path("periods/<int:period_id>/groups/", GroupCreateView.as_view(), name="period-groups"),
]