from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_CASE_FIELDS = {
    "id",
    "task_type",
    "language",
    "system_prompt",
    "user_prompt",
    "input_context",
    "expected_schema",
    "required_facts",
    "forbidden_claims",
    "grading_rules",
}

SUPPORTED_TASK_TYPES = {
    "content_planning",
    "business_report",
    "trend_intelligence",
    "competitor_analysis",
    "strategy",
    "safety",
}


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    task_type: str
    language: str
    system_prompt: str
    user_prompt: str
    input_context: dict[str, Any]
    expected_schema: str
    required_facts: list[str]
    forbidden_claims: list[str]
    grading_rules: dict[str, Any]


def validate_case_payload(payload: dict[str, Any]) -> EvaluationCase:
    missing = sorted(REQUIRED_CASE_FIELDS - set(payload))
    if missing:
        raise ValueError(f"Evaluation case is missing fields: {', '.join(missing)}")
    if payload["task_type"] not in SUPPORTED_TASK_TYPES:
        raise ValueError(f"Unsupported task_type: {payload['task_type']}")
    if not isinstance(payload["input_context"], dict):
        raise ValueError("input_context must be an object")
    if not isinstance(payload["required_facts"], list):
        raise ValueError("required_facts must be a list")
    if not isinstance(payload["forbidden_claims"], list):
        raise ValueError("forbidden_claims must be a list")
    if not isinstance(payload["grading_rules"], dict):
        raise ValueError("grading_rules must be an object")
    return EvaluationCase(
        id=str(payload["id"]),
        task_type=str(payload["task_type"]),
        language=str(payload["language"]),
        system_prompt=str(payload["system_prompt"]),
        user_prompt=str(payload["user_prompt"]),
        input_context=payload["input_context"],
        expected_schema=str(payload["expected_schema"]),
        required_facts=[str(item) for item in payload["required_facts"]],
        forbidden_claims=[str(item) for item in payload["forbidden_claims"]],
        grading_rules=payload["grading_rules"],
    )
