# ratings/serializers.py
from django.utils import timezone
from rest_framework import serializers
from .models import RatingPeriod


class RatingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingPeriod
        fields = ["id", "classroom", "title", "deadline", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value


class GroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    member_ids = serializers.ListField(child=serializers.IntegerField(), min_length=2)
    leader_id = serializers.IntegerField()