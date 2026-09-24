from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import eval_contract_prompt
from .metrics import CaseScore, failure_counts, score_case, summarize
from .runner import _filter_cases, _summarize_group, load_cases

try:
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler
except ImportError:  # pragma: no cover - MLX is local research tooling, not CI dependency.
    generate = None
    load = None
    make_sampler = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = REPO_ROOT / "ml" / "eval" / "cases" / "golden.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "ml" / "outputs" / "mlx_eval"


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _build_case_prompt(case: Any) -> tuple[str, str]:
    system = case.system_prompt
    user_payload: dict[str, Any] = {
        "request": case.user_prompt,
        "input_context": case.input_context,
        "expected_schema": case.expected_schema,
        "grading_rules": case.grading_rules,
    }
    if case.expected_schema != "freeform":
        contract_prompt = eval_contract_prompt(case.expected_schema)
        if contract_prompt:
            system = f"{system} {contract_prompt}"
            user_payload["contract_version"] = case.expected_schema
    user = json.dumps(user_payload, ensure_ascii=False)
    if "/no_think" not in user:
        user = f"{user}\n/no_think"
    return system, user


def _apply_chat_template(tokenizer: Any, *, system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if getattr(tokenizer, "has_chat_template", False):
        return str(
            tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        )
    return f"{system}\n\n{user}"


def _case_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_report(
    *,
    path: Path,
    label: str,
    model: str,
    adapter_path: str,
    summary: dict[str, Any],
    cases: list[Any],
    scores: list[CaseScore],
    records_path: Path,
) -> None:
    lines = [
        f"# MLX Evaluation: {label}",
        "",
        f"- Model: `{model}`",
        f"- Adapter path: `{adapter_path or 'none'}`",
        f"- Evaluation date: `{_utc_timestamp()}Z`",
        f"- Case count: `{summary.get('case_count')}`",
        f"- Instruction following: `{summary.get('instruction_following_rate')}`",
        f"- Required-fact recall: `{summary.get('required_fact_recall')}`",
        f"- Critical required-fact recall: `{summary.get('critical_required_fact_recall')}`",
        f"- Hallucination rate: `{summary.get('hallucination_rate')}`",
        f"- Forbidden-claim rate: `{summary.get('forbidden_claim_rate')}`",
        f"- Numeric preservation: `{summary.get('numeric_preservation_rate')}`",
        f"- Numeric mutation: `{summary.get('numeric_mutation_rate')}`",
        f"- Insufficient-evidence handling: `{summary.get('insufficient_evidence_handling_rate')}`",
        f"- Safe uncertainty: `{summary.get('safe_uncertainty_rate')}`",
        f"- Language match: `{summary.get('language_match_rate')}`",
        f"- Median latency ms: `{summary.get('median_latency_ms')}`",
        f"- P95 latency ms: `{summary.get('p95_latency_ms')}`",
        f"- Failure taxonomy: `{json.dumps(failure_counts(scores), sort_keys=True)}`",
        f"- Raw output file: `{records_path}`",
        "",
        "## By Task Type",
        "",
        "```json",
        json.dumps(_summarize_group(cases, scores, "task_type"), indent=2, sort_keys=True),
        "```",
        "",
        "## By Language",
        "",
        "```json",
        json.dumps(_summarize_group(cases, scores, "language"), indent=2, sort_keys=True),
        "```",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Qwen locally through MLX with optional LoRA adapter.")
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B-MLX-4bit")
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--task-type", default="")
    parser.add_argument("--language", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=20260922)
    args = parser.parse_args()

    if load is None or generate is None or make_sampler is None:
        raise RuntimeError("mlx-lm is required for local MLX evaluation")

    selected = _filter_cases(
        load_cases(Path(args.cases)),
        task_type=args.task_type,
        language=args.language,
        limit=args.limit,
        case_ids=_case_ids(args.case_ids),
    )
    label = args.label or ("lora" if args.adapter_path else "base")
    output_dir = Path(args.output_dir)
    run_name = f"{_utc_timestamp()}-{label}"
    records_path = output_dir / f"{run_name}.jsonl"
    report_path = output_dir / f"{run_name}.md"

    model, tokenizer = load(args.model, adapter_path=args.adapter_path or None, tokenizer_config={"trust_remote_code": True})
    sampler = make_sampler(temp=args.temperature)

    records: list[dict[str, Any]] = []
    scores: list[CaseScore] = []
    for case in selected:
        system, user = _build_case_prompt(case)
        prompt = _apply_chat_template(tokenizer, system=system, user=user)
        started = time.monotonic()
        output = generate(
            model,
            tokenizer,
            prompt,
            max_tokens=args.max_tokens,
            sampler=sampler,
            verbose=False,
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        score = score_case(case, output, latency_ms=latency_ms)
        scores.append(score)
        records.append(
            {
                "case_id": case.id,
                "task_type": case.task_type,
                "language": case.language,
                "latency_ms": latency_ms,
                "score": score.__dict__,
                "output": output,
            }
        )
        _write_jsonl(records_path, records)

    summary = summarize(scores)
    _write_report(
        path=report_path,
        label=label,
        model=args.model,
        adapter_path=args.adapter_path,
        summary=summary,
        cases=selected,
        scores=scores,
        records_path=records_path,
    )
    print(
        json.dumps(
            {
                "label": label,
                "summary": summary,
                "failure_counts": failure_counts(scores),
                "records_path": str(records_path),
                "report_path": str(report_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
