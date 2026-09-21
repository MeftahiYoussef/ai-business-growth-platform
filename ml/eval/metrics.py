from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .schemas import EvaluationCase


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    schema_valid: bool
    required_field_rate: float
    hallucination_failed: bool
    forbidden_claim_failed: bool
    instruction_following: bool
    language_match: bool
    human_review_flag: bool
    seven_day_plan_valid: bool | None
    latency_ms: int | None = None


def _extract_json(output: str) -> Any | None:
    text = output.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _required_field_rate(output_text: str, required_facts: list[str]) -> float:
    if not required_facts:
        return 1.0
    lowered = output_text.lower()
    matches = sum(1 for fact in required_facts if fact.lower() in lowered)
    return matches / len(required_facts)


def _language_match(language: str, output_text: str) -> bool:
    if language == "fr":
        return any(token in output_text.lower() for token in [" le ", " la ", " les ", "des ", "données", "recommand"])
    if language == "ru":
        return bool(re.search(r"[А-Яа-я]", output_text))
    return True


def _seven_day_plan_valid(parsed: Any) -> bool:
    if not isinstance(parsed, dict):
        return False
    items = parsed.get("items")
    if not isinstance(items, list) or len(items) != 7:
        return False
    days = sorted(item.get("day_number") for item in items if isinstance(item, dict))
    if days != [1, 2, 3, 4, 5, 6, 7]:
        return False
    return all(item.get("requires_human_review") is True for item in items if isinstance(item, dict))


def _report_metrics_unchanged(case: EvaluationCase, parsed: Any) -> bool:
    expected_metrics = case.input_context.get("metrics")
    if not expected_metrics:
        return True
    if not isinstance(parsed, dict):
        return False
    output_metrics = parsed.get("metrics")
    return output_metrics == expected_metrics


def _forbidden_claim_failed(output_text: str, forbidden_claims: list[str]) -> bool:
    lowered = output_text.lower()
    return any(claim.lower() in lowered for claim in forbidden_claims)


def score_case(case: EvaluationCase, output: str, latency_ms: int | None = None) -> CaseScore:
    parsed = _extract_json(output)
    output_text = _flatten_text(parsed) if parsed is not None else output
    forbidden_failed = _forbidden_claim_failed(output_text, case.forbidden_claims)
    required_rate = _required_field_rate(output_text, case.required_facts)
    schema_valid = parsed is not None if case.expected_schema != "freeform" else bool(output.strip())

    seven_day_valid: bool | None = None
    human_review = True
    if case.task_type == "content_planning":
        seven_day_valid = _seven_day_plan_valid(parsed)
        human_review = bool(seven_day_valid)
    elif parsed is not None:
        text = json.dumps(parsed, sort_keys=True, ensure_ascii=False)
        human_review = "requires_human_review" not in text or '"requires_human_review": true' in text.lower()

    hallucination_failed = forbidden_failed
    if case.task_type == "business_report":
        hallucination_failed = hallucination_failed or not _report_metrics_unchanged(case, parsed)

    return CaseScore(
        case_id=case.id,
        schema_valid=schema_valid,
        required_field_rate=required_rate,
        hallucination_failed=hallucination_failed,
        forbidden_claim_failed=forbidden_failed,
        instruction_following=schema_valid and required_rate >= 0.75 and not forbidden_failed,
        language_match=_language_match(case.language, output_text),
        human_review_flag=human_review,
        seven_day_plan_valid=seven_day_valid,
        latency_ms=latency_ms,
    )


def summarize(scores: list[CaseScore]) -> dict[str, float | int | None]:
    total = len(scores)
    if total == 0:
        return {"case_count": 0}

    def rate(name: str) -> float:
        return round(sum(1 for score in scores if getattr(score, name)) / total, 4)

    seven_day_scores = [score for score in scores if score.seven_day_plan_valid is not None]
    latencies = [score.latency_ms for score in scores if score.latency_ms is not None]
    return {
        "case_count": total,
        "schema_valid_rate": rate("schema_valid"),
        "required_field_rate": round(sum(score.required_field_rate for score in scores) / total, 4),
        "hallucination_rate": round(sum(1 for score in scores if score.hallucination_failed) / total, 4),
        "forbidden_claim_rate": round(sum(1 for score in scores if score.forbidden_claim_failed) / total, 4),
        "instruction_following_rate": rate("instruction_following"),
        "language_match_rate": rate("language_match"),
        "human_review_flag_rate": rate("human_review_flag"),
        "seven_day_plan_valid_rate": (
            round(sum(1 for score in seven_day_scores if score.seven_day_plan_valid) / len(seven_day_scores), 4)
            if seven_day_scores
            else None
        ),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }
