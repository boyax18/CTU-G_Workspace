# classes/serializers.py
from rest_framework import serializers
from .models import Class


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ["id", "code", "name", "instructor", "created_at"]
        read_only_fields = ["id", "instructor", "created_at"]


class EnrollSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )