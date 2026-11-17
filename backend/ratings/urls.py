
from django.urls import path

from .views import (
    RatingCriteriaListView,
    PeerRatingSubmissionView,
    PeerRatingResultsView,
)

urlpatterns = [
    # Students: retrieve active rating criteria
    path(
        'criteria/',
        RatingCriteriaListView.as_view(),
        name='rating-criteria'
    ),

    # Students: submit peer ratings
    path(
        'submit/',
        PeerRatingSubmissionView.as_view(),
        name='peer-rating-submit'
    ),

    # Instructors/Admins: view detailed rating results
    path(
        'results/<int:period_id>/',
        PeerRatingResultsView.as_view(),
        name='peer-rating-results'
    ),
]

from django.urls import path

from .views import (
    RatingCriteriaListView,
    PeerRatingSubmissionView,
    PeerRatingResultsView,
    StudentPeerRatingResultsView,
)

urlpatterns = [
    # Students: retrieve active rating criteria
    path(
        'criteria/',
        RatingCriteriaListView.as_view(),
        name='rating-criteria'
    ),

    # Students: submit peer ratings
    path(
        'submit/',
        PeerRatingSubmissionView.as_view(),
        name='peer-rating-submit'
    ),

    # Instructors/Admins: view detailed group results
    path(
        'results/<int:period_id>/',
        PeerRatingResultsView.as_view(),
        name='peer-rating-results'
    ),

    # Students: view their own results after period closure
    path(
        'my-results/<int:period_id>/',
        StudentPeerRatingResultsView.as_view(),
        name='student-peer-rating-results'
    ),
]
