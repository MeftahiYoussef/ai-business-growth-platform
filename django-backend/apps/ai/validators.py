import re
from typing import Any

from rest_framework import serializers

from apps.ai.contracts.content_plan import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_OBJECTIVES,
    ALLOWED_PLATFORMS,
    validate_content_plan_payload,
)

SUPPORTED_PLATFORMS = ALLOWED_PLATFORMS
SUPPORTED_CONTENT_TYPES = ALLOWED_CONTENT_TYPES
SUPPORTED_OBJECTIVES = ALLOWED_OBJECTIVES

UNSUPPORTED_METRIC_PATTERNS = [
    re.compile(
        r"\b(?:grew|grow|gained|gain|reached|reach|acquired|acquire|increased|increase|boosted|boost)\b.{0,80}"
        r"(?:\b[\d,]+(?:\.\d+)?\s+(?:users|customers|subscribers|followers|leads|sales|views)\b|"
        r"\b(?:user base|users|customers|subscribers|followers|leads|sales|views)\b.{0,40}\b(?:from|to|by)\s+[\d,]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:increase|grow|boost|improve|double|triple|scale|lift)\b.{0,40}\b(?:engagement|revenue|followers|views|likes|comments|shares|sales|leads|conversions)\b.{0,40}(?:\b\d+(?:\.\d+)?\s?%|\$[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s?x\b|\b\d+\s+days\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\b\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?x\b).{0,30}\b(?:faster|higher|more|growth|increase|lift|improvement|conversion|engagement|revenue|sales|followers|views|leads)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:engagement|revenue|followers|views|likes|comments|shares|sales|leads|conversions)\b.{0,30}(?:\b\d+(?:\.\d+)?\s?%|\$[\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:double|triple)\b.{0,30}\b(?:followers|revenue|sales|leads|conversions|engagement|views)\b",
        re.IGNORECASE,
    ),
]
METRIC_TEXT_FIELDS = ("title", "topic", "hook", "caption", "call_to_action", "visual_brief")


def contains_unsupported_metric_claim(value: str) -> bool:
    return any(pattern.search(value) for pattern in UNSUPPORTED_METRIC_PATTERNS)


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

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for field in METRIC_TEXT_FIELDS:
            value = str(attrs.get(field, "") or "")
            if contains_unsupported_metric_claim(value):
                raise serializers.ValidationError({
                    field: "Unsupported quantitative performance claims are not allowed in generated content plans"
                })
        return attrs


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
    contract_result = validate_content_plan_payload(data)
    if not contract_result.valid:
        raise serializers.ValidationError({"content_plan": contract_result.errors})
    serializer = ContentPlanSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
