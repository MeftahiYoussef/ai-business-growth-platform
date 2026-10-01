from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

EVIDENCE_GROUNDING_CONTRACT_VERSION = "evidence_grounding_v1"

EvidenceScalar = str | int | Decimal | bool | None


class EvidenceStatus(StrEnum):
    KNOWN = "known"
    UNAVAILABLE = "unavailable"


class EvidenceValueType(StrEnum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    PERCENTAGE = "percentage"
    STRING = "string"
    ENUM = "enum"
    BOOLEAN = "boolean"


class RelationOperator(StrEnum):
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUAL = "equal"


class RelationType(StrEnum):
    COMPARISON = "comparison"
    TEMPORAL_COMPARISON = "temporal_comparison"


class RelationProvenance(StrEnum):
    DETERMINISTIC = "deterministic"


@dataclass(frozen=True)
class Evidence:
    id: str
    subject: str
    predicate: str
    status: EvidenceStatus = EvidenceStatus.KNOWN
    value: EvidenceScalar = None
    value_type: EvidenceValueType = EvidenceValueType.STRING
    display_value: str | None = None
    unit: str | None = None
    time_window: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_known(self) -> bool:
        return self.status == EvidenceStatus.KNOWN

    @property
    def is_unavailable(self) -> bool:
        return self.status == EvidenceStatus.UNAVAILABLE


@dataclass(frozen=True)
class TrustedRelation:
    id: str
    relation_type: RelationType
    predicate: str
    left_evidence_id: str
    operator: RelationOperator
    right_evidence_id: str
    provenance: RelationProvenance = RelationProvenance.DETERMINISTIC


@dataclass(frozen=True)
class EvidenceLedger:
    evidence: tuple[Evidence, ...]
    relations: tuple[TrustedRelation, ...] = ()

    @property
    def evidence_by_id(self) -> dict[str, Evidence]:
        return {item.id: item for item in self.evidence}

    @property
    def relation_by_id(self) -> dict[str, TrustedRelation]:
        return {relation.id: relation for relation in self.relations}

    @property
    def known_evidence_ids(self) -> set[str]:
        return {item.id for item in self.evidence if item.is_known}

    @property
    def unavailable_evidence_ids(self) -> set[str]:
        return {item.id for item in self.evidence if item.is_unavailable}

    @property
    def trusted_relation_ids(self) -> set[str]:
        return {relation.id for relation in self.relations}


@dataclass(frozen=True)
class FactSelection:
    evidence_id: str


@dataclass(frozen=True)
class LimitationSelection:
    evidence_id: str


@dataclass(frozen=True)
class RelationSelection:
    relation_id: str


@dataclass(frozen=True)
class ClaimSelections:
    facts: tuple[FactSelection, ...] = ()
    limitations: tuple[LimitationSelection, ...] = ()
    relations: tuple[RelationSelection, ...] = ()


@dataclass(frozen=True)
class EvidenceAllowlists:
    known_evidence_ids: tuple[str, ...]
    unavailable_evidence_ids: tuple[str, ...]
    trusted_relation_ids: tuple[str, ...]


def derive_allowlists(ledger: EvidenceLedger) -> EvidenceAllowlists:
    return EvidenceAllowlists(
        known_evidence_ids=tuple(sorted(ledger.known_evidence_ids)),
        unavailable_evidence_ids=tuple(sorted(ledger.unavailable_evidence_ids)),
        trusted_relation_ids=tuple(sorted(ledger.trusted_relation_ids)),
    )
