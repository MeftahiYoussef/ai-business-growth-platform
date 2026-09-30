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
from ml.eval.claim_ledger import (  # noqa: E402
    EvidenceLedgerV2,
    EvidenceRelationV2,
    EvidenceSourceV2,
    build_evidence_ledger,
    claim_ledger_prompt,
    claim_ledger_response_format,
    claim_ledger_v2_response_format,
    render_claim_ledger,
    render_claim_ledger_v2,
    validate_claim_ledger_v2_payload,
    validate_claim_ledger_payload,
)
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


def test_claim_ledger_validates_evidence_bound_semantic_output():
    ledger = build_evidence_ledger(
        facts={"F1": 4, "F2": 0.22},
        unavailable={"U1": "reach"},
        immutable_numbers={"F2": 0.22},
    )
    payload = {
        "claims": [
            {"claim_type": "fact", "text": "Published posts were 4.", "evidence_ids": ["F1"]},
            {"claim_type": "fact", "text": "Momentum was 22%.", "evidence_ids": ["F2"]},
            {"claim_type": "limitation", "text": "Reach is unavailable.", "evidence_ids": ["U1"]},
            {
                "claim_type": "recommendation",
                "text": "Use the 4 published posts and 22% momentum to guide the next content review.",
                "evidence_ids": ["F1", "F2"],
            },
        ]
    }

    result = validate_claim_ledger_payload(payload, ledger)

    assert result.valid is True
    assert result.errors == []
    rendered = render_claim_ledger(payload, ledger)
    assert "Published posts were 4." in rendered
    assert "Reach is unavailable." in rendered


def test_claim_ledger_rejects_unavailable_fact_and_numeric_mutation():
    ledger = build_evidence_ledger(
        facts={"F1": 4, "F2": 0.22},
        unavailable={"U1": "reach"},
        immutable_numbers={"F2": 0.22},
    )
    payload = {
        "claims": [
            {"claim_type": "fact", "text": "Reach improved.", "evidence_ids": ["U1"]},
            {"claim_type": "fact", "text": "Momentum was 45%.", "evidence_ids": ["F2"]},
        ]
    }

    result = validate_claim_ledger_payload(payload, ledger)

    assert result.valid is False
    assert any("fact cites unavailable evidence" in error for error in result.errors)
    assert any("does not preserve immutable number" in error for error in result.errors)
    assert any("unsupported numeric value" in error for error in result.errors)
    with pytest.raises(ValueError):
        render_claim_ledger(payload, ledger)


def test_claim_ledger_response_format_is_constrained_to_known_evidence_ids():
    ledger = build_evidence_ledger(facts={"F1": 4}, unavailable={"U1": "reach"})
    response_format = claim_ledger_response_format(ledger)
    prompt = claim_ledger_prompt(ledger)

    schema = response_format["json_schema"]["schema"]
    evidence_schema = schema["properties"]["claims"]["items"]["properties"]["evidence_ids"]["items"]
    assert response_format["type"] == "json_schema"
    assert schema["additionalProperties"] is False
    assert evidence_schema["enum"] == ["F1", "U1"]
    assert "fact claims may cite only known facts" in prompt


