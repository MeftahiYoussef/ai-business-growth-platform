from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceGroundingErrorCode(StrEnum):
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    INVALID_FACT_EVIDENCE = "INVALID_FACT_EVIDENCE"
    INVALID_LIMITATION_EVIDENCE = "INVALID_LIMITATION_EVIDENCE"
    UNKNOWN_RELATION_ID = "UNKNOWN_RELATION_ID"
    INVALID_RELATION = "INVALID_RELATION"
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
    MISSING_CRITICAL_EVIDENCE = "MISSING_CRITICAL_EVIDENCE"
    DUPLICATE_SELECTION = "DUPLICATE_SELECTION"
    CONTRADICTORY_SELECTION = "CONTRADICTORY_SELECTION"
    MALFORMED_SELECTION = "MALFORMED_SELECTION"


@dataclass(frozen=True)
class EvidenceGroundingError:
    code: EvidenceGroundingErrorCode
    message: str
    path: str = ""


class EvidenceGroundingContractError(ValueError):
    def __init__(self, errors: list[EvidenceGroundingError]) -> None:
        self.errors = errors
        super().__init__("; ".join(error.message for error in errors))
