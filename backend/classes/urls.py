# classes/urls.py
from django.urls import path
from .views import ClassDetailView, ClassListCreateView, EnrollStudentsView

urlpatterns = [
    path("", ClassListCreateView.as_view(), name="class-list"),
    path("<int:pk>/", ClassDetailView.as_view(), name="class-detail"),
    path("<int:pk>/enroll/", EnrollStudentsView.as_view(), name="class-enroll"),
]