from __future__ import annotations

from decimal import Decimal
from typing import Literal

from .exceptions import EvidenceGroundingContractError
from .models import (
    ClaimSelections,
    Evidence,
    EvidenceLedger,
    EvidenceValueType,
    RelationOperator,
    TrustedRelation,
)
from .validation import validate_claim_selections

SupportedLanguage = Literal["en", "fr", "ru"]


def render_claim_selections(
    selections: ClaimSelections,
    ledger: EvidenceLedger,
    *,
    language: SupportedLanguage = "en",
    required_evidence_ids: tuple[str, ...] = (),
    critical_evidence_ids: tuple[str, ...] = (),
) -> str:
    validation = validate_claim_selections(
        selections,
        ledger,
        required_evidence_ids=required_evidence_ids,
        critical_evidence_ids=critical_evidence_ids,
    )
    if not validation.valid or validation.selections is None:
        raise EvidenceGroundingContractError(validation.errors)

    evidence_by_id = ledger.evidence_by_id
    relation_by_id = ledger.relation_by_id
    relation_covered_ids = {
        evidence_id
        for relation_selection in validation.selections.relations
        for relation in (relation_by_id[relation_selection.relation_id],)
        for evidence_id in (relation.left_evidence_id, relation.right_evidence_id)
    }
    sentences: list[str] = []
    seen_sentences: set[str] = set()

    for fact in validation.selections.facts:
        if fact.evidence_id in relation_covered_ids:
            continue
        _append_sentence(sentences, seen_sentences, _render_fact(evidence_by_id[fact.evidence_id], language))
    for relation_selection in validation.selections.relations:
        relation = relation_by_id[relation_selection.relation_id]
        _append_sentence(sentences, seen_sentences, _render_relation(relation, ledger, language))
    for limitation in validation.selections.limitations:
        _append_sentence(sentences, seen_sentences, _render_limitation(evidence_by_id[limitation.evidence_id], language))
    return " ".join(_ensure_sentence(sentence) for sentence in sentences)


def _append_sentence(sentences: list[str], seen: set[str], sentence: str) -> None:
    normalized = sentence.casefold().strip()
    if normalized in seen:
        return
    seen.add(normalized)
    sentences.append(sentence)


def _render_fact(evidence: Evidence, language: SupportedLanguage) -> str:
    value = _format_value(evidence)
    predicate = evidence.predicate
    subject = _localized_subject(evidence, language)
    if language == "fr":
        if predicate == "published_posts":
            return f"{value} publications ont été publiées"
        if predicate == "momentum":
            return f"Le momentum est de {value}"
        if predicate == "lifecycle":
            return f"Le cycle de vie est {value}"
        if predicate == "competitor_posts":
            return f"{subject} a publié {value} contenus"
        return f"{_localized_predicate(evidence, language)} est {value}"
    if language == "ru":
        if predicate == "published_posts":
            return f"Было опубликовано {value} публикации"
        if predicate == "momentum":
            return f"Momentum составляет {value}"
        if predicate == "lifecycle":
            return f"Стадия тренда: {value}"
        if predicate == "competitor_posts":
            return f"{subject} опубликовал {value} материалов"
        return f"{_localized_predicate(evidence, language)}: {value}"
    if predicate == "published_posts":
        return f"{value} posts were published"
    if predicate == "momentum":
        return f"Momentum is {value}"
    if predicate == "lifecycle":
        return f"The lifecycle is {value}"
    if predicate == "competitor_posts":
        return f"{subject} posted {value} times"
    return f"{_localized_predicate(evidence, language)} is {value}"


def _render_limitation(evidence: Evidence, language: SupportedLanguage) -> str:
    predicate = _localized_predicate(evidence, language)
    if language == "fr":
        return f"Les données de {predicate} ne sont pas disponibles"
    if language == "ru":
        return f"Данные по {predicate} недоступны"
    return f"{predicate.capitalize()} data is unavailable"


