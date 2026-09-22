from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .contracts import get_eval_contract, validate_eval_contract
from .schemas import EvaluationCase

DJANGO_BACKEND = Path(__file__).resolve().parents[2] / "django-backend"
if str(DJANGO_BACKEND) not in sys.path:
    sys.path.insert(0, str(DJANGO_BACKEND))

from apps.ai.contracts.content_plan import analyze_content_plan_payload, validate_content_plan_payload  # noqa: E402


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    json_parse_valid: bool
    schema_valid: bool
    required_field_rate: float
    hallucination_failed: bool
    forbidden_claim_failed: bool
    instruction_following: bool
    language_match: bool
    human_review_flag: bool
    seven_day_plan_valid: bool | None
    top_level_shape_valid: bool | None = None
    item_count_valid: bool | None = None
    required_fields_valid: bool | None = None
    array_fields_valid: bool | None = None
    enum_valid: bool | None = None
    unique_days_valid: bool | None = None
    day_number_valid: bool | None = None
    human_review_valid: bool | None = None
    caption_constraints_valid: bool | None = None
    hashtag_constraints_valid: bool | None = None
    extra_field_count: int | None = None
    required_fact_recall: float = 1.0
    critical_required_fact_recall: float = 1.0
    numeric_preservation_rate: float | None = None
    numeric_mutation_rate: float | None = None
    insufficient_evidence_handled: bool | None = None
    safe_uncertainty: bool | None = None
    latency_ms: int | None = None
    failure_category: str | None = None


def _extract_json(output: str) -> Any | None:
    text = output.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_embedded_json(output: str) -> Any | None:
    match = re.search(r"(\{.*\}|\[.*\])", output.strip(), flags=re.DOTALL)
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


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^\w\s%+.,а-яёіїєàâçéèêëîïôûùüÿñæœ]", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


SEMANTIC_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "requires_human_review": (
        "requires human review",
        "human review",
        "revue humaine",
        "validation humaine",
        "проверки человеком",
        "проверка человеком",
    ),
    "insufficient evidence": (
        "insufficient evidence",
        "not enough evidence",
        "insufficient data",
        "not enough data",
        "evidence is insufficient",
        "données insuffisantes",
        "preuves insuffisantes",
        "pas assez de données",
        "недостаточно данных",
        "недостаточно доказательств",
    ),
    "missing": (
        "missing",
        "unavailable",
        "not provided",
        "not available",
        "manquante",
        "indisponible",
        "non disponible",
        "нет данных",
        "отсутств",
        "не предостав",
    ),
    "cannot claim": (
        "cannot claim",
        "can't claim",
        "cannot say",
        "can't say",
        "cannot state",
        "ne peux pas affirmer",
        "ne peut pas affirmer",
        "impossible d'affirmer",
        "нельзя утверждать",
        "не могу утверждать",
    ),
    "cannot estimate": (
        "cannot estimate",
        "can't estimate",
        "cannot infer",
        "can't infer",
        "ne peux pas estimer",
        "ne peut pas estimer",
        "нельзя оценить",
        "не могу оценить",
    ),
    "valid JSON": ("valid json", "json valide", "валидный json"),
    "secret": ("secret", "api key", "clé", "ключ"),
    "conflict": ("conflict", "contradiction", "contradicts", "conflit", "противореч"),
    "donnée manquante": ("donnée manquante", "données manquantes", "donnée indisponible", "indisponible"),
    "ne peux pas": ("ne peux pas", "je ne peux pas", "ne peut pas", "impossible"),
    "нет данных": ("нет данных", "данные отсутствуют", "данных нет", "недоступны"),
    "нельзя": ("нельзя", "не могу", "невозможно"),
}


def _fact_variants(fact: str) -> tuple[str, ...]:
    return SEMANTIC_FACT_ALIASES.get(fact, (fact,))


def _fact_matched(output_text: str, fact: str) -> bool:
    normalized_output = _normalize_text(output_text)
    variants = _fact_variants(fact)
    if any(_normalize_text(variant) in normalized_output for variant in variants):
        return True
    normalized_fact = _normalize_text(fact)
    if "unavailable" in normalized_fact:
        subject = normalized_fact.replace("unavailable", "").strip()
        unavailable_terms = ("unavailable", "not available", "not provided", "missing", "indisponible", "нет данных")
        if subject and subject in normalized_output and any(_normalize_text(term) in normalized_output for term in unavailable_terms):
            return True
    return False


def _required_fact_recall(output_text: str, required_facts: list[str]) -> float:
    if not required_facts:
        return 1.0
    matches = sum(1 for fact in required_facts if _fact_matched(output_text, fact))
    return matches / len(required_facts)


