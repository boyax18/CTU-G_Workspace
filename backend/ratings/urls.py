# ratings/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("periods/", views.RatingPeriodListCreateView.as_view(), name="period-list"),
    path("periods/<int:period_id>/groups/", views.GroupCreateView.as_view(), name="period-groups"),
    path("periods/<int:period_id>/criteria/", views.CriterionListCreateView.as_view(), name="period-criteria"),
    path("periods/<int:period_id>/open/", views.OpenPeriodView.as_view(), name="period-open"),
    path("periods/<int:period_id>/form/", views.RatingFormView.as_view(), name="period-form"),
    path("periods/<int:period_id>/submit/", views.SubmitRatingsView.as_view(), name="period-submit"),
    path("periods/<int:period_id>/group-status/", views.GroupStatusView.as_view(), name="period-group-status"),
]