from __future__ import annotations

from typing import Any

from .models import EVIDENCE_GROUNDING_CONTRACT_VERSION, EvidenceLedger, derive_allowlists


def evidence_grounding_selection_schema(ledger: EvidenceLedger) -> dict[str, Any]:
    allowlists = derive_allowlists(ledger)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "facts": {
                "type": "array",
                "items": _evidence_selection_schema(allowlists.known_evidence_ids),
            },
            "limitations": {
                "type": "array",
                "items": _evidence_selection_schema(allowlists.unavailable_evidence_ids),
            },
            "relations": {
                "type": "array",
                "maxItems": 100 if allowlists.trusted_relation_ids else 0,
                "items": _relation_selection_schema(allowlists.trusted_relation_ids),
            },
        },
        "required": ["facts", "limitations", "relations"],
    }


def evidence_grounding_response_format(ledger: EvidenceLedger) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": EVIDENCE_GROUNDING_CONTRACT_VERSION,
            "strict": True,
            "schema": evidence_grounding_selection_schema(ledger),
        },
    }


def _evidence_selection_schema(allowed_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"evidence_id": {"type": "string", "enum": list(allowed_ids)}},
        "required": ["evidence_id"],
    }


def _relation_selection_schema(allowed_ids: tuple[str, ...]) -> dict[str, Any]:
    if allowed_ids:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {"relation_id": {"type": "string", "enum": list(allowed_ids)}},
            "required": ["relation_id"],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"relation_id": {"type": "string", "enum": ["__no_trusted_relations__"]}},
        "required": ["relation_id"],
    }
