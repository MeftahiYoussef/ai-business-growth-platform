from __future__ import annotations

# ruff: noqa: E402,I001

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import override_settings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.datasets.build_sft_dataset import load_jsonl  # noqa: E402
from ml.eval.metrics import score_case, summarize  # noqa: E402
from ml.eval.runner import load_cases, main as eval_runner_main  # noqa: E402

from apps.ai.exceptions import AIConfigurationError, AIProviderError, AIValidationError  # noqa: E402
from apps.ai.providers.factory import get_ai_provider  # noqa: E402
from apps.ai.providers.local_llm_provider import LocalLLMProvider  # noqa: E402


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_local_provider_is_disabled_by_default():
    with override_settings(LOCAL_LLM_ENABLED=False):
        with pytest.raises(AIConfigurationError):
            LocalLLMProvider()


def test_local_provider_parses_structured_response():
    payload = {
        "id": "local-1",
        "model": "Qwen/Qwen3-1.7B",
        "choices": [{"message": {"content": "{\"ok\": true}"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
    }
    with override_settings(LOCAL_LLM_ENABLED=True, LOCAL_LLM_BASE_URL="http://127.0.0.1:8080/v1"):
        with patch("apps.ai.providers.local_llm_provider.urlopen", return_value=FakeResponse(payload)):
            result = LocalLLMProvider().generate_structured_json(
                system="Return JSON",
                user="{}",
                schema={"type": "object"},
                prompt_version="test-v1",
            )
    assert result.provider == "local"
    assert result.model == "Qwen/Qwen3-1.7B"
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert result.parsed_data == {"ok": True}


def test_local_provider_malformed_response_is_sanitized():
    payload = {"choices": [{"message": {"content": "not json"}}]}
    with override_settings(LOCAL_LLM_ENABLED=True):
        with patch("apps.ai.providers.local_llm_provider.urlopen", return_value=FakeResponse(payload)):
            with pytest.raises(AIValidationError, match="invalid JSON"):
                LocalLLMProvider().generate_structured_json(
                    system="Return JSON",
                    user="{}",
                    schema={"type": "object"},
                    prompt_version="test-v1",
                )


def test_local_provider_unavailable_is_sanitized():
    with override_settings(LOCAL_LLM_ENABLED=True):
        with patch("apps.ai.providers.local_llm_provider.urlopen", side_effect=OSError("connection refused at /secret/cache")):
            with pytest.raises(AIProviderError, match="local model request failed|local model is unavailable"):
                LocalLLMProvider().generate_text(system="Hi", user="Hi")


def test_no_silent_groq_fallback_to_local(settings):
    settings.AI_PROVIDER = "groq"
    settings.GROQ_API_KEY = ""
    settings.LOCAL_LLM_ENABLED = True
    with pytest.raises(AIConfigurationError):
        get_ai_provider()


def test_golden_dataset_loads_and_has_expected_coverage():
    cases = load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl")
    assert len(cases) == 50
    assert {"content_planning", "business_report", "trend_intelligence", "competitor_analysis", "strategy", "safety"} <= {
        case.task_type for case in cases
    }
    assert {"en", "fr", "ru"} <= {case.language for case in cases}


def test_deterministic_content_plan_grading():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "cp-en-001")
    output = json.dumps({
        "summary": "Plan for Instagram and LinkedIn",
        "items": [
            {"day_number": day, "platform": "instagram" if day % 2 else "linkedin", "requires_human_review": True}
            for day in range(1, 8)
        ],
    })
    score = score_case(case, output)
    assert score.schema_valid is True
    assert score.seven_day_plan_valid is True
    assert score.human_review_flag is True


def test_report_metric_hallucination_is_detected():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "report-en-001")
    output = json.dumps({"metrics": {"content_total": 999}, "recommendations": []})
    score = score_case(case, output)
    assert score.hallucination_failed is True


def test_summary_metrics_are_deterministic():
    cases = load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl")[:2]
    scores = [score_case(case, "{}") for case in cases]
    summary = summarize(scores)
    assert summary["case_count"] == 2
    assert "schema_valid_rate" in summary


def test_eval_runner_sanitizes_model_request_failures(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner", "--provider", "local", "--model", "Qwen/Qwen3-1.7B", "--limit", "1"],
    )
    with patch("ml.eval.runner.generate_output", side_effect=RuntimeError("Model request failed")):
        exit_code = eval_runner_main()
    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert captured["error"] == "model_request_failed"
    assert "Traceback" not in captured["message"]
    assert "Qwen/Qwen3-1.7B" == captured["model"]


def test_dataset_builder_rejects_duplicate_and_secret(tmp_path):
    source = tmp_path / "source.jsonl"
    clean = {
        "messages": [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "request"},
            {"role": "assistant", "content": "answer"},
        ]
    }
    source.write_text(json.dumps(clean) + "\n" + json.dumps(clean) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_jsonl(source)

    source.write_text(
        json.dumps({
            "messages": [
                {"role": "system", "content": "rules"},
                {"role": "user", "content": "request"},
                {"role": "assistant", "content": "postgresql://user:pass@example/db"},
            ]
        }) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="secret"):
        load_jsonl(source)


def test_model_registry_contains_qwen_baseline():
    registry = json.loads((ROOT / "ml" / "configs" / "model_registry.json").read_text(encoding="utf-8"))
    assert registry[0]["name"] == "qwen3-1.7b-baseline"
    assert registry[0]["model_id"] == "Qwen/Qwen3-1.7B"
    assert registry[0]["fine_tuned"] is False
    assert registry[0]["rag_enabled"] is False


def test_rag_plan_documents_tenant_isolation():
    text = (ROOT / "ml" / "rag" / "README.md").read_text(encoding="utf-8")
    assert "business_id" in text
    assert "Tenant isolation" in text
