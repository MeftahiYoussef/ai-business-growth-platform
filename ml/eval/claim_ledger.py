from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

ClaimType = Literal["fact", "limitation", "recommendation"]
ClaimLedgerV2Operator = Literal["greater_than", "less_than", "equal"]

CLAIM_LEDGER_CONTRACT_VERSION = "claim_ledger_v1"
CLAIM_TYPES: tuple[ClaimType, ...] = ("fact", "limitation", "recommendation")
CLAIM_LEDGER_V2_CONTRACT_VERSION = "claim_ledger_v2"
CLAIM_LEDGER_V2_OPERATORS: tuple[ClaimLedgerV2Operator, ...] = ("greater_than", "less_than", "equal")


@dataclass(frozen=True)
class EvidenceSource:
    id: str
    label: str
    value: str | int | float | bool | None = None
    status: Literal["known", "unavailable"] = "known"
    immutable: bool = False


@dataclass(frozen=True)
class EvidenceLedger:
    sources: tuple[EvidenceSource, ...]

    @property
    def ids(self) -> set[str]:
        return {source.id for source in self.sources}

    @property
    def known_ids(self) -> set[str]:
        return {source.id for source in self.sources if source.status == "known"}

    @property
    def unavailable_ids(self) -> set[str]:
        return {source.id for source in self.sources if source.status == "unavailable"}

    @property
    def immutable_numbers(self) -> dict[str, int | float]:
        numbers: dict[str, int | float] = {}
        for source in self.sources:
            if source.immutable and isinstance(source.value, int | float) and not isinstance(source.value, bool):
                numbers[source.id] = source.value
        return numbers


@dataclass(frozen=True)
class ClaimLedgerValidationResult:
    valid: bool
    errors: list[str]
    normalized_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class EvidenceSourceV2:
    id: str
    subject: str
    predicate: str
    status: Literal["known", "unavailable"] = "known"
    value: str | int | float | bool | None = None
    value_type: Literal["count", "percentage", "decimal", "enum", "text"] = "text"
    display_value: str | None = None
    polarity: Literal["positive", "negative", "neutral"] | None = None


@dataclass(frozen=True)
class EvidenceLedgerV2:
    sources: tuple[EvidenceSourceV2, ...]

    @property
    def by_id(self) -> dict[str, EvidenceSourceV2]:
        return {source.id: source for source in self.sources}

    @property
    def ids(self) -> set[str]:
        return {source.id for source in self.sources}

    @property
    def known_ids(self) -> set[str]:
        return {source.id for source in self.sources if source.status == "known"}

    @property
    def unavailable_ids(self) -> set[str]:
        return {source.id for source in self.sources if source.status == "unavailable"}


def build_evidence_ledger(
    *,
    facts: dict[str, str | int | float | bool],
    unavailable: dict[str, str] | list[str] | tuple[str, ...] = (),
    immutable_numbers: dict[str, int | float] | None = None,
) -> EvidenceLedger:
    immutable_numbers = immutable_numbers or {}
    sources: list[EvidenceSource] = []
    for evidence_id, value in facts.items():
        sources.append(
            EvidenceSource(
                id=evidence_id,
                label=evidence_id,
                value=value,
                status="known",
                immutable=evidence_id in immutable_numbers,
            )
    )
    if isinstance(unavailable, dict):
        unavailable_items: Iterable[tuple[str, str]] = unavailable.items()
    else:
        unavailable_items = ((item, item) for item in unavailable)
    for evidence_id, label in unavailable_items:
        sources.append(EvidenceSource(id=evidence_id, label=label, value=None, status="unavailable"))
    for evidence_id, value in immutable_numbers.items():
        if evidence_id not in facts:
            sources.append(EvidenceSource(id=evidence_id, label=evidence_id, value=value, status="known", immutable=True))
    return EvidenceLedger(sources=tuple(sources))


def claim_ledger_schema(allowed_evidence_ids: list[str] | tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claims": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim_type": {"type": "string", "enum": list(CLAIM_TYPES)},
                        "text": {"type": "string", "minLength": 1},
                        "evidence_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "enum": list(allowed_evidence_ids)},
                        },
                    },
                    "required": ["claim_type", "text", "evidence_ids"],
                },
            }
        },
        "required": ["claims"],
    }


