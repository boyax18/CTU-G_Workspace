"""WF-11.01 academic-period routes (all default-off; see apps.academic.api)."""

from django.urls import path

from .api import (
    SchoolYearCollectionView, SchoolYearDeleteView, SchoolYearHistoryView, SemesterActivationView,
    SemesterArchiveView, SemesterClosureView, SemesterCorrectionView, SemesterDatesView,
)

urlpatterns = [
    path("school-years/", SchoolYearCollectionView.as_view(), name="academic-school-years"),
    path("school-years/<int:school_year_id>/delete/", SchoolYearDeleteView.as_view(),
         name="academic-school-year-delete"),
    path("school-years/<int:school_year_id>/history/", SchoolYearHistoryView.as_view(),
         name="academic-school-year-history"),
    path("semesters/<int:semester_id>/dates/", SemesterDatesView.as_view(), name="academic-semester-dates"),
    # GET preview (base gate) / POST confirmation (WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED).
    path("semesters/<int:semester_id>/activation/", SemesterActivationView.as_view(),
         name="academic-semester-activation"),
    path("semesters/<int:semester_id>/closure/", SemesterClosureView.as_view(), name="academic-semester-closure"),
    path("semesters/<int:semester_id>/archive/", SemesterArchiveView.as_view(), name="academic-semester-archive"),
    # GET impact preview / POST reasoned edit (WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED).
    path("semesters/<int:semester_id>/corrections/", SemesterCorrectionView.as_view(),
         name="academic-semester-corrections"),
]
