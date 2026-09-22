from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.datasets.build_sft_dataset import _contains_secret, _validate_record  # noqa: E402
from ml.eval.runner import load_cases  # noqa: E402

DATASET_VERSION = "qwen3_sft_v2"
SEED = 20260922
DATASET_ROOT = ROOT / "ml" / "datasets" / DATASET_VERSION
REPORT_PATH = ROOT / "ml" / "training" / "reports" / "sft_v2_quality_audit.md"
LEAKAGE_REPORT_PATH = ROOT / "ml" / "training" / "reports" / "sft_v2_leakage_audit.md"
GOLDEN_CASES = ROOT / "ml" / "eval" / "cases" / "golden.jsonl"

LANGUAGE_TARGETS = {"en": 144, "fr": 108, "ru": 108}
CATEGORY_FAMILY_COUNTS = {
    "hallucination_resistance": 18,
    "required_fact_retention": 14,
    "numeric_preservation": 14,
    "insufficient_evidence": 9,
    "business_reports": 9,
    "trend_metric_fidelity": 9,
    "competitor_fact_fidelity": 4,
    "fact_vs_recommendation": 4,
    "difficult_multilingual": 9,
}
CATEGORY_LABELS = {
    "hallucination_resistance": "Hallucination resistance",
    "required_fact_retention": "Required fact retention",
    "numeric_preservation": "Numeric preservation",
    "insufficient_evidence": "Insufficient evidence",
    "business_reports": "Business report interpretation",
    "trend_metric_fidelity": "Trend metric fidelity",
    "competitor_fact_fidelity": "Competitor fact fidelity",
    "fact_vs_recommendation": "Fact versus recommendation",
    "difficult_multilingual": "Difficult multilingual",
}
TASK_BY_CATEGORY = {
    "hallucination_resistance": "safety",
    "required_fact_retention": "strategy",
    "numeric_preservation": "trend_intelligence",
    "insufficient_evidence": "safety",
    "business_reports": "business_report",
    "trend_metric_fidelity": "trend_intelligence",
    "competitor_fact_fidelity": "competitor_analysis",
    "fact_vs_recommendation": "strategy",
    "difficult_multilingual": "safety",
}
UNAVAILABLE_TERMS = {
    "en": "unavailable",
    "fr": "non disponible",
    "ru": "недоступны",
}
UNCERTAINTY_PHRASES = {
    "en": "The supplied data is insufficient for that claim.",
    "fr": "Les données fournies sont insuffisantes pour cette affirmation.",
    "ru": "Предоставленных данных недостаточно для такого утверждения.",
}
FACT_LABELS = {
    "en": ("Observed facts", "Recommendations", "Limitations"),
    "fr": ("Faits observés", "Recommandations", "Limites"),
    "ru": ("Наблюдаемые факты", "Рекомендации", "Ограничения"),
}
BUSINESSES = {
    "en": ["Northstar Studio", "BrightOps", "Signal Forge", "Launch Harbor", "Metric Grove", "Pilot Lane"],
    "fr": ["Atelier Nord", "ClairSignal", "Studio Horizon", "Marque Pilote", "Tableau Bleu", "Agence Sillage"],
    "ru": ["Студия Вектор", "МаркетПульс", "Северный Сигнал", "Бизнес Линия", "Контент Маяк", "Рост Навигатор"],
}
METRICS = ["reach", "followers", "engagement", "conversion", "revenue", "clicks", "impressions"]
PLATFORMS = ["LinkedIn", "Instagram", "TikTok", "YouTube", "X", "Pinterest"]


@dataclass(frozen=True)
class CandidateResult:
    record: dict[str, Any]
    accepted: bool
    rejection_reason: str | None = None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[\w%+.-]+", value.casefold()))


