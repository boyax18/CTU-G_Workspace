from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.services import has_permission
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "is_read", "created_at"]


class NotificationPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_permission(request.user, "notifications.read_state.self.read")


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [NotificationPermission]

    def list(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(recipient=request.user)
        unread_count = notifications.filter(is_read=False).count()
        return Response({
            "notifications": NotificationSerializer(notifications, many=True).data,
            "unread_count": unread_count,
        })


class NotificationReadView(APIView):
    permission_classes = [NotificationPermission]

    def post(self, request, notification_id):
        notification = Notification.objects.filter(
            pk=notification_id,
            recipient=request.user,
        ).first()
        if notification is not None:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response({"authenticated": True, "notification_id": notification_id})


class NotificationReadAllView(APIView):
    permission_classes = [NotificationPermission]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"authenticated": True, "unread_count": 0})
