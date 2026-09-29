from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

ClaimType = Literal["FACT", "LIMITATION", "RECOMMENDATION"]

CLAIM_LEDGER_CONTRACT_VERSION = "claim_ledger_v1"
CLAIM_TYPES: tuple[ClaimType, ...] = ("FACT", "LIMITATION", "RECOMMENDATION")


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
                        "evidence": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "enum": list(allowed_evidence_ids)},
                        },
                    },
                    "required": ["claim_type", "text", "evidence"],
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
        "Each claim must be one of FACT, LIMITATION, or RECOMMENDATION and must cite evidence IDs. "
        "FACT claims may cite only known facts. LIMITATION claims must cite unavailable evidence. "
        "RECOMMENDATION claims must cite the known facts that support the recommendation. "
        "Do not cite evidence IDs that are not listed. Do not alter immutable numbers. "
        f"Known facts: {known or 'none'}. "
        f"Unavailable evidence: {unavailable or 'none'}. "
        f"Immutable numbers: {immutable or 'none'}."
    )


def validate_claim_ledger_payload(payload: Any, evidence_ledger: EvidenceLedger) -> ClaimLedgerValidationResult:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ClaimLedgerValidationResult(valid=False, errors=["payload must be an object"])
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        return ClaimLedgerValidationResult(valid=False, errors=["claims must be a non-empty array"])

    normalized_claims: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        path = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{path} must be an object")
            continue
        claim_type = claim.get("claim_type")
        text = claim.get("text")
        evidence = claim.get("evidence")
        if claim_type not in CLAIM_TYPES:
            errors.append(f"{path}.claim_type must be one of {', '.join(CLAIM_TYPES)}")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{path}.text must be a non-empty string")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{path}.evidence must be a non-empty array")
            evidence_ids: list[str] = []
        else:
            evidence_ids = [item for item in evidence if isinstance(item, str)]
            if len(evidence_ids) != len(evidence):
                errors.append(f"{path}.evidence must contain only strings")
            unknown = sorted(set(evidence_ids) - evidence_ledger.ids)
            if unknown:
                errors.append(f"{path}.evidence contains unknown ids: {', '.join(unknown)}")

        if isinstance(text, str):
            errors.extend(_validate_immutable_numbers(path, text, evidence_ids, evidence_ledger))

        if claim_type == "FACT" and evidence_ids:
            non_fact_ids = sorted(set(evidence_ids) - evidence_ledger.known_ids)
            if non_fact_ids:
                errors.append(f"{path}.FACT cites unavailable evidence: {', '.join(non_fact_ids)}")
        elif claim_type == "LIMITATION" and evidence_ids:
            if not set(evidence_ids) & evidence_ledger.unavailable_ids:
                errors.append(f"{path}.LIMITATION must cite unavailable evidence")
        elif claim_type == "RECOMMENDATION" and evidence_ids:
            if not set(evidence_ids) & evidence_ledger.known_ids:
                errors.append(f"{path}.RECOMMENDATION must cite at least one known fact")

        if isinstance(claim_type, str) and isinstance(text, str):
            normalized_claims.append({"claim_type": claim_type, "text": text.strip(), "evidence": evidence_ids})

    normalized = {"claims": normalized_claims} if not errors else None
    return ClaimLedgerValidationResult(valid=not errors, errors=errors, normalized_payload=normalized)


def render_claim_ledger(payload: dict[str, Any], evidence_ledger: EvidenceLedger) -> str:
    result = validate_claim_ledger_payload(payload, evidence_ledger)
    if not result.valid or result.normalized_payload is None:
        raise ValueError("; ".join(result.errors))
    groups: dict[str, list[str]] = {"FACT": [], "LIMITATION": [], "RECOMMENDATION": []}
    for claim in result.normalized_payload["claims"]:
        groups[claim["claim_type"]].append(claim["text"])
    ordered = groups["FACT"] + groups["LIMITATION"] + groups["RECOMMENDATION"]
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
