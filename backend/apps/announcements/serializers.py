from rest_framework import serializers

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ["id", "title", "body", "author_name", "created_at"]

    def get_author_name(self, announcement):
        if announcement.author is None:
            return "Admin Office"
        profile = getattr(announcement.author, "profile", None)
        if profile is not None:
            name = " ".join(
                part for part in (
                    getattr(profile, "first_name", ""),
                    getattr(profile, "middle_name", ""),
                    getattr(profile, "last_name", ""),
                    getattr(profile, "suffix", ""),
                ) if part
            )
            if name:
                return name
        return announcement.author.school_id
