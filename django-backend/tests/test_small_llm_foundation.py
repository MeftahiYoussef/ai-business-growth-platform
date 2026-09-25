from __future__ import annotations

# ruff: noqa: E402,I001

import json
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import override_settings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.datasets.build_sft_dataset import load_jsonl, main as dataset_builder_main  # noqa: E402
from ml.datasets import generate_sft_v2, generate_sft_v2_1  # noqa: E402
from ml.eval.contracts import eval_contract_prompt, validate_eval_contract  # noqa: E402
from ml.eval.metrics import score_case, summarize  # noqa: E402
from ml.eval.runner import load_cases, main as eval_runner_main  # noqa: E402
from ml.eval import semantic_analysis  # noqa: E402

from apps.ai.contracts.content_plan import (  # noqa: E402
    CONTENT_PLAN_CONTRACT_VERSION,
    analyze_content_plan_payload,
    content_plan_serving_schema,
    validate_content_plan_payload,
)
from apps.ai.exceptions import AIConfigurationError, AIProviderError, AIValidationError  # noqa: E402
from apps.ai.providers.factory import get_ai_provider  # noqa: E402
from apps.ai.providers.local_llm_provider import LocalLLMProvider  # noqa: E402
from tests.test_api import valid_content_plan  # noqa: E402


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


def test_local_provider_suppresses_qwen_thinking():
    payload = {
        "id": "local-1",
        "model": "Qwen/Qwen3-1.7B-MLX-4bit",
        "choices": [{"message": {"content": "{\"ok\": true}"}, "finish_reason": "stop"}],
        "usage": {},
    }
    captured: dict = {}

    def fake_urlopen(request, timeout):  # noqa: ANN001, ANN202
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(payload)

    with override_settings(
        LOCAL_LLM_ENABLED=True,
        LOCAL_LLM_MODEL="Qwen/Qwen3-1.7B-MLX-4bit",
        LOCAL_LLM_DISABLE_THINKING=True,
    ):
        with patch("apps.ai.providers.local_llm_provider.urlopen", side_effect=fake_urlopen):
            LocalLLMProvider().generate_structured_json(
                system="Return JSON",
                user="{}",
                schema={"type": "object"},
                prompt_version="test-v1",
            )
    assert captured["payload"]["messages"][-1]["content"].endswith("/no_think")


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


def test_content_plan_contract_validator_matches_application_shape():
    result = validate_content_plan_payload(valid_content_plan())
    assert result.valid is True
    invalid_plan = valid_content_plan()
    invalid_plan["items"][0].pop("caption")
    result = validate_content_plan_payload(invalid_plan)
    assert result.valid is False
    assert any("caption" in error for error in result.errors)


def test_content_plan_ordered_serving_schema_is_derived_from_contract():
    schema = content_plan_serving_schema(ordered_days=True)
    items_schema = schema["properties"]["items"]["prefixItems"]
    assert len(items_schema) == 7
    assert [item["properties"]["day_number"]["const"] for item in items_schema] == list(range(1, 8))
    assert items_schema[0]["properties"]["source_context"]["type"] == "array"
    assert items_schema[0]["properties"]["requires_human_review"]["const"] is True
    assert schema["properties"]["items"]["items"] is False


def test_content_plan_golden_cases_use_current_contract():
    cases = load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl")
    content_cases = [case for case in cases if case.task_type == "content_planning"]
    assert content_cases
    assert {case.expected_schema for case in content_cases} == {CONTENT_PLAN_CONTRACT_VERSION}


def _content_plan_case():
    return next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "cp-en-001")


