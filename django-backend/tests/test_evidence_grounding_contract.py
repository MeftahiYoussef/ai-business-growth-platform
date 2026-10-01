from __future__ import annotations

from decimal import Decimal

import pytest

from apps.ai.contracts.evidence_grounding import (
    EVIDENCE_GROUNDING_CONTRACT_VERSION,
    ClaimSelections,
    Evidence,
    EvidenceLedger,
    EvidenceStatus,
    EvidenceValueType,
    FactSelection,
    LimitationSelection,
    RelationOperator,
    RelationSelection,
    RelationType,
    build_trusted_relation,
    derive_allowlists,
    evidence_grounding_response_format,
    evidence_grounding_selection_schema,
    numeric_representation_matches,
    render_claim_selections,
    validate_claim_selections,
)
from apps.ai.contracts.evidence_grounding.exceptions import (
    EvidenceGroundingContractError,
    EvidenceGroundingErrorCode,
)


def _evidence_a() -> EvidenceLedger:
    return EvidenceLedger(
        evidence=(
            Evidence(
                id="F1",
                subject="content_performance",
                predicate="published_posts",
                value=4,
                value_type=EvidenceValueType.INTEGER,
            ),
            Evidence(
                id="F2",
                subject="trend",
                predicate="momentum",
                value=Decimal("0.22"),
                value_type=EvidenceValueType.PERCENTAGE,
                display_value="22%",
            ),
            Evidence(id="U1", subject="content_performance", predicate="reach", status=EvidenceStatus.UNAVAILABLE),
        )
    )


def _competitor_ledger() -> EvidenceLedger:
    competitor_a = Evidence(
        id="F1",
        subject="competitor_a",
        predicate="competitor_posts",
        value=8,
        value_type=EvidenceValueType.INTEGER,
        unit="posts",
    )
    competitor_b = Evidence(
        id="F2",
        subject="competitor_b",
        predicate="competitor_posts",
        value=3,
        value_type=EvidenceValueType.INTEGER,
        unit="posts",
    )
    relation = build_trusted_relation(
        id="R1",
        left=competitor_a,
        operator=RelationOperator.GREATER_THAN,
        right=competitor_b,
    )
    return EvidenceLedger(
        evidence=(
            competitor_a,
            competitor_b,
            Evidence(id="U1", subject="content_performance", predicate="engagement", status=EvidenceStatus.UNAVAILABLE),
        ),
        relations=(relation,),
    )


def test_evidence_grounding_contract_version_and_allowlists():
    ledger = _evidence_a()
    allowlists = derive_allowlists(ledger)

    assert EVIDENCE_GROUNDING_CONTRACT_VERSION == "evidence_grounding_v1"
    assert allowlists.known_evidence_ids == ("F1", "F2")
    assert allowlists.unavailable_evidence_ids == ("U1",)
    assert allowlists.trusted_relation_ids == ()


def test_numeric_normalization_is_exact_for_percentages_and_numbers():
    momentum = _evidence_a().evidence_by_id["F2"]
    integer = _evidence_a().evidence_by_id["F1"]
    negative = Evidence(
        id="F3",
        subject="trend",
        predicate="momentum",
        value=Decimal("-0.08"),
        value_type=EvidenceValueType.PERCENTAGE,
        display_value="-8%",
    )
    zero = Evidence(id="F4", subject="report", predicate="failure_rate", value=Decimal("0"), value_type=EvidenceValueType.DECIMAL)
    decimal = Evidence(
        id="F5",
        subject="report",
        predicate="failure_rate",
        value=Decimal("0.03"),
        value_type=EvidenceValueType.DECIMAL,
    )

    assert numeric_representation_matches(momentum, "22%")
    assert numeric_representation_matches(momentum, "+22%")
    assert numeric_representation_matches(momentum, Decimal("0.22"))
    assert not numeric_representation_matches(momentum, "23%")
    assert not numeric_representation_matches(momentum, "45%")
    assert numeric_representation_matches(integer, 4)
    assert numeric_representation_matches(negative, "-8%")
    assert numeric_representation_matches(zero, "0")
    assert numeric_representation_matches(decimal, "0.03")


def test_unavailable_evidence_supports_limitation_but_not_fact():
    ledger = _evidence_a()
    valid = validate_claim_selections(ClaimSelections(limitations=(LimitationSelection("U1"),)), ledger)
    invalid = validate_claim_selections(ClaimSelections(facts=(FactSelection("U1"),)), ledger)

    assert valid.valid is True
    assert invalid.valid is False
    assert invalid.errors[0].code == EvidenceGroundingErrorCode.INVALID_FACT_EVIDENCE


