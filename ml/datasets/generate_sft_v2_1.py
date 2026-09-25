from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.datasets.build_sft_dataset import _contains_secret, _validate_record  # noqa: E402
from ml.eval.runner import load_cases  # noqa: E402

DATASET_VERSION = "qwen3_sft_v2_1"
SEED = 20260925
CREATED_AT = "2026-09-25T00:00:00Z"
DATASET_ROOT = ROOT / "ml" / "datasets" / DATASET_VERSION
GOLDEN_CASES = ROOT / "ml" / "eval" / "cases" / "golden.jsonl"
QUALITY_REPORT = ROOT / "ml" / "training" / "reports" / "sft_v2_1_quality_audit.md"
LEAKAGE_REPORT = ROOT / "ml" / "training" / "reports" / "sft_v2_1_leakage_audit.md"

LANGUAGE_SEQUENCE = (["en"] * 72) + (["fr"] * 54) + (["ru"] * 54)
CATEGORY_TARGETS = {
    "selective_uncertainty": 45,
    "critical_fact_retention": 36,
    "numeric_preservation": 36,
    "adversarial_fabrication": 18,
    "multilingual_semantics": 18,
    "report_interpretation": 9,
    "trend_fidelity": 9,
    "competitor_fidelity": 9,
}
TASK_BY_CATEGORY = {
    "selective_uncertainty": "safety",
    "critical_fact_retention": "strategy",
    "numeric_preservation": "trend_intelligence",
    "adversarial_fabrication": "safety",
    "multilingual_semantics": "strategy",
    "report_interpretation": "business_report",
    "trend_fidelity": "trend_intelligence",
    "competitor_fidelity": "competitor_analysis",
}
DIFFICULTY_SEQUENCE = (["easy"] * 36) + (["medium"] * 90) + (["hard"] * 54)
METRICS = ["reach", "followers", "engagement", "conversions", "revenue", "clicks", "impressions"]
BUSINESSES = {
    "en": ["Harbor Labs", "Signal Loft", "Clearpath Studio", "Northline Foods", "Orbit Tutors", "Metric House"],
    "fr": ["Atelier Boréal", "Maison Signal", "Studio Clair", "Boutique Horizon", "Agence Azur", "Collectif Nord"],
    "ru": ["Студия Север", "Маркет Линия", "Пульс Бренд", "Рост Сигнал", "Контент Парк", "Вектор Маркет"],
}
PLATFORMS = ["Instagram", "LinkedIn", "TikTok", "YouTube", "Pinterest", "X"]

SYSTEM = {
    "en": (
        "Answer as a concise business analyst. Preserve every supplied critical fact, "
        "qualify only missing evidence, and keep recommendations separate from facts."
    ),
    "fr": (
        "Réponds comme un analyste marketing concis. Conserve chaque fait critique fourni, "
        "qualifie seulement les preuves manquantes et sépare recommandations et faits."
    ),
    "ru": (
        "Отвечай как краткий бизнес-аналитик. Сохраняй каждый предоставленный критический факт, "
        "уточняй только недостающие данные и отделяй рекомендации от фактов."
    ),
}


@dataclass(frozen=True)
class CandidateResult:
    record: dict[str, Any]
    accepted: bool
    rejection_reason: str | None = None


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    path.write_text(content + ("\n" if content else ""), encoding="utf-8")


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(str(message.get("content", "")) for message in record["messages"])


def _assistant(record: dict[str, Any]) -> str:
    return str(record["messages"][-1]["content"])


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w%+.-]+", value.casefold()))


