from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTENT_PLAN_CONTRACT_VERSION = "content_plan_contract_v2"
CONTENT_PLAN_ITEM_COUNT = 7

ALLOWED_PLATFORMS = ["instagram", "facebook", "linkedin", "tiktok", "youtube", "x", "pinterest"]
ALLOWED_CONTENT_TYPES = [
    "instagram_caption",
    "facebook_post",
    "linkedin_post",
    "tiktok_script",
    "short_video",
    "carousel",
    "promotional_copy",
    "educational_post",
    "story_sequence",
    "hook",
]
ALLOWED_OBJECTIVES = ["awareness", "engagement", "leads", "traffic", "education", "conversion", "retention"]

CONTENT_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1200},
        "primary_goal": {"type": "string", "enum": ALLOWED_OBJECTIVES},
        "target_audience": {"type": "string", "minLength": 1, "maxLength": 800},
        "items": {
            "type": "array",
            "minItems": CONTENT_PLAN_ITEM_COUNT,
            "maxItems": CONTENT_PLAN_ITEM_COUNT,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "day_number": {"type": "integer", "minimum": 1, "maximum": 7},
                    "title": {"type": "string", "minLength": 1, "maxLength": 180},
                    "platform": {"type": "string", "enum": ALLOWED_PLATFORMS},
                    "content_type": {"type": "string", "enum": ALLOWED_CONTENT_TYPES},
                    "objective": {"type": "string", "enum": ALLOWED_OBJECTIVES},
                    "topic": {"type": "string", "minLength": 1, "maxLength": 220},
                    "hook": {"type": "string", "minLength": 1, "maxLength": 500},
                    "caption": {"type": "string", "minLength": 1, "maxLength": 2200},
                    "call_to_action": {"type": "string", "minLength": 1, "maxLength": 300},
                    "hashtags": {"type": "array", "maxItems": 12, "items": {"type": "string", "maxLength": 80}},
                    "visual_brief": {"type": "string", "maxLength": 700},
                    "recommended_time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"},
                    "source_context": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 180}},
                    "risk_flags": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 180}},
                    "requires_human_review": {"type": "boolean", "const": True},
                },
                "required": [
                    "day_number",
                    "title",
                    "platform",
                    "content_type",
                    "objective",
                    "topic",
                    "hook",
                    "caption",
                    "call_to_action",
                    "hashtags",
                    "visual_brief",
                    "recommended_time",
                    "source_context",
                    "risk_flags",
                    "requires_human_review",
                ],
            },
        },
    },
    "required": ["summary", "primary_goal", "target_audience", "items"],
}

_ITEM_REQUIRED_FIELDS = set(CONTENT_PLAN_SCHEMA["properties"]["items"]["items"]["required"])


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    normalized_payload: dict[str, Any] | None = None


def content_plan_contract_prompt() -> str:
    return (
        f"Return JSON only using {CONTENT_PLAN_CONTRACT_VERSION}. "
        "Top-level keys: summary, primary_goal, target_audience, items. "
        f"items must contain exactly {CONTENT_PLAN_ITEM_COUNT} objects. "
        "day_number must be unique integers 1 through 7. "
        f"platform must be one of: {', '.join(ALLOWED_PLATFORMS)}. "
        f"content_type must be one of: {', '.join(ALLOWED_CONTENT_TYPES)}. "
        f"objective and primary_goal must be one of: {', '.join(ALLOWED_OBJECTIVES)}. "
        "Each item requires these exact keys: day_number, title, platform, content_type, objective, topic, hook, caption, "
        "call_to_action, hashtags, visual_brief, recommended_time, source_context, risk_flags, requires_human_review. "
        "recommended_time must use 24-hour HH:MM format. "
        "hashtags, source_context, and risk_flags must be arrays. "
        "requires_human_review must be true for every item. "
        "Do not include Markdown, comments, alternate top-level wrappers, approval, scheduling, or publishing."
    )


