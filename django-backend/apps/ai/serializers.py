from rest_framework import serializers

from common.serializers import dt
from common.utilities.ids import external_id

from .models import AIContentGeneration, AIContentGenerationVersion


class AIContentGenerationSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    contentFormat = serializers.CharField(source="content_format", required=False, allow_blank=True)
    generatedContent = serializers.JSONField(source="generated_content", required=False)
    featureName = serializers.CharField(source="feature_name", required=False)
    promptVersion = serializers.CharField(source="prompt_version", required=False, allow_blank=True)
    structuredOutput = serializers.JSONField(source="structured_output", required=False)
    inputSnapshot = serializers.JSONField(source="input_snapshot", required=False)
    generationParameters = serializers.JSONField(source="generation_parameters", required=False)
    errorType = serializers.CharField(source="error_type", required=False, allow_blank=True)
    providerRequestId = serializers.CharField(source="provider_request_id", required=False, allow_blank=True)
    latencyMs = serializers.IntegerField(source="latency_ms", required=False)
    draftLinks = serializers.JSONField(source="draft_links", required=False)
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = AIContentGeneration
        fields = [
            "_id", "businessId", "userId", "featureName", "promptVersion", "objective", "platform", "audience", "tone", "language",
            "contentFormat", "prompt", "inputSnapshot", "generatedContent", "structuredOutput", "provider", "model", "generationParameters",
            "usage", "feedback", "status", "errorType", "providerRequestId", "latencyMs", "draftLinks", "createdAt",
        ]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_businessId(self, obj) -> str:
        return external_id(obj.business)

    def get_userId(self, obj) -> str | None:
        return external_id(obj.user) if obj.user else None

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)


class AIContentGenerationVersionSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    generatedContent = serializers.JSONField(source="generated_content")
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = AIContentGenerationVersion
        fields = ["_id", "version_number", "action", "generatedContent", "createdAt"]

    def get__id(self, obj) -> str:
        return str(obj.id)

    def get_createdAt(self, obj) -> str | None:
        return dt(obj.created_at)


class ContentPlanGenerateRequestSerializer(serializers.Serializer):
    business_id = serializers.CharField(required=False, allow_blank=True)
    businessId = serializers.CharField(required=False, allow_blank=True)
    platforms = serializers.ListField(child=serializers.CharField(max_length=40), min_length=1, max_length=6)
    start_date = serializers.DateField()
    goal = serializers.CharField(required=False, allow_blank=True, max_length=500)
    additional_instructions = serializers.CharField(required=False, allow_blank=True, max_length=1200)
    additionalInstructions = serializers.CharField(required=False, allow_blank=True, max_length=1200)

    def validate(self, attrs):
        attrs["business_id"] = attrs.get("business_id") or attrs.get("businessId")
        attrs["additional_instructions"] = attrs.get("additional_instructions") or attrs.get("additionalInstructions") or ""
        if not attrs.get("business_id"):
            raise serializers.ValidationError({"business_id": ["This field is required"]})
        return attrs


class ContentPlanCreateDraftsRequestSerializer(serializers.Serializer):
    item_day_numbers = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=7), min_length=1, max_length=7, required=False)
    itemDayNumbers = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=7), min_length=1, max_length=7, required=False)
    edited_items = serializers.DictField(child=serializers.DictField(), required=False)
    editedItems = serializers.DictField(child=serializers.DictField(), required=False)

    def validate(self, attrs):
        attrs["item_day_numbers"] = attrs.get("item_day_numbers") or attrs.get("itemDayNumbers")
        attrs["edited_items"] = attrs.get("edited_items") or attrs.get("editedItems") or {}
        return attrs


class ContentPlanUsageSerializer(serializers.Serializer):
    input_tokens = serializers.IntegerField(min_value=0)
    output_tokens = serializers.IntegerField(min_value=0)


class ContentPlanGenerateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    id = serializers.CharField()
    status = serializers.CharField()
    provider = serializers.CharField()
    model = serializers.CharField()
    prompt_version = serializers.CharField()
    plan = serializers.JSONField()
    usage = ContentPlanUsageSerializer()
    created_at = serializers.DateTimeField()
    data = AIContentGenerationSerializer()