def test_claim_ledger_extended_semantic_failure_matrix():
    ledger = build_evidence_ledger(
        facts={"F1": 4, "F2": 0.22, "F3": -0.08, "F4": "fading"},
        unavailable={"U1": "reach", "U2": "engagement"},
        immutable_numbers={"F2": 0.22, "F3": -0.08},
    )
    valid_payload = {
        "claims": [
            {"claim_type": "fact", "text": "Published posts were 4.", "evidence_ids": ["F1"]},
            {"claim_type": "fact", "text": "Momentum was +22%.", "evidence_ids": ["F2"]},
            {"claim_type": "fact", "text": "Trend momentum was -8%.", "evidence_ids": ["F3"]},
            {"claim_type": "fact", "text": "The trend lifecycle was fading.", "evidence_ids": ["F4"]},
            {"claim_type": "limitation", "text": "Reach is unavailable.", "evidence_ids": ["U1"]},
            {"claim_type": "recommendation", "text": "Use the 4 published posts and 22% momentum to plan the next review.", "evidence_ids": ["F1", "F2"]},
        ]
    }
    assert validate_claim_ledger_payload(
        valid_payload,
        ledger,
        required_evidence_ids=["F1", "F2", "U1"],
        critical_evidence_ids=["F2"],
    ).valid

    invalid_cases = {
        "invented evidence id": {
            "claims": [{"claim_type": "fact", "text": "Published posts were 4.", "evidence_ids": ["F99"]}]
        },
        "limitation cites known evidence only": {
            "claims": [{"claim_type": "limitation", "text": "Published posts are limited.", "evidence_ids": ["F1"]}]
        },
        "unsupported numeric value": {
            "claims": [{"claim_type": "fact", "text": "Momentum was 23%.", "evidence_ids": ["F2"]}]
        },
        "conflicting categorical fact": {
            "claims": [{"claim_type": "fact", "text": "The trend lifecycle was emerging.", "evidence_ids": ["F4"]}]
        },
        "duplicate contradictory claims": {
            "claims": [
                {"claim_type": "fact", "text": "The trend lifecycle was fading.", "evidence_ids": ["F4"]},
                {"claim_type": "fact", "text": "The trend lifecycle was emerging.", "evidence_ids": ["F4"]},
            ]
        },
        "recommendation phrased as observation": {
            "claims": [{"claim_type": "recommendation", "text": "Published posts were strong.", "evidence_ids": ["F1"]}]
        },
        "required fact omitted": {
            "claims": [{"claim_type": "limitation", "text": "Reach is unavailable.", "evidence_ids": ["U1"]}]
        },
        "empty evidence ids": {
            "claims": [{"claim_type": "fact", "text": "Published posts were 4.", "evidence_ids": []}]
        },
        "unavailable metric asserted through known citation": {
            "claims": [{"claim_type": "fact", "text": "Reach improved after 4 posts.", "evidence_ids": ["F1"]}]
        },
    }
    for label, payload in invalid_cases.items():
        result = validate_claim_ledger_payload(
            payload,
            ledger,
            required_evidence_ids=["F1", "F2"] if label == "required fact omitted" else [],
        )
        assert result.valid is False, label


def test_claim_ledger_multilingual_claim_metadata_remains_canonical():
    ledger = build_evidence_ledger(
        facts={"F1": 4, "F2": 0.22},
        unavailable={"U1": "reach"},
        immutable_numbers={"F2": 0.22},
    )
    french_payload = {
        "claims": [
            {"claim_type": "fact", "text": "Quatre publications ont été publiées.", "evidence_ids": ["F1"]},
            {"claim_type": "fact", "text": "Le momentum est de 22%.", "evidence_ids": ["F2"]},
            {"claim_type": "limitation", "text": "La portée est indisponible.", "evidence_ids": ["U1"]},
        ]
    }
    russian_payload = {
        "claims": [
            {"claim_type": "fact", "text": "Опубликовано 4 публикации.", "evidence_ids": ["F1"]},
            {"claim_type": "fact", "text": "Momentum составляет 22%.", "evidence_ids": ["F2"]},
            {"claim_type": "limitation", "text": "Данные о reach недоступны.", "evidence_ids": ["U1"]},
        ]
    }

    assert validate_claim_ledger_payload(french_payload, ledger).valid is True
    assert validate_claim_ledger_payload(russian_payload, ledger).valid is True


def _claim_ledger_v2_fixture() -> EvidenceLedgerV2:
    return EvidenceLedgerV2(
        sources=(
            EvidenceSourceV2(
                id="F1",
                subject="content_performance",
                predicate="published_posts",
                value=4,
                value_type="count",
            ),
            EvidenceSourceV2(
                id="F2",
                subject="trend",
                predicate="momentum",
                value=0.22,
                value_type="percentage",
                display_value="22%",
                polarity="positive",
            ),
            EvidenceSourceV2(
                id="F3",
                subject="trend",
                predicate="lifecycle",
                value="fading",
                value_type="enum",
            ),
            EvidenceSourceV2(
                id="F4",
                subject="competitor_a",
                predicate="competitor_posts",
                value=8,
                value_type="count",
            ),
            EvidenceSourceV2(
                id="F5",
                subject="competitor_b",
                predicate="competitor_posts",
                value=3,
                value_type="count",
            ),
            EvidenceSourceV2(
                id="U1",
                subject="content_performance",
                predicate="reach",
                status="unavailable",
            ),
        )
    )