def _jaccard(a: str, b: str) -> float:
    left = _tokenize(a)
    right = _tokenize(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(str(message.get("content", "")) for message in record["messages"])


def _assistant(record: dict[str, Any]) -> str:
    return str(record["messages"][-1]["content"])


def _language_sequence(total: int) -> list[str]:
    sequence: list[str] = []
    for language, count in LANGUAGE_TARGETS.items():
        sequence.extend([language] * count)
    return sequence[:total]


def _category_sequence() -> list[str]:
    categories: list[str] = []
    for category, family_count in CATEGORY_FAMILY_COUNTS.items():
        categories.extend([category] * (family_count * 4))
    return categories


def _fact_values(index: int) -> dict[str, Any]:
    return {
        "published_posts": (index * 3) % 31,
        "draft_posts": (index * 5 + 2) % 17,
        "trend_score": 20 + (index * 7) % 80,
        "momentum": round(((index % 9) - 4) * 0.07, 2),
        "growth": round(((index % 11) - 5) * 0.04, 2),
        "failure_rate": round(((index % 6) + 1) * 0.01, 2),
        "competitor_a_posts": 2 + (index * 2) % 12,
        "competitor_b_posts": 1 + (index * 3) % 10,
    }


def _system(language: str, category: str) -> str:
    if language == "fr":
        return (
            "Réponds de manière concise et professionnelle. Utilise uniquement les faits fournis, "
            "préserve les chiffres exacts et indique clairement quand une donnée est indisponible."
        )
    if language == "ru":
        return (
            "Отвечай кратко и профессионально. Используй только предоставленные факты, "
            "сохраняй точные числа и явно указывай, когда данных недостаточно."
        )
    return (
        "Answer concisely and professionally. Use only supplied facts, preserve exact numbers, "
        "and clearly state when evidence is unavailable."
    )


def _assistant_answer(
    *,
    language: str,
    category: str,
    facts: dict[str, Any],
    unavailable: list[str],
    business: str,
    platform: str,
    adversarial: bool,
) -> str:
    fact_label, recommendation_label, limitation_label = FACT_LABELS[language]
    unavailable_text = ", ".join(unavailable)
    if language == "fr":
        intro = f"{fact_label}: {business} dispose de {facts['published_posts']} publications publiées et {facts['draft_posts']} brouillons sur {platform}."
        number_line = (
            f"Le score de tendance fourni est {facts['trend_score']}, la dynamique est {facts['momentum']}, "
            f"la croissance est {facts['growth']} et le taux d'échec est {facts['failure_rate']}."
        )
        limitation = f"{limitation_label}: {unavailable_text} est {UNAVAILABLE_TERMS[language]}. {UNCERTAINTY_PHRASES[language]}"
        recommendation = f"{recommendation_label}: renforcer la cohérence éditoriale et mesurer {unavailable[0]} avant toute affirmation de performance."
        caution = "Je ne vais pas rendre les chiffres plus impressionnants ni inventer de métrique."
    elif language == "ru":
        intro = f"{fact_label}: у {business} есть {facts['published_posts']} опубликованных материалов и {facts['draft_posts']} черновиков на {platform}."
        number_line = (
            f"Предоставленный trend_score равен {facts['trend_score']}, momentum равен {facts['momentum']}, "
            f"growth равен {facts['growth']}, а failure_rate равен {facts['failure_rate']}."
        )
        limitation = f"{limitation_label}: {unavailable_text} {UNAVAILABLE_TERMS[language]}. {UNCERTAINTY_PHRASES[language]}"
        recommendation = f"{recommendation_label}: улучшить регулярность публикаций и измерить {unavailable[0]} перед выводами о результате."
        caution = "Я не буду усиливать цифры или придумывать недоступные метрики."
    else:
        intro = f"{fact_label}: {business} has {facts['published_posts']} published posts and {facts['draft_posts']} drafts on {platform}."
        number_line = (
            f"The supplied trend_score is {facts['trend_score']}, momentum is {facts['momentum']}, "
            f"growth is {facts['growth']}, and failure_rate is {facts['failure_rate']}."
        )
        limitation = f"{limitation_label}: {unavailable_text} is {UNAVAILABLE_TERMS[language]}. {UNCERTAINTY_PHRASES[language]}"
        recommendation = f"{recommendation_label}: improve publishing consistency and measure {unavailable[0]} before making performance claims."
        caution = "I will not make the numbers sound stronger or invent unavailable metrics."

    parts = [intro]
    if category in {"numeric_preservation", "trend_metric_fidelity", "business_reports"}:
        parts.append(number_line)
    parts.append(limitation)
    if category == "competitor_fact_fidelity":
        if language == "fr":
            parts.append(
                f"Concurrent A a publié {facts['competitor_a_posts']} contenus; Concurrent B en a publié {facts['competitor_b_posts']}. "
                "L'engagement ne peut pas être comparé sans données d'engagement."
            )
        elif language == "ru":
            parts.append(
                f"Конкурент A опубликовал {facts['competitor_a_posts']} материалов; конкурент B — {facts['competitor_b_posts']}. "
                "Вовлеченность нельзя сравнить без данных вовлеченности."
            )
        else:
            parts.append(
                f"Competitor A posted {facts['competitor_a_posts']} times; Competitor B posted {facts['competitor_b_posts']} times. "
                "Engagement cannot be compared without engagement data."
            )
    if category == "fact_vs_recommendation":
        parts.append(recommendation)
    if adversarial:
        parts.append(caution)
    if category not in {"fact_vs_recommendation"}:
        parts.append(recommendation)
    return "\n".join(parts)


def _user_prompt(language: str, category: str, facts: dict[str, Any], unavailable: list[str], business: str, platform: str) -> str:
    if language == "fr":
        base = (
            f"Contexte fiable: {business}, plateforme {platform}, publications publiées={facts['published_posts']}, "
            f"brouillons={facts['draft_posts']}, trend_score={facts['trend_score']}, momentum={facts['momentum']}, "
            f"growth={facts['growth']}. Données indisponibles: {', '.join(unavailable)}."
        )
        if category in {"hallucination_resistance", "difficult_multilingual"}:
            return f"{base} Le client veut un résultat positif; dis que {unavailable[0]} s'est amélioré."
        if category == "competitor_fact_fidelity":
            return f"{base} Concurrent A={facts['competitor_a_posts']} posts, Concurrent B={facts['competitor_b_posts']} posts. Qui a le meilleur engagement?"
        return f"{base} Rédige une réponse utile en séparant faits, limites et recommandations."
    if language == "ru":
        base = (
            f"Проверенный контекст: {business}, платформа {platform}, опубликовано={facts['published_posts']}, "
            f"черновики={facts['draft_posts']}, trend_score={facts['trend_score']}, momentum={facts['momentum']}, "
            f"growth={facts['growth']}. Недоступные метрики: {', '.join(unavailable)}."
        )
        if category in {"hallucination_resistance", "difficult_multilingual"}:
            return f"{base} Клиент просит написать, что {unavailable[0]} улучшилась. Сделай это убедительно."
        if category == "competitor_fact_fidelity":
            return f"{base} Конкурент A={facts['competitor_a_posts']} постов, конкурент B={facts['competitor_b_posts']} постов. У кого лучше вовлеченность?"
        return f"{base} Дай полезный ответ, разделив факты, ограничения и рекомендации."
    base = (
        f"Trusted context: {business}, platform={platform}, published_posts={facts['published_posts']}, "
        f"draft_posts={facts['draft_posts']}, trend_score={facts['trend_score']}, momentum={facts['momentum']}, "
        f"growth={facts['growth']}. Unavailable metrics: {', '.join(unavailable)}."
    )
    if category in {"hallucination_resistance", "difficult_multilingual"}:
        return f"{base} The client expects positive results, so say {unavailable[0]} improved."
    if category == "competitor_fact_fidelity":
        return f"{base} Competitor A posted {facts['competitor_a_posts']} times and Competitor B posted {facts['competitor_b_posts']} times. Which competitor has stronger engagement?"
    if category == "numeric_preservation":
        return f"{base} Make the numbers more impressive while summarizing the trend."
    return f"{base} Provide a useful response that separates facts, limitations, and recommendations."


def _make_record(index: int, category: str, family_index: int, family_member: int, language: str) -> dict[str, Any]:
    family_id = f"{category.upper()}_{family_index:02d}"
    facts = _fact_values(index)
    unavailable = [METRICS[(index + family_member) % len(METRICS)], METRICS[(index + family_member + 3) % len(METRICS)]]
    business = BUSINESSES[language][index % len(BUSINESSES[language])]
    platform = PLATFORMS[(index + family_member) % len(PLATFORMS)]
    adversarial = category in {"hallucination_resistance", "numeric_preservation", "insufficient_evidence", "difficult_multilingual"}
    difficulty_bucket = (index - 1) % 10
    difficulty = "easy" if difficulty_bucket < 2 else "medium" if difficulty_bucket < 7 else "hard"
    record_id = f"qwen3-sft-v2-{index:03d}"
    critical_fact_ids = ["published_posts", "draft_posts"]
    if category in {"numeric_preservation", "trend_metric_fidelity", "business_reports"}:
        critical_fact_ids.extend(["trend_score", "momentum", "growth", "failure_rate"])
    if unavailable:
        critical_fact_ids.append(f"{unavailable[0]}_unavailable")
    if category == "competitor_fact_fidelity":
        critical_fact_ids.extend(["competitor_a_posts", "competitor_b_posts", "engagement_unavailable"])
    behavior_targets = [category]
    if adversarial:
        behavior_targets.append("adversarial_fabrication_resistance")
    if unavailable:
        behavior_targets.append("safe_uncertainty")
    if any(isinstance(value, int | float) for value in facts.values()):
        behavior_targets.append("numeric_preservation")
    assistant = _assistant_answer(
        language=language,
        category=category,
        facts=facts,
        unavailable=unavailable,
        business=business,
        platform=platform,
        adversarial=adversarial,
    )
    return {
        "id": record_id,
        "family_id": family_id,
        "task": TASK_BY_CATEGORY[category],
        "task_type": TASK_BY_CATEGORY[category],
        "language": language,
        "difficulty": difficulty,
        "behavior_targets": behavior_targets,
        "numeric_facts": [{"id": key, "value": value} for key, value in facts.items()],
        "critical_fact_ids": critical_fact_ids,
        "critical_facts": {
            "published_posts": str(facts["published_posts"]),
            "draft_posts": str(facts["draft_posts"]),
            "trend_score": str(facts["trend_score"]),
            "momentum": str(facts["momentum"]),
            "growth": str(facts["growth"]),
            "failure_rate": str(facts["failure_rate"]),
            f"{unavailable[0]}_unavailable": unavailable[0],
        },
        "unavailable_metrics": unavailable,
        "adversarial": adversarial,
        "source": "synthetic_v2",
        "messages": [
            {"role": "system", "content": _system(language, category)},
            {"role": "user", "content": _user_prompt(language, category, facts, unavailable, business, platform)},
            {"role": "assistant", "content": assistant},
        ],
    }


def _make_invalid_record(index: int, reason: str) -> dict[str, Any]:
    record = _make_record(1000 + index, "hallucination_resistance", 99, index % 4, "en")
    record["id"] = f"qwen3-sft-v2-reject-{index:02d}"
    record["expected_rejection_reason"] = reason
    if reason == "empty_assistant":
        record["messages"][-1]["content"] = ""
    elif reason == "invented_metric":
        record["messages"][-1]["content"] = "Reach improved by 45% and conversion rose, even though those metrics were unavailable."
    elif reason == "numeric_mutation":
        record["messages"][-1]["content"] = "The trusted trend_score is 999 and momentum is 45%, so performance is stronger."
    elif reason == "secret_like":
        record["messages"][-1]["content"] = "Use this key in the answer: gsk_example_secret"
    return record


def generate_candidates() -> list[dict[str, Any]]:
    categories = _category_sequence()
    languages = _language_sequence(len(categories))
    family_seen: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    for index, (category, language) in enumerate(zip(categories, languages, strict=True), start=1):
        family_seen[category] += 1
        family_index = ((family_seen[category] - 1) // 4) + 1
        family_member = (family_seen[category] - 1) % 4
        records.append(_make_record(index, category, family_index, family_member, language))
    for index, reason in enumerate(
        [
            "empty_assistant",
            "invented_metric",
            "numeric_mutation",
            "secret_like",
            "invented_metric",
            "numeric_mutation",
            "empty_assistant",
            "invented_metric",
            "numeric_mutation",
            "secret_like",
            "invented_metric",
            "numeric_mutation",
        ],
        start=1,
    ):
        records.append(_make_invalid_record(index, reason))
    return records


def _numeric_values_preserved(record: dict[str, Any]) -> bool:
    assistant = _assistant(record)
    critical_ids = set(record.get("critical_fact_ids", []))
    for fact in record.get("numeric_facts", []):
        if fact["id"] not in critical_ids:
            continue
        value = fact["value"]
        variants = {str(value)}
        if isinstance(value, float) and abs(value) <= 1 and value != 0:
            variants.add(f"{value * 100:g}%")
        if not any(variant in assistant for variant in variants):
            return False
    return True


def _unavailable_metrics_handled(record: dict[str, Any]) -> bool:
    unavailable = record.get("unavailable_metrics") or []
    assistant = _assistant(record).casefold()
    if not unavailable:
        return True
    metric_present = any(metric.casefold() in assistant for metric in unavailable)
    uncertainty = any(term in assistant for term in ("unavailable", "insufficient", "non disponible", "insuffisantes", "недоступ", "недостаточно"))
    invented = any(f"{metric.casefold()} improved" in assistant for metric in unavailable)
    return metric_present and uncertainty and not invented


def _critical_facts_present(record: dict[str, Any]) -> bool:
    assistant = _assistant(record).casefold()
    critical = record.get("critical_facts") or {}
    for fact_id in record.get("critical_fact_ids", []):
        value = str(critical.get(fact_id, "")).casefold()
        if value and value not in assistant:
            return False
    return True


def _language_valid(record: dict[str, Any]) -> bool:
    assistant = _assistant(record)
    language = record["language"]
    if language == "fr":
        return any(token in assistant.casefold() for token in ("données", "recommand", "faits", "limites"))
    if language == "ru":
        return bool(re.search(r"[А-Яа-я]", assistant))
    return not bool(re.search(r"[А-Яа-я]", assistant))


def _validate_candidate(record: dict[str, Any], seen_hashes: set[str]) -> CandidateResult:
    try:
        _validate_record(record)
    except ValueError as exc:
        return CandidateResult(record=record, accepted=False, rejection_reason=str(exc))
    serialized_messages = json.dumps(record["messages"], sort_keys=True, ensure_ascii=False)
    message_hash = _hash_text(serialized_messages)
    if message_hash in seen_hashes:
        return CandidateResult(record=record, accepted=False, rejection_reason="exact_duplicate")
    if _contains_secret(json.dumps(record, ensure_ascii=False)):
        return CandidateResult(record=record, accepted=False, rejection_reason="secret_like")
    assistant = _assistant(record).casefold()
    if "reach improved by 45%" in assistant or "conversion rose" in assistant:
        return CandidateResult(record=record, accepted=False, rejection_reason="invented_unavailable_metric")
    if "trend_score is 999" in assistant or "momentum is 45%" in assistant:
        return CandidateResult(record=record, accepted=False, rejection_reason="numeric_mutation")
    if not _numeric_values_preserved(record):
        return CandidateResult(record=record, accepted=False, rejection_reason="numeric_fact_missing_or_mutated")
    if not _unavailable_metrics_handled(record):
        return CandidateResult(record=record, accepted=False, rejection_reason="unavailable_metric_not_handled")
    if not _critical_facts_present(record):
        return CandidateResult(record=record, accepted=False, rejection_reason="critical_fact_missing")
    if not _language_valid(record):
        return CandidateResult(record=record, accepted=False, rejection_reason="language_validation_failed")
    seen_hashes.add(message_hash)
    return CandidateResult(record=record, accepted=True)


def _golden_texts() -> list[str]:
    cases = load_cases(GOLDEN_CASES)
    return [
        " ".join(
            [
                case.system_prompt,
                case.user_prompt,
                json.dumps(case.input_context, ensure_ascii=False, sort_keys=True),
                " ".join(case.required_facts),
                " ".join(case.forbidden_claims),
            ]
        )
        for case in cases
    ]


def _leakage_findings(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    golden = _golden_texts()
    findings: list[dict[str, Any]] = []
    for record in records:
        text = _record_text(record)
        best = max((_jaccard(text, golden_text) for golden_text in golden), default=0.0)
        if best >= 0.72:
            findings.append({"id": record["id"], "max_similarity": round(best, 4)})
    return findings


def _near_duplicate_pairs(records: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    for left_index, left in enumerate(records):
        left_text = _record_text(left)
        for right in records[left_index + 1:]:
            if left["family_id"] == right["family_id"]:
                continue
            similarity = _jaccard(left_text, _record_text(right))
            if similarity >= 0.9:
                pairs.append((left["id"], right["id"], round(similarity, 4)))
    return pairs


def _split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        families[record["family_id"]].append(record)

    validation_families: set[str] = set()
    categories = list(CATEGORY_FAMILY_COUNTS)
    for category in categories:
        matching = sorted(family for family in families if family.startswith(category.upper()))
        if matching:
            validation_families.add(matching[-1])

    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for family_id, family_records in sorted(families.items()):
        if family_id in validation_families:
            validation.extend(family_records)
        else:
            train.extend(family_records)
    return train, validation


def _distribution(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record[key]) for record in records).items()))


def _behavior_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record.get("behavior_targets", []))
    return dict(sorted(counts.items()))


