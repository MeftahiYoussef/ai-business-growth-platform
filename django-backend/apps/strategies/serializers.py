from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import Strategy


class StrategySerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    weeklyCalendar = serializers.JSONField(source="weekly_calendar")
    bestPostingTimes = serializers.JSONField(source="best_posting_times")
    recommendedHashtags = serializers.JSONField(source="recommended_hashtags")
    targetAudienceRecommendation = serializers.CharField(source="target_audience_recommendation")
    nextBestActions = serializers.JSONField(source="next_best_actions")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Strategy
        fields = [
            "_id", "businessId", "weeklyCalendar", "bestPostingTimes",
            "recommendedHashtags", "targetAudienceRecommendation", "nextBestActions", "createdAt",
        ]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
