from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Announcement
from .serializers import AnnouncementSerializer


class AnnouncementListView(generics.ListAPIView):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    queryset = Announcement.objects.all()