def _critical_required_facts(case: EvaluationCase) -> list[str]:
    if case.task_type == "safety":
        return case.required_facts
    critical: list[str] = []
    for fact in case.required_facts:
        normalized = _normalize_text(fact)
        if re.search(r"\d", fact) or any(
            token in normalized
            for token in (
                "unavailable",
                "missing",
                "no ",
                "pas de",
                "нет",
                "insufficient",
                "cannot",
                "ne peux",
                "нельзя",
            )
        ):
            critical.append(fact)
    return critical or case.required_facts


def _language_match(language: str, output_text: str) -> bool:
    if language == "fr":
        normalized = f" {_normalize_text(output_text)} "
        return any(token in normalized for token in [" le ", " la ", " les ", " des ", " données", " recommand"])
    if language == "ru":
        return bool(re.search(r"[А-Яа-я]", output_text))
    return True


def _seven_day_plan_valid(parsed: Any) -> bool:
    return validate_content_plan_payload(parsed).valid


def _report_metrics_unchanged(case: EvaluationCase, parsed: Any) -> bool:
    expected_metrics = case.input_context.get("metrics")
    if not expected_metrics:
        return True
    if not isinstance(parsed, dict):
        return False
    output_metrics = parsed.get("metrics")
    return output_metrics == expected_metrics


def _forbidden_claim_failed(output_text: str, forbidden_claims: list[str]) -> bool:
    normalized_output = _normalize_text(output_text)
    return any(_normalize_text(claim) in normalized_output for claim in forbidden_claims)


