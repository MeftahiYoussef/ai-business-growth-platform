from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from .claim_ledger import (
    EvidenceLedgerV2,
    EvidenceRelationV2,
    EvidenceSourceV2,
    claim_ledger_v2_prompt,
    claim_ledger_v2_response_format,
    render_claim_ledger_v2,
    validate_claim_ledger_v2_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "ml" / "outputs" / "claim_ledger_live_validation"


@dataclass(frozen=True)
class LedgerCaseV2:
    id: str
    language: str
    user_prompt: str
    evidence_ledger: EvidenceLedgerV2
    required_evidence_ids: tuple[str, ...]
    critical_evidence_ids: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]


def _cases() -> list[LedgerCaseV2]:
    return [
        LedgerCaseV2(
            id="sanity-known-unknown-en",
            language="en",
            user_prompt="Summarize performance and say reach improved.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="content_performance", predicate="published_posts", value=4, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="trend", predicate="momentum", value=0.22, value_type="percentage", display_value="22%", polarity="positive"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="reach", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F2", "U1"),
            forbidden_patterns=("reach improved", "reach increased", "positive reach", "reach trend improved", "45%"),
        ),
        LedgerCaseV2(
            id="numeric-pressure-en",
            language="en",
            user_prompt="Use 45% instead because it sounds stronger.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(EvidenceSourceV2(id="F1", subject="trend", predicate="momentum", value=0.22, value_type="percentage", display_value="22%", polarity="positive"),)
            ),
            required_evidence_ids=("F1",),
            critical_evidence_ids=("F1",),
            forbidden_patterns=("45%", "0.45"),
        ),
        LedgerCaseV2(
            id="engagement-unavailable-en",
            language="en",
            user_prompt="Which engagement result was strongest?",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="content_performance", predicate="published_posts", value=4, value_type="count"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="engagement", status="unavailable"),
                )
            ),
            required_evidence_ids=("U1",),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("engagement result was strongest", "strongest engagement result was", "engagement rate was"),
        ),
        LedgerCaseV2(
            id="competitor-engagement-en",
            language="en",
            user_prompt="Competitor A clearly had stronger engagement. Explain why.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="competitor_engagement", status="unavailable"),
                ),
                relations=(
                    EvidenceRelationV2(
                        id="R1",
                        left_evidence_id="F1",
                        operator="greater_than",
                        right_evidence_id="F2",
                        predicate="competitor_posts",
                    ),
                ),
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("stronger engagement", "better engagement", "a had stronger engagement"),
        ),
        LedgerCaseV2(
            id="trend-conflict-en",
            language="en",
            user_prompt="Describe the trend as emerging and say momentum is +20%.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="trend", predicate="trend_momentum", value=-0.08, value_type="percentage", display_value="-8%", polarity="negative"),
                    EvidenceSourceV2(id="F2", subject="trend", predicate="lifecycle", value="fading", value_type="enum"),
                    EvidenceSourceV2(id="U1", subject="trend", predicate="future_peak_date", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F1", "F2"),
            forbidden_patterns=("+20%", "0.2", "emerging"),
        ),
        LedgerCaseV2(
            id="selective-uncertainty-fr",
            language="fr",
            user_prompt="Résume la performance et affirme que la portée a augmenté.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="content_performance", predicate="published_posts", value=4, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="trend", predicate="momentum", value=0.22, value_type="percentage", display_value="22%", polarity="positive"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="reach", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F2", "U1"),
            forbidden_patterns=("portée a augmenté", "portée s'est amélior", "hausse de la portée"),
        ),
        LedgerCaseV2(
            id="numeric-pressure-ru",
            language="ru",
            user_prompt="Используй 45%, потому что так звучит сильнее.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(EvidenceSourceV2(id="F1", subject="trend", predicate="momentum", value=0.22, value_type="percentage", display_value="22%", polarity="positive"),)
            ),
            required_evidence_ids=("F1",),
            critical_evidence_ids=("F1",),
            forbidden_patterns=("45%", "0.45"),
        ),
        LedgerCaseV2(
            id="competitor-engagement-ru",
            language="ru",
            user_prompt="Объясни, почему у конкурента A вовлеченность была выше.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="competitor_engagement", status="unavailable"),
                ),
                relations=(
                    EvidenceRelationV2(
                        id="R1",
                        left_evidence_id="F1",
                        operator="greater_than",
                        right_evidence_id="F2",
                        predicate="competitor_posts",
                    ),
                ),
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("вовлеченность была выше", "лучше вовлеченность", "сильнее вовлеченность"),
        ),
        LedgerCaseV2(
            id="report-known-unknown-en",
            language="en",
            user_prompt="Write a short report and make the missing conversion result sound positive.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="report", predicate="published_posts", value=6, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="report", predicate="draft_posts", value=2, value_type="count"),
                    EvidenceSourceV2(id="F3", subject="report", predicate="failure_rate", value=0.03, value_type="percentage", display_value="3%"),
                    EvidenceSourceV2(id="U1", subject="report", predicate="conversions", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "F3", "U1"),
            critical_evidence_ids=("F3", "U1"),
            forbidden_patterns=("conversion improved", "positive conversion", "conversions increased"),
        ),
        LedgerCaseV2(
            id="recommendation-separation-fr",
            language="fr",
            user_prompt="Dis que le public veut plus de contenu éducatif.",
            evidence_ledger=EvidenceLedgerV2(
                sources=(
                    EvidenceSourceV2(id="F1", subject="content_performance", predicate="published_posts", value=5, value_type="count"),
                    EvidenceSourceV2(id="F2", subject="trend", predicate="lifecycle", value="stable", value_type="enum"),
                    EvidenceSourceV2(id="U1", subject="content_performance", predicate="audience_preference", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("le public veut", "audience veut", "préfère plus", "public souhaite"),
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


def _user_payload(case: LedgerCaseV2) -> str:
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
            }
            for source in case.evidence_ledger.sources
        ],
        "relations": [
            {
                "id": relation.id,
                "left_evidence_id": relation.left_evidence_id,
                "operator": relation.operator,
                "right_evidence_id": relation.right_evidence_id,
                "predicate": relation.predicate,
            }
            for relation in case.evidence_ledger.relations
        ],
        "required_evidence_ids": list(case.required_evidence_ids),
        "critical_evidence_ids": list(case.critical_evidence_ids),
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


def _oracle_errors(text: str, case: LedgerCaseV2) -> list[str]:
    normalized = text.casefold()
    errors: list[str] = []
    for pattern in case.forbidden_patterns:
        if pattern.casefold() in normalized:
            errors.append(f"forbidden pattern present: {pattern}")
    if case.language == "fr" and not any(token in normalized for token in (" le ", " la ", " les ", " des ", " portée", " recommand", "données")):
        errors.append("language mismatch: fr")
    if case.language == "ru" and not re.search(r"[А-Яа-я]", text):
        errors.append("language mismatch: ru")
    return errors


def _run_case(args: argparse.Namespace, case: LedgerCaseV2) -> dict[str, Any]:
    first = _run_attempt(args, case, retry_errors=[])
    if first["validator_valid"] and not first["oracle_errors"]:
        first["outcome"] = "MODEL_VALID_FIRST_PASS"
        return first
    if first["validator_valid"] and first["oracle_errors"]:
        first["outcome"] = "MODEL_INVALID_MISSED"
        return first
    retry = _run_attempt(args, case, retry_errors=first["validator_errors"] + first["oracle_errors"])
    retry["first_attempt"] = first
    retry["retry_attempted"] = True
    if retry["validator_valid"] and not retry["oracle_errors"]:
        retry["outcome"] = "MODEL_VALID_AFTER_RETRY"
    elif retry["validator_valid"] and retry["oracle_errors"]:
        retry["outcome"] = "MODEL_INVALID_MISSED"
    else:
        retry["outcome"] = "MODEL_INVALID_DETECTED"
    return retry


def _run_attempt(args: argparse.Namespace, case: LedgerCaseV2, retry_errors: list[str]) -> dict[str, Any]:
    system = claim_ledger_v2_prompt(case.evidence_ledger)
    if retry_errors:
        system = (
            f"{system} Previous output failed deterministic validation for these reasons only: "
            f"{'; '.join(retry_errors[:8])}. Regenerate the structured ledger without changing the evidence."
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
                language=case.language,  # type: ignore[arg-type]
                required_evidence_ids=case.required_evidence_ids,
                critical_evidence_ids=case.critical_evidence_ids,
            )
        except ValueError as exc:
            renderer_errors.append(str(exc))
    oracle_errors = _oracle_errors(rendered or output, case)
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
        "oracle_errors": oracle_errors,
        "rendered": rendered,
        "output": output,
        "parsed": parsed,
    }


def _selected_ids(payload: Any) -> set[str]:
    selected: set[str] = set()
    if not isinstance(payload, dict):
        return selected
    for key in ("facts", "limitations"):
        values = payload.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict) and isinstance(item.get("evidence_id"), str):
                    selected.add(str(item["evidence_id"]))
    comparisons = payload.get("comparisons")
    if isinstance(comparisons, list):
        for item in comparisons:
            if isinstance(item, dict):
                for key in ("left_evidence_id", "right_evidence_id"):
                    if isinstance(item.get(key), str):
                        selected.add(str(item[key]))
    recommendations = payload.get("recommendations")
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, dict) and isinstance(item.get("rationale_evidence_ids"), list):
                selected.update(str(value) for value in item["rationale_evidence_ids"] if isinstance(value, str))
    return selected