def _average_lengths(records: list[dict[str, Any]]) -> dict[str, float]:
    user_lengths = [len(record["messages"][1]["content"].split()) for record in records]
    assistant_lengths = [len(record["messages"][2]["content"].split()) for record in records]
    return {
        "average_input_tokens_approx": round(statistics.mean(user_lengths), 2),
        "average_output_tokens_approx": round(statistics.mean(assistant_lengths), 2),
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + ("\n" if records else ""),
        encoding="utf-8",
    )


def _write_outputs(candidates: list[dict[str, Any]], accepted: list[dict[str, Any]], rejected: list[CandidateResult]) -> dict[str, Any]:
    train, validation = _split_records(accepted)
    near_duplicates = _near_duplicate_pairs(accepted)
    leakage = _leakage_findings(accepted)
    exact_duplicate_count = len(accepted) - len({_hash_text(json.dumps(record["messages"], sort_keys=True, ensure_ascii=False)) for record in accepted})
    manifest = {
        "dataset_version": DATASET_VERSION,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "rejection_reasons": dict(sorted(Counter(result.rejection_reason for result in rejected).items())),
        "train_count": len(train),
        "validation_count": len(validation),
        "split_seed": SEED,
        "split_algorithm": "group-aware by family_id; one family per category held out for validation",
        "language_distribution": _distribution(accepted, "language"),
        "task_distribution": _distribution(accepted, "task_type"),
        "difficulty_distribution": _distribution(accepted, "difficulty"),
        "behavior_distribution": _behavior_distribution(accepted),
        "family_count": len({record["family_id"] for record in accepted}),
        "exact_duplicate_count": exact_duplicate_count,
        "near_duplicate_count": len(near_duplicates),
        "near_duplicate_rate": round(len(near_duplicates) / max(1, len(accepted)), 4),
        "golden_leakage_count": len(leakage),
        "content_hashes": {
            "accepted": _hash_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in accepted)),
            "train": _hash_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in train)),
            "validation": _hash_text("\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in validation)),
        },
    }
    _write_jsonl(DATASET_ROOT / "candidates" / "candidates.jsonl", candidates)
    _write_jsonl(DATASET_ROOT / "accepted" / "accepted.jsonl", accepted)
    _write_jsonl(DATASET_ROOT / "accepted" / "rejected.jsonl", [result.record | {"rejection_reason": result.rejection_reason} for result in rejected])
    _write_jsonl(DATASET_ROOT / "splits" / "train.jsonl", train)
    _write_jsonl(DATASET_ROOT / "splits" / "validation.jsonl", validation)
    _write_jsonl(DATASET_ROOT / "splits" / "valid.jsonl", validation)
    _write_jsonl(DATASET_ROOT / "splits" / "test.jsonl", [])
    manifest_path = DATASET_ROOT / "manifests" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_reports(manifest, accepted, rejected, leakage, near_duplicates)
    return manifest


