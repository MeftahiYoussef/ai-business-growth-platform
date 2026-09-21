from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .metrics import failure_counts, score_case, summarize
from .schemas import EvaluationCase, validate_case_payload

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = LAB_ROOT / "eval" / "cases" / "golden.jsonl"
DEFAULT_OUTPUT_DIR = LAB_ROOT / "eval" / "results"


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore[import-not-found]
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        case = validate_case_payload(payload)
        if case.id in seen:
            raise ValueError(f"Duplicate case id {case.id} at line {line_number}")
        seen.add(case.id)
        cases.append(case)
    return cases


def _chat_completion(*, base_url: str, model: str, system: str, user: str, api_key: str = "", timeout: int = 120) -> tuple[str, int | None]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ai-business-growth-eval/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.monotonic()
    try:
        with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Model request failed") from exc
    latency_ms = round((time.monotonic() - started) * 1000)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Model response contained no choices")
    message = choices[0].get("message", {})
    content = message.get("content")
    if content is None:
        content = message.get("reasoning_content") or json.dumps(message, ensure_ascii=False)
    return content, latency_ms


def _disable_qwen_thinking(provider: str, model: str, user: str) -> str:
    if provider == "local" and "qwen3" in model.lower() and "/no_think" not in user:
        return f"{user}\n/no_think"
    return user


def generate_output(case: EvaluationCase, *, provider: str, model: str) -> tuple[str, int | None]:
    system = case.system_prompt
    user = json.dumps(
        {
            "request": case.user_prompt,
            "input_context": case.input_context,
            "expected_schema": case.expected_schema,
            "grading_rules": case.grading_rules,
        },
        ensure_ascii=False,
    )
    user = _disable_qwen_thinking(provider, model, user)
    if provider == "local":
        return _chat_completion(
            base_url=os.environ.get("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
            model=model,
            system=system,
            user=user,
            timeout=int(os.environ.get("LOCAL_LLM_TIMEOUT_SECONDS", "120")),
        )
    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for Groq benchmark runs")
        return _chat_completion(
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            model=model,
            system=system,
            user=user,
            api_key=api_key,
            timeout=int(os.environ.get("GROQ_TIMEOUT_SECONDS", "60")),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def _filter_cases(
    cases: list[EvaluationCase],
    *,
    task_type: str,
    language: str,
    limit: int | None,
    case_ids: list[str],
) -> list[EvaluationCase]:
    filtered = cases
    if case_ids:
        requested = set(case_ids)
        filtered = [case for case in filtered if case.id in requested]
    if task_type:
        filtered = [case for case in filtered if case.task_type == task_type]
    if language:
        filtered = [case for case in filtered if case.language == language]
    return filtered[:limit] if limit else filtered


def _summarize_group(cases: list[EvaluationCase], scores: list[Any], attr: str) -> dict[str, dict[str, Any]]:
    cases_by_id = {case.id: case for case in cases}
    grouped: dict[str, list[Any]] = {}
    for score in scores:
        key = getattr(cases_by_id[score.case_id], attr)
        grouped.setdefault(key, []).append(score)
    return {key: summarize(value) for key, value in sorted(grouped.items())}


def _write_outputs(
    *,
    output_dir: Path,
    provider: str,
    model: str,
    records: list[dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"{provider}-{model.replace('/', '_')}-{timestamp}.jsonl"
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _write_summary(
    *,
    output_dir: Path,
    provider: str,
    model: str,
    cases: list[EvaluationCase],
    scores: list[Any],
    summary: dict[str, Any],
    output_path: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"{provider}-{model.replace('/', '_')}-{timestamp}.md"
    lines = [
        f"# Model Evaluation: {model}",
        "",
        f"- Provider: `{provider}`",
        f"- Evaluation date: `{timestamp}Z`",
        f"- Case count: `{summary.get('case_count', 0)}`",
        f"- Schema validity: `{summary.get('schema_valid_rate')}`",
        f"- Hallucination failures: `{summary.get('hallucination_rate')}`",
        f"- Task accuracy: `{summary.get('instruction_following_rate')}`",
        f"- Language match: `{summary.get('language_match_rate')}`",
        f"- Average latency ms: `{summary.get('average_latency_ms')}`",
        f"- Median latency ms: `{summary.get('median_latency_ms')}`",
        f"- P95 latency ms: `{summary.get('p95_latency_ms')}`",
        f"- Failure taxonomy: `{json.dumps(failure_counts(scores), sort_keys=True)}`",
        f"- Raw output file: `{output_path.name}`",
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
        "",
        "## Known Limitations",
        "",
        "- Deterministic grading checks structure, supplied facts, forbidden claims, and selected task-specific invariants.",
        "- It does not replace human review or future task-specific expert grading.",
        "- Raw API keys, cookies, and authorization headers are never written to this summary.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a model against project-specific golden cases.")
    parser.add_argument("--provider", choices=["local", "groq"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--task-type", default="")
    parser.add_argument("--language", default="")
    parser.add_argument("--case-ids", default="", help="Comma-separated case ids to evaluate.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    case_ids = [item.strip() for item in args.case_ids.split(",") if item.strip()]
    cases = _filter_cases(
        load_cases(Path(args.cases)),
        task_type=args.task_type,
        language=args.language,
        limit=args.limit,
        case_ids=case_ids,
    )
    scores = []
    records = []
    try:
        for case in cases:
            output, latency_ms = generate_output(case, provider=args.provider, model=args.model)
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
    except RuntimeError as exc:
        print(
            json.dumps(
                {
                    "error": "model_request_failed",
                    "message": str(exc),
                    "provider": args.provider,
                    "model": args.model,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    summary = summarize(scores)
    output_path = _write_outputs(
        output_dir=Path(args.output_dir),
        provider=args.provider,
        model=args.model,
        records=records,
    )
    summary_path = _write_summary(
        output_dir=Path(args.output_dir),
        provider=args.provider,
        model=args.model,
        cases=cases,
        scores=scores,
        summary=summary,
        output_path=output_path,
    )
    print(
        json.dumps(
            {
                "summary": summary,
                "failure_counts": failure_counts(scores),
                "summary_path": str(summary_path),
                "output_path": str(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