def test_selection_schema_disables_relations_when_none_exist():
    schema = evidence_grounding_selection_schema(_evidence_a())

    assert schema["properties"]["facts"]["items"]["properties"]["evidence_id"]["enum"] == ["F1", "F2"]
    assert schema["properties"]["limitations"]["items"]["properties"]["evidence_id"]["enum"] == ["U1"]
    assert schema["properties"]["relations"]["maxItems"] == 0
    assert "operator" not in schema["properties"]["relations"]["items"]["properties"]
    assert evidence_grounding_response_format(_evidence_a())["json_schema"]["name"] == EVIDENCE_GROUNDING_CONTRACT_VERSION


def test_single_and_multiple_relation_schemas_are_request_specific():
    single = _competitor_ledger()
    first = Evidence(id="F1", subject="current_period", predicate="published_posts", value=10, value_type=EvidenceValueType.INTEGER)
    second = Evidence(id="F2", subject="previous_period", predicate="published_posts", value=6, value_type=EvidenceValueType.INTEGER)
    third = Evidence(id="F3", subject="competitor_a", predicate="published_posts", value=4, value_type=EvidenceValueType.INTEGER)
    multi = EvidenceLedger(
        evidence=(first, second, third),
        relations=(
            build_trusted_relation(id="R1", left=first, operator=RelationOperator.GREATER_THAN, right=second),
            build_trusted_relation(id="R2", left=first, operator=RelationOperator.GREATER_THAN, right=third),
            build_trusted_relation(id="R3", left=second, operator=RelationOperator.GREATER_THAN, right=third),
        ),
    )

    single_enum = evidence_grounding_selection_schema(single)["properties"]["relations"]["items"]["properties"]["relation_id"]["enum"]
    multi_enum = evidence_grounding_selection_schema(multi)["properties"]["relations"]["items"]["properties"]["relation_id"]["enum"]

    assert single_enum == ["R1"]
    assert multi_enum == ["R1", "R2", "R3"]


def test_relation_builder_accepts_true_operators_and_rejects_false_relations():
    high = Evidence(id="F1", subject="current_period", predicate="published_posts", value=10, value_type=EvidenceValueType.INTEGER)
    low = Evidence(id="F2", subject="previous_period", predicate="published_posts", value=6, value_type=EvidenceValueType.INTEGER)
    equal_a = Evidence(id="F3", subject="current_period", predicate="published_posts", value=5, value_type=EvidenceValueType.INTEGER)
    equal_b = Evidence(id="F4", subject="previous_period", predicate="published_posts", value=5, value_type=EvidenceValueType.INTEGER)

    assert build_trusted_relation(id="R1", left=high, operator=RelationOperator.GREATER_THAN, right=low).operator == RelationOperator.GREATER_THAN
    assert build_trusted_relation(id="R2", left=low, operator=RelationOperator.LESS_THAN, right=high).operator == RelationOperator.LESS_THAN
    assert build_trusted_relation(id="R3", left=equal_a, operator=RelationOperator.EQUAL, right=equal_b).operator == RelationOperator.EQUAL
    with pytest.raises(EvidenceGroundingContractError):
        build_trusted_relation(id="R4", left=low, operator=RelationOperator.GREATER_THAN, right=high)


def test_relation_builder_rejects_incompatible_operands():
    known = Evidence(id="F1", subject="current_period", predicate="published_posts", value=10, value_type=EvidenceValueType.INTEGER, unit="posts")
    unavailable = Evidence(id="U1", subject="current_period", predicate="published_posts", status=EvidenceStatus.UNAVAILABLE)
    draft_posts = Evidence(id="F2", subject="current_period", predicate="draft_posts", value=5, value_type=EvidenceValueType.INTEGER, unit="posts")
    unit_mismatch = Evidence(id="F3", subject="previous_period", predicate="published_posts", value=5, value_type=EvidenceValueType.INTEGER, unit="items")
    type_mismatch = Evidence(id="F4", subject="previous_period", predicate="published_posts", value="5", value_type=EvidenceValueType.STRING, unit="posts")
    week_1 = Evidence(id="F5", subject="current_period", predicate="published_posts", value=5, value_type=EvidenceValueType.INTEGER, time_window="week_1")
    week_2 = Evidence(id="F6", subject="previous_period", predicate="published_posts", value=4, value_type=EvidenceValueType.INTEGER, time_window="week_2")

    for other in (unavailable, draft_posts, unit_mismatch, type_mismatch, known):
        with pytest.raises(EvidenceGroundingContractError):
            build_trusted_relation(id="RX", left=known, operator=RelationOperator.GREATER_THAN, right=other)
    with pytest.raises(EvidenceGroundingContractError):
        build_trusted_relation(id="RT", left=week_1, operator=RelationOperator.GREATER_THAN, right=week_2)
    temporal = build_trusted_relation(
        id="RT2",
        left=week_1,
        operator=RelationOperator.GREATER_THAN,
        right=week_2,
        relation_type=RelationType.TEMPORAL_COMPARISON,
    )
    assert temporal.relation_type == RelationType.TEMPORAL_COMPARISON