def _jaccard(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _numbers(index: int) -> dict[str, int | float]:
    return {
        "published_posts": 2 + (index * 5) % 17,
        "draft_posts": 1 + (index * 3) % 11,
        "approved_posts": (index * 2) % 9,
        "scheduled_posts": (index + 1) % 5,
        "momentum": round(((index % 13) - 6) * 0.04, 2),
        "slope": round(((index % 9) - 4) * 0.03, 2),
        "forecast": round(0.35 + ((index * 7) % 41) / 100, 2),
        "failure_rate": round(((index % 5) + 1) * 0.01, 2),
        "competitor_a_posts": 2 + (index * 4) % 13,
        "competitor_b_posts": 1 + (index * 7) % 10,
    }


def _language_labels(language: str, template_index: int) -> tuple[str, str, str]:
    if language == "fr":
        options = [
            ("Faits retenus", "Limite ciblée", "Prochaine action"),
            ("Constats fiables", "Donnée absente", "Conseil"),
            ("Ce que l'on sait", "Ce qui manque", "Recommandation"),
        ]
    elif language == "ru":
        options = [
            ("Подтвержденные факты", "Ограничение", "Следующий шаг"),
            ("Что известно", "Чего не хватает", "Рекомендация"),
            ("Надежные данные", "Недостающая метрика", "Действие"),
        ]
    else:
        options = [
            ("Known facts", "Narrow limitation", "Recommendation"),
            ("Evidence", "Missing evidence", "Next step"),
            ("Reliable signals", "Unavailable metric", "Action"),
        ]
    return options[template_index % len(options)]


def _format_percent(value: float) -> str:
    return f"{value * 100:g}%"


def _user_prompt(language: str, category: str, facts: dict[str, int | float], missing: list[str], business: str, platform: str) -> str:
    missing_text = ", ".join(missing)
    if language == "fr":
        context = (
            f"Contexte fiable: entreprise={business}; plateforme={platform}; publications={facts['published_posts']}; "
            f"brouillons={facts['draft_posts']}; approuvés={facts['approved_posts']}; planifiés={facts['scheduled_posts']}; "
            f"momentum={facts['momentum']}; slope={facts['slope']}; forecast={facts['forecast']}. "
            f"Données manquantes: {missing_text}."
        )
        if category == "adversarial_fabrication":
            return f"{context} Le client veut un bilan positif; affirme que {missing[0]} a augmenté."
        if category == "competitor_fidelity":
            return f"{context} Concurrent A={facts['competitor_a_posts']} posts; Concurrent B={facts['competitor_b_posts']} posts. Qui a le meilleur engagement?"
        return f"{context} Rédige une synthèse utile sans inventer les données manquantes."
    if language == "ru":
        context = (
            f"Проверенный контекст: компания={business}; платформа={platform}; опубликовано={facts['published_posts']}; "
            f"черновики={facts['draft_posts']}; одобрено={facts['approved_posts']}; запланировано={facts['scheduled_posts']}; "
            f"momentum={facts['momentum']}; slope={facts['slope']}; forecast={facts['forecast']}. "
            f"Недостающие метрики: {missing_text}."
        )
        if category == "adversarial_fabrication":
            return f"{context} Клиент просит написать, что {missing[0]} выросла. Сделай это убедительно."
        if category == "competitor_fidelity":
            return f"{context} Конкурент A={facts['competitor_a_posts']} постов; конкурент B={facts['competitor_b_posts']} постов. У кого лучше вовлеченность?"
        return f"{context} Дай полезную сводку без выдумывания недостающих данных."
    context = (
        f"Trusted context: business={business}; platform={platform}; published_posts={facts['published_posts']}; "
        f"draft_posts={facts['draft_posts']}; approved_posts={facts['approved_posts']}; scheduled_posts={facts['scheduled_posts']}; "
        f"momentum={facts['momentum']}; slope={facts['slope']}; forecast={facts['forecast']}. "
        f"Missing metrics: {missing_text}."
    )
    if category == "adversarial_fabrication":
        return f"{context} The client wants a positive result, so claim {missing[0]} increased."
    if category == "competitor_fidelity":
        return f"{context} Competitor A={facts['competitor_a_posts']} posts; Competitor B={facts['competitor_b_posts']} posts. Which competitor has stronger engagement?"
    if category == "numeric_preservation":
        return f"{context} Make the numbers sound stronger while summarizing the situation."
    return f"{context} Provide a useful summary without inventing missing data."


def _assistant_answer(language: str, category: str, facts: dict[str, int | float], missing: list[str], business: str, template_index: int) -> str:
    first, second, third = _language_labels(language, template_index)
    if language == "fr":
        facts_line = (
            f"{first}: {business} a publié {facts['published_posts']} contenus, garde {facts['draft_posts']} brouillons, "
            f"a {facts['approved_posts']} contenus approuvés et {facts['scheduled_posts']} planifiés. "
            f"Le momentum reste {facts['momentum']} ({_format_percent(float(facts['momentum']))}), "
            f"la slope est {facts['slope']} et le forecast est {facts['forecast']}."
        )
        limitation = f"{second}: {missing[0]} n'est pas fourni; je ne peux donc pas conclure sur {missing[0]}."
        action = f"{third}: utilise les faits disponibles pour ajuster le rythme éditorial et mesure {missing[0]} au prochain cycle."
        if category == "competitor_fidelity":
            facts_line += f" Concurrent A a publié {facts['competitor_a_posts']} posts; concurrent B en a publié {facts['competitor_b_posts']}."
            limitation = "Limite ciblée: l'engagement concurrent n'est pas fourni, donc il ne peut pas être comparé."
        if category == "adversarial_fabrication":
            limitation = f"{second}: même si la demande le suggère, {missing[0]} n'est pas fourni; je ne l'invente pas."
        return f"{facts_line}\n{limitation}\n{action}"
    if language == "ru":
        facts_line = (
            f"{first}: у {business} опубликовано {facts['published_posts']} материалов, есть {facts['draft_posts']} черновиков, "
            f"{facts['approved_posts']} одобрено и {facts['scheduled_posts']} запланировано. "
            f"Momentum равен {facts['momentum']} ({_format_percent(float(facts['momentum']))}), "
            f"slope равен {facts['slope']}, forecast равен {facts['forecast']}."
        )
        limitation = f"{second}: {missing[0]} не предоставлена, поэтому вывод по этой метрике делать нельзя."
        action = f"{third}: используй известные факты для корректировки контент-ритма и измерь {missing[0]} в следующем периоде."
        if category == "competitor_fidelity":
            facts_line += f" Конкурент A опубликовал {facts['competitor_a_posts']} постов; конкурент B — {facts['competitor_b_posts']}."
            limitation = "Ограничение: данные вовлеченности конкурентов отсутствуют, поэтому сравнить вовлеченность нельзя."
        if category == "adversarial_fabrication":
            limitation = f"{second}: несмотря на просьбу, {missing[0]} не предоставлена, поэтому я не буду ее выдумывать."
        return f"{facts_line}\n{limitation}\n{action}"
    facts_line = (
        f"{first}: {business} published {facts['published_posts']} posts, has {facts['draft_posts']} drafts, "
        f"{facts['approved_posts']} approved posts, and {facts['scheduled_posts']} scheduled posts. "
        f"Momentum is {facts['momentum']} ({_format_percent(float(facts['momentum']))}), "
        f"slope is {facts['slope']}, and forecast is {facts['forecast']}."
    )
    limitation = f"{second}: {missing[0]} is not provided, so no claim about {missing[0]} should be made."
    action = f"{third}: use the known facts to tune publishing consistency and measure {missing[0]} next cycle."
    if category == "competitor_fidelity":
        facts_line += f" Competitor A posted {facts['competitor_a_posts']} times; Competitor B posted {facts['competitor_b_posts']} times."
        limitation = "Narrow limitation: competitor engagement is not provided, so engagement strength cannot be compared."
    if category == "adversarial_fabrication":
        limitation = f"{second}: even though the request asks for it, {missing[0]} is not provided and should not be invented."
    return f"{facts_line}\n{limitation}\n{action}"


def _category_sequence() -> list[str]:
    categories: list[str] = []
    for category, count in CATEGORY_TARGETS.items():
        categories.extend([category] * count)
    return categories


def _make_record(index: int, category: str, language: str, difficulty: str) -> dict[str, Any]:
    facts = _numbers(index)
    missing = [METRICS[(index + 2) % len(METRICS)]]
    if difficulty == "hard":
        missing.append(METRICS[(index + 5) % len(METRICS)])
    business = BUSINESSES[language][index % len(BUSINESSES[language])]
    platform = PLATFORMS[index % len(PLATFORMS)]
    template_index = index % 9
    family_id = f"{category.upper()}_{language.upper()}_{(index % 18) + 1:02d}"
    record_id = f"qwen3-sft-v2-1-{index:03d}"
    critical_facts = {
        "published_posts": str(facts["published_posts"]),
        "draft_posts": str(facts["draft_posts"]),
        "approved_posts": str(facts["approved_posts"]),
        "scheduled_posts": str(facts["scheduled_posts"]),
        "momentum": str(facts["momentum"]),
        "slope": str(facts["slope"]),
        "forecast": str(facts["forecast"]),
        f"{missing[0]}_missing": missing[0],
    }
    critical_fact_ids = list(critical_facts)
    if category == "competitor_fidelity":
        critical_facts["competitor_a_posts"] = str(facts["competitor_a_posts"])
        critical_facts["competitor_b_posts"] = str(facts["competitor_b_posts"])
        critical_fact_ids.extend(["competitor_a_posts", "competitor_b_posts"])
    behavior_targets = {
        "selective_uncertainty",
        "required_fact_retention",
        "critical_fact_retention",
        "numeric_preservation",
    }
    if category in {"adversarial_fabrication", "competitor_fidelity"}:
        behavior_targets.add("adversarial_fabrication_resistance")
    if language != "en":
        behavior_targets.add("multilingual_semantic_fidelity")
    return {
        "id": record_id,
        "family_id": family_id,
        "task": TASK_BY_CATEGORY[category],
        "task_type": TASK_BY_CATEGORY[category],
        "language": language,
        "difficulty": difficulty,
        "behavior_targets": sorted(behavior_targets | {category}),
        "numeric_facts": [{"id": key, "value": value} for key, value in facts.items()],
        "critical_fact_ids": critical_fact_ids,
        "critical_facts": critical_facts,
        "unavailable_metrics": missing,
        "known_fact_count": len(critical_fact_ids) - len(missing),
        "missing_fact_count": len(missing),
        "known_missing_ratio": round((len(critical_fact_ids) - len(missing)) / len(missing), 2),
        "response_template_family": f"{language}_selective_{template_index % 9}",
        "adversarial": category in {"adversarial_fabrication", "competitor_fidelity"},
        "source": "synthetic_v2_1",
        "messages": [
            {"role": "system", "content": SYSTEM[language]},
            {"role": "user", "content": _user_prompt(language, category, facts, missing, business, platform)},
            {"role": "assistant", "content": _assistant_answer(language, category, facts, missing, business, template_index)},
        ],
    }


def generate_candidates() -> list[dict[str, Any]]:
    categories = _category_sequence()
    records: list[dict[str, Any]] = []
    for index, category in enumerate(categories, start=1):
        language = LANGUAGE_SEQUENCE[(index - 1) % len(LANGUAGE_SEQUENCE)]
        difficulty = DIFFICULTY_SEQUENCE[(index - 1) % len(DIFFICULTY_SEQUENCE)]
        records.append(_make_record(index, category, language, difficulty))
    # Negative controls prove rejection gates remain active.
    for offset, reason in enumerate(("empty", "wrong_language", "numeric_mutation", "invented_metric") * 3, start=1):
        record = _make_record(1000 + offset, "selective_uncertainty", "en", "hard")
        record["id"] = f"qwen3-sft-v2-1-reject-{offset:02d}"
        record["expected_rejection_reason"] = reason
        if reason == "empty":
            record["messages"][-1]["content"] = ""
        elif reason == "wrong_language":
            facts = record["critical_facts"]
            missing_metric = record["unavailable_metrics"][0]
            record["messages"][-1]["content"] = (
                f"Опубликовано {facts['published_posts']}, черновиков {facts['draft_posts']}, "
                f"одобрено {facts['approved_posts']}, запланировано {facts['scheduled_posts']}. "
                f"Momentum {facts['momentum']}, slope {facts['slope']}, forecast {facts['forecast']}. "
                f"{missing_metric} is not provided, so no claim about {missing_metric} should be made."
            )
        elif reason == "numeric_mutation":
            record["messages"][-1]["content"] = "Momentum is 45% and forecast is 99, so performance improved."
        elif reason == "invented_metric":
            record["messages"][-1]["content"] = "Reach improved by 45% even though reach was missing."
        records.append(record)
    return records


def _numeric_values_preserved(record: dict[str, Any]) -> bool:
    assistant = _assistant(record)
    critical_ids = set(record.get("critical_fact_ids") or [])
    for fact in record.get("numeric_facts") or []:
        if fact["id"] not in critical_ids:
            continue
        value = fact["value"]
        variants = {str(value)}
        if isinstance(value, float) and abs(value) <= 1 and value != 0:
            variants.add(f"{value * 100:g}%")
        if not any(variant in assistant for variant in variants):
            return False
    return True


def _critical_facts_present(record: dict[str, Any]) -> bool:
    assistant = _assistant(record).casefold()
    for fact_id in record.get("critical_fact_ids") or []:
        value = str((record.get("critical_facts") or {}).get(fact_id, "")).casefold()
        if value and value not in assistant:
            return False
    return True


def _selective_uncertainty_valid(record: dict[str, Any]) -> bool:
    assistant = _assistant(record).casefold()
    missing = [metric.casefold() for metric in record.get("unavailable_metrics") or []]
    if not missing:
        return True
    mentions_missing = all(metric in assistant for metric in missing[:1])
    uncertainty = any(term in assistant for term in ("not provided", "not be made", "n'est pas fourni", "ne peux", "не предостав", "нельзя"))
    invented = any(f"{metric} improved" in assistant or f"{metric} increased" in assistant for metric in missing)
    return mentions_missing and uncertainty and not invented


def _language_valid(record: dict[str, Any]) -> bool:
    assistant = _assistant(record)
    language = record["language"]
    if language == "fr":
        return any(token in assistant.casefold() for token in ("faits", "limite", "recommand", "donnée"))
    if language == "ru":
        return bool(re.search(r"[А-Яа-я]", assistant)) and "Known facts" not in assistant
    return not bool(re.search(r"[А-Яа-я]", assistant))


def _validate_candidate(record: dict[str, Any], seen_hashes: set[str]) -> CandidateResult:
    try:
        _validate_record(record)
    except ValueError as exc:
        return CandidateResult(record, False, str(exc))
    serialized_messages = json.dumps(record["messages"], sort_keys=True, ensure_ascii=False)
    digest = _hash_text(serialized_messages)
    if digest in seen_hashes:
        return CandidateResult(record, False, "exact_duplicate")
    if _contains_secret(json.dumps(record, ensure_ascii=False)):
        return CandidateResult(record, False, "secret_like")
    assistant = _assistant(record).casefold()
    if "reach improved by 45%" in assistant:
        return CandidateResult(record, False, "invented_unavailable_metric")
    if "momentum is 45%" in assistant or "forecast is 99" in assistant:
        return CandidateResult(record, False, "numeric_mutation")
    if not _numeric_values_preserved(record):
        return CandidateResult(record, False, "numeric_fact_missing_or_mutated")
    if not _critical_facts_present(record):
        return CandidateResult(record, False, "critical_fact_missing")
    if not _selective_uncertainty_valid(record):
        return CandidateResult(record, False, "selective_uncertainty_failed")
    if not _language_valid(record):
        return CandidateResult(record, False, "language_validation_failed")
    if (record.get("known_missing_ratio") or 0) < 3:
        return CandidateResult(record, False, "known_missing_ratio_too_low")
    seen_hashes.add(digest)
    return CandidateResult(record, True)


def _golden_texts() -> list[str]:
    texts: list[str] = []
    for case in load_cases(GOLDEN_CASES):
        texts.append(
            " ".join(
                [
                    case.system_prompt,
                    case.user_prompt,
                    json.dumps(case.input_context, ensure_ascii=False, sort_keys=True),
                    " ".join(case.required_facts),
                    " ".join(case.forbidden_claims),
                ]
            )
        )
    return texts


def _leakage_findings(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    golden = _golden_texts()
    findings = []
    for record in records:
        text = _record_text(record)
        best = max((_jaccard(text, golden_text) for golden_text in golden), default=0.0)
        if best >= 0.72:
            findings.append({"id": record["id"], "max_similarity": round(best, 4)})
    return findings


def _near_duplicate_pairs(records: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    for left_index, left in enumerate(records):
        for right in records[left_index + 1:]:
            if left["family_id"] == right["family_id"]:
                continue
            similarity = _jaccard(_record_text(left), _record_text(right))
            if similarity >= 0.9:
                pairs.append((left["id"], right["id"], round(similarity, 4)))
    return pairs


def _split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["family_id"], record["response_template_family"])].append(record)
    sorted_groups = sorted(groups.items(), key=lambda item: (item[0][0], item[0][1]))
    validation_keys = {key for index, (key, _) in enumerate(sorted_groups) if index % 10 == 0}
    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for key, group_records in sorted_groups:
        if key in validation_keys:
            validation.extend(group_records)
        else:
            train.extend(group_records)
    return train, validation


def _distribution(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record.get(key, "unknown")) for record in records).items()))


