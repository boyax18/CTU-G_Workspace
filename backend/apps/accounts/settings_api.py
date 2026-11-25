from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control.services import has_permission
from .models import UserProfile


class ProfileSettingsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and has_permission(
            request.user,
            "accounts.profile.self.update",
        )


class ProfileSettingsSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    middle_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    suffix = serializers.CharField(max_length=20, allow_blank=True, required=False)
    email = serializers.EmailField(max_length=150, allow_blank=True, required=False)


class ProfileSettingsView(APIView):
    permission_classes = [ProfileSettingsPermission]

    def get_payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(account=request.user)
        return {
            "first_name": profile.first_name or "",
            "middle_name": profile.middle_name or "",
            "last_name": profile.last_name or "",
            "suffix": profile.suffix or "",
            "email": request.user.email or "",
        }

    def get(self, request):
        return Response(self.get_payload(request))

    def patch(self, request):
        return self.update(request)

    def post(self, request):
        return self.update(request)

    def update(self, request):
        serializer = ProfileSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if set(request.data) - {
            "first_name", "middle_name", "last_name", "suffix", "email",
        }:
            raise serializers.ValidationError("Unsupported settings fields.")

        profile, _ = UserProfile.objects.get_or_create(account=request.user)
        for field in ("first_name", "middle_name", "last_name", "suffix"):
            if field in serializer.validated_data:
                setattr(profile, field, serializer.validated_data[field] or "")
        profile.save(update_fields=["first_name", "middle_name", "last_name", "suffix"])

        if "email" in serializer.validated_data:
            email = serializer.validated_data["email"].strip()
            request.user.email = email or None
            request.user.save(update_fields=["email"])

        return Response(self.get_payload(request))