def test_validator_rejects_unknown_relation_and_duplicate_selection():
    ledger = _competitor_ledger()
    result = validate_claim_selections(
        ClaimSelections(
            facts=(FactSelection("F1"), FactSelection("F1")),
            relations=(RelationSelection("R99"),),
        ),
        ledger,
    )

    assert result.valid is False
    assert {error.code for error in result.errors} >= {
        EvidenceGroundingErrorCode.DUPLICATE_SELECTION,
        EvidenceGroundingErrorCode.UNKNOWN_RELATION_ID,
    }


def test_validator_enforces_required_and_critical_evidence_through_relations():
    ledger = _competitor_ledger()
    valid = validate_claim_selections(
        ClaimSelections(relations=(RelationSelection("R1"),), limitations=(LimitationSelection("U1"),)),
        ledger,
        required_evidence_ids=("F1", "F2", "U1"),
        critical_evidence_ids=("U1",),
    )
    invalid = validate_claim_selections(
        ClaimSelections(relations=(RelationSelection("R1"),)),
        ledger,
        required_evidence_ids=("F1", "F2", "U1"),
        critical_evidence_ids=("U1",),
    )

    assert valid.valid is True
    assert invalid.valid is False
    assert EvidenceGroundingErrorCode.MISSING_REQUIRED_EVIDENCE in {error.code for error in invalid.errors}
    assert EvidenceGroundingErrorCode.MISSING_CRITICAL_EVIDENCE in {error.code for error in invalid.errors}


def test_renderer_outputs_deterministic_en_fr_ru_without_semantic_additions():
    selections = ClaimSelections(facts=(FactSelection("F1"), FactSelection("F2")), limitations=(LimitationSelection("U1"),))

    english = render_claim_selections(selections, _evidence_a(), language="en")
    french = render_claim_selections(selections, _evidence_a(), language="fr")
    russian = render_claim_selections(selections, _evidence_a(), language="ru")

    assert english == "4 posts were published. Momentum is 22%. Reach data is unavailable."
    assert french == "4 publications ont été publiées. Le momentum est de 22%. Les données de portée ne sont pas disponibles."
    assert russian == "Было опубликовано 4 публикации. Momentum составляет 22%. Данные по охвату недоступны."
    assert "45%" not in english + french + russian


def test_renderer_preserves_authoritative_relation_direction_and_deduplicates_facts():
    ledger = _competitor_ledger()
    selections = ClaimSelections(
        facts=(FactSelection("F1"), FactSelection("F2")),
        limitations=(LimitationSelection("U1"),),
        relations=(RelationSelection("R1"),),
    )
    rendered = render_claim_selections(selections, ledger)

    assert rendered == "Competitor A is greater than Competitor B for posts: 8 versus 3. Engagement data is unavailable."
    assert rendered.count("Competitor A") == 1
    assert "3 versus 8" not in rendered


def test_renderer_refuses_invalid_selection_instead_of_repairing_it():
    with pytest.raises(EvidenceGroundingContractError):
        render_claim_selections(ClaimSelections(facts=(FactSelection("U1"),)), _evidence_a())


def test_selection_model_cannot_override_authoritative_data():
    ledger = _evidence_a()
    schema = evidence_grounding_selection_schema(ledger)
    fact_properties = schema["properties"]["facts"]["items"]["properties"]
    relation_properties = schema["properties"]["relations"]["items"]["properties"]
    rendered = render_claim_selections(ClaimSelections(facts=(FactSelection("F2"),)), ledger)

    assert set(fact_properties) == {"evidence_id"}
    assert "value" not in fact_properties
    assert "operator" not in relation_properties
    assert rendered == "Momentum is 22%."