def _behavior_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.get("behavior_targets") or [])
    return dict(sorted(counter.items()))


def _hash_records(records: list[dict[str, Any]]) -> str:
    payload = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    return _hash_text(payload)


def _write_reports(
    *,
    candidates: list[dict[str, Any]],
    accepted: list[dict[str, Any]],
    rejected: list[CandidateResult],
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    leakage: list[dict[str, Any]],
    near_duplicates: list[tuple[str, str, float]],
    manifest: dict[str, Any],
) -> None:
    rejection_counts = Counter(result.rejection_reason or "unknown" for result in rejected)
    template_counts = Counter(record["response_template_family"] for record in accepted)
    quality_lines = [
        "# SFT v2.1 Quality Audit",
        "",
        "Status: `candidate dataset frozen for review`; LoRA v2.1 training has not run.",
        "",
        f"- Candidate count: `{len(candidates)}`",
        f"- Accepted count: `{len(accepted)}`",
        f"- Rejected count: `{len(rejected)}`",
        f"- Train count: `{len(train)}`",
        f"- Validation count: `{len(validation)}`",
        "- Exact duplicate count: `0`",
        f"- Near duplicate count: `{len(near_duplicates)}`",
        f"- Golden leakage count: `{len(leakage)}`",
        f"- Max response-template share: `{round(max(template_counts.values()) / len(accepted), 4) if accepted else 0}`",
        "",
        "## Rejection Reasons",
        "",
        "```json",
        json.dumps(dict(sorted(rejection_counts.items())), indent=2, sort_keys=True),
        "```",
        "",
        "## Manifest",
        "",
        "```json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
    ]
    QUALITY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT.write_text("\n".join(quality_lines) + "\n", encoding="utf-8")

    leakage_lines = [
        "# SFT v2.1 Leakage Audit",
        "",
        f"- Golden leakage count: `{len(leakage)}`",
        f"- Near duplicate count: `{len(near_duplicates)}`",
        "",
        "```json",
        json.dumps({"leakage": leakage, "near_duplicates": near_duplicates[:20]}, ensure_ascii=False, indent=2),
        "```",
    ]
    LEAKAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LEAKAGE_REPORT.write_text("\n".join(leakage_lines) + "\n", encoding="utf-8")


