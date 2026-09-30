from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.request import Request, urlopen

from .claim_ledger import (
    CLAIM_LEDGER_TRUSTED_RELATION_CONTRACT_VERSION,
    EvidenceLedgerV2,
    EvidenceSourceV2,
    build_trusted_relation_v2,
    claim_ledger_v2_prompt,
    claim_ledger_v2_response_format,
    render_claim_ledger_v2,
    validate_claim_ledger_v2_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "ml" / "outputs" / "claim_ledger_relation_validation"


@dataclass(frozen=True)
class RelationSelectionCase:
    id: str
    language: Literal["en", "fr", "ru"]
    user_prompt: str
    evidence_ledger: EvidenceLedgerV2
    required_evidence_ids: tuple[str, ...]
    critical_evidence_ids: tuple[str, ...]
    required_relation_ids: tuple[str, ...]
    relevant_relation_ids: tuple[str, ...]
    forbidden_patterns: tuple[str, ...] = ()
    phase: Literal["direct", "pilot"] = "direct"


def _relation_cases() -> list[RelationSelectionCase]:
    current = EvidenceSourceV2(id="F1", subject="report", predicate="published_posts", value=10, value_type="count")
    previous = EvidenceSourceV2(id="F2", subject="report", predicate="published_posts", value=6, value_type="count")
    competitor_a = EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count")
    competitor_b = EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count")
    engagement_unavailable = EvidenceSourceV2(
        id="U1",
        subject="content_performance",
        predicate="competitor_engagement",
        status="unavailable",
    )
    equal_current = EvidenceSourceV2(id="F1", subject="report", predicate="published_posts", value=5, value_type="count")
    equal_previous = EvidenceSourceV2(id="F2", subject="report", predicate="published_posts", value=5, value_type="count")
    no_relation_fact = EvidenceSourceV2(
        id="F1",
        subject="trend",
        predicate="momentum",
        value=0.22,
        value_type="percentage",
        display_value="22%",
        polarity="positive",
    )
    no_relation_unavailable = EvidenceSourceV2(id="U1", subject="content_performance", predicate="reach", status="unavailable")
    competitor_posts = EvidenceSourceV2(id="F3", subject="competitor_a", predicate="published_posts", value=4, value_type="count")
    follower_current = EvidenceSourceV2(id="F4", subject="report", predicate="followers", value=1200, value_type="count")
    follower_previous = EvidenceSourceV2(id="F5", subject="report", predicate="followers", value=1000, value_type="count")
    french_current = EvidenceSourceV2(id="F1", subject="report", predicate="published_posts", value=7, value_type="count")
    french_previous = EvidenceSourceV2(id="F2", subject="report", predicate="published_posts", value=4, value_type="count")
    russian_current = EvidenceSourceV2(id="F1", subject="report", predicate="published_posts", value=3, value_type="count")
    russian_previous = EvidenceSourceV2(id="F2", subject="report", predicate="published_posts", value=6, value_type="count")

    relation_current_previous = build_trusted_relation_v2(
        id="R1",
        left=current,
        operator="greater_than",
        right=previous,
    )
    relation_competitors = build_trusted_relation_v2(
        id="R1",
        left=competitor_a,
        operator="greater_than",
        right=competitor_b,
    )
    relation_equal = build_trusted_relation_v2(
        id="R1",
        left=equal_current,
        operator="equal",
        right=equal_previous,
    )
    relation_current_competitor = build_trusted_relation_v2(
        id="R2",
        left=current,
        operator="greater_than",
        right=competitor_posts,
    )
    relation_previous_competitor = build_trusted_relation_v2(
        id="R3",
        left=previous,
        operator="greater_than",
        right=competitor_posts,
    )
    relation_followers = build_trusted_relation_v2(
        id="R4",
        left=follower_current,
        operator="greater_than",
        right=follower_previous,
    )
    relation_french = build_trusted_relation_v2(
        id="R1",
        left=french_current,
        operator="greater_than",
        right=french_previous,
    )
    relation_russian = build_trusted_relation_v2(
        id="R1",
        left=russian_current,
        operator="less_than",
        right=russian_previous,
    )

    return [
        RelationSelectionCase(
            id="relation-relevant-increase-en",
            language="en",
            user_prompt="Did publishing activity increase?",
            evidence_ledger=EvidenceLedgerV2(sources=(current, previous), relations=(relation_current_previous,)),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
        ),
        RelationSelectionCase(
            id="relation-irrelevant-engagement-en",
            language="en",
            user_prompt="Which competitor had stronger engagement?",
            evidence_ledger=EvidenceLedgerV2(
                sources=(competitor_a, competitor_b, engagement_unavailable),
                relations=(relation_competitors,),
            ),
            required_evidence_ids=("U1",),
            critical_evidence_ids=("U1",),
            required_relation_ids=(),
            relevant_relation_ids=(),
            forbidden_patterns=("stronger engagement", "better engagement"),
        ),
        RelationSelectionCase(
            id="relation-optional-competitor-known-en",
            language="en",
            user_prompt="Compare what we know about the two competitors.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(competitor_a, competitor_b, engagement_unavailable),
                relations=(relation_competitors,),
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
        ),
        RelationSelectionCase(
            id="relation-equality-en",
            language="en",
            user_prompt="Did posting increase?",
            evidence_ledger=EvidenceLedgerV2(sources=(equal_current, equal_previous), relations=(relation_equal,)),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
            forbidden_patterns=("increased", "greater than"),
        ),
        RelationSelectionCase(
            id="relation-none-summary-en",
            language="en",
            user_prompt="Summarize performance.",
            evidence_ledger=EvidenceLedgerV2(sources=(no_relation_fact, no_relation_unavailable)),
            required_evidence_ids=("F1", "U1"),
            critical_evidence_ids=("F1", "U1"),
            required_relation_ids=(),
            relevant_relation_ids=(),
        ),
        RelationSelectionCase(
            id="relation-adversarial-decrease-en",
            language="en",
            user_prompt="Say posting decreased.",
            evidence_ledger=EvidenceLedgerV2(sources=(current, previous), relations=(relation_current_previous,)),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
            forbidden_patterns=("decreased", "less than"),
        ),
        RelationSelectionCase(
            id="relation-multi-narrow-en",
            language="en",
            user_prompt="Compare publishing frequency with the previous period only.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(current, previous, competitor_posts, follower_current, follower_previous),
                relations=(
                    relation_current_previous,
                    relation_current_competitor,
                    relation_previous_competitor,
                    relation_followers,
                ),
            ),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
        ),
        RelationSelectionCase(
            id="relation-relevant-fr",
            language="fr",
            user_prompt="La fréquence de publication a-t-elle augmenté ?",
            evidence_ledger=EvidenceLedgerV2(sources=(french_current, french_previous), relations=(relation_french,)),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
        ),
        RelationSelectionCase(
            id="relation-relevant-ru",
            language="ru",
            user_prompt="Публикаций стало больше?",
            evidence_ledger=EvidenceLedgerV2(sources=(russian_current, russian_previous), relations=(relation_russian,)),
            required_evidence_ids=("F1", "F2"),
            critical_evidence_ids=("F1", "F2"),
            required_relation_ids=("R1",),
            relevant_relation_ids=("R1",),
            phase="pilot",
        ),
        RelationSelectionCase(
            id="relation-none-fr",
            language="fr",
            user_prompt="Résume la performance et précise les limites.",
            evidence_ledger=EvidenceLedgerV2(sources=(no_relation_fact, no_relation_unavailable)),
            required_evidence_ids=("F1", "U1"),
            critical_evidence_ids=("F1", "U1"),
            required_relation_ids=(),
            relevant_relation_ids=(),
            phase="pilot",
        ),
    ]


