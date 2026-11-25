from django.urls import path

from .views import HelpArticleListView, HelpRequestCreateView


urlpatterns = [
    path("help/articles/", HelpArticleListView.as_view()),
    path("help/contact/", HelpRequestCreateView.as_view()),
]