def claim_ledger_response_format(evidence_ledger: EvidenceLedger) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": CLAIM_LEDGER_CONTRACT_VERSION,
            "strict": True,
            "schema": claim_ledger_schema(tuple(sorted(evidence_ledger.ids))),
        },
    }


def claim_ledger_prompt(evidence_ledger: EvidenceLedger) -> str:
    known = ", ".join(f"{source.id}={source.value}" for source in evidence_ledger.sources if source.status == "known")
    unavailable = ", ".join(f"{source.id}={source.label}" for source in evidence_ledger.sources if source.status == "unavailable")
    immutable = ", ".join(f"{source.id}={source.value}" for source in evidence_ledger.sources if source.immutable)
    return (
        f"Return JSON only using {CLAIM_LEDGER_CONTRACT_VERSION}. "
        "Each claim must be one of fact, limitation, or recommendation and must cite evidence_ids. "
        "fact claims may cite only known facts. limitation claims must cite unavailable evidence. "
        "recommendation claims must cite the known facts that support the recommendation. "
        "Do not cite evidence IDs that are not listed. Do not alter immutable numbers. "
        f"Known facts: {known or 'none'}. "
        f"Unavailable evidence: {unavailable or 'none'}. "
        f"Immutable numbers: {immutable or 'none'}."
    )


def claim_ledger_v2_schema(evidence_ledger: EvidenceLedgerV2) -> dict[str, Any]:
    known_ids = sorted(evidence_ledger.known_ids)
    unavailable_ids = sorted(evidence_ledger.unavailable_ids)
    unavailable_item_schema: dict[str, Any]
    if unavailable_ids:
        unavailable_item_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"evidence_id": {"type": "string", "enum": unavailable_ids}},
            "required": ["evidence_id"],
        }
    else:
        unavailable_item_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"evidence_id": {"type": "string", "enum": ["__no_unavailable_evidence__"]}},
            "required": ["evidence_id"],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"evidence_id": {"type": "string", "enum": known_ids}},
                    "required": ["evidence_id"],
                },
            },
            "limitations": {
                "type": "array",
                "maxItems": 100 if unavailable_ids else 0,
                "items": unavailable_item_schema,
            },
            "comparisons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "left_evidence_id": {"type": "string", "enum": known_ids},
                        "operator": {"type": "string", "enum": list(CLAIM_LEDGER_V2_OPERATORS)},
                        "right_evidence_id": {"type": "string", "enum": known_ids},
                    },
                    "required": ["left_evidence_id", "operator", "right_evidence_id"],
                },
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "action": {"type": "string", "minLength": 1},
                        "rationale_evidence_ids": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "enum": known_ids},
                        },
                    },
                    "required": ["action", "rationale_evidence_ids"],
                },
            },
        },
        "required": ["facts", "limitations", "comparisons", "recommendations"],
    }


def claim_ledger_v2_response_format(evidence_ledger: EvidenceLedgerV2) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": CLAIM_LEDGER_V2_CONTRACT_VERSION,
            "strict": True,
            "schema": claim_ledger_v2_schema(evidence_ledger),
        },
    }


def claim_ledger_v2_prompt(evidence_ledger: EvidenceLedgerV2) -> str:
    known = ", ".join(
        f"{source.id}: {source.subject}.{source.predicate}={_format_v2_value(source, 'en')}"
        for source in evidence_ledger.sources
        if source.status == "known"
    )
    unavailable = ", ".join(
        f"{source.id}: {source.subject}.{source.predicate}"
        for source in evidence_ledger.sources
        if source.status == "unavailable"
    )
    return (
        f"Return JSON only using {CLAIM_LEDGER_V2_CONTRACT_VERSION}. "
        "Do not write fact text. For factual observations, select evidence IDs in facts. "
        "For missing data, select unavailable evidence IDs in limitations. "
        "For comparisons, select two known evidence IDs and a true operator. "
        "Use recommendations only when a helpful action is needed; cite known evidence IDs. "
        "Do not copy, rewrite, or invent numeric values. The renderer will write all factual prose. "
        f"Known evidence: {known or 'none'}. "
        f"Unavailable evidence: {unavailable or 'none'}."
    )


