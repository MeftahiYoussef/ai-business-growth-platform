from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvalContract:
    name: str
    required_fields: tuple[str, ...]
    prompt: str
    schema: dict[str, Any]


_GENERIC_ARRAY = {"type": "array", "items": {"type": ["string", "object"]}}

EVAL_CONTRACTS: dict[str, EvalContract] = {
    "business_report_v1": EvalContract(
        name="business_report_v1",
        required_fields=("metrics", "recommendations", "data_limitations"),
        prompt=(
            "Return JSON only using business_report_v1. Required top-level keys: "
            "metrics, recommendations, data_limitations. Copy deterministic metrics exactly from input_context.metrics. "
            "Put recommendations in recommendations and unavailable metrics in data_limitations. Do not invent social metrics."
        ),
        schema={
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "metrics": {"type": "object"},
                "recommendations": _GENERIC_ARRAY,
                "data_limitations": _GENERIC_ARRAY,
            },
            "required": ["metrics", "recommendations", "data_limitations"],
        },
    ),
    "trend_explanation_v1": EvalContract(
        name="trend_explanation_v1",
        required_fields=("trend", "supplied_evidence", "interpretation", "recommended_actions"),
        prompt=(
            "Return JSON only using trend_explanation_v1. Required top-level keys: "
            "trend, supplied_evidence, interpretation, recommended_actions. Preserve supplied trend numbers exactly. "
            "Separate calculated evidence from narrative interpretation."
        ),
        schema={
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "trend": {"type": ["string", "object"]},
                "supplied_evidence": {"type": ["object", "array"]},
                "interpretation": {"type": ["string", "array"]},
                "recommended_actions": _GENERIC_ARRAY,
            },
            "required": ["trend", "supplied_evidence", "interpretation", "recommended_actions"],
        },
    ),
    "competitor_summary_v1": EvalContract(
        name="competitor_summary_v1",
        required_fields=("competitor_facts", "recommendations", "data_limitations"),
        prompt=(
            "Return JSON only using competitor_summary_v1. Required top-level keys: "
            "competitor_facts, recommendations, data_limitations. Use only supplied competitor facts. "
            "Keep facts separate from recommendations."
        ),
        schema={
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "competitor_facts": _GENERIC_ARRAY,
                "recommendations": _GENERIC_ARRAY,
                "data_limitations": _GENERIC_ARRAY,
            },
            "required": ["competitor_facts", "recommendations", "data_limitations"],
        },
    ),
    "strategy_v1": EvalContract(
        name="strategy_v1",
        required_fields=("facts", "swot", "next_actions", "limitations"),
        prompt=(
            "Return JSON only using strategy_v1. Required top-level keys: facts, swot, next_actions, limitations. "
            "Use only supplied facts, make unsupported metrics explicit in limitations, and provide concrete next actions."
        ),
        schema={
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "facts": _GENERIC_ARRAY,
                "swot": {"type": "object"},
                "next_actions": _GENERIC_ARRAY,
                "limitations": _GENERIC_ARRAY,
            },
            "required": ["facts", "swot", "next_actions", "limitations"],
        },
    ),
}


@dataclass(frozen=True)
class EvalContractResult:
    valid: bool
    errors: list[str]


def get_eval_contract(name: str) -> EvalContract | None:
    return EVAL_CONTRACTS.get(name)


def eval_contract_prompt(name: str) -> str:
    contract = get_eval_contract(name)
    return contract.prompt if contract else ""


def eval_contract_response_format(name: str) -> dict[str, Any] | None:
    contract = get_eval_contract(name)
    if not contract:
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": contract.name,
            "strict": True,
            "schema": contract.schema,
        },
    }


def validate_eval_contract(name: str, payload: Any) -> EvalContractResult:
    contract = get_eval_contract(name)
    if not contract:
        return EvalContractResult(valid=True, errors=[])
    if not isinstance(payload, dict):
        return EvalContractResult(valid=False, errors=["payload must be an object"])
    errors = [f"missing top-level field: {field}" for field in contract.required_fields if field not in payload]
    return EvalContractResult(valid=not errors, errors=errors)
