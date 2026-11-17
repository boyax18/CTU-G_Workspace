# accounts/views.py
from rest_framework import generics
from .serializers import MeSerializer


class MeView(generics.RetrieveAPIView):
    """Returns the logged-in user. React uses this to pick the dashboard."""
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user