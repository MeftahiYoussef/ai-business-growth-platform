from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .metrics import score_case, summarize
from .schemas import EvaluationCase, validate_case_payload

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = LAB_ROOT / "eval" / "cases" / "golden.jsonl"
DEFAULT_OUTPUT_DIR = LAB_ROOT / "eval" / "results"


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
    headers = {"Content-Type": "application/json"}
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
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Model request failed") from exc
    latency_ms = round((time.monotonic() - started) * 1000)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Model response contained no choices")
    return choices[0].get("message", {}).get("content", ""), latency_ms


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


def _filter_cases(cases: list[EvaluationCase], *, task_type: str, language: str, limit: int | None) -> list[EvaluationCase]:
    filtered = cases
    if task_type:
        filtered = [case for case in filtered if case.task_type == task_type]
    if language:
        filtered = [case for case in filtered if case.language == language]
    return filtered[:limit] if limit else filtered


def _write_summary(*, output_dir: Path, provider: str, model: str, scores: list[Any], summary: dict[str, Any]) -> Path:
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
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    cases = _filter_cases(load_cases(Path(args.cases)), task_type=args.task_type, language=args.language, limit=args.limit)
    scores = []
    try:
        for case in cases:
            output, latency_ms = generate_output(case, provider=args.provider, model=args.model)
            scores.append(score_case(case, output, latency_ms=latency_ms))
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
    summary_path = _write_summary(
        output_dir=Path(args.output_dir),
        provider=args.provider,
        model=args.model,
        scores=scores,
        summary=summary,
    )
    print(json.dumps({"summary": summary, "summary_path": str(summary_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