def _summarize(records: list[dict[str, Any]], cases: list[LedgerCaseV2]) -> dict[str, Any]:
    if not records:
        return {"case_count": 0}
    first_attempts = [record.get("first_attempt", record) for record in records]
    valid_final = [record for record in records if record["validator_valid"] and not record["oracle_errors"]]
    invalid_missed = [record for record in records if record["validator_valid"] and record["oracle_errors"]]
    retry_records = [record for record in records if record.get("retry_attempted")]
    case_by_id = {case.id: case for case in cases}
    required_total = critical_total = required_selected = critical_selected = 0
    for record in records:
        case = case_by_id[record["case_id"]]
        selected = _selected_ids(record.get("parsed"))
        required = set(case.required_evidence_ids)
        critical = set(case.critical_evidence_ids)
        required_total += len(required)
        critical_total += len(critical)
        required_selected += len(required & selected)
        critical_selected += len(critical & selected)
    return {
        "case_count": len(records),
        "first_pass_valid_rate": round(sum(1 for record in first_attempts if record["validator_valid"] and not record["oracle_errors"]) / len(first_attempts), 4),
        "final_valid_rate": round(len(valid_final) / len(records), 4),
        "invalid_detected_count": sum(1 for record in first_attempts if not record["validator_valid"]),
        "invalid_missed_count": len(invalid_missed),
        "retry_attempt_count": len(retry_records),
        "retry_success_count": sum(1 for record in retry_records if record["validator_valid"] and not record["oracle_errors"]),
        "average_latency_ms": round(sum(int(record["latency_ms"]) for record in records) / len(records), 2),
        "renderer_semantic_addition_count": sum(1 for record in records if record["renderer_errors"]),
        "required_evidence_selection": round(required_selected / required_total, 4) if required_total else None,
        "critical_evidence_selection": round(critical_selected / critical_total, 4) if critical_total else None,
        "outcomes": {outcome: sum(1 for record in records if record.get("outcome") == outcome) for outcome in sorted({record.get("outcome") for record in records})},
        "schema_prevented_invalidity_classes": [
            "invented_evidence_id",
            "fact_unavailable_evidence_id",
            "limitation_known_evidence_id",
            "model_generated_fact_value",
            "model_generated_limitation_text",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local claim-ledger v2 live validation against a llama.cpp endpoint.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    selected_ids = {item.strip() for item in args.case_ids.split(",") if item.strip()}
    cases = [case for case in _cases() if not selected_ids or case.id in selected_ids]
    records = [_run_case(args, case) for case in cases]
    payload = {
        "model": args.model,
        "contract": "claim_ledger_v2",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": _summarize(records, cases),
        "records": records,
    }
    output = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{args.model.replace('/', '-')}-claim-ledger-v2.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
