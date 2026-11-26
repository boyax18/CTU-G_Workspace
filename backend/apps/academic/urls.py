"""WF-11.01 academic-period routes (all default-off; see apps.academic.api)."""

from django.urls import include, path

from . import configuration_api as c
from . import student_api as st
from .api import (
    CurrentAcademicPeriodView, SchoolYearCollectionView, SchoolYearDeleteView, SchoolYearHistoryView, SemesterActivationView,
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

onboarding_urls = [
    path("status/", st.OnboardingStatusView.as_view(), name="academic-onboarding-status"),
    path("context/", st.OnboardingContextView.as_view(), name="academic-onboarding-context"),
    path("subject-options/", st.OnboardingSubjectOptionsView.as_view(), name="academic-onboarding-subject-options"),
    path("type/", st.OnboardingTypeView.as_view(), name="academic-onboarding-type"),
    path("subjects/", st.OnboardingSubjectsView.as_view(), name="academic-onboarding-subjects"),
    path("course/", st.OnboardingCourseView.as_view(), name="academic-onboarding-course"),
    path("review/", st.OnboardingReviewView.as_view(), name="academic-onboarding-review"),
    path("finalize/", st.OnboardingFinalizeView.as_view(), name="academic-onboarding-finalize"),
    path("my-semester/", st.MySemesterView.as_view(), name="academic-onboarding-my-semester"),
    path("my-history/", st.MyHistoryView.as_view(), name="academic-onboarding-my-history"),
]

verification_urls = [
    path("students/", st.StudentSearchView.as_view(), name="academic-verification-students"),
    path("students/<int:student_account_id>/", st.StudentRecordView.as_view(), name="academic-verification-student"),
    path("evidence/", st.EvidenceRecordView.as_view(), name="academic-verification-evidence"),
    path("evidence/<int:evidence_id>/revoke/", st.EvidenceRevokeView.as_view(),
         name="academic-verification-evidence-revoke"),
    path("gaps/", st.GapRecordView.as_view(), name="academic-verification-gaps"),
    path("gaps/<int:gap_id>/revoke/", st.GapRevokeView.as_view(), name="academic-verification-gap-revoke"),
    # WF11-D14 (WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED).
    path("historical-participation/", st.HistoricalPreviewView.as_view(), name="academic-historical-preview"),
    path("historical-participation/confirm/", st.HistoricalCorrectView.as_view(), name="academic-historical-confirm"),
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
    # Read-only current period for every academic.catalogue.read holder (WORKSPACE_ACADEMIC_CATALOGUE_ENABLED).
    path("catalogue/current-period/", CurrentAcademicPeriodView.as_view(), name="academic-catalogue-current-period"),
    # Academic configuration (WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED; area write switches).
    path("config/", include(configuration_urls)),
    # Student Semester Onboarding (WORKSPACE_STUDENT_ONBOARDING_ENABLED; finalization switch separate).
    path("onboarding/", include(onboarding_urls)),
    # School Admin official verification (WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED).
    path("verification/", include(verification_urls)),
]