def validate_claim_ledger_v2_payload(
    payload: Any,
    evidence_ledger: EvidenceLedgerV2,
    *,
    required_evidence_ids: list[str] | tuple[str, ...] = (),
    critical_evidence_ids: list[str] | tuple[str, ...] = (),
) -> ClaimLedgerValidationResult:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ClaimLedgerValidationResult(valid=False, errors=["payload must be an object"])
    expected_top_level = {"facts", "limitations", "comparisons", "recommendations"}
    extra_top_level = sorted(set(payload) - expected_top_level)
    if extra_top_level:
        errors.append(f"payload contains unsupported top-level fields: {', '.join(extra_top_level)}")
    missing_top_level = sorted(expected_top_level - set(payload))
    if missing_top_level:
        errors.append(f"payload is missing top-level fields: {', '.join(missing_top_level)}")

    by_id = evidence_ledger.by_id
    cited_ids: set[str] = set()
    normalized: dict[str, list[dict[str, Any]]] = {
        "facts": [],
        "limitations": [],
        "comparisons": [],
        "recommendations": [],
    }

    facts = payload.get("facts", [])
    if not isinstance(facts, list):
        errors.append("facts must be an array")
        facts = []
    for index, fact in enumerate(facts):
        path = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{path} must be an object")
            continue
        if sorted(set(fact) - {"evidence_id"}):
            errors.append(f"{path} contains unsupported fields")
        evidence_id = fact.get("evidence_id")
        if evidence_id not in evidence_ledger.known_ids:
            errors.append(f"{path}.evidence_id must reference known evidence")
            continue
        cited_ids.add(str(evidence_id))
        normalized["facts"].append({"evidence_id": evidence_id})

    limitations = payload.get("limitations", [])
    if not isinstance(limitations, list):
        errors.append("limitations must be an array")
        limitations = []
    for index, limitation in enumerate(limitations):
        path = f"limitations[{index}]"
        if not isinstance(limitation, dict):
            errors.append(f"{path} must be an object")
            continue
        if sorted(set(limitation) - {"evidence_id"}):
            errors.append(f"{path} contains unsupported fields")
        evidence_id = limitation.get("evidence_id")
        if evidence_id not in evidence_ledger.unavailable_ids:
            errors.append(f"{path}.evidence_id must reference unavailable evidence")
            continue
        cited_ids.add(str(evidence_id))
        normalized["limitations"].append({"evidence_id": evidence_id})

    comparisons = payload.get("comparisons", [])
    if not isinstance(comparisons, list):
        errors.append("comparisons must be an array")
        comparisons = []
    for index, comparison in enumerate(comparisons):
        path = f"comparisons[{index}]"
        if not isinstance(comparison, dict):
            errors.append(f"{path} must be an object")
            continue
        if sorted(set(comparison) - {"left_evidence_id", "operator", "right_evidence_id"}):
            errors.append(f"{path} contains unsupported fields")
        left_id = comparison.get("left_evidence_id")
        right_id = comparison.get("right_evidence_id")
        operator = comparison.get("operator")
        if left_id not in evidence_ledger.known_ids:
            errors.append(f"{path}.left_evidence_id must reference known evidence")
            continue
        if right_id not in evidence_ledger.known_ids:
            errors.append(f"{path}.right_evidence_id must reference known evidence")
            continue
        if operator not in CLAIM_LEDGER_V2_OPERATORS:
            errors.append(f"{path}.operator must be one of {', '.join(CLAIM_LEDGER_V2_OPERATORS)}")
            continue
        left = by_id[str(left_id)]
        right = by_id[str(right_id)]
        if not _comparison_is_true(left, str(operator), right):
            errors.append(f"{path} comparison is not true for trusted evidence")
        cited_ids.update((str(left_id), str(right_id)))
        normalized["comparisons"].append(
            {"left_evidence_id": left_id, "operator": operator, "right_evidence_id": right_id}
        )

    recommendations = payload.get("recommendations", [])
    if not isinstance(recommendations, list):
        errors.append("recommendations must be an array")
        recommendations = []
    for index, recommendation in enumerate(recommendations):
        path = f"recommendations[{index}]"
        if not isinstance(recommendation, dict):
            errors.append(f"{path} must be an object")
            continue
        if sorted(set(recommendation) - {"action", "rationale_evidence_ids"}):
            errors.append(f"{path} contains unsupported fields")
        action = recommendation.get("action")
        rationale = recommendation.get("rationale_evidence_ids")
        if not isinstance(action, str) or not action.strip():
            errors.append(f"{path}.action must be a non-empty string")
            action_text = ""
        else:
            action_text = action.strip()
            text_numbers = _numbers_in_text(action_text)
            if text_numbers:
                errors.append(f"{path}.action must not contain numeric values")
            if _asserts_unavailable_metric(_normalize_text(action_text)):
                errors.append(f"{path}.action asserts unsupported metric state")
        if not isinstance(rationale, list) or not rationale:
            errors.append(f"{path}.rationale_evidence_ids must be a non-empty array")
            rationale_ids: list[str] = []
        else:
            rationale_ids = [item for item in rationale if isinstance(item, str)]
            if len(rationale_ids) != len(rationale):
                errors.append(f"{path}.rationale_evidence_ids must contain only strings")
            invalid = sorted(set(rationale_ids) - evidence_ledger.known_ids)
            if invalid:
                errors.append(f"{path}.rationale_evidence_ids must reference known evidence: {', '.join(invalid)}")
        cited_ids.update(rationale_ids)
        if action_text and rationale_ids:
            normalized["recommendations"].append({"action": action_text, "rationale_evidence_ids": rationale_ids})

    missing_required = sorted(set(required_evidence_ids) - cited_ids)
    if missing_required:
        errors.append(f"required evidence not selected: {', '.join(missing_required)}")
    missing_critical = sorted(set(critical_evidence_ids) - cited_ids)
    if missing_critical:
        errors.append(f"critical evidence not selected: {', '.join(missing_critical)}")
    return ClaimLedgerValidationResult(valid=not errors, errors=errors, normalized_payload=normalized if not errors else None)


