from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import HelpArticle
from .permissions import IsStudent
from .serializers import HelpArticleSerializer, HelpRequestSerializer


class HelpArticleListView(generics.ListAPIView):
    serializer_class = HelpArticleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = HelpArticle.objects.filter(is_published=True)
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__iexact=category.strip())
        return queryset


class HelpRequestCreateView(generics.CreateAPIView):
    serializer_class = HelpRequestSerializer
    permission_classes = [IsStudent]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