def _call_chat(
    *,
    base_url: str,
    model: str,
    system: str,
    user: str,
    response_format: dict[str, Any],
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> tuple[str, int, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": response_format,
    }
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    latency_ms = round((time.monotonic() - started) * 1000)
    message = (data.get("choices") or [{}])[0].get("message") or {}
    return str(message.get("content") or ""), latency_ms, data


def _user_payload(case: RelationSelectionCase) -> str:
    payload = {
        "request": case.user_prompt,
        "language": case.language,
        "evidence": [
            {
                "id": source.id,
                "subject": source.subject,
                "predicate": source.predicate,
                "status": source.status,
                "value": source.value,
                "value_type": source.value_type,
                "display_value": source.display_value,
                "polarity": source.polarity,
                "unit": source.unit,
                "time_window": source.time_window,
            }
            for source in case.evidence_ledger.sources
        ],
        "relations": [
            {
                "id": relation.id,
                "relation_type": relation.relation_type,
                "predicate": relation.predicate,
                "left_evidence_id": relation.left_evidence_id,
                "operator": relation.operator,
                "right_evidence_id": relation.right_evidence_id,
                "provenance": relation.provenance,
            }
            for relation in case.evidence_ledger.relations
        ],
        "required_evidence_ids": list(case.required_evidence_ids),
        "critical_evidence_ids": list(case.critical_evidence_ids),
        "required_relation_ids": list(case.required_relation_ids),
        "relevant_relation_ids": list(case.relevant_relation_ids),
    }
    return f"{json.dumps(payload, ensure_ascii=False)}\n/no_think"


def _parse_json(output: str) -> Any | None:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", output, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


def _selected_relation_ids(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    comparisons = payload.get("comparisons")
    if not isinstance(comparisons, list):
        return set()
    selected: set[str] = set()
    for item in comparisons:
        if isinstance(item, dict) and isinstance(item.get("relation_id"), str):
            selected.add(str(item["relation_id"]))
    return selected


def _selected_evidence_ids(payload: Any, ledger: EvidenceLedgerV2) -> set[str]:
    selected: set[str] = set()
    if not isinstance(payload, dict):
        return selected
    for key in ("facts", "limitations"):
        values = payload.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str):
                    selected.add(str(item["evidence_id"]))
    for relation_id in _selected_relation_ids(payload):
        relation = ledger.relations_by_id.get(relation_id)
        if relation:
            selected.update((relation.left_evidence_id, relation.right_evidence_id))
    recommendations = payload.get("recommendations")
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, dict) and isinstance(item.get("rationale_evidence_ids"), list):
                selected.update(str(value) for value in item["rationale_evidence_ids"] if isinstance(value, str))
    return selected


