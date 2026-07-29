from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import Campaign, ContentDraft, ContentVersion, ReviewComment


class CampaignSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    startDate = serializers.DateField(source="start_date", required=False, allow_null=True)
    endDate = serializers.DateField(source="end_date", required=False, allow_null=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ["_id", "businessId", "name", "description", "objective", "startDate", "endDate", "platforms", "goals", "status", "createdAt"]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_businessId(self, obj) -> str:
        return external_id(obj.business)

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)


class ContentDraftSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    contentType = serializers.CharField(source="content_type", required=False, allow_blank=True)
    assignedTo = serializers.SerializerMethodField()
    createdBy = serializers.SerializerMethodField()
    scheduledAt = serializers.SerializerMethodField()
    approvalStatus = serializers.CharField(source="approval_status", required=False)
    providerPostId = serializers.CharField(source="provider_post_id", required=False, allow_blank=True)
    sourceAiGenerationId = serializers.SerializerMethodField()
    sourcePlanDay = serializers.IntegerField(source="source_plan_day", required=False, allow_null=True)
    publicationResult = serializers.JSONField(source="publication_result", required=False)
    retryCount = serializers.IntegerField(source="retry_count", required=False)
    maxRetries = serializers.IntegerField(source="max_retries", required=False)
    createdAt = serializers.SerializerMethodField()
    updatedAt = serializers.SerializerMethodField()

    class Meta:
        model = ContentDraft
        fields = [
            "_id", "businessId", "title", "caption", "platform", "contentType", "hashtags", "cta",
            "assignedTo", "createdBy", "status", "scheduledAt", "timezone", "approvalStatus",
            "providerPostId", "sourceAiGenerationId", "sourcePlanDay", "publicationResult", "retryCount", "maxRetries", "createdAt", "updatedAt",
        ]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_businessId(self, obj) -> str:
        return external_id(obj.business)

    def get_assignedTo(self, obj) -> str | None:
        return external_id(obj.assigned_to) if obj.assigned_to else None

    def get_createdBy(self, obj) -> str | None:
        return external_id(obj.created_by) if obj.created_by else None

    def get_scheduledAt(self, obj) -> str | None:
        return dt(obj.scheduled_at)

    def get_sourceAiGenerationId(self, obj) -> str | None:
        return str(obj.source_ai_generation_id) if obj.source_ai_generation_id else None

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)

    def get_updatedAt(self, obj) -> str | None:
        return dt(obj.updated_at)


class ContentVersionSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    versionNumber = serializers.IntegerField(source="version_number")
    changeSummary = serializers.CharField(source="change_summary")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = ContentVersion
        fields = ["_id", "versionNumber", "title", "caption", "changeSummary", "createdAt"]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)


class ReviewCommentSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    userEmail = serializers.EmailField(source="user.email", read_only=True)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = ReviewComment
        fields = ["_id", "userEmail", "comment", "mentions", "createdAt"]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)
