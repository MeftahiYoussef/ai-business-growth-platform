from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import ActivityLog, BusinessMember, TeamInvitation


class BusinessMemberSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    fullName = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = BusinessMember
        fields = ["_id", "businessId", "userId", "fullName", "email", "role", "createdAt"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_userId(self, obj):
        return external_id(obj.user)

    def get_createdAt(self, obj):
        return dt(obj.created_at)


class TeamInvitationSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()
    respondedAt = serializers.SerializerMethodField()

    class Meta:
        model = TeamInvitation
        fields = ["_id", "businessId", "email", "role", "status", "token", "createdAt", "respondedAt"]
        read_only_fields = ["token", "status"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)

    def get_respondedAt(self, obj):
        return dt(obj.responded_at)


class ActivityLogSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    userEmail = serializers.EmailField(source="user.email", read_only=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ["_id", "businessId", "userEmail", "action", "entityType", "entityId", "metadata", "createdAt"]

    entityType = serializers.CharField(source="entity_type")
    entityId = serializers.CharField(source="entity_id")

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
