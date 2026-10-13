import json
from typing import Any

from apps.ai.contracts.content_plan import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_OBJECTIVES,
    ALLOWED_PLATFORMS,
    CONTENT_PLAN_CONTRACT_VERSION,
    CONTENT_PLAN_SCHEMA,
    content_plan_contract_prompt,
)

CONTENT_PLAN_PROMPT_VERSION = "content-plan-v2"

SUPPORTED_PLATFORMS = ALLOWED_PLATFORMS
SUPPORTED_CONTENT_TYPES = ALLOWED_CONTENT_TYPES
SUPPORTED_OBJECTIVES = ALLOWED_OBJECTIVES


def build_content_plan_prompt(*, context: dict[str, Any], platforms: list[str], start_date: str, goal: str, additional_instructions: str) -> dict[str, Any]:
    system = (
        "You are an expert social media strategist for a SaaS competitor-intelligence platform. "
        "Return structured JSON only, with no Markdown wrapper. Never fabricate analytics values. "
        "Do not invent percentages, growth rates, revenue, engagement, follower counts, or case-study performance numbers. "
        "Use only the provided business, trend, competitor and analytics data. If information is unavailable, mark it as unavailable. "
        "Avoid unsupported promises and respect all brand restrictions. Return exactly seven meaningfully different items. "
        "Adapt each item to its selected platform and respect the preferred language. "
        f"{content_plan_contract_prompt()}"
    )
    user_input = {
        "task": "Generate a structured seven-day social media content plan.",
        "contract_version": CONTENT_PLAN_CONTRACT_VERSION,
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