def _render_relation(relation: TrustedRelation, ledger: EvidenceLedger, language: SupportedLanguage) -> str:
    evidence_by_id = ledger.evidence_by_id
    left = evidence_by_id[relation.left_evidence_id]
    right = evidence_by_id[relation.right_evidence_id]
    left_label = _localized_subject(left, language)
    right_label = _localized_subject(right, language)
    predicate = _localized_predicate(left, language)
    left_value = _format_value(left)
    right_value = _format_value(right)
    if language == "fr":
        if relation.operator == RelationOperator.GREATER_THAN:
            return f"{left_label} est supérieur à {right_label} pour {predicate}: {left_value} contre {right_value}"
        if relation.operator == RelationOperator.LESS_THAN:
            return f"{left_label} est inférieur à {right_label} pour {predicate}: {left_value} contre {right_value}"
        return f"{left_label} est égal à {right_label} pour {predicate}: {left_value}"
    if language == "ru":
        if relation.operator == RelationOperator.GREATER_THAN:
            return f"{left_label} больше, чем {right_label}, по показателю {predicate}: {left_value} против {right_value}"
        if relation.operator == RelationOperator.LESS_THAN:
            return f"{left_label} меньше, чем {right_label}, по показателю {predicate}: {left_value} против {right_value}"
        return f"{left_label} равен {right_label} по показателю {predicate}: {left_value}"
    if relation.operator == RelationOperator.GREATER_THAN:
        return f"{left_label} is greater than {right_label} for {predicate}: {left_value} versus {right_value}"
    if relation.operator == RelationOperator.LESS_THAN:
        return f"{left_label} is less than {right_label} for {predicate}: {left_value} versus {right_value}"
    return f"{left_label} equals {right_label} for {predicate}: {left_value}"


def _format_value(evidence: Evidence) -> str:
    if evidence.display_value:
        return evidence.display_value
    if evidence.value is None:
        return "unavailable"
    if evidence.value_type == EvidenceValueType.PERCENTAGE and isinstance(evidence.value, int | Decimal):
        return f"{Decimal(str(evidence.value)) * Decimal('100'):g}%"
    return str(evidence.value)


def _localized_subject(evidence: Evidence, language: SupportedLanguage) -> str:
    labels = {
        "competitor_a": {"en": "Competitor A", "fr": "Le concurrent A", "ru": "Конкурент A"},
        "competitor_b": {"en": "Competitor B", "fr": "Le concurrent B", "ru": "Конкурент B"},
        "current_period": {"en": "current period", "fr": "la période actuelle", "ru": "текущий период"},
        "previous_period": {"en": "previous period", "fr": "la période précédente", "ru": "предыдущий период"},
        "trend": {"en": "the trend", "fr": "la tendance", "ru": "тренд"},
        "content_performance": {"en": "content performance", "fr": "la performance du contenu", "ru": "эффективность контента"},
        "report": {"en": "the report", "fr": "le rapport", "ru": "отчет"},
    }
    return labels.get(evidence.subject, {}).get(language, evidence.subject.replace("_", " "))


def _localized_predicate(evidence: Evidence, language: SupportedLanguage) -> str:
    labels = {
        "published_posts": {"en": "published posts", "fr": "publications publiées", "ru": "опубликованным публикациям"},
        "momentum": {"en": "momentum", "fr": "momentum", "ru": "momentum"},
        "lifecycle": {"en": "lifecycle", "fr": "cycle de vie", "ru": "стадии"},
        "reach": {"en": "reach", "fr": "portée", "ru": "охвату"},
        "engagement": {"en": "engagement", "fr": "engagement", "ru": "вовлеченности"},
        "future_peak": {"en": "future peak", "fr": "prochain pic", "ru": "будущему пику"},
        "competitor_posts": {"en": "posts", "fr": "publications", "ru": "публикациям"},
    }
    return labels.get(evidence.predicate, {}).get(language, evidence.predicate.replace("_", " "))


def _ensure_sentence(text: str) -> str:
    return text if text.endswith((".", "!", "?")) else f"{text}."
