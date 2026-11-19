# ratings/result_serializers.py
from rest_framework import serializers


class MyResultSerializer(serializers.Serializer):
    """What a student sees: their own score only. No rater count, no rater identities."""
    period_title = serializers.CharField(source="period.title")
    final_score = serializers.DecimalField(max_digits=4, decimal_places=2, allow_null=True)
    released_at = serializers.DateTimeField()


class InstructorResultSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(source="student.id")
    name = serializers.SerializerMethodField()
    final_score = serializers.DecimalField(max_digits=4, decimal_places=2, allow_null=True)
    rater_count = serializers.IntegerField()

    def get_name(self, obj):
        return obj.student.get_full_name() or obj.student.username