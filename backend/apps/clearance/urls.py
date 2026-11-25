from django.urls import path
from . import views
from django.urls import path
from . import views

urlpatterns = [
    path("clearance/", views.ClearanceListView.as_view()),
]
