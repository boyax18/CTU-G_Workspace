# ratings/serializers.py
from django.utils import timezone
from rest_framework import serializers
from .models import RatingCriterion, RatingPeriod


class RatingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingPeriod
        fields = ["id", "classroom", "title", "deadline", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The deadline must be in the future.")
        return value


class RatingCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingCriterion
        fields = ["id", "name", "description", "weight", "order"]
        read_only_fields = ["id"]


class GroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    member_ids = serializers.ListField(child=serializers.IntegerField(), min_length=2)
    leader_id = serializers.IntegerField()


class ScoreItemSerializer(serializers.Serializer):
    target_id = serializers.IntegerField()
    criterion_id = serializers.IntegerField()
    value = serializers.IntegerField(min_value=1, max_value=5)


class SubmitRatingsSerializer(serializers.Serializer):
    scores = ScoreItemSerializer(many=True, allow_empty=False)