def render_claim_ledger_v2(
    payload: dict[str, Any],
    evidence_ledger: EvidenceLedgerV2,
    *,
    language: Literal["en", "fr", "ru"] = "en",
    required_evidence_ids: list[str] | tuple[str, ...] = (),
    critical_evidence_ids: list[str] | tuple[str, ...] = (),
) -> str:
    result = validate_claim_ledger_v2_payload(
        payload,
        evidence_ledger,
        required_evidence_ids=required_evidence_ids,
        critical_evidence_ids=critical_evidence_ids,
    )
    if not result.valid or result.normalized_payload is None:
        raise ValueError("; ".join(result.errors))
    by_id = evidence_ledger.by_id
    sentences: list[str] = []
    for fact in result.normalized_payload["facts"]:
        sentences.append(_render_v2_fact(by_id[fact["evidence_id"]], language))
    for comparison in result.normalized_payload["comparisons"]:
        sentences.append(
            _render_v2_comparison(
                by_id[comparison["left_evidence_id"]],
                comparison["operator"],
                by_id[comparison["right_evidence_id"]],
                language,
            )
        )
    for limitation in result.normalized_payload["limitations"]:
        sentences.append(_render_v2_limitation(by_id[limitation["evidence_id"]], language))
    for recommendation in result.normalized_payload["recommendations"]:
        sentences.append(_render_v2_recommendation(recommendation["action"], language))
    return " ".join(_ensure_sentence(sentence) for sentence in sentences)


