from typing import Any

from rest_framework import serializers

from apps.ai.prompts.content_plan import SUPPORTED_CONTENT_TYPES, SUPPORTED_OBJECTIVES, SUPPORTED_PLATFORMS


class ContentPlanItemSerializer(serializers.Serializer):
    day_number = serializers.IntegerField(min_value=1, max_value=7)
    title = serializers.CharField(max_length=180, allow_blank=False)
    platform = serializers.ChoiceField(choices=SUPPORTED_PLATFORMS)
    content_type = serializers.ChoiceField(choices=SUPPORTED_CONTENT_TYPES)
    objective = serializers.ChoiceField(choices=SUPPORTED_OBJECTIVES)
    topic = serializers.CharField(max_length=220, allow_blank=False)
    hook = serializers.CharField(max_length=500, allow_blank=False)
    caption = serializers.CharField(max_length=2200, allow_blank=False)
    call_to_action = serializers.CharField(max_length=300, allow_blank=False)
    hashtags = serializers.ListField(child=serializers.CharField(max_length=80), max_length=12, allow_empty=True)
    visual_brief = serializers.CharField(max_length=700, allow_blank=True)
    recommended_time = serializers.RegexField(regex=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    source_context = serializers.ListField(child=serializers.CharField(max_length=180), max_length=8, allow_empty=True)
    risk_flags = serializers.ListField(child=serializers.CharField(max_length=180), max_length=8, allow_empty=True)
    requires_human_review = serializers.BooleanField()

    def validate_requires_human_review(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Generated content must require human review")
        return value


class ContentPlanSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=1200, allow_blank=False)
    primary_goal = serializers.ChoiceField(choices=SUPPORTED_OBJECTIVES)
    target_audience = serializers.CharField(max_length=800, allow_blank=False)
    items = ContentPlanItemSerializer(many=True)

    def validate_items(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) != 7:
            raise serializers.ValidationError("Exactly seven content items are required")
        day_numbers = sorted(item["day_number"] for item in value)
        if day_numbers != list(range(1, 8)):
            raise serializers.ValidationError("day_number values must be unique and cover 1 through 7")
        return value


def validate_content_plan(data: Any) -> dict[str, Any]:
    serializer = ContentPlanSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
