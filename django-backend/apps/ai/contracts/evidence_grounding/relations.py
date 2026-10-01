from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .exceptions import EvidenceGroundingContractError, EvidenceGroundingError, EvidenceGroundingErrorCode
from .models import (
    Evidence,
    EvidenceLedger,
    EvidenceValueType,
    RelationOperator,
    RelationProvenance,
    RelationType,
    TrustedRelation,
)


def build_trusted_relation(
    *,
    id: str,
    left: Evidence,
    operator: RelationOperator,
    right: Evidence,
    predicate: str | None = None,
    relation_type: RelationType = RelationType.COMPARISON,
) -> TrustedRelation:
    relation = TrustedRelation(
        id=id,
        relation_type=relation_type,
        predicate=predicate or left.predicate,
        left_evidence_id=left.id,
        operator=operator,
        right_evidence_id=right.id,
        provenance=RelationProvenance.DETERMINISTIC,
    )
    errors = validate_relation_definition(relation, EvidenceLedger(evidence=(left, right), relations=(relation,)))
    if errors:
        raise EvidenceGroundingContractError(errors)
    return relation


def validate_relation_definition(relation: TrustedRelation, ledger: EvidenceLedger) -> list[EvidenceGroundingError]:
    evidence_by_id = ledger.evidence_by_id
    left = evidence_by_id.get(relation.left_evidence_id)
    right = evidence_by_id.get(relation.right_evidence_id)
    if left is None or right is None:
        return [
            EvidenceGroundingError(
                EvidenceGroundingErrorCode.UNKNOWN_EVIDENCE_ID,
                f"relation {relation.id} references unknown evidence",
                path=f"relations.{relation.id}",
            )
        ]
    compatibility_error = _relation_compatibility_error(relation, left, right)
    if compatibility_error is not None:
        return [compatibility_error]
    if not relation_truth_is_deterministic(relation, left, right):
        return [
            EvidenceGroundingError(
                EvidenceGroundingErrorCode.INVALID_RELATION,
                f"relation {relation.id} is not true for trusted evidence",
                path=f"relations.{relation.id}",
            )
        ]
    return []


def relation_truth_is_deterministic(relation: TrustedRelation, left: Evidence, right: Evidence) -> bool:
    if relation.operator == RelationOperator.EQUAL:
        return left.value == right.value
    left_number = numeric_value(left)
    right_number = numeric_value(right)
    if left_number is None or right_number is None:
        return False
    if relation.operator == RelationOperator.GREATER_THAN:
        return left_number > right_number
    if relation.operator == RelationOperator.LESS_THAN:
        return left_number < right_number
    return False


def numeric_value(evidence: Evidence) -> Decimal | None:
    if evidence.value_type not in {
        EvidenceValueType.INTEGER,
        EvidenceValueType.DECIMAL,
        EvidenceValueType.PERCENTAGE,
    }:
        return None
    if isinstance(evidence.value, bool) or evidence.value is None:
        return None
    try:
        return Decimal(str(evidence.value))
    except (InvalidOperation, ValueError):
        return None


def numeric_representation_matches(evidence: Evidence, candidate: str | int | Decimal) -> bool:
    authoritative = numeric_value(evidence)
    if authoritative is None:
        return False
    if isinstance(candidate, str):
        candidate_text = candidate.strip()
        if candidate_text.endswith("%"):
            try:
                candidate_value = Decimal(candidate_text[:-1].replace("+", "")) / Decimal("100")
            except (InvalidOperation, ValueError):
                return False
        else:
            try:
                candidate_value = Decimal(candidate_text.replace("+", ""))
            except (InvalidOperation, ValueError):
                return False
    else:
        candidate_value = Decimal(str(candidate))
    return candidate_value == authoritative


def _relation_compatibility_error(
    relation: TrustedRelation,
    left: Evidence,
    right: Evidence,
) -> EvidenceGroundingError | None:
    if relation.provenance != RelationProvenance.DETERMINISTIC:
        return _invalid_relation(relation.id, "relation provenance must be deterministic")
    if left.id == right.id:
        return _invalid_relation(relation.id, "relation cannot compare evidence with itself")
    if not left.is_known or not right.is_known:
        return _invalid_relation(relation.id, "relation operands must both be known")
    if relation.predicate != left.predicate or relation.predicate != right.predicate:
        return _invalid_relation(relation.id, "relation operands must share the relation predicate")
    if left.value_type != right.value_type:
        return _invalid_relation(relation.id, "relation operands must share a value type")
    if left.unit != right.unit:
        return _invalid_relation(relation.id, "relation operands must share a unit")
    if (
        relation.relation_type == RelationType.COMPARISON
        and left.time_window is not None
        and right.time_window is not None
        and left.time_window != right.time_window
    ):
        return _invalid_relation(relation.id, "relation operands must share a time window")
    return None


def _invalid_relation(relation_id: str, message: str) -> EvidenceGroundingError:
    return EvidenceGroundingError(
        EvidenceGroundingErrorCode.INVALID_RELATION,
        f"relation {relation_id} is invalid: {message}",
        path=f"relations.{relation_id}",
    )
