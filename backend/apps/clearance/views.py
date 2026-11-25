from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import ClearanceItem
from .permissions import IsStudent
from .serializers import ClearanceItemSerializer


class ClearanceListView(generics.ListAPIView):
    """Read-only. Students can see their clearance items but cannot change them."""
    serializer_class = ClearanceItemSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return ClearanceItem.objects.filter(student=self.request.user)