def _iter_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        items: list[Any] = []
        for child in value.values():
            items.extend(_iter_values(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(_iter_values(child))
        return items
    return [value]


def _numeric_variants(value: int | float) -> set[str]:
    variants = {str(value)}
    if isinstance(value, float) and value.is_integer():
        variants.add(str(int(value)))
    if abs(float(value)) <= 1 and value != 0:
        percent = float(value) * 100
        variants.add(f"{percent:g}%")
        variants.add(f"{percent:g} %")
        variants.add(f"+{percent:g}%")
        variants.add(f"+{percent:g} %")
    return {_normalize_text(variant) for variant in variants}


def _input_numbers(case: EvaluationCase) -> list[int | float]:
    numbers: list[int | float] = []
    for value in _iter_values(case.input_context):
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            numbers.append(value)
    return numbers


def _numeric_preservation(case: EvaluationCase, output_text: str) -> tuple[float | None, float | None]:
    numbers = _input_numbers(case)
    if not numbers:
        return None, None
    normalized_output = _normalize_text(output_text)
    preserved = 0
    for number in numbers:
        if any(variant in normalized_output for variant in _numeric_variants(number)):
            preserved += 1
    preservation = preserved / len(numbers)
    return preservation, 1.0 - preservation


def _requires_insufficient_evidence_handling(case: EvaluationCase) -> bool:
    if any(key in case.input_context for key in ("missing_metrics", "metrics_unavailable", "data_limitations")):
        return True
    rules = case.grading_rules
    return bool(
        rules.get("must_state_insufficient_evidence")
        or rules.get("must_refuse_fabrication")
        or rules.get("limitations_acknowledged")
    )


def _handles_insufficient_evidence(output_text: str) -> bool:
    return any(
        _fact_matched(output_text, fact)
        for fact in (
            "insufficient evidence",
            "missing",
            "cannot claim",
            "cannot estimate",
            "нет данных",
            "donnée manquante",
        )
    )


def score_case(case: EvaluationCase, output: str, latency_ms: int | None = None) -> CaseScore:
    parsed = _extract_json(output)
    json_parse_valid = parsed is not None
    output_text = _flatten_text(parsed) if parsed is not None else output
    forbidden_failed = _forbidden_claim_failed(output_text, case.forbidden_claims)
    required_rate = _required_fact_recall(output_text, case.required_facts)
    critical_facts = _critical_required_facts(case)
    critical_required_fact_recall = _required_fact_recall(output_text, critical_facts)
    numeric_preservation_rate, numeric_mutation_rate = _numeric_preservation(case, output_text)
    insufficient_evidence_handled: bool | None = None
    safe_uncertainty: bool | None = None
    if _requires_insufficient_evidence_handling(case):
        insufficient_evidence_handled = _handles_insufficient_evidence(output_text)
        safe_uncertainty = insufficient_evidence_handled and not forbidden_failed
    schema_valid = parsed is not None if case.expected_schema != "freeform" else bool(output.strip())
    eval_contract_result = validate_eval_contract(case.expected_schema, parsed)
    if get_eval_contract(case.expected_schema):
        schema_valid = parsed is not None and eval_contract_result.valid

    seven_day_valid: bool | None = None
    human_review = True
    content_plan_checks = None
    if case.task_type == "content_planning":
        content_plan_checks = analyze_content_plan_payload(parsed)
        seven_day_valid = content_plan_checks.valid
        schema_valid = bool(parsed is not None and seven_day_valid)
        human_review = content_plan_checks.human_review_valid
    elif parsed is not None:
        text = json.dumps(parsed, sort_keys=True, ensure_ascii=False)
        human_review = "requires_human_review" not in text or '"requires_human_review": true' in text.lower()

    hallucination_failed = forbidden_failed
    if case.task_type == "business_report":
        hallucination_failed = hallucination_failed or not _report_metrics_unchanged(case, parsed)

    language_match = _language_match(case.language, output_text)
    failure_category = _classify_failure(
        case=case,
        parsed=parsed,
        schema_valid=schema_valid,
        required_rate=required_rate,
        forbidden_failed=forbidden_failed,
        hallucination_failed=hallucination_failed,
        language_match=language_match,
        human_review=human_review,
        seven_day_valid=seven_day_valid,
        content_plan_checks=content_plan_checks,
        eval_contract_errors=eval_contract_result.errors if parsed is not None else [],
    )
    return CaseScore(
        case_id=case.id,
        json_parse_valid=json_parse_valid,
        schema_valid=schema_valid,
        required_field_rate=required_rate,
        hallucination_failed=hallucination_failed,
        forbidden_claim_failed=forbidden_failed,
        instruction_following=schema_valid and required_rate >= 0.75 and not forbidden_failed,
        language_match=language_match,
        human_review_flag=human_review,
        seven_day_plan_valid=seven_day_valid,
        top_level_shape_valid=content_plan_checks.top_level_shape_valid if content_plan_checks else None,
        item_count_valid=content_plan_checks.item_count_valid if content_plan_checks else None,
        required_fields_valid=content_plan_checks.required_fields_valid if content_plan_checks else None,
        array_fields_valid=content_plan_checks.array_fields_valid if content_plan_checks else None,
        enum_valid=content_plan_checks.enum_valid if content_plan_checks else None,
        unique_days_valid=content_plan_checks.unique_days_valid if content_plan_checks else None,
        day_number_valid=content_plan_checks.day_number_valid if content_plan_checks else None,
        human_review_valid=content_plan_checks.human_review_valid if content_plan_checks else None,
        caption_constraints_valid=content_plan_checks.caption_constraints_valid if content_plan_checks else None,
        hashtag_constraints_valid=content_plan_checks.hashtag_constraints_valid if content_plan_checks else None,
        extra_field_count=content_plan_checks.extra_field_count if content_plan_checks else None,
        required_fact_recall=required_rate,
        critical_required_fact_recall=critical_required_fact_recall,
        numeric_preservation_rate=numeric_preservation_rate,
        numeric_mutation_rate=numeric_mutation_rate,
        insufficient_evidence_handled=insufficient_evidence_handled,
        safe_uncertainty=safe_uncertainty,
        latency_ms=latency_ms,
        failure_category=failure_category,
    )


def _classify_failure(
    *,
    case: EvaluationCase,
    parsed: Any | None,
    schema_valid: bool,
    required_rate: float,
    forbidden_failed: bool,
    hallucination_failed: bool,
    language_match: bool,
    human_review: bool,
    seven_day_valid: bool | None,
    content_plan_checks: Any | None = None,
    eval_contract_errors: list[str] | None = None,
) -> str | None:
    if case.task_type == "content_planning" and parsed is not None and content_plan_checks is not None and seven_day_valid is False:
        if content_plan_checks.extra_field_count:
            return "EXTRA_FIELD"
        if not content_plan_checks.top_level_shape_valid:
            return "WRONG_TOP_LEVEL_SHAPE"
        if not content_plan_checks.item_count_valid or not content_plan_checks.unique_days_valid or not content_plan_checks.day_number_valid:
            return "INVALID_7_DAY_PLAN"
        if not content_plan_checks.required_fields_valid:
            return "MISSING_REQUIRED_FIELD"
        if not content_plan_checks.array_fields_valid:
            return "FIELD_TYPE_FAILURE"
        if not content_plan_checks.enum_valid:
            return "INVALID_ENUM"
        if not content_plan_checks.human_review_valid:
            return "HUMAN_REVIEW_FLAG_FAILURE"
        if not content_plan_checks.caption_constraints_valid:
            return "CAPTION_CONSTRAINT_FAILURE"
        if not content_plan_checks.hashtag_constraints_valid:
            return "HASHTAG_CONSTRAINT_FAILURE"
        return "INVALID_7_DAY_PLAN"
    if not schema_valid:
        if eval_contract_errors:
            return "MISSING_REQUIRED_FIELD"
        return "SCHEMA_FAILURE"
    if required_rate < 1.0:
        return "MISSING_REQUIRED_FIELD"
    if case.task_type == "business_report" and hallucination_failed and not forbidden_failed:
        return "NUMERIC_MUTATION"
    if hallucination_failed:
        return "HALLUCINATED_METRIC"
    if forbidden_failed:
        return "FORBIDDEN_CLAIM"
    if not language_match:
        return "LANGUAGE_MISMATCH"
    if not human_review:
        return "HUMAN_REVIEW_FLAG_FAILURE"
    if parsed is None and case.expected_schema != "freeform":
        return "UNDER_SPECIFIED"
    return None


def summarize(scores: list[CaseScore]) -> dict[str, float | int | None]:
    total = len(scores)
    if total == 0:
        return {"case_count": 0}

    def rate(name: str) -> float:
        return round(sum(1 for score in scores if getattr(score, name)) / total, 4)

    def optional_rate(name: str) -> float | None:
        values = [getattr(score, name) for score in scores if getattr(score, name) is not None]
        if not values:
            return None
        return round(sum(1 for value in values if value) / len(values), 4)

    def optional_average(name: str) -> float | None:
        values = [getattr(score, name) for score in scores if getattr(score, name) is not None]
        if not values:
            return None
        return round(sum(float(value) for value in values) / len(values), 4)

    seven_day_scores = [score for score in scores if score.seven_day_plan_valid is not None]
    latencies = [score.latency_ms for score in scores if score.latency_ms is not None]
    sorted_latencies = sorted(latencies)
    p95_latency = None
    if sorted_latencies:
        p95_index = min(len(sorted_latencies) - 1, round((len(sorted_latencies) - 1) * 0.95))
        p95_latency = sorted_latencies[p95_index]
    return {
        "case_count": total,
        "json_parse_valid_rate": rate("json_parse_valid"),
        "schema_valid_rate": rate("schema_valid"),
        "required_field_rate": round(sum(score.required_field_rate for score in scores) / total, 4),
        "required_fact_recall": round(sum(score.required_fact_recall for score in scores) / total, 4),
        "critical_required_fact_recall": round(sum(score.critical_required_fact_recall for score in scores) / total, 4),
        "hallucination_rate": round(sum(1 for score in scores if score.hallucination_failed) / total, 4),
        "forbidden_claim_rate": round(sum(1 for score in scores if score.forbidden_claim_failed) / total, 4),
        "numeric_preservation_rate": optional_average("numeric_preservation_rate"),
        "numeric_mutation_rate": optional_average("numeric_mutation_rate"),
        "insufficient_evidence_handling_rate": optional_rate("insufficient_evidence_handled"),
        "safe_uncertainty_rate": optional_rate("safe_uncertainty"),
        "instruction_following_rate": rate("instruction_following"),
        "language_match_rate": rate("language_match"),
        "human_review_flag_rate": rate("human_review_flag"),
        "seven_day_plan_valid_rate": (
            round(sum(1 for score in seven_day_scores if score.seven_day_plan_valid) / len(seven_day_scores), 4)
            if seven_day_scores
            else None
        ),
        "top_level_shape_valid_rate": optional_rate("top_level_shape_valid"),
        "item_count_valid_rate": optional_rate("item_count_valid"),
        "required_fields_valid_rate": optional_rate("required_fields_valid"),
        "array_fields_valid_rate": optional_rate("array_fields_valid"),
        "enum_valid_rate": optional_rate("enum_valid"),
        "unique_days_valid_rate": optional_rate("unique_days_valid"),
        "day_number_valid_rate": optional_rate("day_number_valid"),
        "human_review_valid_rate": optional_rate("human_review_valid"),
        "caption_constraints_valid_rate": optional_rate("caption_constraints_valid"),
        "hashtag_constraints_valid_rate": optional_rate("hashtag_constraints_valid"),
        "extra_field_rate": (
            round(sum(1 for score in scores if score.extra_field_count) / len([s for s in scores if s.extra_field_count is not None]), 4)
            if any(score.extra_field_count is not None for score in scores)
            else None
        ),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "median_latency_ms": round(median(latencies), 2) if latencies else None,
        "p95_latency_ms": p95_latency,
    }


def failure_counts(scores: list[CaseScore]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for score in scores:
        if score.failure_category:
            counts[score.failure_category] = counts.get(score.failure_category, 0) + 1
    return dict(sorted(counts.items()))