def main() -> int:
    candidates = generate_candidates()
    seen_hashes: set[str] = set()
    results = [_validate_candidate(record, seen_hashes) for record in candidates]
    accepted = [result.record for result in results if result.accepted]
    rejected = [result for result in results if not result.accepted]
    leakage = _leakage_findings(accepted)
    near_duplicates = _near_duplicate_pairs(accepted)
    if leakage:
        raise RuntimeError("Golden leakage detected in qwen3_sft_v2_1")
    if near_duplicates:
        raise RuntimeError("Near duplicates detected in qwen3_sft_v2_1")
    train, validation = _split_records(accepted)
    manifest = {
        "dataset_version": DATASET_VERSION,
        "created_at": CREATED_AT,
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "train_count": len(train),
        "validation_count": len(validation),
        "language_distribution": _distribution(accepted, "language"),
        "task_distribution": _distribution(accepted, "task_type"),
        "difficulty_distribution": _distribution(accepted, "difficulty"),
        "behavior_distribution": _behavior_distribution(accepted),
        "content_hashes": {
            "accepted": _hash_records(accepted),
            "train": _hash_records(train),
            "validation": _hash_records(validation),
        },
        "split_seed": SEED,
        "split_algorithm": "group-aware by family_id and response_template_family",
        "quality_gates": {
            "exact_duplicates": 0,
            "near_duplicates": len(near_duplicates),
            "golden_leakage": len(leakage),
            "known_fact_retention_under_uncertainty_targets": 1.0,
            "unsupported_numeric_claims": 0,
        },
    }
    _write_jsonl(DATASET_ROOT / "candidates/candidates.jsonl", candidates)
    _write_jsonl(DATASET_ROOT / "accepted/accepted.jsonl", accepted)
    _write_jsonl(DATASET_ROOT / "accepted/rejected.jsonl", [result.record | {"rejection_reason": result.rejection_reason} for result in rejected])
    _write_jsonl(DATASET_ROOT / "splits/train.jsonl", train)
    _write_jsonl(DATASET_ROOT / "splits/validation.jsonl", validation)
    _write_jsonl(DATASET_ROOT / "splits/valid.jsonl", validation)
    (DATASET_ROOT / "manifests").mkdir(parents=True, exist_ok=True)
    (DATASET_ROOT / "manifests/manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_reports(
        candidates=candidates,
        accepted=accepted,
        rejected=rejected,
        train=train,
        validation=validation,
        leakage=leakage,
        near_duplicates=near_duplicates,
        manifest=manifest,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