def validate_claim_ledger_payload(
    payload: Any,
    evidence_ledger: EvidenceLedger,
    *,
    required_evidence_ids: list[str] | tuple[str, ...] = (),
    critical_evidence_ids: list[str] | tuple[str, ...] = (),
    expected_language: str | None = None,
) -> ClaimLedgerValidationResult:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ClaimLedgerValidationResult(valid=False, errors=["payload must be an object"])
    extra_top_level = sorted(set(payload) - {"claims"})
    if extra_top_level:
        errors.append(f"payload contains unsupported top-level fields: {', '.join(extra_top_level)}")
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        return ClaimLedgerValidationResult(valid=False, errors=["claims must be a non-empty array"])

    normalized_claims: list[dict[str, Any]] = []
    cited_ids: set[str] = set()
    for index, claim in enumerate(claims):
        path = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{path} must be an object")
            continue
        extra_fields = sorted(set(claim) - {"claim_type", "text", "evidence_ids"})
        if extra_fields:
            errors.append(f"{path} contains unsupported fields: {', '.join(extra_fields)}")
        claim_type = claim.get("claim_type")
        text = claim.get("text")
        evidence = claim.get("evidence_ids")
        if claim_type not in CLAIM_TYPES:
            errors.append(f"{path}.claim_type must be one of {', '.join(CLAIM_TYPES)}")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{path}.text must be a non-empty string")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{path}.evidence_ids must be a non-empty array")
            evidence_ids: list[str] = []
        else:
            evidence_ids = [item for item in evidence if isinstance(item, str)]
            if len(evidence_ids) != len(evidence):
                errors.append(f"{path}.evidence_ids must contain only strings")
            unknown = sorted(set(evidence_ids) - evidence_ledger.ids)
            if unknown:
                errors.append(f"{path}.evidence_ids contains unknown ids: {', '.join(unknown)}")
        cited_ids.update(evidence_ids)

        if isinstance(text, str):
            errors.extend(_validate_immutable_numbers(path, text, evidence_ids, evidence_ledger))
            errors.extend(_validate_text_against_evidence(path, str(claim_type), text, evidence_ids, evidence_ledger))
            if expected_language and not _language_matches(expected_language, text):
                errors.append(f"{path}.text does not match expected language: {expected_language}")

        if claim_type == "fact" and evidence_ids:
            non_fact_ids = sorted(set(evidence_ids) - evidence_ledger.known_ids)
            if non_fact_ids:
                errors.append(f"{path}.fact cites unavailable evidence: {', '.join(non_fact_ids)}")
        elif claim_type == "limitation" and evidence_ids:
            if not set(evidence_ids) & evidence_ledger.unavailable_ids:
                errors.append(f"{path}.limitation must cite unavailable evidence")
        elif claim_type == "recommendation" and evidence_ids:
            if not set(evidence_ids) & evidence_ledger.known_ids:
                errors.append(f"{path}.recommendation must cite at least one known fact")

        if isinstance(claim_type, str) and isinstance(text, str):
            normalized_claims.append({"claim_type": claim_type, "text": text.strip(), "evidence_ids": evidence_ids})

    missing_required = sorted(set(required_evidence_ids) - cited_ids)
    if missing_required:
        errors.append(f"required evidence not cited: {', '.join(missing_required)}")
    missing_critical = sorted(set(critical_evidence_ids) - cited_ids)
    if missing_critical:
        errors.append(f"critical evidence not cited: {', '.join(missing_critical)}")

    normalized = {"claims": normalized_claims} if not errors else None
    return ClaimLedgerValidationResult(valid=not errors, errors=errors, normalized_payload=normalized)


def render_claim_ledger(
    payload: dict[str, Any],
    evidence_ledger: EvidenceLedger,
    *,
    required_evidence_ids: list[str] | tuple[str, ...] = (),
    critical_evidence_ids: list[str] | tuple[str, ...] = (),
    expected_language: str | None = None,
) -> str:
    result = validate_claim_ledger_payload(
        payload,
        evidence_ledger,
        required_evidence_ids=required_evidence_ids,
        critical_evidence_ids=critical_evidence_ids,
        expected_language=expected_language,
    )
    if not result.valid or result.normalized_payload is None:
        raise ValueError("; ".join(result.errors))
    groups: dict[str, list[str]] = {"fact": [], "limitation": [], "recommendation": []}
    for claim in result.normalized_payload["claims"]:
        groups[claim["claim_type"]].append(claim["text"])
    ordered = groups["fact"] + groups["limitation"] + groups["recommendation"]
    return " ".join(_ensure_sentence(text) for text in ordered)


