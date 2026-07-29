from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import BusinessAnalysis


class BusinessAnalysisSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    growthRecommendations = serializers.JSONField(source="growth_recommendations")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = BusinessAnalysis
        fields = [
            "_id", "businessId", "strengths", "weaknesses", "opportunities",
            "threats", "growthRecommendations", "createdAt",
        ]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
