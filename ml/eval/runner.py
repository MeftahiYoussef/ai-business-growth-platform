from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import eval_contract_prompt, eval_contract_response_format
from .metrics import CaseScore, failure_counts, score_case, summarize
from .schemas import EvaluationCase, validate_case_payload

LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DJANGO_BACKEND = REPO_ROOT / "django-backend"
if str(DJANGO_BACKEND) not in sys.path:
    sys.path.insert(0, str(DJANGO_BACKEND))

from apps.ai.contracts.content_plan import (  # noqa: E402
    CONTENT_PLAN_CONTRACT_VERSION,
    content_plan_contract_prompt,
    content_plan_serving_schema,
)

DEFAULT_CASES = LAB_ROOT / "eval" / "cases" / "golden.jsonl"
DEFAULT_OUTPUT_DIR = LAB_ROOT / "eval" / "results"
DEFAULT_RUN_ROOT = REPO_ROOT / "ml" / "outputs" / "runs"


class BenchmarkRequestError(RuntimeError):
    error_type = "NETWORK_FAILURE"

    def __init__(self, message: str, *, status_code: int | None = None, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class BenchmarkRateLimitError(BenchmarkRequestError):
    error_type = "RATE_LIMIT"


def _ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore[import-not-found]
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_run_id(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    return safe.strip("-") or "benchmark-run"


def _new_run_id(provider: str, model: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return _safe_run_id(f"{timestamp}-{provider}-{model.replace('/', '-')}")


def _run_dir(run_id: str) -> Path:
    return DEFAULT_RUN_ROOT / _safe_run_id(run_id)


def _state_path(run_id: str) -> Path:
    return _run_dir(run_id) / "state.json"


def _records_path(run_id: str) -> Path:
    return _run_dir(run_id) / "records.jsonl"


def _load_records(run_id: str) -> list[dict[str, Any]]:
    path = _records_path(run_id)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_run_state(state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    run_dir = _run_dir(str(state["run_id"]))
    run_dir.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utc_now()
    _state_path(str(state["run_id"])).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _records_path(str(state["run_id"])).write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + ("\n" if records else ""),
        encoding="utf-8",
    )


def _initial_state(*, run_id: str, provider: str, model: str, case_ids: list[str]) -> dict[str, Any]:
    now = _utc_now()
    return {
        "run_id": run_id,
        "evaluation_version": "golden_eval_v2",
        "provider": provider,
        "model": model,
        "selected_case_ids": case_ids,
        "completed_case_ids": [],
        "pending_case_ids": case_ids,
        "failed_infrastructure_case_ids": [],
        "started_at": now,
        "updated_at": now,
    }


def _load_or_create_state(*, run_id: str, resume: str, provider: str, model: str, case_ids: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    effective_run_id = resume or run_id
    if resume:
        path = _state_path(effective_run_id)
        if not path.exists():
            raise ValueError(f"Benchmark run state not found: {effective_run_id}")
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("provider") != provider or state.get("model") != model:
            raise ValueError("Resume provider/model does not match saved run state")
        return state, _load_records(effective_run_id)
    state = _initial_state(run_id=effective_run_id, provider=provider, model=model, case_ids=case_ids)
    _write_run_state(state, [])
    return state, []


def _retry_after_seconds(headers: Any) -> int | None:
    value = headers.get("Retry-After") if headers else None
    if not value:
        return None
    try:
        seconds = int(str(value))
    except ValueError:
        return None
    return max(0, seconds)


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


def _chat_completion(
    *,
    base_url: str,
    model: str,
    system: str,
    user: str,
    api_key: str = "",
    timeout: int = 120,
    response_format: dict[str, Any] | None = None,
    max_output_tokens: int = 4096,
    temperature: float = 0.2,
) -> tuple[str, int | None]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "stream": False,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ai-business-growth-eval/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    started = time.monotonic()
    attempts = [payload]
    data: dict[str, Any] | None = None
    for attempt_index, attempt_payload in enumerate(attempts):
        request = Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(attempt_payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                data = json.loads(response.read().decode("utf-8"))
                break
        except HTTPError as exc:
            retry_after = _retry_after_seconds(getattr(exc, "headers", None))
            if exc.code == 429:
                raise BenchmarkRateLimitError("Provider rate limit reached", status_code=429, retry_after_seconds=retry_after) from exc
            retry_schema_failure = os.environ.get("EVAL_RETRY_PROVIDER_SCHEMA_FAILURE", "true").lower() in {"1", "true", "yes"}
            if response_format is not None and exc.code == 400 and attempt_index == 0 and retry_schema_failure:
                retry_payload = {
                    **payload,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"{system} The JSON Schema is strict. Satisfy every required field, enum, const, "
                                "array type, minItems, and maxItems rule exactly. Return JSON only."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"{user}\n\nRetry once. Return only one JSON object that satisfies the schema exactly."
                            ),
                        },
                    ],
                }
                attempts.append(retry_payload)
                continue
            raise BenchmarkRequestError("Model request failed", status_code=exc.code) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise BenchmarkRequestError("Model request failed") from exc
    if data is None:
        raise BenchmarkRequestError("Model request failed")
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
    if os.environ.get("EVAL_DISABLE_QWEN_THINKING", "true").lower() not in {"1", "true", "yes"}:
        return user
    if provider == "local" and "qwen3" in model.lower() and "/no_think" not in user:
        return f"{user}\n/no_think"
    return user


def generate_output(case: EvaluationCase, *, provider: str, model: str) -> tuple[str, int | None]:
    system = case.system_prompt
    user_payload: dict[str, Any] = {
        "request": case.user_prompt,
        "input_context": case.input_context,
        "expected_schema": case.expected_schema,
        "grading_rules": case.grading_rules,
    }
    response_format = None
    if case.task_type == "content_planning":
        system = f"{system} {content_plan_contract_prompt()}"
        user_payload["contract_version"] = CONTENT_PLAN_CONTRACT_VERSION
        user_payload["canonical_contract"] = content_plan_contract_prompt()
        serving_schema_mode = os.environ.get("EVAL_CONTENT_PLAN_SERVING_SCHEMA", "standard").lower()
        serving_schema = content_plan_serving_schema(ordered_days=serving_schema_mode == "ordered_days")
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": CONTENT_PLAN_CONTRACT_VERSION,
                "strict": True,
                "schema": serving_schema,
            },
        }
    elif case.expected_schema != "freeform":
        contract_prompt = eval_contract_prompt(case.expected_schema)
        if contract_prompt:
            system = f"{system} {contract_prompt}"
            user_payload["contract_version"] = case.expected_schema
            response_format = eval_contract_response_format(case.expected_schema)
    response_format_mode = os.environ.get("EVAL_RESPONSE_FORMAT_MODE", "schema").lower()
    if response_format_mode == "none":
        response_format = None
    elif response_format_mode == "json_object" and response_format is not None:
        response_format = {"type": "json_object"}
    user = json.dumps(
        user_payload,
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
            response_format=response_format,
            max_output_tokens=int(os.environ.get("LOCAL_LLM_MAX_OUTPUT_TOKENS", "4096")),
            temperature=float(os.environ.get("EVAL_TEMPERATURE", "0.2")),
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
            response_format=response_format,
            max_output_tokens=int(os.environ.get("GROQ_MAX_OUTPUT_TOKENS", "4000")),
            temperature=float(os.environ.get("EVAL_TEMPERATURE", "0.2")),
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
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
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
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
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
    parser.add_argument("--run-id", default="")
    parser.add_argument("--resume", default="", help="Resume a saved benchmark run id from ml/outputs/runs.")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--rate-limit-max-wait", type=int, default=300)
    args = parser.parse_args()

    case_ids = [item.strip() for item in args.case_ids.split(",") if item.strip()]
    cases = _filter_cases(
        load_cases(Path(args.cases)),
        task_type=args.task_type,
        language=args.language,
        limit=args.limit,
        case_ids=case_ids,
    )
    selected_case_ids = [case.id for case in cases]
    run_id = args.resume or _safe_run_id(args.run_id or _new_run_id(args.provider, args.model))
    try:
        state, records = _load_or_create_state(
            run_id=run_id,
            resume=args.resume,
            provider=args.provider,
            model=args.model,
            case_ids=selected_case_ids,
        )
    except ValueError as exc:
        print(json.dumps({"error": "invalid_resume_state", "message": str(exc)}, indent=2, sort_keys=True))
        return 2
    if args.resume:
        selected_case_ids = [str(case_id) for case_id in state["selected_case_ids"]]
        selected_case_id_set = set(selected_case_ids)
        cases = [case for case in cases if case.id in selected_case_id_set]
    completed_ids = {str(record["case_id"]) for record in records}
    scores: list[CaseScore] = []
    for record in records:
        scores.append(CaseScore(**record["score"]))
    current_case_id: str | None = None
    try:
        for case in cases:
            if case.id in completed_ids:
                continue
            current_case_id = case.id
            retry_count = 0
            while True:
                try:
                    output, latency_ms = generate_output(case, provider=args.provider, model=args.model)
                    break
                except BenchmarkRateLimitError as exc:
                    retry_count += 1
                    if retry_count > args.max_retries:
                        failed_ids = set(state.setdefault("failed_infrastructure_case_ids", []))
                        state["failed_infrastructure_case_ids"] = sorted(failed_ids | {case.id})
                        state["pending_case_ids"] = [item for item in selected_case_ids if item not in completed_ids]
                        _write_run_state(state, records)
                        raise
                    wait_seconds = exc.retry_after_seconds if exc.retry_after_seconds is not None else min(60 * retry_count, args.rate_limit_max_wait)
                    wait_seconds = min(wait_seconds, args.rate_limit_max_wait)
                    time.sleep(wait_seconds)
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
            completed_ids.add(case.id)
            state["completed_case_ids"] = sorted(completed_ids)
            state["pending_case_ids"] = [item for item in selected_case_ids if item not in completed_ids]
            _write_run_state(state, records)
    except (BenchmarkRequestError, RuntimeError) as exc:
        cause = exc.__cause__
        if current_case_id:
            failed_ids = set(state.setdefault("failed_infrastructure_case_ids", []))
            state["failed_infrastructure_case_ids"] = sorted(failed_ids | {current_case_id})
            state["pending_case_ids"] = [item for item in selected_case_ids if item not in completed_ids]
            _write_run_state(state, records)
        error_type = exc.error_type if isinstance(exc, BenchmarkRequestError) else "MODEL_FAILURE"
        print(
            json.dumps(
                {
                    "error": error_type,
                    "case_id": current_case_id,
                    "message": str(exc),
                    "provider": args.provider,
                    "model": args.model,
                    "run_id": state["run_id"],
                    "cause_type": type(cause).__name__ if cause else None,
                    "status_code": exc.status_code if isinstance(exc, BenchmarkRequestError) else None,
                    "retry_after_seconds": exc.retry_after_seconds if isinstance(exc, BenchmarkRequestError) else None,
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
