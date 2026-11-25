from rest_framework import serializers

from .models import HelpArticle, HelpRequest


class HelpArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpArticle
        fields = ["id", "question", "answer", "category", "order"]
        read_only_fields = fields


class HelpRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequest
        fields = ["id", "subject", "message", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_subject(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Subject is required.")
        return value.strip()

    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message is required.")
        return value.strip()
