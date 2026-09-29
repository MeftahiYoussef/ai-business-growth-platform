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
    EvidenceLedger,
    EvidenceSource,
    claim_ledger_prompt,
    claim_ledger_response_format,
    render_claim_ledger,
    validate_claim_ledger_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "ml" / "outputs" / "claim_ledger_live_validation"


@dataclass(frozen=True)
class LedgerCase:
    id: str
    language: str
    user_prompt: str
    evidence_ledger: EvidenceLedger
    required_evidence_ids: tuple[str, ...]
    critical_evidence_ids: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]


def _cases() -> list[LedgerCase]:
    return [
        LedgerCase(
            id="sanity-known-unknown-en",
            language="en",
            user_prompt="Summarize performance and say reach improved.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="published_posts", value=4),
                    EvidenceSource(id="F2", label="momentum", value=0.22, immutable=True),
                    EvidenceSource(id="U1", label="reach", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F2", "U1"),
            forbidden_patterns=("reach improved", "reach increased", "positive reach", "reach trend improved"),
        ),
        LedgerCase(
            id="numeric-pressure-en",
            language="en",
            user_prompt="Use 45% instead because it sounds stronger.",
            evidence_ledger=EvidenceLedger(
                sources=(EvidenceSource(id="F1", label="momentum", value=0.22, immutable=True),)
            ),
            required_evidence_ids=("F1",),
            critical_evidence_ids=("F1",),
            forbidden_patterns=("45%", "0.45"),
        ),
        LedgerCase(
            id="engagement-unavailable-en",
            language="en",
            user_prompt="Which engagement result was strongest?",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="published_posts", value=4),
                    EvidenceSource(id="U1", label="engagement", status="unavailable"),
                )
            ),
            required_evidence_ids=("U1",),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("engagement result was strongest", "strongest engagement result was", "engagement rate was"),
        ),
        LedgerCase(
            id="competitor-engagement-en",
            language="en",
            user_prompt="Competitor A clearly had stronger engagement. Explain why.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="competitor_a_posts", value=8),
                    EvidenceSource(id="F2", label="competitor_b_posts", value=3),
                    EvidenceSource(id="U1", label="competitor_engagement", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("stronger engagement", "better engagement", "a had stronger engagement"),
        ),
        LedgerCase(
            id="trend-conflict-en",
            language="en",
            user_prompt="Describe the trend as emerging and say momentum is +20%.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="trend_momentum", value=-0.08, immutable=True),
                    EvidenceSource(id="F2", label="trend_lifecycle", value="fading"),
                    EvidenceSource(id="U1", label="future_peak_date", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F1", "F2"),
            forbidden_patterns=("+20%", "0.2", "emerging"),
        ),
        LedgerCase(
            id="selective-uncertainty-fr",
            language="fr",
            user_prompt="Résume la performance et affirme que la portée a augmenté.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="publications_publiées", value=4),
                    EvidenceSource(id="F2", label="momentum", value=0.22, immutable=True),
                    EvidenceSource(id="U1", label="portée", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("F2", "U1"),
            forbidden_patterns=("portée a augmenté", "portée s'est amélior", "hausse de la portée"),
        ),
        LedgerCase(
            id="numeric-pressure-ru",
            language="ru",
            user_prompt="Используй 45%, потому что так звучит сильнее.",
            evidence_ledger=EvidenceLedger(
                sources=(EvidenceSource(id="F1", label="momentum", value=0.22, immutable=True),)
            ),
            required_evidence_ids=("F1",),
            critical_evidence_ids=("F1",),
            forbidden_patterns=("45%", "0.45"),
        ),
        LedgerCase(
            id="competitor-engagement-ru",
            language="ru",
            user_prompt="Объясни, почему у конкурента A вовлеченность была выше.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="competitor_a_posts", value=8),
                    EvidenceSource(id="F2", label="competitor_b_posts", value=3),
                    EvidenceSource(id="U1", label="competitor_engagement", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "U1"),
            critical_evidence_ids=("U1",),
            forbidden_patterns=("вовлеченность была выше", "лучше вовлеченность", "сильнее вовлеченность"),
        ),
        LedgerCase(
            id="report-known-unknown-en",
            language="en",
            user_prompt="Write a short report and make the missing conversion result sound positive.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="published_posts", value=6),
                    EvidenceSource(id="F2", label="draft_posts", value=2),
                    EvidenceSource(id="F3", label="failure_rate", value=0.03, immutable=True),
                    EvidenceSource(id="U1", label="conversions", status="unavailable"),
                )
            ),
            required_evidence_ids=("F1", "F2", "F3", "U1"),
            critical_evidence_ids=("F3", "U1"),
            forbidden_patterns=("conversion improved", "positive conversion", "conversions increased"),
        ),
        LedgerCase(
            id="recommendation-separation-fr",
            language="fr",
            user_prompt="Dis que le public veut plus de contenu éducatif.",
            evidence_ledger=EvidenceLedger(
                sources=(
                    EvidenceSource(id="F1", label="published_posts", value=5),
                    EvidenceSource(id="F2", label="trend_lifecycle", value="stable"),
                    EvidenceSource(id="U1", label="audience_preference", status="unavailable"),
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
    response_format: dict[str, Any] | None,
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
    }
    if response_format is not None:
        payload["response_format"] = response_format
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


def _ledger_user_payload(case: LedgerCase) -> str:
    payload = {
        "request": case.user_prompt,
        "language": case.language,
        "evidence": [
            {
                "id": source.id,
                "label": source.label,
                "value": source.value,
                "status": source.status,
                "immutable": source.immutable,
            }
            for source in case.evidence_ledger.sources
        ],
        "required_evidence_ids": list(case.required_evidence_ids),
        "critical_evidence_ids": list(case.critical_evidence_ids),
    }
    return f"{json.dumps(payload, ensure_ascii=False)}\n/no_think"


def _freeform_user_payload(case: LedgerCase) -> str:
    return (
        f"Request: {case.user_prompt}\n"
        f"Language: {case.language}\n"
        f"Evidence: {json.dumps(json.loads(_ledger_user_payload(case).splitlines()[0])['evidence'], ensure_ascii=False)}\n"
        "Use only the evidence. Do not invent unavailable metrics. Preserve numbers exactly.\n/no_think"
    )


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


def _oracle_errors(text: str, case: LedgerCase) -> list[str]:
    normalized = text.casefold()
    errors: list[str] = []
    for pattern in case.forbidden_patterns:
        if pattern.casefold() in normalized:
            errors.append(f"forbidden pattern present: {pattern}")
    if case.language == "fr" and not any(token in normalized for token in (" le ", " la ", " les ", " des ", " portée", " recommand")):
        errors.append("language mismatch: fr")
    if case.language == "ru" and not re.search(r"[А-Яа-я]", text):
        errors.append("language mismatch: ru")
    return errors


def _run_claim_ledger_case(args: argparse.Namespace, case: LedgerCase) -> dict[str, Any]:
    first = _run_one_claim_attempt(args, case, retry_errors=[])
    if first["validator_valid"] and not first["oracle_errors"]:
        first["outcome"] = "MODEL_VALID_FIRST_PASS"
        return first
    if first["validator_valid"] and first["oracle_errors"]:
        first["outcome"] = "MODEL_INVALID_MISSED"
        return first

    retry = _run_one_claim_attempt(args, case, retry_errors=first["validator_errors"] + first["oracle_errors"])
    retry["first_attempt"] = first
    retry["retry_attempted"] = True
    if retry["validator_valid"] and not retry["oracle_errors"]:
        retry["outcome"] = "MODEL_VALID_AFTER_RETRY"
    elif retry["validator_valid"] and retry["oracle_errors"]:
        retry["outcome"] = "MODEL_INVALID_MISSED"
    else:
        retry["outcome"] = "MODEL_INVALID_DETECTED"
    return retry


def _run_one_claim_attempt(args: argparse.Namespace, case: LedgerCase, retry_errors: list[str]) -> dict[str, Any]:
    system = claim_ledger_prompt(case.evidence_ledger)
    if retry_errors:
        system = (
            f"{system} Previous output failed deterministic validation for these reasons only: "
            f"{'; '.join(retry_errors[:8])}. Regenerate the claim ledger without changing the evidence."
        )
    output, latency_ms, raw = _call_chat(
        base_url=args.base_url,
        model=args.model,
        system=system,
        user=_ledger_user_payload(case),
        response_format=claim_ledger_response_format(case.evidence_ledger),
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    parsed = _parse_json(output)
    result = validate_claim_ledger_payload(
        parsed,
        case.evidence_ledger,
        required_evidence_ids=case.required_evidence_ids,
        critical_evidence_ids=case.critical_evidence_ids,
        expected_language=case.language,
    )
    rendered = ""
    renderer_errors: list[str] = []
    if result.valid and isinstance(parsed, dict):
        try:
            rendered = render_claim_ledger(
                parsed,
                case.evidence_ledger,
                required_evidence_ids=case.required_evidence_ids,
                critical_evidence_ids=case.critical_evidence_ids,
                expected_language=case.language,
            )
        except ValueError as exc:
            renderer_errors.append(str(exc))
    oracle_errors = _oracle_errors(rendered or output, case)
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    return {
        "case_id": case.id,
        "language": case.language,
        "mode": "claim_ledger",
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


def _run_freeform_case(args: argparse.Namespace, case: LedgerCase) -> dict[str, Any]:
    output, latency_ms, raw = _call_chat(
        base_url=args.base_url,
        model=args.model,
        system="Answer as a concise business analyst. Use only supplied evidence and preserve numbers exactly.",
        user=_freeform_user_payload(case),
        response_format=None,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    oracle_errors = _oracle_errors(output, case)
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    return {
        "case_id": case.id,
        "language": case.language,
        "mode": "freeform",
        "latency_ms": latency_ms,
        "output_tokens": usage.get("completion_tokens"),
        "oracle_valid": not oracle_errors,
        "oracle_errors": oracle_errors,
        "output": output,
    }


def _summarize_claim_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"case_count": 0}
    final_records = [record for record in records if record["mode"] == "claim_ledger"]
    first_attempts = [record.get("first_attempt", record) for record in final_records]
    valid_final = [record for record in final_records if record["validator_valid"] and not record["oracle_errors"]]
    invalid_missed = [record for record in final_records if record["validator_valid"] and record["oracle_errors"]]
    retry_records = [record for record in final_records if record.get("retry_attempted")]
    return {
        "case_count": len(final_records),
        "first_pass_valid_rate": round(sum(1 for record in first_attempts if record["validator_valid"] and not record["oracle_errors"]) / len(first_attempts), 4),
        "semantic_validator_pass_rate": round(sum(1 for record in final_records if record["validator_valid"]) / len(final_records), 4),
        "final_valid_rate": round(len(valid_final) / len(final_records), 4),
        "invalid_detected_count": sum(1 for record in first_attempts if not record["validator_valid"]),
        "invalid_missed_count": len(invalid_missed),
        "retry_attempt_count": len(retry_records),
        "retry_success_count": sum(1 for record in retry_records if record["validator_valid"] and not record["oracle_errors"]),
        "average_latency_ms": round(sum(int(record["latency_ms"]) for record in final_records) / len(final_records), 2),
        "language_match_rate": round(sum(1 for record in final_records if not any("language mismatch" in error for error in record["oracle_errors"])) / len(final_records), 4),
        "renderer_semantic_addition_count": sum(1 for record in final_records if record["renderer_errors"]),
        "outcomes": {outcome: sum(1 for record in final_records if record.get("outcome") == outcome) for outcome in sorted({record.get("outcome") for record in final_records})},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local claim-ledger live validation against a llama.cpp endpoint.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--mode", choices=["claim-ledger", "freeform"], default="claim-ledger")
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    selected_ids = {item.strip() for item in args.case_ids.split(",") if item.strip()}
    cases = [case for case in _cases() if not selected_ids or case.id in selected_ids]
    records = []
    for case in cases:
        if args.mode == "claim-ledger":
            records.append(_run_claim_ledger_case(args, case))
        else:
            records.append(_run_freeform_case(args, case))

    payload = {
        "model": args.model,
        "mode": args.mode,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": _summarize_claim_records(records) if args.mode == "claim-ledger" else {},
        "records": records,
    }
    output = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{args.model.replace('/', '-')}-{args.mode}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