def _validate_immutable_numbers(path: str, text: str, evidence_ids: list[str], evidence_ledger: EvidenceLedger) -> list[str]:
    errors: list[str] = []
    immutable = evidence_ledger.immutable_numbers
    known_numbers = _known_numbers(evidence_ledger)
    text_numbers = _numbers_in_text(text)
    for evidence_id in evidence_ids:
        if evidence_id not in immutable:
            continue
        expected = immutable[evidence_id]
        if not any(_numbers_equivalent(number, expected) for number in text_numbers):
            errors.append(f"{path}.text does not preserve immutable number for {evidence_id}: {expected}")
    for number in text_numbers:
        if any(_numbers_equivalent(number, expected) for expected in known_numbers.values()):
            continue
        if _looks_like_metric_number(number):
            errors.append(f"{path}.text contains unsupported numeric value: {number:g}")
    return errors


def _known_numbers(evidence_ledger: EvidenceLedger) -> dict[str, int | float]:
    numbers: dict[str, int | float] = {}
    for source in evidence_ledger.sources:
        if source.status == "known" and isinstance(source.value, int | float) and not isinstance(source.value, bool):
            numbers[source.id] = source.value
    return numbers


def _validate_text_against_evidence(
    path: str,
    claim_type: str,
    text: str,
    evidence_ids: list[str],
    evidence_ledger: EvidenceLedger,
) -> list[str]:
    errors: list[str] = []
    sources = {source.id: source for source in evidence_ledger.sources}
    normalized_text = _normalize_text(text)
    if claim_type != "limitation" and _asserts_unavailable_metric(normalized_text):
        if any(source.status == "unavailable" for source in evidence_ledger.sources):
            errors.append(f"{path}.text asserts a metric that is unavailable in the evidence ledger")
    for source in evidence_ledger.sources:
        if source.status != "unavailable":
            continue
        label = _normalize_text(source.label)
        if label and label in normalized_text and claim_type != "limitation" and _asserts_unavailable_metric(normalized_text):
            errors.append(f"{path}.text makes unsupported claim about unavailable evidence: {source.id}")

    for evidence_id in evidence_ids:
        source = sources.get(evidence_id)
        if source is None or claim_type != "fact" or source.status != "known":
            continue
        if isinstance(source.value, str):
            expected = _normalize_text(source.value)
            if expected and expected not in normalized_text:
                errors.append(f"{path}.text does not preserve fact value for {evidence_id}: {source.value}")
            for contradiction in _contradictory_terms(source.value):
                if contradiction in normalized_text:
                    errors.append(f"{path}.text contradicts fact value for {evidence_id}: {source.value}")

    if claim_type == "recommendation" and not _looks_like_recommendation(normalized_text):
        errors.append(f"{path}.recommendation is phrased as an observation")
    return errors


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().replace("_", " ").replace("-", " ")).strip()


def _asserts_unavailable_metric(normalized_text: str) -> bool:
    assertion_terms = (
        "improved",
        "increased",
        "stronger",
        "better",
        "grew",
        "growth",
        "positive",
        "likely improving",
        "probably improved",
        "clearly had",
        "strongest engagement",
        "stronger engagement",
        "engagement was higher",
        "had more engagement",
        "s'est amélior",
        "augment",
        "meilleur",
        "souhaite plus",
        "лучше",
        "улучш",
        "рост",
        "сильнее",
        "вовлеченность была выше",
        "вовлечённость была выше",
    )
    return any(term in normalized_text for term in assertion_terms)


def _contradictory_terms(value: str) -> tuple[str, ...]:
    normalized = _normalize_text(value)
    if normalized == "fading":
        return ("emerging",)
    if normalized == "emerging":
        return ("fading",)
    return ()


def _looks_like_recommendation(normalized_text: str) -> bool:
    recommendation_terms = (
        "recommend",
        "consider",
        "should",
        "use ",
        "prioritize",
        "track",
        "collect",
        "review",
        "test",
        "recommande",
        "envisage",
        "devrait",
        "utilise",
        "suivre",
        "collecter",
        "рекоменду",
        "стоит",
        "следует",
        "использ",
        "отслеж",
        "собир",
    )
    return any(term in normalized_text for term in recommendation_terms)


