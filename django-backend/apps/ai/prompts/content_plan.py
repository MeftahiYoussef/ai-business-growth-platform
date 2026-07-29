import json
from typing import Any

CONTENT_PLAN_PROMPT_VERSION = "content-plan-v1"

SUPPORTED_PLATFORMS = ["instagram", "facebook", "linkedin", "tiktok", "youtube", "x", "pinterest"]
SUPPORTED_CONTENT_TYPES = [
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
SUPPORTED_OBJECTIVES = ["awareness", "engagement", "leads", "traffic", "education", "conversion", "retention"]


CONTENT_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1200},
        "primary_goal": {"type": "string", "enum": SUPPORTED_OBJECTIVES},
        "target_audience": {"type": "string", "minLength": 1, "maxLength": 800},
        "items": {
            "type": "array",
            "minItems": 7,
            "maxItems": 7,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "day_number": {"type": "integer", "minimum": 1, "maximum": 7},
                    "title": {"type": "string", "minLength": 1, "maxLength": 180},
                    "platform": {"type": "string", "enum": SUPPORTED_PLATFORMS},
                    "content_type": {"type": "string", "enum": SUPPORTED_CONTENT_TYPES},
                    "objective": {"type": "string", "enum": SUPPORTED_OBJECTIVES},
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


def build_content_plan_prompt(*, context: dict[str, Any], platforms: list[str], start_date: str, goal: str, additional_instructions: str) -> dict[str, Any]:
    system = (
        "You are an expert social media strategist for a SaaS competitor-intelligence platform. "
        "Return structured JSON only, with no Markdown wrapper. Never fabricate analytics values. "
        "Use only the provided business, trend, competitor and analytics data. If information is unavailable, mark it as unavailable. "
        "Avoid unsupported promises and respect all brand restrictions. Return exactly seven meaningfully different items. "
        "Adapt each item to its selected platform, respect the preferred language, and set requires_human_review to true for every item."
    )
    user_input = {
        "task": "Generate a structured seven-day social media content plan.",
        "start_date": start_date,
        "requested_platforms": platforms,
        "requested_goal": goal or "Use the business goals from the context.",
        "additional_instructions": additional_instructions,
        "application_context": context,
    }
    return {
        "system": system,
        "user": json.dumps(user_input, ensure_ascii=True),
        "schema": CONTENT_PLAN_SCHEMA,
        "prompt_version": CONTENT_PLAN_PROMPT_VERSION,
        "input_snapshot": user_input,
    }