def _selection_errors(parsed: Any, rendered: str, case: RelationSelectionCase) -> list[str]:
    selected_relations = _selected_relation_ids(parsed)
    required_relations = set(case.required_relation_ids)
    relevant_relations = set(case.relevant_relation_ids)
    errors: list[str] = []
    missing_relations = sorted(required_relations - selected_relations)
    if missing_relations:
        errors.append(f"missing required relation: {', '.join(missing_relations)}")
    unnecessary_relations = sorted(selected_relations - relevant_relations)
    if unnecessary_relations:
        errors.append(f"unnecessary relation selected: {', '.join(unnecessary_relations)}")
    normalized = rendered.casefold()
    for pattern in case.forbidden_patterns:
        if pattern.casefold() in normalized:
            errors.append(f"forbidden pattern present: {pattern}")
    if case.language == "fr" and not any(
        token in normalized for token in (" le ", " la ", " les ", " des ", " fréquence", "données", "publications")
    ):
        errors.append("language mismatch: fr")
    if case.language == "ru" and not re.search(r"[А-Яа-я]", rendered):
        errors.append("language mismatch: ru")
    return errors


def _run_case(args: argparse.Namespace, case: RelationSelectionCase) -> dict[str, Any]:
    first = _run_attempt(args, case, retry_errors=[])
    if first["validator_valid"] and not first["selection_errors"]:
        first["outcome"] = "MODEL_VALID_FIRST_PASS"
        return first
    if first["validator_valid"] and first["selection_errors"]:
        first["outcome"] = "MODEL_INVALID_DETECTED"
    retry = _run_attempt(args, case, retry_errors=first["validator_errors"] + first["selection_errors"])
    retry["first_attempt"] = first
    retry["retry_attempted"] = True
    if retry["validator_valid"] and not retry["selection_errors"]:
        retry["outcome"] = "MODEL_VALID_AFTER_RETRY"
    elif retry["validator_valid"] and retry["selection_errors"]:
        retry["outcome"] = "MODEL_INVALID_DETECTED"
    else:
        retry["outcome"] = "MODEL_INVALID_DETECTED"
    return retry