def _language_matches(language: str, text: str) -> bool:
    if language == "fr":
        normalized = f" {_normalize_text(text)} "
        return any(token in normalized for token in (" le ", " la ", " les ", " des ", " est ", " sont ", " portée", " recommand"))
    if language == "ru":
        return bool(re.search(r"[А-Яа-я]", text))
    return True


def _comparison_is_true(left: EvidenceSourceV2, operator: str, right: EvidenceSourceV2) -> bool:
    if left.status != "known" or right.status != "known":
        return False
    if left.predicate != right.predicate:
        return False
    if operator == "equal":
        return left.value == right.value
    if not _is_number(left.value) or not _is_number(right.value):
        return False
    if operator == "greater_than":
        return float(left.value) > float(right.value)
    if operator == "less_than":
        return float(left.value) < float(right.value)
    return False


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _format_v2_value(source: EvidenceSourceV2, language: str) -> str:
    if source.display_value:
        return source.display_value
    value = source.value
    if source.value_type == "percentage" and _is_number(value):
        percentage = float(value) * 100
        formatted = f"{percentage:g}%"
        return f"+{formatted}" if percentage > 0 and source.polarity == "positive" else formatted
    if source.value_type in {"count", "decimal"} and _is_number(value):
        return f"{float(value):g}" if isinstance(value, float) else str(value)
    if value is None:
        return _localized_unavailable(language)
    return str(value)


def _localized_unavailable(language: str) -> str:
    if language == "fr":
        return "non disponible"
    if language == "ru":
        return "недоступно"
    return "unavailable"


def _render_v2_fact(source: EvidenceSourceV2, language: str) -> str:
    value = _format_v2_value(source, language)
    predicate = source.predicate
    if language == "fr":
        if predicate in {"published_posts", "publications_publiees"}:
            return f"{value} publications ont été publiées"
        if predicate == "draft_posts":
            return f"{value} brouillons sont disponibles"
        if predicate in {"momentum", "trend_momentum"}:
            return f"Le momentum est de {value}"
        if predicate == "lifecycle":
            return f"Le cycle de vie est {value}"
        if predicate == "failure_rate":
            return f"Le taux d'échec est de {value}"
        if predicate == "competitor_posts":
            return f"{_localized_subject(source, language)} a publié {value} contenus"
        return f"{_localized_predicate(source, language)} est {value}"
    if language == "ru":
        if predicate == "published_posts":
            return f"Было опубликовано {value} публикации"
        if predicate == "draft_posts":
            return f"Доступно {value} черновика"
        if predicate in {"momentum", "trend_momentum"}:
            return f"Momentum составляет {value}"
        if predicate == "lifecycle":
            return f"Стадия тренда: {value}"
        if predicate == "failure_rate":
            return f"Доля ошибок составляет {value}"
        if predicate == "competitor_posts":
            return f"{_localized_subject(source, language)} опубликовал {value} материалов"
        return f"{_localized_predicate(source, language)}: {value}"
    if predicate == "published_posts":
        return f"{value} posts were published"
    if predicate == "draft_posts":
        return f"{value} draft posts are available"
    if predicate in {"momentum", "trend_momentum"}:
        return f"Momentum is {value}"
    if predicate == "lifecycle":
        return f"The trend lifecycle is {value}"
    if predicate == "failure_rate":
        return f"The failure rate is {value}"
    if predicate == "competitor_posts":
        return f"{_localized_subject(source, language)} posted {value} times"
    return f"{_localized_predicate(source, language)} is {value}"


def _render_v2_limitation(source: EvidenceSourceV2, language: str) -> str:
    predicate = _localized_predicate(source, language)
    if language == "fr":
        return f"Les données de {predicate} ne sont pas disponibles"
    if language == "ru":
        return f"Данные по {predicate} недоступны"
    return f"{predicate.capitalize()} data is unavailable"