def test_claim_ledger_v2_schema_separates_known_and_unavailable_ids():
    ledger = _claim_ledger_v2_fixture()
    schema = claim_ledger_v2_response_format(ledger)["json_schema"]["schema"]

    fact_enum = schema["properties"]["facts"]["items"]["properties"]["evidence_id"]["enum"]
    limitation_enum = schema["properties"]["limitations"]["items"]["properties"]["evidence_id"]["enum"]
    comparison_left_enum = schema["properties"]["comparisons"]["items"]["properties"]["left_evidence_id"]["enum"]

    assert "F1" in fact_enum
    assert "U1" not in fact_enum
    assert limitation_enum == ["U1"]
    assert "F4" in comparison_left_enum
    assert "U1" not in comparison_left_enum


def test_claim_ledger_v2_renders_authoritative_facts_without_model_text():
    ledger = _claim_ledger_v2_fixture()
    payload = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}, {"evidence_id": "F3"}],
        "limitations": [{"evidence_id": "U1"}],
        "comparisons": [],
        "recommendations": [],
    }

    result = validate_claim_ledger_v2_payload(
        payload,
        ledger,
        required_evidence_ids=["F1", "F2", "U1"],
        critical_evidence_ids=["F2", "U1"],
    )
    rendered = render_claim_ledger_v2(
        payload,
        ledger,
        required_evidence_ids=["F1", "F2", "U1"],
        critical_evidence_ids=["F2", "U1"],
    )

    assert result.valid is True
    assert "4 posts were published." in rendered
    assert "Momentum is 22%." in rendered
    assert "The trend lifecycle is fading." in rendered
    assert "Reach data is unavailable." in rendered
    assert "45%" not in rendered
    assert "emerging" not in rendered


def test_claim_ledger_v2_validates_relations_and_rejects_false_comparisons():
    ledger = _claim_ledger_v2_fixture()
    valid_payload = {
        "facts": [{"evidence_id": "F4"}, {"evidence_id": "F5"}],
        "limitations": [],
        "comparisons": [{"left_evidence_id": "F4", "operator": "greater_than", "right_evidence_id": "F5"}],
        "recommendations": [],
    }
    invalid_payload = {
        "facts": [{"evidence_id": "F4"}, {"evidence_id": "F5"}],
        "limitations": [],
        "comparisons": [{"left_evidence_id": "F5", "operator": "greater_than", "right_evidence_id": "F4"}],
        "recommendations": [],
    }

    assert validate_claim_ledger_v2_payload(valid_payload, ledger).valid is True
    invalid = validate_claim_ledger_v2_payload(invalid_payload, ledger)
    assert invalid.valid is False
    assert any("comparison is not true" in error for error in invalid.errors)


def test_claim_ledger_v2_rejects_cross_predicate_comparisons():
    ledger = _claim_ledger_v2_fixture()
    payload = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [],
        "comparisons": [{"left_evidence_id": "F1", "operator": "greater_than", "right_evidence_id": "F2"}],
        "recommendations": [],
    }

    result = validate_claim_ledger_v2_payload(payload, ledger)

    assert result.valid is False
    assert any("comparison is not true" in error for error in result.errors)


def test_claim_ledger_v2_rejects_required_omission_and_unsafe_recommendation():
    ledger = _claim_ledger_v2_fixture()
    payload = {
        "facts": [{"evidence_id": "F1"}],
        "limitations": [],
        "comparisons": [],
        "recommendations": [{"action": "Say reach improved by 45%.", "rationale_evidence_ids": ["F1"]}],
    }

    result = validate_claim_ledger_v2_payload(
        payload,
        ledger,
        required_evidence_ids=["F1", "F2", "U1"],
        critical_evidence_ids=["U1"],
    )

    assert result.valid is False
    assert any("action must not contain numeric values" in error for error in result.errors)
    assert any("action asserts unsupported metric state" in error for error in result.errors)
    assert any("required evidence not selected" in error for error in result.errors)
    assert any("critical evidence not selected" in error for error in result.errors)