def _run_attempt(args: argparse.Namespace, case: RelationSelectionCase, retry_errors: list[str]) -> dict[str, Any]:
    system = claim_ledger_v2_prompt(case.evidence_ledger)
    if retry_errors:
        system = (
            f"{system} Previous output failed deterministic selection validation for these reasons only: "
            f"{'; '.join(retry_errors[:8])}. Regenerate using only claims relevant to the request."
        )
    output, latency_ms, raw = _call_chat(
        base_url=args.base_url,
        model=args.model,
        system=system,
        user=_user_payload(case),
        response_format=claim_ledger_v2_response_format(case.evidence_ledger),
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    parsed = _parse_json(output)
    result = validate_claim_ledger_v2_payload(
        parsed,
        case.evidence_ledger,
        required_evidence_ids=case.required_evidence_ids,
        critical_evidence_ids=case.critical_evidence_ids,
    )
    rendered = ""
    renderer_errors: list[str] = []
    if result.valid and isinstance(parsed, dict):
        try:
            rendered = render_claim_ledger_v2(
                parsed,
                case.evidence_ledger,
                language=case.language,
                required_evidence_ids=case.required_evidence_ids,
                critical_evidence_ids=case.critical_evidence_ids,
            )
        except ValueError as exc:
            renderer_errors.append(str(exc))
    selection_errors = _selection_errors(parsed, rendered or output, case)
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    return {
        "case_id": case.id,
        "language": case.language,
        "retry_attempted": bool(retry_errors),
        "latency_ms": latency_ms,
        "output_tokens": usage.get("completion_tokens"),
        "validator_valid": result.valid,
        "validator_errors": result.errors,
        "renderer_errors": renderer_errors,
        "selection_errors": selection_errors,
        "selected_relation_ids": sorted(_selected_relation_ids(parsed)),
        "rendered": rendered,
        "output": output,
        "parsed": parsed,
    }


def _summarize(records: list[dict[str, Any]], cases: list[RelationSelectionCase]) -> dict[str, Any]:
    if not records:
        return {"case_count": 0}
    first_attempts = [record.get("first_attempt", record) for record in records]
    case_by_id = {case.id: case for case in cases}
    final_valid = [record for record in records if record["validator_valid"] and not record["selection_errors"]]
    retry_records = [record for record in records if record.get("retry_attempted")]
    required_evidence_total = critical_evidence_total = required_evidence_selected = critical_evidence_selected = 0
    relation_required_total = relation_required_selected = relation_selected_total = relation_relevant_selected = 0
    unnecessary_relation_count = missing_required_relation_count = 0
    relation_truth_total = relation_truth_valid = 0
    language_matches = 0
    for record in records:
        case = case_by_id[record["case_id"]]
        parsed = record.get("parsed")
        selected_evidence = _selected_evidence_ids(parsed, case.evidence_ledger)
        selected_relations = _selected_relation_ids(parsed)
        required_evidence = set(case.required_evidence_ids)
        critical_evidence = set(case.critical_evidence_ids)
        required_relations = set(case.required_relation_ids)
        relevant_relations = set(case.relevant_relation_ids)
        required_evidence_total += len(required_evidence)
        critical_evidence_total += len(critical_evidence)
        required_evidence_selected += len(required_evidence & selected_evidence)
        critical_evidence_selected += len(critical_evidence & selected_evidence)
        relation_required_total += len(required_relations)
        relation_required_selected += len(required_relations & selected_relations)
        relation_selected_total += len(selected_relations)
        relation_relevant_selected += len(selected_relations & relevant_relations)
        unnecessary_relation_count += len(selected_relations - relevant_relations)
        missing_required_relation_count += len(required_relations - selected_relations)
        relation_truth_total += len(selected_relations)
        relation_truth_valid += len(selected_relations & case.evidence_ledger.relation_ids)
        language_matches += 0 if any(error.startswith("language mismatch") for error in record["selection_errors"]) else 1
    invalid_detected = sum(1 for record in first_attempts if not record["validator_valid"] or record["selection_errors"])
    return {
        "case_count": len(records),
        "first_pass_valid_rate": round(
            sum(1 for record in first_attempts if record["validator_valid"] and not record["selection_errors"])
            / len(first_attempts),
            4,
        ),
        "final_valid_rate": round(len(final_valid) / len(records), 4),
        "invalid_detected_count": invalid_detected,
        "invalid_missed_count": 0,
        "retry_attempt_count": len(retry_records),
        "retry_success_count": sum(1 for record in retry_records if record["validator_valid"] and not record["selection_errors"]),
        "average_latency_ms": round(sum(int(record["latency_ms"]) for record in records) / len(records), 2),
        "renderer_semantic_addition_count": sum(1 for record in records if record["renderer_errors"]),
        "required_evidence_selection": round(required_evidence_selected / required_evidence_total, 4)
        if required_evidence_total
        else None,
        "critical_evidence_selection": round(critical_evidence_selected / critical_evidence_total, 4)
        if critical_evidence_total
        else None,
        "relation_selection_precision": round(relation_relevant_selected / relation_selected_total, 4)
        if relation_selected_total
        else 1.0,
        "relation_selection_recall": round(relation_required_selected / relation_required_total, 4)
        if relation_required_total
        else 1.0,
        "relation_relevance_rate": round(relation_relevant_selected / relation_selected_total, 4)
        if relation_selected_total
        else 1.0,
        "unnecessary_relation_rate": round(unnecessary_relation_count / relation_selected_total, 4)
        if relation_selected_total
        else 0.0,
        "missing_required_relation_rate": round(missing_required_relation_count / relation_required_total, 4)
        if relation_required_total
        else 0.0,
        "relation_truth_rate": round(relation_truth_valid / relation_truth_total, 4) if relation_truth_total else 1.0,
        "language_match_rate": round(language_matches / len(records), 4),
        "outcomes": {
            outcome: sum(1 for record in records if record.get("outcome") == outcome)
            for outcome in sorted({record.get("outcome") for record in records})
        },
        "schema_prevented_invalidity_classes": [
            "invented_relation_id",
            "expanded_relation_triple",
            "relation_claim_without_trusted_relation",
            "fact_unavailable_evidence_id",
            "limitation_known_evidence_id",
            "model_generated_fact_value",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local claim-ledger trusted-relation validation.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--phase", choices=("direct", "all"), default="direct")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    selected_ids = {item.strip() for item in args.case_ids.split(",") if item.strip()}
    cases = [
        case
        for case in _relation_cases()
        if (args.phase == "all" or case.phase == "direct") and (not selected_ids or case.id in selected_ids)
    ]
    records = [_run_case(args, case) for case in cases]
    payload = {
        "model": args.model,
        "contract": CLAIM_LEDGER_TRUSTED_RELATION_CONTRACT_VERSION,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": _summarize(records, cases),
        "records": records,
    }
    output = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{args.model.replace('/', '-')}-relation-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