def _render_v2_comparison(
    left: EvidenceSourceV2,
    operator: str,
    right: EvidenceSourceV2,
    language: str,
) -> str:
    left_label = _localized_subject(left, language)
    right_label = _localized_subject(right, language)
    left_value = _format_v2_value(left, language)
    right_value = _format_v2_value(right, language)
    predicate = _localized_predicate(left, language)
    if language == "fr":
        if operator == "greater_than":
            return f"{left_label} est supérieur à {right_label} pour {predicate}: {left_value} contre {right_value}"
        if operator == "less_than":
            return f"{left_label} est inférieur à {right_label} pour {predicate}: {left_value} contre {right_value}"
        return f"{left_label} est égal à {right_label} pour {predicate}: {left_value}"
    if language == "ru":
        if operator == "greater_than":
            return f"{left_label} больше, чем {right_label}, по показателю {predicate}: {left_value} против {right_value}"
        if operator == "less_than":
            return f"{left_label} меньше, чем {right_label}, по показателю {predicate}: {left_value} против {right_value}"
        return f"{left_label} равен {right_label} по показателю {predicate}: {left_value}"
    if operator == "greater_than":
        return f"{left_label} is greater than {right_label} for {predicate}: {left_value} versus {right_value}"
    if operator == "less_than":
        return f"{left_label} is less than {right_label} for {predicate}: {left_value} versus {right_value}"
    return f"{left_label} equals {right_label} for {predicate}: {left_value}"


def _render_v2_recommendation(action: str, language: str) -> str:
    if language == "fr":
        return f"Recommandation: {action}"
    if language == "ru":
        return f"Рекомендация: {action}"
    return f"Recommendation: {action}"


def _localized_subject(source: EvidenceSourceV2, language: str) -> str:
    labels = {
        "competitor_a": {"en": "Competitor A", "fr": "Le concurrent A", "ru": "Конкурент A"},
        "competitor_b": {"en": "Competitor B", "fr": "Le concurrent B", "ru": "Конкурент B"},
        "trend": {"en": "the trend", "fr": "la tendance", "ru": "тренд"},
        "content_performance": {"en": "content performance", "fr": "la performance du contenu", "ru": "эффективность контента"},
        "report": {"en": "the report", "fr": "le rapport", "ru": "отчет"},
    }
    return labels.get(source.subject, {}).get(language, source.subject.replace("_", " "))


def _localized_predicate(source: EvidenceSourceV2, language: str) -> str:
    labels = {
        "published_posts": {"en": "published posts", "fr": "publications publiées", "ru": "опубликованным публикациям"},
        "draft_posts": {"en": "draft posts", "fr": "brouillons", "ru": "черновикам"},
        "momentum": {"en": "momentum", "fr": "momentum", "ru": "momentum"},
        "trend_momentum": {"en": "momentum", "fr": "momentum", "ru": "momentum"},
        "lifecycle": {"en": "lifecycle", "fr": "cycle de vie", "ru": "стадии"},
        "reach": {"en": "reach", "fr": "portée", "ru": "охвату"},
        "engagement": {"en": "engagement", "fr": "engagement", "ru": "вовлеченности"},
        "competitor_engagement": {"en": "competitor engagement", "fr": "engagement concurrentiel", "ru": "вовлеченности конкурентов"},
        "competitor_posts": {"en": "posts", "fr": "publications", "ru": "публикациям"},
        "future_peak_date": {"en": "future peak date", "fr": "date du prochain pic", "ru": "дате будущего пика"},
        "conversions": {"en": "conversions", "fr": "conversions", "ru": "конверсиям"},
        "failure_rate": {"en": "failure rate", "fr": "taux d'échec", "ru": "доле ошибок"},
        "audience_preference": {"en": "audience preference", "fr": "préférence du public", "ru": "предпочтениям аудитории"},
    }
    return labels.get(source.predicate, {}).get(language, source.predicate.replace("_", " "))


def _numbers_in_text(text: str) -> list[float]:
    values: list[float] = []
    for match in re.finditer(r"(?<![\w.])([+-]?\d+(?:\.\d+)?)\s*(%)?", text):
        value = float(match.group(1))
        if match.group(2):
            value = value / 100
        values.append(value)
    return values


def _numbers_equivalent(left: float, right: int | float) -> bool:
    return abs(float(left) - float(right)) < 1e-9


def _looks_like_metric_number(value: float) -> bool:
    return abs(value) > 0


def _ensure_sentence(text: str) -> str:
    return text if text.endswith((".", "!", "?")) else f"{text}."
