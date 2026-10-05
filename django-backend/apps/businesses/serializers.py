from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import Business


class BusinessSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    ownerId = serializers.SerializerMethodField()
    productOrService = serializers.CharField(source="product_or_service")
    targetAudience = serializers.CharField(source="target_audience")
    knownCompetitors = serializers.JSONField(source="known_competitors", required=False)
    brandVoice = serializers.CharField(source="brand_voice", required=False, allow_blank=True)
    preferredPlatforms = serializers.JSONField(source="preferred_platforms", required=False)
    postingFrequency = serializers.CharField(source="posting_frequency", required=False, allow_blank=True)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "_id", "ownerId", "name", "industry", "country", "productOrService",
            "targetAudience", "goals", "knownCompetitors", "brandVoice", "preferredPlatforms",
            "postingFrequency", "createdAt", "updatedAt",
        ]

    def get_ownerId(self, obj):
        return external_id(obj.owner)

    def get_createdAt(self, obj):
        return dt(obj.created_at)

    def get_updatedAt(self, obj):
        return dt(obj.updated_at)

    def validate_goals(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("goals must be an array")
        return value

    def validate_known_competitors(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("knownCompetitors must be an array")
        return value

    def validate_preferred_platforms(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("preferredPlatforms must be an array")
        return value
