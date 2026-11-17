
from rest_framework import serializers
from django.utils import timezone

from .models import (
    RatingPeriod,
    RatingCriteria,
    PeerRating,
    RatingScore,
)
from groups.models import Group, GroupMember


class RatingCriteriaSerializer(serializers.ModelSerializer):

    class Meta:
        model = RatingCriteria
        fields = [
            'id',
            'name',
            'description',
            'weight',
            'is_active',
            'display_order',
        ]
        read_only_fields = fields


class RatingPeriodSerializer(serializers.ModelSerializer):

    group_name = serializers.CharField(
        source='group.name',
        read_only=True
    )

    class Meta:
        model = RatingPeriod
        fields = [
            'id',
            'group',
            'group_name',
            'title',
            'start_at',
            'end_at',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class RatingScoreInputSerializer(serializers.Serializer):

    criterion_id = serializers.IntegerField(min_value=1)

    score = serializers.IntegerField(
        min_value=1,
        max_value=5
    )


class PeerRatingSubmissionSerializer(serializers.Serializer):

    rating_period_id = serializers.IntegerField(min_value=1)

    reviewee_id = serializers.IntegerField(min_value=1)

    comment = serializers.CharField(
        required=False,
        allow_blank=True
    )

    scores = RatingScoreInputSerializer(many=True)

    def validate(self, data):

        request = self.context['request']
        reviewer = request.user

        # Only students can submit ratings.
        if reviewer.role != 'STUDENT':
            raise serializers.ValidationError(
                "Only students can submit peer ratings."
            )

        # Find the rating period.
        try:
            period = RatingPeriod.objects.select_related(
                'group'
            ).get(pk=data['rating_period_id'])
        except RatingPeriod.DoesNotExist:
            raise serializers.ValidationError(
                "Rating period does not exist."
            )

        now = timezone.now()

        if period.status != 'OPEN':
            raise serializers.ValidationError(
                "This rating period is not open."
            )

        if now < period.start_at or now > period.end_at:
            raise serializers.ValidationError(
                "This rating period is outside its submission schedule."
            )

        # Reviewer must belong to the group.
        reviewer_is_member = GroupMember.objects.filter(
            group=period.group,
            student=reviewer
        ).exists()

        if not reviewer_is_member:
            raise serializers.ValidationError(
                "You are not a member of this group."
            )

        # Reviewer cannot rate themselves.
        if reviewer.pk == data['reviewee_id']:
            raise serializers.ValidationError(
                "You cannot rate yourself."
            )

        # Reviewee must belong to the same group.
        reviewee_is_member = GroupMember.objects.filter(
            group=period.group,
            student_id=data['reviewee_id']
        ).exists()

        if not reviewee_is_member:
            raise serializers.ValidationError(
                "The selected student is not a member of this group."
            )

        # Prevent duplicate submissions.
        already_submitted = PeerRating.objects.filter(
            rating_period=period,
            reviewer=reviewer,
            reviewee_id=data['reviewee_id']
        ).exists()

        if already_submitted:
            raise serializers.ValidationError(
                "You have already rated this student for this period."
            )

        # All active criteria must be submitted exactly once.
        active_criteria_ids = set(
            RatingCriteria.objects.filter(
                is_active=True
            ).values_list('id', flat=True)
        )

        submitted_ids = [
            item['criterion_id'] for item in data['scores']
        ]

        if len(submitted_ids) != len(set(submitted_ids)):
            raise serializers.ValidationError(
                "Duplicate rating criteria are not allowed."
            )

        if set(submitted_ids) != active_criteria_ids:
            raise serializers.ValidationError(
                "You must submit a score for every active rating criterion."
            )

        data['period'] = period

        return data
