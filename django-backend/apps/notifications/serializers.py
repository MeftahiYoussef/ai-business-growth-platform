from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    notificationType = serializers.CharField(source="notification_type")
    readAt = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["_id", "businessId", "notificationType", "title", "message", "readAt", "metadata", "createdAt"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_readAt(self, obj):
        return dt(obj.read_at)

    def get_createdAt(self, obj):
        return dt(obj.created_at)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    enabledAlertTypes = serializers.JSONField(source="enabled_alert_types", required=False)
    dailyDigest = serializers.BooleanField(source="daily_digest", required=False)
    weeklyDigest = serializers.BooleanField(source="weekly_digest", required=False)
    quietHours = serializers.JSONField(source="quiet_hours", required=False)

    class Meta:
        model = NotificationPreference
        fields = ["_id", "businessId", "enabledAlertTypes", "in_app", "email", "dailyDigest", "weeklyDigest", "thresholds", "quietHours"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)
