"""WF-11.01 academic-period routes (all default-off; see apps.academic.api)."""

from django.urls import include, path

from . import configuration_api as c
from .api import (
    SchoolYearCollectionView, SchoolYearDeleteView, SchoolYearHistoryView, SemesterActivationView,
    SemesterArchiveView, SemesterClosureView, SemesterCorrectionView, SemesterDatesView,
)

configuration_urls = [
    path("courses/", c.CourseCollection.as_view(), name="academic-config-courses"),
    path("courses/<int:course_id>/", c.CourseDetail.as_view(), name="academic-config-course"),
    path("courses/<int:course_id>/status/", c.CourseStatus.as_view(), name="academic-config-course-status"),
    path("subjects/", c.SubjectCollection.as_view(), name="academic-config-subjects"),
    path("subjects/<int:subject_id>/", c.SubjectDetail.as_view(), name="academic-config-subject"),
    path("subjects/<int:subject_id>/status/", c.SubjectStatus.as_view(), name="academic-config-subject-status"),
    path("sections/", c.SectionCollection.as_view(), name="academic-config-sections"),
    path("sections/<int:section_id>/", c.SectionDetail.as_view(), name="academic-config-section"),
    path("sections/<int:section_id>/status/", c.SectionStatus.as_view(), name="academic-config-section-status"),
    path("curricula/", c.CurriculumCollection.as_view(), name="academic-config-curricula"),
    path("curricula/<int:curriculum_id>/", c.CurriculumDetail.as_view(), name="academic-config-curriculum"),
    path("curricula/<int:curriculum_id>/entries/", c.CurriculumEntries.as_view(), name="academic-config-curriculum-entries"),
    path("curricula/<int:curriculum_id>/entries/<int:entry_id>/remove/", c.CurriculumEntryRemove.as_view(),
         name="academic-config-curriculum-entry-remove"),
    path("curricula/<int:curriculum_id>/publish/", c.CurriculumPublish.as_view(), name="academic-config-curriculum-publish"),
    path("curricula/<int:curriculum_id>/supersede/", c.CurriculumSupersede.as_view(),
         name="academic-config-curriculum-supersede"),
    path("curricula/<int:curriculum_id>/delete/", c.CurriculumDelete.as_view(), name="academic-config-curriculum-delete"),
    path("semesters/", c.SemesterLookup.as_view(), name="academic-config-semesters"),
    path("offerings/", c.OfferingCollection.as_view(), name="academic-config-offerings"),
    path("offerings/candidates/", c.OfferingCandidates.as_view(), name="academic-config-offering-candidates"),
    path("offerings/<int:offering_id>/remove/", c.OfferingRemove.as_view(), name="academic-config-offering-remove"),
    path("offerings/<int:offering_id>/instructor/", c.OfferingInstructor.as_view(), name="academic-config-instructor"),
    path("offerings/<int:offering_id>/instructor/end/", c.OfferingInstructorEnd.as_view(),
         name="academic-config-instructor-end"),
    path("offerings/<int:offering_id>/instructor/history/", c.OfferingInstructorHistory.as_view(),
         name="academic-config-instructor-history"),
    path("instructors/", c.InstructorLookup.as_view(), name="academic-config-instructors"),
    path("history/<str:kind>/<int:entity_id>/", c.RecordHistory.as_view(), name="academic-config-history"),
]

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
    # Academic configuration (WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED; area write switches).
    path("config/", include(configuration_urls)),
]
