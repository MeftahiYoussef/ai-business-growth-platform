from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import CompetitorPost


class CompetitorPostSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    competitorId = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    postUrl = serializers.URLField(source="post_url", required=False, allow_blank=True)
    engagementScore = serializers.FloatField(source="engagement_score")
    publishedAt = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = CompetitorPost
        fields = [
            "_id", "competitorId", "businessId", "platform", "postUrl", "caption",
            "hashtags", "hook", "format", "likes", "comments", "shares", "views",
            "engagementScore", "publishedAt", "createdAt",
        ]

    def get_competitorId(self, obj):
        return external_id(obj.competitor)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_publishedAt(self, obj):
        return dt(obj.published_at)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
