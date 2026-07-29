from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import SocialAccount, SocialConnection, SocialPost


class SocialConnectionSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    displayName = serializers.CharField(source="display_name")
    requiredPermissions = serializers.JSONField(source="required_permissions", required=False)
    tokenExpiresAt = serializers.SerializerMethodField()
    lastSuccessfulSyncAt = serializers.SerializerMethodField()
    lastError = serializers.CharField(source="last_error", required=False, allow_blank=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = SocialConnection
        fields = [
            "_id", "businessId", "provider", "status", "displayName", "requiredPermissions",
            "tokenExpiresAt", "lastSuccessfulSyncAt", "lastError", "createdAt",
        ]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_tokenExpiresAt(self, obj):
        return dt(obj.token_expires_at)

    def get_lastSuccessfulSyncAt(self, obj):
        return dt(obj.last_successful_sync_at)

    def get_createdAt(self, obj):
        return dt(obj.created_at)


class SocialAccountSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    providerAccountId = serializers.CharField(source="provider_account_id")
    profileUrl = serializers.URLField(source="profile_url", required=False, allow_blank=True)

    class Meta:
        model = SocialAccount
        fields = ["_id", "businessId", "platform", "providerAccountId", "username", "profileUrl", "followers", "metadata"]

    def get__id(self, obj):
        return str(obj.id)

    def get_businessId(self, obj):
        return external_id(obj.business)


class SocialPostSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    accountId = serializers.SerializerMethodField()
    providerPostId = serializers.CharField(source="provider_post_id")
    contentType = serializers.CharField(source="content_type")
    publishedAt = serializers.SerializerMethodField()

    class Meta:
        model = SocialPost
        fields = ["_id", "accountId", "providerPostId", "caption", "contentType", "publishedAt", "permalink"]

    def get__id(self, obj):
        return str(obj.id)

    def get_accountId(self, obj):
        return str(obj.account_id)

    def get_publishedAt(self, obj):
        return dt(obj.published_at)
