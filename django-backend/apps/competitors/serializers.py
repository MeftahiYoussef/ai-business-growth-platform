from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import Competitor


class CompetitorSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    profileUrl = serializers.URLField(source="profile_url", required=False, allow_blank=True)
    engagementRate = serializers.FloatField(source="engagement_rate", required=False)
    postingFrequency = serializers.CharField(source="posting_frequency", required=False, allow_blank=True)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()

    class Meta:
        model = Competitor
        fields = [
            "_id", "businessId", "name", "platform", "profileUrl", "followers",
            "engagementRate", "postingFrequency", "status", "createdAt", "updatedAt",
        ]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)

    def get_updatedAt(self, obj):
        return dt(obj.updated_at)
