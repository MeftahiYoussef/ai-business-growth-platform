from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

ClaimType = Literal["fact", "limitation", "recommendation"]

CLAIM_LEDGER_CONTRACT_VERSION = "claim_ledger_v1"
CLAIM_TYPES: tuple[ClaimType, ...] = ("fact", "limitation", "recommendation")


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
