from rest_framework import serializers
from .models import ClearanceItem


class ClearanceItemSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ClearanceItem
        fields = ["id", "office", "status", "status_label", "remarks", "updated_at"]
        read_only_fields = fields