def validate_content_plan_payload(payload: Any) -> ValidationResult:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ValidationResult(valid=False, errors=["payload must be an object"])
    extra_top_level = sorted(set(payload) - set(CONTENT_PLAN_SCHEMA["required"]))
    if extra_top_level:
        errors.append(f"unsupported top-level fields: {', '.join(extra_top_level)}")
    for field in CONTENT_PLAN_SCHEMA["required"]:
        if field not in payload:
            errors.append(f"missing top-level field: {field}")
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 1200:
        errors.append("summary must be a non-empty string up to 1200 characters")
    primary_goal = payload.get("primary_goal")
    if primary_goal not in ALLOWED_OBJECTIVES:
        errors.append("primary_goal is not allowed")
    target_audience = payload.get("target_audience")
    if not isinstance(target_audience, str) or not target_audience.strip() or len(target_audience) > 800:
        errors.append("target_audience must be a non-empty string up to 800 characters")
    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("items must be an array")
        return ValidationResult(valid=False, errors=errors)
    if len(items) != CONTENT_PLAN_ITEM_COUNT:
        errors.append(f"items must contain exactly {CONTENT_PLAN_ITEM_COUNT} entries")
    day_numbers: list[int] = []
    normalized_items: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(_ITEM_REQUIRED_FIELDS - set(item))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
        extra = sorted(set(item) - _ITEM_REQUIRED_FIELDS)
        if extra:
            errors.append(f"{prefix} has unsupported fields: {', '.join(extra)}")
        day_number = item.get("day_number")
        if not isinstance(day_number, int) or not 1 <= day_number <= 7:
            errors.append(f"{prefix}.day_number must be an integer from 1 through 7")
        else:
            day_numbers.append(day_number)
        _validate_string(errors, item, "title", 180, prefix)
        _validate_string(errors, item, "topic", 220, prefix)
        _validate_string(errors, item, "hook", 500, prefix)
        _validate_string(errors, item, "caption", 2200, prefix)
        _validate_string(errors, item, "call_to_action", 300, prefix)
        _validate_string(errors, item, "visual_brief", 700, prefix, allow_blank=True)
        if item.get("platform") not in ALLOWED_PLATFORMS:
            errors.append(f"{prefix}.platform is not allowed")
        if item.get("content_type") not in ALLOWED_CONTENT_TYPES:
            errors.append(f"{prefix}.content_type is not allowed")
        if item.get("objective") not in ALLOWED_OBJECTIVES:
            errors.append(f"{prefix}.objective is not allowed")
        if item.get("requires_human_review") is not True:
            errors.append(f"{prefix}.requires_human_review must be true")
        _validate_string_list(errors, item, "hashtags", 12, 80, prefix)
        _validate_string_list(errors, item, "source_context", 8, 180, prefix)
        _validate_string_list(errors, item, "risk_flags", 8, 180, prefix)
        time_value = item.get("recommended_time")
        if not isinstance(time_value, str) or len(time_value) != 5 or time_value[2] != ":":
            errors.append(f"{prefix}.recommended_time must use HH:MM")
        else:
            try:
                hour = int(time_value[:2])
                minute = int(time_value[3:])
            except ValueError:
                errors.append(f"{prefix}.recommended_time must use HH:MM")
            else:
                if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                    errors.append(f"{prefix}.recommended_time must use HH:MM")
        normalized_items.append(item)
    if sorted(day_numbers) != list(range(1, 8)):
        errors.append("day_number values must be unique and cover 1 through 7")
    if errors:
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult(valid=True, errors=[], normalized_payload={**payload, "items": normalized_items})


def _validate_string(errors: list[str], item: dict[str, Any], field: str, max_length: int, prefix: str, *, allow_blank: bool = False) -> None:
    value = item.get(field)
    if not isinstance(value, str) or (not allow_blank and not value.strip()) or len(value) > max_length:
        errors.append(f"{prefix}.{field} must be a string up to {max_length} characters")


def _validate_string_list(errors: list[str], item: dict[str, Any], field: str, max_items: int, max_length: int, prefix: str) -> None:
    value = item.get(field)
    if not isinstance(value, list):
        errors.append(f"{prefix}.{field} must be an array")
        return
    if len(value) > max_items:
        errors.append(f"{prefix}.{field} must contain at most {max_items} entries")
    for item_index, entry in enumerate(value):
        if not isinstance(entry, str) or len(entry) > max_length:
            errors.append(f"{prefix}.{field}[{item_index}] must be a string up to {max_length} characters")
