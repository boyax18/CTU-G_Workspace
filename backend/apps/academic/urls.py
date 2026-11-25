"""WF-11.01 Draft academic-period routes (all default-off; see apps.academic.api)."""

from django.urls import path

from .api import SchoolYearCollectionView, SchoolYearDeleteView, SemesterDatesView

urlpatterns = [
    path("school-years/", SchoolYearCollectionView.as_view(), name="academic-school-years"),
    path("school-years/<int:school_year_id>/delete/", SchoolYearDeleteView.as_view(),
         name="academic-school-year-delete"),
    path("semesters/<int:semester_id>/dates/", SemesterDatesView.as_view(), name="academic-semester-dates"),
]