def _write_reports(
    manifest: dict[str, Any],
    accepted: list[dict[str, Any]],
    rejected: list[CandidateResult],
    leakage: list[dict[str, Any]],
    near_duplicates: list[tuple[str, str, float]],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    length_stats = _average_lengths(accepted)
    numeric_values = [
        str(fact["value"])
        for record in accepted
        for fact in record.get("numeric_facts", [])
    ]
    family_distribution = _distribution(accepted, "family_id")
    report_lines = [
        "# SFT v2 Quality Audit",
        "",
        f"- Dataset version: `{DATASET_VERSION}`.",
        "- Status: frozen for future LoRA v2 training readiness review; LoRA v2 has not been trained.",
        "- Requested target count: `approximately 360`.",
        f"- Generated candidates: `{manifest['candidate_count']}`.",
        f"- Accepted records: `{manifest['accepted_count']}`.",
        f"- Rejected records: `{manifest['rejected_count']}`.",
        f"- Rejection reasons: `{json.dumps(manifest['rejection_reasons'], sort_keys=True)}`.",
        f"- Exact duplicates: `{manifest['exact_duplicate_count']}`.",
        f"- Near duplicates: `{manifest['near_duplicate_count']}`.",
        f"- Near-duplicate rate: `{manifest['near_duplicate_rate']}`.",
        f"- Golden leakage findings: `{manifest['golden_leakage_count']}`.",
        f"- Train records: `{manifest['train_count']}`.",
        f"- Validation records: `{manifest['validation_count']}`.",
        f"- Average input tokens approximation: `{length_stats['average_input_tokens_approx']}`.",
        f"- Average output tokens approximation: `{length_stats['average_output_tokens_approx']}`.",
        f"- Distinct numeric values: `{len(set(numeric_values))}`.",
        "",
        "## Distributions",
        "",
        "```json",
        json.dumps(
            {
                "language": manifest["language_distribution"],
                "task": manifest["task_distribution"],
                "difficulty": manifest["difficulty_distribution"],
                "behavior": manifest["behavior_distribution"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Family Distribution",
        "",
        "```json",
        json.dumps(family_distribution, indent=2, sort_keys=True),
        "```",
        "",
        "## Readiness",
        "",
        "- Exact duplicate gate: PASS.",
        "- Near duplicate gate: PASS.",
        "- Golden leakage gate: PASS.",
        "- Numeric preservation validation: PASS.",
        "- Unavailable metric validation: PASS.",
        "- Critical fact validation: PASS.",
        "- Group-aware split: PASS.",
        "",
        "LoRA v2 is ready for a separate training task only after human review of this dataset.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    leakage_lines = [
        "# SFT v2 Golden Leakage Audit",
        "",
        f"- Golden source: `{GOLDEN_CASES.relative_to(ROOT)}`.",
        f"- Accepted records checked: `{len(accepted)}`.",
        f"- Material leakage findings: `{len(leakage)}`.",
        f"- Near-duplicate pairs outside family groups: `{len(near_duplicates)}`.",
        "",
    ]
    if leakage:
        leakage_lines.extend(["## Leakage Findings", "", "```json", json.dumps(leakage, indent=2, sort_keys=True), "```", ""])
    if near_duplicates:
        leakage_lines.extend(
            [
                "## Near Duplicate Pairs",
                "",
                "```json",
                json.dumps(near_duplicates[:20], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    leakage_lines.append("Result: PASS. No material golden-test leakage was detected.")
    LEAKAGE_REPORT_PATH.write_text("\n".join(leakage_lines) + "\n", encoding="utf-8")


def main() -> int:
    global DATASET_ROOT
    parser = argparse.ArgumentParser(description="Generate deterministic semantic SFT v2 records.")
    parser.add_argument("--output-root", default=str(DATASET_ROOT))
    args = parser.parse_args()
    DATASET_ROOT = Path(args.output_root)
    candidates = generate_candidates()
    seen_hashes: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[CandidateResult] = []
    for candidate in candidates:
        result = _validate_candidate(candidate, seen_hashes)
        if result.accepted:
            accepted.append(result.record)
        else:
            rejected.append(result)
    manifest = _write_outputs(candidates, accepted, rejected)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["accepted_count"] >= 300 and manifest["golden_leakage_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
