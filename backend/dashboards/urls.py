from django.urls import path
from .views import AdminDashboardView, InstructorDashboardView, StudentDashboardView

urlpatterns = [
    path("student/", StudentDashboardView.as_view(), name="dashboard-student"),
    path("instructor/", InstructorDashboardView.as_view(), name="dashboard-instructor"),
    path("admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
]
