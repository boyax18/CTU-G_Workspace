# ratings/urls.py
from django.urls import path
from . import pdf_views, result_views, views

urlpatterns = [
    path("periods/", views.RatingPeriodListCreateView.as_view(), name="period-list"),
    path("periods/<int:period_id>/groups/", views.GroupCreateView.as_view(), name="period-groups"),
    path("periods/<int:period_id>/criteria/", views.CriterionListCreateView.as_view(), name="period-criteria"),
    path("periods/<int:period_id>/open/", views.OpenPeriodView.as_view(), name="period-open"),
    path("periods/<int:period_id>/form/", views.RatingFormView.as_view(), name="period-form"),
    path("periods/<int:period_id>/submit/", views.SubmitRatingsView.as_view(), name="period-submit"),
    path("periods/<int:period_id>/group-status/", views.GroupStatusView.as_view(), name="period-group-status"),
    path("periods/<int:period_id>/close/", result_views.ClosePeriodView.as_view(), name="period-close"),
    path("periods/<int:period_id>/release/", result_views.ReleasePeriodView.as_view(), name="period-release"),
    path("periods/<int:period_id>/my-result/", result_views.MyResultView.as_view(), name="period-my-result"),
    path("periods/<int:period_id>/my-result/pdf/", pdf_views.MyResultPdfView.as_view(), name="period-my-result-pdf"),
    path("periods/<int:period_id>/results/", result_views.PeriodResultsView.as_view(), name="period-results"),
    path("periods/<int:period_id>/export/", result_views.ExportResultsView.as_view(), name="period-export"),
    path("periods/<int:period_id>/summary.pdf", pdf_views.PeriodSummaryPdfView.as_view(), name="period-summary-pdf"),
]