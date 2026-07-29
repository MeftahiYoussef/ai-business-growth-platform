from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import Trend


class TrendSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    momentumLabel = serializers.ChoiceField(source="momentum_label", choices=Trend.Momentum.choices)
    trendScore = serializers.FloatField(source="trend_score")
    growthRate = serializers.FloatField(source="growth_rate", required=False)
    sourcePosts = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Trend
        fields = [
            "_id", "businessId", "topic", "hashtags", "hooks", "format",
            "momentumLabel", "trendScore", "growthRate", "confidence",
            "explanation", "sourcePosts", "createdAt",
        ]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_sourcePosts(self, obj):
        return [external_id(post) for post in obj.source_posts.all()]

    def get_createdAt(self, obj):
        return dt(obj.created_at)