def test_claim_ledger_v2_localizes_facts_and_limitations():
    ledger = _claim_ledger_v2_fixture()
    payload = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [{"evidence_id": "U1"}],
        "comparisons": [],
        "recommendations": [],
    }

    french = render_claim_ledger_v2(payload, ledger, language="fr")
    russian = render_claim_ledger_v2(payload, ledger, language="ru")

    assert "4 publications ont été publiées." in french
    assert "Le momentum est de 22%." in french
    assert "Les données de portée ne sont pas disponibles." in french
    assert "Было опубликовано 4 публикации." in russian
    assert "Momentum составляет 22%." in russian
    assert "Данные по охвату недоступны." in russian


def test_claim_ledger_v2_uses_trusted_relation_affordances():
    ledger = EvidenceLedgerV2(
        sources=(
            EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count"),
            EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count"),
            EvidenceSourceV2(id="U1", subject="content_performance", predicate="engagement", status="unavailable"),
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
    )
    payload = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [{"evidence_id": "U1"}],
        "comparisons": [{"relation_id": "R1"}],
        "recommendations": [],
    }

    schema = claim_ledger_v2_response_format(ledger)["json_schema"]["schema"]
    comparison_schema = schema["properties"]["comparisons"]["items"]["oneOf"][0]
    result = validate_claim_ledger_v2_payload(payload, ledger, required_evidence_ids=["F1", "F2", "U1"])
    rendered = render_claim_ledger_v2(payload, ledger)

    assert comparison_schema["properties"]["relation_id"]["enum"] == ["R1"]
    assert "left_evidence_id" not in comparison_schema["properties"]
    assert result.valid is True
    assert "Competitor A is greater than Competitor B for posts: 8 versus 3." in rendered
    assert "Engagement data is unavailable." in rendered


def test_claim_ledger_v2_rejects_invented_or_expanded_relations_when_affordances_exist():
    ledger = EvidenceLedgerV2(
        sources=(
            EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count"),
            EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count"),
            EvidenceSourceV2(id="U1", subject="content_performance", predicate="engagement", status="unavailable"),
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
    )
    invented_relation = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [{"evidence_id": "U1"}],
        "comparisons": [{"relation_id": "R99"}],
        "recommendations": [],
    }
    expanded_relation = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [{"evidence_id": "U1"}],
        "comparisons": [{"left_evidence_id": "F1", "operator": "greater_than", "right_evidence_id": "F2"}],
        "recommendations": [],
    }

    invented = validate_claim_ledger_v2_payload(invented_relation, ledger)
    expanded = validate_claim_ledger_v2_payload(expanded_relation, ledger)

    assert invented.valid is False
    assert any("relation_id must reference a trusted relation" in error for error in invented.errors)
    assert expanded.valid is False
    assert any("relation_id is required when trusted relations are supplied" in error for error in expanded.errors)


def test_claim_ledger_v2_rejects_invalid_trusted_relation_definition():
    ledger = EvidenceLedgerV2(
        sources=(
            EvidenceSourceV2(id="F1", subject="competitor_a", predicate="competitor_posts", value=8, value_type="count"),
            EvidenceSourceV2(id="F2", subject="competitor_b", predicate="competitor_posts", value=3, value_type="count"),
        ),
        relations=(
            EvidenceRelationV2(
                id="R1",
                left_evidence_id="F2",
                operator="greater_than",
                right_evidence_id="F1",
                predicate="competitor_posts",
            ),
        ),
    )
    payload = {
        "facts": [{"evidence_id": "F1"}, {"evidence_id": "F2"}],
        "limitations": [],
        "comparisons": [{"relation_id": "R1"}],
        "recommendations": [],
    }

    result = validate_claim_ledger_v2_payload(payload, ledger)

    assert result.valid is False
    assert any("relation_id references an invalid trusted relation" in error for error in result.errors)


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
