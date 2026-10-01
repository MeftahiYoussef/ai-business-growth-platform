from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import EvidenceGroundingError, EvidenceGroundingErrorCode
from .models import (
    ClaimSelections,
    EvidenceLedger,
    FactSelection,
    LimitationSelection,
    RelationSelection,
)
from .relations import validate_relation_definition


@dataclass(frozen=True)
class EvidenceGroundingValidationResult:
    valid: bool
    errors: list[EvidenceGroundingError]
    selections: ClaimSelections | None = None


def parse_selections(payload: Any) -> ClaimSelections:
    if not isinstance(payload, dict):
        raise ValueError("selection payload must be an object")
    facts = tuple(
        FactSelection(evidence_id=str(item["evidence_id"]))
        for item in payload.get("facts", ())
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    )
    limitations = tuple(
        LimitationSelection(evidence_id=str(item["evidence_id"]))
        for item in payload.get("limitations", ())
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    )
    relations = tuple(
        RelationSelection(relation_id=str(item["relation_id"]))
        for item in payload.get("relations", ())
        if isinstance(item, dict) and isinstance(item.get("relation_id"), str)
    )
    return ClaimSelections(facts=facts, limitations=limitations, relations=relations)


def validate_claim_selections(
    selections: ClaimSelections | Any,
    ledger: EvidenceLedger,
    *,
    required_evidence_ids: tuple[str, ...] = (),
    critical_evidence_ids: tuple[str, ...] = (),
) -> EvidenceGroundingValidationResult:
    errors: list[EvidenceGroundingError] = []
    if not isinstance(selections, ClaimSelections):
        try:
            selections = parse_selections(selections)
        except ValueError as exc:
            return EvidenceGroundingValidationResult(
                valid=False,
                errors=[
                    EvidenceGroundingError(
                        EvidenceGroundingErrorCode.MALFORMED_SELECTION,
                        str(exc),
                    )
                ],
            )

    known_ids = ledger.known_evidence_ids
    unavailable_ids = ledger.unavailable_evidence_ids
    relation_by_id = ledger.relation_by_id
    selected_evidence_ids: set[str] = set()

    seen_fact_ids: set[str] = set()
    for index, fact_selection in enumerate(selections.facts):
        if fact_selection.evidence_id in seen_fact_ids:
            errors.append(
                _error(
                    EvidenceGroundingErrorCode.DUPLICATE_SELECTION,
                    f"duplicate fact selection {fact_selection.evidence_id}",
                    f"facts.{index}",
                )
            )
        seen_fact_ids.add(fact_selection.evidence_id)
        if fact_selection.evidence_id not in known_ids:
            code = EvidenceGroundingErrorCode.UNKNOWN_EVIDENCE_ID
            if fact_selection.evidence_id in unavailable_ids:
                code = EvidenceGroundingErrorCode.INVALID_FACT_EVIDENCE
            errors.append(
                _error(
                    code,
                    f"fact selection must reference known evidence: {fact_selection.evidence_id}",
                    f"facts.{index}",
                )
            )
            continue
        selected_evidence_ids.add(fact_selection.evidence_id)

    seen_limitation_ids: set[str] = set()
    for index, limitation_selection in enumerate(selections.limitations):
        if limitation_selection.evidence_id in seen_limitation_ids:
            errors.append(
                _error(
                    EvidenceGroundingErrorCode.DUPLICATE_SELECTION,
                    f"duplicate limitation selection {limitation_selection.evidence_id}",
                    f"limitations.{index}",
                )
            )
        seen_limitation_ids.add(limitation_selection.evidence_id)
        if limitation_selection.evidence_id not in unavailable_ids:
            code = EvidenceGroundingErrorCode.UNKNOWN_EVIDENCE_ID
            if limitation_selection.evidence_id in known_ids:
                code = EvidenceGroundingErrorCode.INVALID_LIMITATION_EVIDENCE
            errors.append(
                _error(
                    code,
                    f"limitation selection must reference unavailable evidence: {limitation_selection.evidence_id}",
                    f"limitations.{index}",
                )
            )
            continue
        selected_evidence_ids.add(limitation_selection.evidence_id)

    seen_relation_ids: set[str] = set()
    for index, relation_selection in enumerate(selections.relations):
        if relation_selection.relation_id in seen_relation_ids:
            errors.append(
                _error(
                    EvidenceGroundingErrorCode.DUPLICATE_SELECTION,
                    f"duplicate relation selection {relation_selection.relation_id}",
                    f"relations.{index}",
                )
            )
        seen_relation_ids.add(relation_selection.relation_id)
        relation = relation_by_id.get(relation_selection.relation_id)
        if relation is None:
            errors.append(
                _error(
                    EvidenceGroundingErrorCode.UNKNOWN_RELATION_ID,
                    f"relation selection must reference trusted relation: {relation_selection.relation_id}",
                    f"relations.{index}",
                )
            )
            continue
        relation_errors = validate_relation_definition(relation, ledger)
        if relation_errors:
            errors.extend(relation_errors)
            continue
        selected_evidence_ids.update((relation.left_evidence_id, relation.right_evidence_id))

    for evidence_id in sorted(set(seen_fact_ids) & set(seen_limitation_ids)):
        errors.append(
            _error(
                EvidenceGroundingErrorCode.CONTRADICTORY_SELECTION,
                f"evidence cannot be both fact and limitation: {evidence_id}",
            )
        )

    missing_required = sorted(set(required_evidence_ids) - selected_evidence_ids)
    if missing_required:
        errors.append(
            _error(
                EvidenceGroundingErrorCode.MISSING_REQUIRED_EVIDENCE,
                f"required evidence not selected: {', '.join(missing_required)}",
            )
        )
    missing_critical = sorted(set(critical_evidence_ids) - selected_evidence_ids)
    if missing_critical:
        errors.append(
            _error(
                EvidenceGroundingErrorCode.MISSING_CRITICAL_EVIDENCE,
                f"critical evidence not selected: {', '.join(missing_critical)}",
            )
        )
    return EvidenceGroundingValidationResult(valid=not errors, errors=errors, selections=selections if not errors else None)


def _error(code: EvidenceGroundingErrorCode, message: str, path: str = "") -> EvidenceGroundingError:
    return EvidenceGroundingError(code=code, message=message, path=path)
