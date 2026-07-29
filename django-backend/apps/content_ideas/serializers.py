from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import ContentIdea


class ContentIdeaSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    engagementPotentialScore = serializers.FloatField(source="engagement_potential_score")
    trendMatchScore = serializers.FloatField(source="trend_match_score")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = ContentIdea
        fields = [
            "_id", "businessId", "title", "hook", "caption", "cta", "hashtags",
            "format", "engagementPotentialScore", "trendMatchScore", "reason", "status", "createdAt",
        ]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
