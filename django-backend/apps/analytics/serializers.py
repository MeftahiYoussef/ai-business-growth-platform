from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import Goal


class GoalSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    currentValue = serializers.FloatField(source="current_value", required=False)
    targetValue = serializers.FloatField(source="target_value")
    startDate = serializers.DateField(source="start_date")
    progressPercentage = serializers.FloatField(source="progress_percentage", read_only=True)
    recommendedNextActions = serializers.JSONField(source="recommended_next_actions", required=False)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "_id", "businessId", "metric", "currentValue", "targetValue", "startDate", "deadline",
            "platform", "status", "progressPercentage", "recommendedNextActions", "createdAt",
        ]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