def test_content_plan_evaluator_fixture_matrix():
    valid_plan = valid_content_plan()
    fixtures = []

    fixtures.append(("VALID_CANONICAL_PLAN", valid_plan, True, "valid"))

    six_item_plan = deepcopy(valid_plan)
    six_item_plan["items"] = six_item_plan["items"][:6]
    fixtures.append(("SIX_ITEM_PLAN", six_item_plan, False, "item_count_valid"))

    duplicate_day_plan = deepcopy(valid_plan)
    duplicate_day_plan["items"][1]["day_number"] = 1
    fixtures.append(("DUPLICATE_DAY_PLAN", duplicate_day_plan, False, "unique_days_valid"))

    wrong_enum_plan = deepcopy(valid_plan)
    wrong_enum_plan["items"][0]["platform"] = "telegram"
    fixtures.append(("WRONG_ENUM_PLAN", wrong_enum_plan, False, "enum_valid"))

    wrong_array_field_plan = deepcopy(valid_plan)
    wrong_array_field_plan["items"][0]["source_context"] = "trend signal"
    fixtures.append(("WRONG_ARRAY_FIELD_PLAN", wrong_array_field_plan, False, "array_fields_valid"))

    human_review_false_plan = deepcopy(valid_plan)
    human_review_false_plan["items"][0]["requires_human_review"] = False
    fixtures.append(("HUMAN_REVIEW_FALSE_PLAN", human_review_false_plan, False, "human_review_valid"))

    wrong_top_level_shape = {"content_plan": valid_plan["items"]}
    fixtures.append(("WRONG_TOP_LEVEL_SHAPE", wrong_top_level_shape, False, "top_level_shape_valid"))

    multilingual_plan = deepcopy(valid_plan)
    multilingual_plan["summary"] = "Plan bilingue avec contenus français et russes."
    multilingual_plan["target_audience"] = "Fondateurs et предприниматели"
    multilingual_plan["items"][0]["caption"] = "Publiez un conseil utile pour les fondateurs."
    multilingual_plan["items"][1]["caption"] = "Опишите один практический совет для предпринимателей."
    fixtures.append(("VALID_MULTILINGUAL_CONTENT", multilingual_plan, True, "valid"))

    case = _content_plan_case()
    for fixture_name, payload, expected_valid, failed_layer in fixtures:
        production_result = validate_content_plan_payload(payload)
        diagnostics = analyze_content_plan_payload(payload)
        score = score_case(case, json.dumps(payload))

        assert production_result.valid is expected_valid, fixture_name
        assert diagnostics.valid is expected_valid, fixture_name
        assert score.schema_valid is expected_valid, fixture_name
        assert score.seven_day_plan_valid is expected_valid, fixture_name
        assert score.human_review_flag is (diagnostics.human_review_valid if not expected_valid else True), fixture_name

        if failed_layer != "valid":
            assert getattr(diagnostics, failed_layer) is False, fixture_name


def test_content_plan_evaluator_rejects_extra_top_level_text():
    case = _content_plan_case()
    score = score_case(case, f"Here is the plan: {json.dumps(valid_content_plan())}")
    assert score.json_parse_valid is False
    assert score.schema_valid is False
    assert score.seven_day_plan_valid is False
    assert score.failure_category == "SCHEMA_FAILURE"


def test_deterministic_content_plan_grading():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "cp-en-001")
    output = json.dumps({
        "summary": "Plan for Instagram and LinkedIn",
        "primary_goal": "engagement",
        "target_audience": "startup founders",
        "items": [
            {
                "day_number": day,
                "title": f"Day {day} idea",
                "platform": "instagram" if day % 2 else "linkedin",
                "content_type": "instagram_caption" if day % 2 else "linkedin_post",
                "objective": "engagement",
                "topic": f"Topic {day}",
                "hook": f"Hook {day}",
                "caption": f"Caption {day}",
                "call_to_action": "Review this idea.",
                "hashtags": ["#growth"],
                "visual_brief": "Simple branded visual.",
                "recommended_time": "09:00",
                "source_context": ["synthetic evaluation case"],
                "risk_flags": [],
                "requires_human_review": True,
            }
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


def test_semantic_required_fact_aliases_reduce_false_negatives():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "report-safety-001")
    output = "Reach is not available in the supplied data, so I cannot state that it doubled."
    score = score_case(case, output)
    assert score.required_fact_recall == 1.0
    assert score.critical_required_fact_recall == 1.0
    assert score.insufficient_evidence_handled is True
    assert score.safe_uncertainty is True


def test_semantic_numeric_preservation_detects_mutation():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "trend-en-001")
    preserved = score_case(case, json.dumps({"trend": "emerging", "supplied_evidence": {"trend_score": 72, "growth_rate": "18"}, "interpretation": "rising", "recommended_actions": []}))
    mutated = score_case(case, json.dumps({"trend": "emerging", "supplied_evidence": {"trend_score": 45, "growth_rate": "99"}, "interpretation": "rising", "recommended_actions": []}))
    assert preserved.numeric_preservation_rate == 1.0
    assert mutated.numeric_mutation_rate and mutated.numeric_mutation_rate > 0


def test_semantic_analysis_rescores_existing_records(tmp_path, monkeypatch, capsys):
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "report-safety-001")
    records = tmp_path / "records.jsonl"
    records.write_text(
        json.dumps({
            "case_id": case.id,
            "task_type": case.task_type,
            "language": case.language,
            "latency_ms": 10,
            "score": {"instruction_following": False, "required_field_rate": 0.5},
            "output": "Reach is not available in the supplied data, so I cannot state that it doubled.",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(semantic_analysis, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(semantic_analysis, "MANIFEST_PATH", tmp_path / "semantic_manifest_v3.json")
    monkeypatch.setattr(sys, "argv", ["semantic", "--records", str(records)])
    assert semantic_analysis.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["required_fact_recall"] == 1.0


def test_non_content_eval_contracts_require_declared_fields():
    result = validate_eval_contract(
        "business_report_v1",
        {"metrics": {"content_total": 1}, "recommendations": [], "data_limitations": []},
    )
    assert result.valid is True

    result = validate_eval_contract("business_report_v1", {"metrics": {"content_total": 1}})
    assert result.valid is False
    assert "recommendations" in " ".join(result.errors)

    prompt = eval_contract_prompt("business_report_v1")
    assert "Return JSON only" in prompt
    assert "metrics, recommendations, data_limitations" in prompt


def test_non_content_schema_scoring_uses_eval_contract():
    case = next(case for case in load_cases(ROOT / "ml" / "eval" / "cases" / "golden.jsonl") if case.id == "report-en-001")
    valid_output = json.dumps({
        "metrics": case.input_context["metrics"],
        "recommendations": ["Review the draft pipeline."],
        "data_limitations": ["No reach data"],
    })
    assert score_case(case, valid_output).schema_valid is True

    missing_field_output = json.dumps({"metrics": case.input_context["metrics"]})
    score = score_case(case, missing_field_output)
    assert score.schema_valid is False
    assert score.failure_category == "MISSING_REQUIRED_FIELD"


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
    assert captured["error"] == "MODEL_FAILURE"
    assert captured["case_id"] == "cp-en-001"
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


def test_dataset_builder_allows_no_test_split(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.jsonl"
    records = []
    for index in range(10):
        records.append({
            "messages": [
                {"role": "system", "content": "rules"},
                {"role": "user", "content": f"request {index}"},
                {"role": "assistant", "content": f"answer {index}"},
            ]
        })
    source.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    output_dir = tmp_path / "splits"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "builder",
            "--input",
            str(source),
            "--output-dir",
            str(output_dir),
            "--validation-ratio",
            "0.1",
            "--test-ratio",
            "0",
        ],
    )
    assert dataset_builder_main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"test": 0, "train": 9, "validation": 1}
    assert not (output_dir / "test.jsonl").read_text(encoding="utf-8").strip()


def test_sft_v2_generator_quality_gates(tmp_path):
    old_root = generate_sft_v2.DATASET_ROOT
    generate_sft_v2.DATASET_ROOT = tmp_path / "qwen3_sft_v2"
    try:
        candidates = generate_sft_v2.generate_candidates()
        seen_hashes: set[str] = set()
        accepted = []
        rejected = []
        for candidate in candidates:
            result = generate_sft_v2._validate_candidate(candidate, seen_hashes)
            if result.accepted:
                accepted.append(result.record)
            else:
                rejected.append(result)
        manifest = generate_sft_v2._write_outputs(candidates, accepted, rejected)
    finally:
        generate_sft_v2.DATASET_ROOT = old_root

    assert manifest["accepted_count"] == 360
    assert manifest["rejected_count"] == 12
    assert manifest["exact_duplicate_count"] == 0
    assert manifest["near_duplicate_rate"] == 0.0
    assert manifest["golden_leakage_count"] == 0
    assert manifest["language_distribution"] == {"en": 144, "fr": 108, "ru": 108}
    assert manifest["difficulty_distribution"] == {"easy": 72, "hard": 108, "medium": 180}
    assert manifest["train_count"] == 324
    assert manifest["validation_count"] == 36


def test_sft_v2_group_split_keeps_families_isolated():
    candidates = generate_sft_v2.generate_candidates()
    seen_hashes: set[str] = set()
    accepted = [
        result.record
        for candidate in candidates
        if (result := generate_sft_v2._validate_candidate(candidate, seen_hashes)).accepted
    ]
    train, validation = generate_sft_v2._split_records(accepted)
    train_families = {record["family_id"] for record in train}
    validation_families = {record["family_id"] for record in validation}
    assert train_families.isdisjoint(validation_families)
    assert len(validation_families) == 9


def test_sft_v2_validation_rejects_bad_examples():
    secret = generate_sft_v2._make_invalid_record(1, "secret_like")
    invented = generate_sft_v2._make_invalid_record(2, "invented_metric")
    mutated = generate_sft_v2._make_invalid_record(3, "numeric_mutation")
    seen_hashes: set[str] = set()
    assert generate_sft_v2._validate_candidate(secret, seen_hashes).accepted is False
    assert generate_sft_v2._validate_candidate(invented, seen_hashes).rejection_reason == "invented_unavailable_metric"
    assert generate_sft_v2._validate_candidate(mutated, seen_hashes).rejection_reason == "numeric_mutation"


def test_sft_v2_1_generator_quality_gates():
    candidates = generate_sft_v2_1.generate_candidates()
    seen_hashes: set[str] = set()
    accepted = []
    rejected = []
    for candidate in candidates:
        result = generate_sft_v2_1._validate_candidate(candidate, seen_hashes)
        if result.accepted:
            accepted.append(result.record)
        else:
            rejected.append(result)
    train, validation = generate_sft_v2_1._split_records(accepted)

    assert len(candidates) == 192
    assert len(accepted) == 180
    assert len(rejected) == 12
    assert len(train) == 162
    assert len(validation) == 18
    assert generate_sft_v2_1._leakage_findings(accepted) == []
    assert generate_sft_v2_1._near_duplicate_pairs(accepted) == []
    assert generate_sft_v2_1._distribution(accepted, "language") == {"en": 72, "fr": 54, "ru": 54}
    assert generate_sft_v2_1._distribution(accepted, "difficulty") == {"easy": 36, "hard": 54, "medium": 90}
    assert all(record["known_missing_ratio"] >= 3 for record in accepted)


def test_sft_v2_1_group_split_keeps_family_template_groups_isolated():
    candidates = generate_sft_v2_1.generate_candidates()
    seen_hashes: set[str] = set()
    accepted = [
        result.record
        for candidate in candidates
        if (result := generate_sft_v2_1._validate_candidate(candidate, seen_hashes)).accepted
    ]
    train, validation = generate_sft_v2_1._split_records(accepted)
    train_groups = {(record["family_id"], record["response_template_family"]) for record in train}
    validation_groups = {(record["family_id"], record["response_template_family"]) for record in validation}
    assert train_groups.isdisjoint(validation_groups)


def test_sft_v2_1_rejects_bad_examples():
    candidates = generate_sft_v2_1.generate_candidates()
    rejected_controls = [candidate for candidate in candidates if candidate["id"].startswith("qwen3-sft-v2-1-reject")]
    seen_hashes: set[str] = set()
    reasons = {
        generate_sft_v2_1._validate_candidate(candidate, seen_hashes).rejection_reason
        for candidate in rejected_controls
    }
    assert "Assistant answer cannot be empty" in reasons
    assert "language_validation_failed" in reasons
    assert "numeric_mutation" in reasons
    assert "invented_unavailable_metric" in reasons


def test_model_registry_contains_qwen_baseline():
    registry = json.loads((ROOT / "ml" / "configs" / "model_registry.json").read_text(encoding="utf-8"))
    assert registry[0]["name"] == "qwen3-1.7b-baseline"
    assert registry[0]["model_id"] == "Qwen/Qwen3-1.7B"
    assert registry[0]["fine_tuned"] is False
    assert registry[0]["rag_enabled"] is False


def test_runtime_capabilities_record_schema_enforcement():
    capabilities = json.loads((ROOT / "ml" / "configs" / "runtime_capabilities.json").read_text(encoding="utf-8"))
    by_name = {item["name"]: item for item in capabilities}
    assert by_name["mlx-lm-qwen3-1.7b"]["supports_json_schema"] is True
    assert by_name["mlx-lm-qwen3-1.7b"]["enforces_json_schema"] is False
    assert by_name["llama-cpp-qwen3-1.7b-q4-k-m"]["supports_json_schema"] is True
    assert by_name["llama-cpp-qwen3-1.7b-q4-k-m"]["enforces_json_schema"] is True


def test_rag_plan_documents_tenant_isolation():
    text = (ROOT / "ml" / "rag" / "README.md").read_text(encoding="utf-8")
    assert "business_id" in text
    assert "Tenant isolation" in text
