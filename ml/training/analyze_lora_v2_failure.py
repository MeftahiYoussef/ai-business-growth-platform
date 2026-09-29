from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.eval.metrics import (  # noqa: E402
    _critical_required_facts,
    _fact_matched,
    _normalize_text,
    _requires_insufficient_evidence_handling,
)
from ml.eval.runner import load_cases  # noqa: E402

BASE_OUTPUTS = ROOT / "ml/outputs/mlx_eval/lora_v2_pilot/20260923-235322-base_mlx_lora_v2_pilot.jsonl"
LORA_OUTPUTS = ROOT / "ml/outputs/mlx_eval/lora_v2_pilot/20260923-235431-lora_v2_mlx_pilot.jsonl"
GOLDEN_CASES = ROOT / "ml/eval/cases/golden.jsonl"
SFT_V2_ACCEPTED = ROOT / "ml/datasets/qwen3_sft_v2/accepted/accepted.jsonl"
SFT_V2_TRAIN = ROOT / "ml/datasets/qwen3_sft_v2/splits/train.jsonl"
SFT_V2_VALID = ROOT / "ml/datasets/qwen3_sft_v2/splits/validation.jsonl"
SFT_V2_MANIFEST = ROOT / "ml/datasets/qwen3_sft_v2/manifests/manifest.json"

OUTPUT_FORENSICS = ROOT / "ml/eval/reports/lora_v2_output_forensics.md"
FAILURE_ANALYSIS = ROOT / "ml/training/reports/lora_v2_failure_analysis.md"
STRUCTURAL_DIVERSITY = ROOT / "ml/training/reports/sft_v2_structural_diversity.md"
V2_1_DESIGN = ROOT / "ml/training/reports/sft_v2_1_design.md"
V2_1_CONFIG = ROOT / "ml/training/qwen3_1_7b_lora_v2_1.yaml"

UNCERTAINTY_PATTERNS = (
    "insufficient information",
    "insufficient evidence",
    "insufficient data",
    "not enough information",
    "not enough evidence",
    "not enough data",
    "unavailable",
    "not available",
    "not provided",
    "cannot determine",
    "can't determine",
    "cannot conclude",
    "can't conclude",
    "cannot assess",
    "can't assess",
    "données insuffisantes",
    "preuves insuffisantes",
    "pas assez de données",
    "indisponible",
    "non disponible",
    "ne peut pas déterminer",
    "impossible de déterminer",
    "недостаточно данных",
    "недостаточно доказательств",
    "недоступ",
    "нет данных",
    "нельзя определить",
    "невозможно определить",
)

REFUSAL_PATTERNS = (
    "cannot",
    "can't",
    "i will not",
    "i won't",
    "ne peux pas",
    "ne peut pas",
    "je ne vais pas",
    "impossible",
    "не могу",
    "нельзя",
    "не буду",
    "невозможно",
)

RECOMMENDATION_PATTERNS = (
    "recommend",
    "consider",
    "should",
    "recommand",
    "envisage",
    "devrait",
    "рекоменд",
    "следует",
    "стоит",
)

THINKING_MARKERS = ("<think", "</think", "reasoning:", "analysis:")


@dataclass(frozen=True)
class OutputStats:
    chars: int
    word_tokens: int
    sentences: int
    paragraphs: int
    repeated_sentence_count: int
    long_digit_run: bool
    degenerative_repetition: bool
    uncertainty_count: int
    refusal_count: int
    recommendation_count: int
    thinking_marker: bool
    approx_word_tokens_per_second: float | None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assistant(record: dict[str, Any]) -> str:
    return str(record["messages"][-1]["content"])


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[\w%+.-]+", text, flags=re.UNICODE)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]


def _phrase_count(text: str, phrases: tuple[str, ...]) -> int:
    normalized = _normalize_text(text)
    return sum(normalized.count(_normalize_text(phrase)) for phrase in phrases)


def _output_stats(text: str, latency_ms: int | None) -> OutputStats:
    words = _word_tokens(text)
    sentences = _sentences(text)
    repeated = len(sentences) - len({_normalize_text(sentence) for sentence in sentences})
    long_digit_run = bool(re.search(r"\d{25,}", text))
    repeated_long_token = bool(re.search(r"(\w{8,})(?:[_\s-]*\1){3,}", _normalize_text(text)))
    line_repetition = False
    normalized_lines = [_normalize_text(line) for line in text.splitlines() if line.strip()]
    if normalized_lines:
        line_counts = Counter(normalized_lines)
        line_repetition = max(line_counts.values()) >= 3
    tps = None
    if latency_ms and latency_ms > 0:
        tps = round(len(words) / (latency_ms / 1000), 2)
    return OutputStats(
        chars=len(text),
        word_tokens=len(words),
        sentences=len(sentences),
        paragraphs=len([p for p in text.splitlines() if p.strip()]),
        repeated_sentence_count=max(0, repeated),
        long_digit_run=long_digit_run,
        degenerative_repetition=long_digit_run or repeated_long_token or line_repetition or max(0, repeated) >= 3,
        uncertainty_count=_phrase_count(text, UNCERTAINTY_PATTERNS),
        refusal_count=_phrase_count(text, REFUSAL_PATTERNS),
        recommendation_count=_phrase_count(text, RECOMMENDATION_PATTERNS),
        thinking_marker=any(marker in text.casefold() for marker in THINKING_MARKERS),
        approx_word_tokens_per_second=tps,
    )


def _matched_facts(output: str, facts: list[str]) -> list[str]:
    return [fact for fact in facts if _fact_matched(output, fact)]


def _missing_facts(output: str, facts: list[str]) -> list[str]:
    return [fact for fact in facts if not _fact_matched(output, fact)]


def _classify_missing_fact(output: str, fact: str) -> str:
    normalized_output = _normalize_text(output)
    normalized_fact = _normalize_text(fact)
    if any(_normalize_text(pattern) in normalized_output for pattern in UNCERTAINTY_PATTERNS):
        if any(token in normalized_fact for token in ("unavailable", "missing", "insufficient", "нет", "pas de")):
            return "FACT_REPLACED_WITH_UNCERTAINTY"
        if any(_normalize_text(pattern) in normalized_output for pattern in RECOMMENDATION_PATTERNS):
            return "FACT_REPLACED_WITH_RECOMMENDATION"
        return "FACT_HIDDEN_BY_REFUSAL"
    if re.search(r"\d", fact) and re.search(r"\d", output):
        return "FACT_MUTATED"
    if any(_normalize_text(pattern) in normalized_output for pattern in RECOMMENDATION_PATTERNS):
        return "FACT_REPLACED_WITH_RECOMMENDATION"
    return "FACT_DROPPED"


def _language_mixing(language: str, output: str) -> str:
    normalized = output.casefold()
    has_cyrillic = bool(re.search(r"[А-Яа-я]", output))
    has_latin = bool(re.search(r"[A-Za-z]", output))
    english_headers = ("observed facts", "recommendations", "limitations")
    russian_headers = ("наблюдаемые факты", "рекомендации", "ограничения")
    french_headers = ("faits observés", "recommandations", "limites")
    if language == "fr":
        if any(header in normalized for header in english_headers):
            return "ENGLISH_HEADER_ONLY"
        if any(header in normalized for header in russian_headers) or has_cyrillic:
            return "TEMPLATE_LEAKAGE"
    if language == "ru":
        if any(header in normalized for header in english_headers):
            return "ENGLISH_HEADER_ONLY"
        if any(header in normalized for header in french_headers):
            return "TEMPLATE_LEAKAGE"
    if language == "en" and has_cyrillic:
        return "TEMPLATE_LEAKAGE"
    if language in {"fr", "ru"} and has_latin and language == "ru":
        return "ENGLISH_TECHNICAL_TERM"
    return "OK"


def _label_pattern(text: str) -> str:
    labels = []
    for line in text.splitlines():
        if ":" in line:
            labels.append(_normalize_text(line.split(":", 1)[0])[:40])
    return "|".join(labels[:8]) or "plain"


def _skeleton(text: str) -> str:
    normalized = _normalize_text(text)
    normalized = re.sub(r"\b\d+(?:[.,]\d+)?%?\b", "<num>", normalized)
    normalized = re.sub(r"\b[a-z]{1,2}\b", " ", normalized)
    prefix = _label_pattern(text)
    compact = re.sub(r"\s+", " ", normalized).strip()
    digest = hashlib.sha256(compact[:800].encode("utf-8")).hexdigest()[:10]
    return f"{prefix}::{digest}"


def _jaccard(left: str, right: str) -> float:
    left_tokens = set(_word_tokens(_normalize_text(left)))
    right_tokens = set(_word_tokens(_normalize_text(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _distribution(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record.get(key, "unknown")) for record in records).items()))


def _target_text_distribution(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for record in records:
        totals[str(record.get(key, "unknown"))] += len(_word_tokens(_assistant(record)))
    return dict(sorted(totals.items()))


def _summarize_numbers(values: Sequence[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "average": None, "median": None, "max": None}
    return {
        "count": len(values),
        "average": round(sum(values) / len(values), 2),
        "median": round(statistics.median(values), 2),
        "max": max(values),
    }


def _metric_delta(lora: float | None, base: float | None) -> float | None:
    if lora is None or base is None:
        return None
    return round(lora - base, 4)


def _pilot_forensics() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases = {case.id: case for case in load_cases(GOLDEN_CASES)}
    base_records = {record["case_id"]: record for record in _read_jsonl(BASE_OUTPUTS)}
    lora_records = {record["case_id"]: record for record in _read_jsonl(LORA_OUTPUTS)}
    case_ids = [case_id for case_id in base_records if case_id in lora_records]

    rows: list[dict[str, Any]] = []
    missing_breakdown: Counter[str] = Counter()
    critical_missing_breakdown: Counter[str] = Counter()
    uncertainty_case_counts = {"base": 0, "lora": 0}
    over_uncertainty_counts = {"base": 0, "lora": 0}
    selective_uncertainty_counts = {"base": 0, "lora": 0}
    partial_answer_counts = {"base": 0, "lora": 0}
    known_fact_recall_under_uncertainty: dict[str, list[float]] = {"base": [], "lora": []}
    correct_uncertainty_counts = {"base": 0, "lora": 0}
    required_uncertainty_total = 0
    language_mixing_counts: Counter[str] = Counter()

    base_stats: list[OutputStats] = []
    lora_stats: list[OutputStats] = []
    base_latencies: list[int] = []
    lora_latencies: list[int] = []
    base_degenerate = 0
    lora_degenerate = 0
    base_long_digit = 0
    lora_long_digit = 0

    for case_id in case_ids:
        case = cases[case_id]
        base = base_records[case_id]
        lora = lora_records[case_id]
        required_facts = list(case.required_facts)
        critical_facts = _critical_required_facts(case)
        requires_uncertainty = _requires_insufficient_evidence_handling(case)
        if requires_uncertainty:
            required_uncertainty_total += 1

        pair: dict[str, Any] = {
            "case_id": case_id,
            "task": case.task_type,
            "language": case.language,
            "requires_uncertainty": requires_uncertainty,
            "base": {},
            "lora": {},
        }
        for label, record in (("base", base), ("lora", lora)):
            output = str(record["output"])
            score = record.get("score", {})
            stats = _output_stats(output, record.get("latency_ms"))
            if label == "base":
                base_stats.append(stats)
                base_latencies.append(record.get("latency_ms", 0))
                base_degenerate += int(stats.degenerative_repetition)
                base_long_digit += int(stats.long_digit_run)
            else:
                lora_stats.append(stats)
                lora_latencies.append(record.get("latency_ms", 0))
                lora_degenerate += int(stats.degenerative_repetition)
                lora_long_digit += int(stats.long_digit_run)

            missing_required = _missing_facts(output, required_facts)
            missing_critical = _missing_facts(output, critical_facts)
            if label == "lora":
                for fact in missing_required:
                    missing_breakdown[_classify_missing_fact(output, fact)] += 1
                for fact in missing_critical:
                    critical_missing_breakdown[_classify_missing_fact(output, fact)] += 1
                mixing = _language_mixing(case.language, output)
                if mixing != "OK":
                    language_mixing_counts[mixing] += 1

            has_uncertainty = stats.uncertainty_count > 0
            if has_uncertainty:
                uncertainty_case_counts[label] += 1
                known_fact_recall_under_uncertainty[label].append(float(score.get("required_fact_recall", 0.0)))
            if requires_uncertainty and score.get("insufficient_evidence_handled"):
                correct_uncertainty_counts[label] += 1
            if has_uncertainty and (not requires_uncertainty or float(score.get("required_fact_recall", 0.0)) < 0.5):
                over_uncertainty_counts[label] += 1
            if requires_uncertainty and score.get("insufficient_evidence_handled") and float(score.get("required_fact_recall", 0.0)) >= 0.75:
                selective_uncertainty_counts[label] += 1
            if requires_uncertainty and score.get("insufficient_evidence_handled") and (
                float(score.get("required_fact_recall", 0.0)) > 0.0 or stats.recommendation_count > 0
            ):
                partial_answer_counts[label] += 1

            pair[label] = {
                "latency_ms": record.get("latency_ms"),
                "chars": stats.chars,
                "word_tokens": stats.word_tokens,
                "approx_word_tokens_per_second": stats.approx_word_tokens_per_second,
                "facts_retained": len(_matched_facts(output, required_facts)),
                "facts_total": len(required_facts),
                "critical_retained": len(_matched_facts(output, critical_facts)),
                "critical_total": len(critical_facts),
                "required_fact_recall": score.get("required_fact_recall"),
                "critical_required_fact_recall": score.get("critical_required_fact_recall"),
                "numeric_preservation_rate": score.get("numeric_preservation_rate"),
                "hallucination_failed": score.get("hallucination_failed"),
                "forbidden_claim_failed": score.get("forbidden_claim_failed"),
                "insufficient_evidence_handled": score.get("insufficient_evidence_handled"),
                "safe_uncertainty": score.get("safe_uncertainty"),
                "language_match": score.get("language_match"),
                "uncertainty_count": stats.uncertainty_count,
                "refusal_count": stats.refusal_count,
                "recommendation_count": stats.recommendation_count,
                "repeated_sentence_count": stats.repeated_sentence_count,
                "thinking_marker": stats.thinking_marker,
                "long_digit_run": stats.long_digit_run,
                "degenerative_repetition": stats.degenerative_repetition,
                "missing_required_facts": missing_required,
                "missing_critical_facts": missing_critical,
                "language_mixing": _language_mixing(case.language, output),
            }
        rows.append(pair)

    summary = {
        "paired_case_count": len(rows),
        "base_output_stats": {
            "chars": _summarize_numbers([stat.chars for stat in base_stats]),
            "word_tokens": _summarize_numbers([stat.word_tokens for stat in base_stats]),
            "approx_word_tokens_per_second": _summarize_numbers([
                stat.approx_word_tokens_per_second
                for stat in base_stats
                if stat.approx_word_tokens_per_second is not None
            ]),
            "latency_ms": _summarize_numbers(base_latencies),
            "uncertainty_cases": uncertainty_case_counts["base"],
            "thinking_marker_cases": sum(1 for stat in base_stats if stat.thinking_marker),
            "long_digit_run_cases": base_long_digit,
            "degenerative_repetition_cases": base_degenerate,
        },
        "lora_output_stats": {
            "chars": _summarize_numbers([stat.chars for stat in lora_stats]),
            "word_tokens": _summarize_numbers([stat.word_tokens for stat in lora_stats]),
            "approx_word_tokens_per_second": _summarize_numbers([
                stat.approx_word_tokens_per_second
                for stat in lora_stats
                if stat.approx_word_tokens_per_second is not None
            ]),
            "latency_ms": _summarize_numbers(lora_latencies),
            "uncertainty_cases": uncertainty_case_counts["lora"],
            "thinking_marker_cases": sum(1 for stat in lora_stats if stat.thinking_marker),
            "long_digit_run_cases": lora_long_digit,
            "degenerative_repetition_cases": lora_degenerate,
        },
        "fact_retention_failure_breakdown": dict(sorted(missing_breakdown.items())),
        "critical_fact_failure_breakdown": dict(sorted(critical_missing_breakdown.items())),
        "correct_uncertainty_rate": {
            label: round(correct_uncertainty_counts[label] / required_uncertainty_total, 4)
            if required_uncertainty_total
            else None
            for label in ("base", "lora")
        },
        "over_uncertainty_rate": {
            label: round(over_uncertainty_counts[label] / len(rows), 4) if rows else None
            for label in ("base", "lora")
        },
        "selective_uncertainty_rate": {
            label: round(selective_uncertainty_counts[label] / required_uncertainty_total, 4)
            if required_uncertainty_total
            else None
            for label in ("base", "lora")
        },
        "partial_answer_success_rate": {
            label: round(partial_answer_counts[label] / required_uncertainty_total, 4)
            if required_uncertainty_total
            else None
            for label in ("base", "lora")
        },
        "known_fact_retention_under_uncertainty": {
            label: round(sum(values) / len(values), 4) if values else None
            for label, values in known_fact_recall_under_uncertainty.items()
        },
        "language_mixing_counts": dict(sorted(language_mixing_counts.items())),
    }
    return summary, rows


def _dataset_forensics() -> dict[str, Any]:
    accepted = _read_jsonl(SFT_V2_ACCEPTED)
    train = _read_jsonl(SFT_V2_TRAIN)
    validation = _read_jsonl(SFT_V2_VALID)
    manifest = json.loads(SFT_V2_MANIFEST.read_text(encoding="utf-8"))

    uncertainty_records = sum(1 for record in accepted if _phrase_count(_assistant(record), UNCERTAINTY_PATTERNS) > 0)
    refusal_records = sum(1 for record in accepted if _phrase_count(_assistant(record), REFUSAL_PATTERNS) > 0)
    phrase_counts: Counter[str] = Counter()
    for record in accepted:
        assistant = _assistant(record)
        for phrase in UNCERTAINTY_PATTERNS:
            count = _normalize_text(assistant).count(_normalize_text(phrase))
            if count:
                phrase_counts[phrase] += count

    skeleton_counts = Counter(_skeleton(_assistant(record)) for record in accepted)
    label_pattern_counts = Counter(_label_pattern(_assistant(record)) for record in accepted)
    family_counts = Counter(str(record.get("family_id", "unknown")) for record in accepted)
    train_skeletons = Counter(_skeleton(_assistant(record)) for record in train)
    validation_skeletons = Counter(_skeleton(_assistant(record)) for record in validation)
    train_label_patterns = Counter(_label_pattern(_assistant(record)) for record in train)
    validation_label_patterns = Counter(_label_pattern(_assistant(record)) for record in validation)
    shared_skeletons = sorted(set(train_skeletons) & set(validation_skeletons))
    shared_label_patterns = sorted(set(train_label_patterns) & set(validation_label_patterns))
    train_validation_similarity = [
        max((_jaccard(_assistant(valid_record), _assistant(train_record)) for train_record in train), default=0.0)
        for valid_record in validation
    ]

    assistant_lengths = [len(_word_tokens(_assistant(record))) for record in accepted]
    unavailable_counts = [len(record.get("unavailable_metrics") or []) for record in accepted]
    numeric_counts = [len(record.get("numeric_facts") or []) for record in accepted]
    critical_counts = [len(record.get("critical_fact_ids") or []) for record in accepted]

    target_quality_flags: Counter[str] = Counter()
    for record in accepted:
        assistant = _assistant(record)
        if _phrase_count(assistant, UNCERTAINTY_PATTERNS) > 0 and len(record.get("critical_fact_ids") or []) < 3:
            target_quality_flags["uncertainty_with_low_positive_fact_density"] += 1
        if _phrase_count(assistant, REFUSAL_PATTERNS) > 0:
            target_quality_flags["refusal_phrase_present"] += 1
        if len(_word_tokens(assistant)) > 95:
            target_quality_flags["long_target"] += 1
        if _normalize_text("I will not make the numbers sound stronger") in _normalize_text(assistant):
            target_quality_flags["repeated_en_caution_template"] += 1

    max_cluster_count = max(skeleton_counts.values()) if skeleton_counts else 0
    max_label_pattern_count = max(label_pattern_counts.values()) if label_pattern_counts else 0
    top_clusters = skeleton_counts.most_common(10)
    top_label_patterns = label_pattern_counts.most_common(10)
    return {
        "manifest": manifest,
        "record_distribution_by_count": {
            "task": _distribution(accepted, "task_type"),
            "language": _distribution(accepted, "language"),
            "difficulty": _distribution(accepted, "difficulty"),
        },
        "record_distribution_by_assistant_tokens": {
            "task": _target_text_distribution(accepted, "task_type"),
            "language": _target_text_distribution(accepted, "language"),
            "difficulty": _target_text_distribution(accepted, "difficulty"),
        },
        "assistant_length_words": _summarize_numbers(assistant_lengths),
        "unavailable_metric_count": _summarize_numbers(unavailable_counts),
        "numeric_fact_count": _summarize_numbers(numeric_counts),
        "critical_fact_count": _summarize_numbers(critical_counts),
        "uncertainty_record_rate": round(uncertainty_records / len(accepted), 4),
        "refusal_record_rate": round(refusal_records / len(accepted), 4),
        "top_uncertainty_phrases": dict(phrase_counts.most_common(12)),
        "template_cluster_count": len(skeleton_counts),
        "max_template_cluster_share": round(max_cluster_count / len(accepted), 4) if accepted else 0,
        "top_template_clusters": [{"cluster": cluster, "count": count} for cluster, count in top_clusters],
        "label_pattern_cluster_count": len(label_pattern_counts),
        "max_label_pattern_share": round(max_label_pattern_count / len(accepted), 4) if accepted else 0,
        "top_label_pattern_clusters": [{"cluster": cluster, "count": count} for cluster, count in top_label_patterns],
        "family_count": len(family_counts),
        "max_family_share": round(max(family_counts.values()) / len(accepted), 4) if accepted else 0,
        "shared_train_validation_skeleton_count": len(shared_skeletons),
        "shared_train_validation_label_pattern_count": len(shared_label_patterns),
        "validation_max_similarity_to_train": _summarize_numbers(train_validation_similarity),
        "target_quality_flags": dict(sorted(target_quality_flags.items())),
    }


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _json_block(value: Any) -> list[str]:
    return ["```json", json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), "```"]


def _write_output_forensics(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# LoRA v2 Output Forensics",
        "",
        "Status: `LoRA v2 rejected`.",
        "",
        "This report analyzes the existing 10-case pilot outputs only. No model calls were made.",
        "",
        "## Summary",
        "",
        *[f"- Paired cases analyzed: `{summary['paired_case_count']}`"],
        f"- Base median latency: `{summary['base_output_stats']['latency_ms']['median']} ms`",
        f"- LoRA median latency: `{summary['lora_output_stats']['latency_ms']['median']} ms`",
        f"- Base median output chars: `{summary['base_output_stats']['chars']['median']}`",
        f"- LoRA median output chars: `{summary['lora_output_stats']['chars']['median']}`",
        f"- Base median output words: `{summary['base_output_stats']['word_tokens']['median']}`",
        f"- LoRA median output words: `{summary['lora_output_stats']['word_tokens']['median']}`",
        f"- Base approximate word tokens/sec: `{summary['base_output_stats']['approx_word_tokens_per_second']['median']}`",
        f"- LoRA approximate word tokens/sec: `{summary['lora_output_stats']['approx_word_tokens_per_second']['median']}`",
        f"- Base outputs with uncertainty phrases: `{summary['base_output_stats']['uncertainty_cases']}`",
        f"- LoRA outputs with uncertainty phrases: `{summary['lora_output_stats']['uncertainty_cases']}`",
        f"- Thinking marker cases, base: `{summary['base_output_stats']['thinking_marker_cases']}`",
        f"- Thinking marker cases, LoRA: `{summary['lora_output_stats']['thinking_marker_cases']}`",
        f"- Long digit-run cases, base: `{summary['base_output_stats']['long_digit_run_cases']}`",
        f"- Long digit-run cases, LoRA: `{summary['lora_output_stats']['long_digit_run_cases']}`",
        f"- Degenerative repetition cases, base: `{summary['base_output_stats']['degenerative_repetition_cases']}`",
        f"- Degenerative repetition cases, LoRA: `{summary['lora_output_stats']['degenerative_repetition_cases']}`",
        "",
        "## Fact-Retention Error Types",
        "",
        *_json_block(
            {
                "required_fact_failures": summary["fact_retention_failure_breakdown"],
                "critical_fact_failures": summary["critical_fact_failure_breakdown"],
            }
        ),
        "",
        "## Uncertainty Behavior",
        "",
        *_json_block(
            {
                "correct_uncertainty_rate": summary["correct_uncertainty_rate"],
                "over_uncertainty_rate": summary["over_uncertainty_rate"],
                "selective_uncertainty_rate": summary["selective_uncertainty_rate"],
                "partial_answer_success_rate": summary["partial_answer_success_rate"],
                "known_fact_retention_under_uncertainty": summary["known_fact_retention_under_uncertainty"],
            }
        ),
        "",
        "## Language Mixing",
        "",
        *_json_block(summary["language_mixing_counts"]),
        "",
        "## Case-Level Comparison",
        "",
        "| Case | Task | Lang | Base facts | LoRA facts | Base words | LoRA words | Base latency ms | LoRA latency ms | LoRA missing critical | LoRA notes |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        base = row["base"]
        lora = row["lora"]
        notes = []
        if lora["uncertainty_count"]:
            notes.append("uncertainty")
        if lora["refusal_count"]:
            notes.append("refusal")
        if lora["language_mixing"] != "OK":
            notes.append(lora["language_mixing"])
        if lora["thinking_marker"]:
            notes.append("thinking_marker")
        if lora["long_digit_run"]:
            notes.append("long_digit_run")
        if lora["degenerative_repetition"]:
            notes.append("degenerative_repetition")
        lines.append(
            "| {case_id} | {task} | {language} | {base_f}/{base_t} | {lora_f}/{lora_t} | {base_w} | {lora_w} | {base_l} | {lora_l} | {missing} | {notes} |".format(
                case_id=row["case_id"],
                task=row["task"],
                language=row["language"],
                base_f=base["facts_retained"],
                base_t=base["facts_total"],
                lora_f=lora["facts_retained"],
                lora_t=lora["facts_total"],
                base_w=base["word_tokens"],
                lora_w=lora["word_tokens"],
                base_l=base["latency_ms"],
                lora_l=lora["latency_ms"],
                missing=", ".join(lora["missing_critical_facts"]) or "none",
                notes=", ".join(notes) or "none",
            )
        )
    _write_markdown(OUTPUT_FORENSICS, lines)


def _write_failure_analysis(summary: dict[str, Any], dataset: dict[str, Any]) -> None:
    lines = [
        "# LoRA v2 Failure Analysis",
        "",
        "Status: `completed`; promotion status: `rejected`; reason: `semantic pilot regression`.",
        "",
        "## Root Cause",
        "",
        "The dominant failure is a curriculum-induced selective-uncertainty problem. The adapter learned to become safer and more cautious, but it did not preserve known supplied facts while qualifying only missing metrics. This explains the hallucination improvement and the simultaneous collapse in required-fact recall.",
        "",
        "The latency increase is primarily a generation-pathology issue: several LoRA outputs contain long digit runs or repeated fragments and likely ran to the token budget. Exact token-level throughput and finish reasons were not recorded by the pilot runner, so this report does not claim a precise adapter kernel overhead.",
        "",
        "## Evidence",
        "",
        f"- LoRA required-fact failure breakdown: `{json.dumps(summary['fact_retention_failure_breakdown'], sort_keys=True)}`",
        f"- LoRA critical-fact failure breakdown: `{json.dumps(summary['critical_fact_failure_breakdown'], sort_keys=True)}`",
        f"- Correct uncertainty rate, base -> LoRA: `{summary['correct_uncertainty_rate']['base']}` -> `{summary['correct_uncertainty_rate']['lora']}`",
        f"- Selective uncertainty rate, base -> LoRA: `{summary['selective_uncertainty_rate']['base']}` -> `{summary['selective_uncertainty_rate']['lora']}`",
        f"- Known-fact retention under uncertainty, base -> LoRA: `{summary['known_fact_retention_under_uncertainty']['base']}` -> `{summary['known_fact_retention_under_uncertainty']['lora']}`",
        f"- Median output words, base -> LoRA: `{summary['base_output_stats']['word_tokens']['median']}` -> `{summary['lora_output_stats']['word_tokens']['median']}`",
        f"- Median output chars, base -> LoRA: `{summary['base_output_stats']['chars']['median']}` -> `{summary['lora_output_stats']['chars']['median']}`",
        f"- Degenerative repetition cases, base -> LoRA: `{summary['base_output_stats']['degenerative_repetition_cases']}` -> `{summary['lora_output_stats']['degenerative_repetition_cases']}`",
        f"- Long digit-run cases, base -> LoRA: `{summary['base_output_stats']['long_digit_run_cases']}` -> `{summary['lora_output_stats']['long_digit_run_cases']}`",
        f"- Median latency ms, base -> LoRA: `{summary['base_output_stats']['latency_ms']['median']}` -> `{summary['lora_output_stats']['latency_ms']['median']}`",
        "",
        "## Dataset Findings",
        "",
        f"- SFT v2 uncertainty phrase record rate: `{dataset['uncertainty_record_rate']}`",
        f"- SFT v2 refusal phrase record rate: `{dataset['refusal_record_rate']}`",
        f"- SFT v2 max template-cluster share: `{dataset['max_template_cluster_share']}`",
        f"- SFT v2 max label-pattern share: `{dataset['max_label_pattern_share']}`",
        f"- Shared train/validation skeleton count: `{dataset['shared_train_validation_skeleton_count']}`",
        f"- Shared train/validation label-pattern count: `{dataset['shared_train_validation_label_pattern_count']}`",
        f"- Validation max similarity to train: `{json.dumps(dataset['validation_max_similarity_to_train'], sort_keys=True)}`",
        "",
        "## Semantic Response Policy V1",
        "",
        "1. Every supplied critical fact relevant to the answer must be retained.",
        "2. Supplied numeric values must remain unchanged unless deterministic code explicitly calculates a derived value.",
        "3. Only unsupported or missing facts receive uncertainty language.",
        "4. Missing one metric does not invalidate available metrics.",
        "5. Recommendations must be phrased as recommendations, not reported facts.",
        "6. Do not invent evidence.",
        "7. Remain helpful after stating a limitation.",
        "8. Do not over-refuse ordinary business analysis.",
        "9. Answer in the requested language, including labels and headers.",
        "10. Prefer concise output unless detail is requested.",
        "",
        "## Dataset vs Optimization",
        "",
        "Conclusion: `BOTH`, with dataset design as the primary cause.",
        "",
        "The dataset over-rewards uncertainty and repeats response skeletons. The low train/validation loss indicates that the validation split was too semantically similar to training despite family-level splitting. The 240-iteration rank-8 run may have amplified these templates, but the observed regression is not explainable by optimization intensity alone.",
        "",
        "## Decision",
        "",
        "A smaller `qwen3_sft_v2_1` dataset experiment is justified. It should target selective uncertainty, known-fact retention under missing data, concise answers, and multilingual labels. Do not train until the v2.1 candidates are generated, audited, and frozen.",
    ]
    _write_markdown(FAILURE_ANALYSIS, lines)


def _write_structural_diversity(dataset: dict[str, Any]) -> None:
    lines = [
        "# SFT v2 Structural Diversity Analysis",
        "",
        "This report goes beyond exact and near-duplicate text matching. It clusters assistant answer skeletons to detect repeated semantic templates.",
        "",
        "## Distributions By Record Count",
        "",
        *_json_block(dataset["record_distribution_by_count"]),
        "",
        "## Distributions By Assistant Word Tokens",
        "",
        *_json_block(dataset["record_distribution_by_assistant_tokens"]),
        "",
        "## Length And Metadata",
        "",
        *_json_block(
            {
                "assistant_length_words": dataset["assistant_length_words"],
                "unavailable_metric_count": dataset["unavailable_metric_count"],
                "numeric_fact_count": dataset["numeric_fact_count"],
                "critical_fact_count": dataset["critical_fact_count"],
            }
        ),
        "",
        "## Uncertainty Phrases",
        "",
        f"- Record rate with uncertainty phrase: `{dataset['uncertainty_record_rate']}`",
        f"- Record rate with refusal phrase: `{dataset['refusal_record_rate']}`",
        "",
        *_json_block(dataset["top_uncertainty_phrases"]),
        "",
        "## Template Clusters",
        "",
        f"- Template cluster count: `{dataset['template_cluster_count']}`",
        f"- Max template cluster share: `{dataset['max_template_cluster_share']}`",
        f"- Label-pattern cluster count: `{dataset['label_pattern_cluster_count']}`",
        f"- Max label-pattern share: `{dataset['max_label_pattern_share']}`",
        f"- Family count: `{dataset['family_count']}`",
        f"- Max family share: `{dataset['max_family_share']}`",
        f"- Shared train/validation skeleton count: `{dataset['shared_train_validation_skeleton_count']}`",
        f"- Shared train/validation label-pattern count: `{dataset['shared_train_validation_label_pattern_count']}`",
        "",
        *_json_block(dataset["top_template_clusters"]),
        "",
        "## Label Pattern Clusters",
        "",
        *_json_block(dataset["top_label_pattern_clusters"]),
        "",
        "## Target Quality Flags",
        "",
        *_json_block(dataset["target_quality_flags"]),
        "",
        "## Finding",
        "",
        "The dataset is lexically unique but semantically repetitive. The repeated fact/limitation/recommendation skeleton and global uncertainty target likely taught caution as a default style instead of selective qualification.",
    ]
    _write_markdown(STRUCTURAL_DIVERSITY, lines)


def _write_v2_1_design() -> None:
    lines = [
        "# SFT v2.1 Curriculum Design",
        "",
        "Status: `design prepared`; dataset generation and training are deferred.",
        "",
        "## Objective",
        "",
        "Teach semantic behavior, not JSON syntax. Constrained decoding remains responsible for structural output.",
        "",
        "## Candidate Size",
        "",
        "- Candidate generation target: `180-220`",
        "- Accepted target: `150-190`",
        "- Rationale: higher information density and less template repetition than the 360-record v2 curriculum.",
        "",
        "## Proposed Distribution",
        "",
        "| Category | Target Share | Purpose |",
        "| --- | ---: | --- |",
        "| Known + unknown selective uncertainty | 25% | Preserve known facts while qualifying only missing metrics. |",
        "| Required/critical fact retention | 20% | Keep 3-6 relevant facts in the answer. |",
        "| Numeric preservation | 20% | Preserve integers, decimals, percentages, negative growth, and zero values. |",
        "| Adversarial fabrication resistance | 10% | Resist requests to inflate or invent values. |",
        "| Multilingual semantic fidelity | 10% | Natural EN/FR/RU answers with localized labels. |",
        "| Report interpretation | 5% | Separate observed metrics from recommendations. |",
        "| Trend metric fidelity | 5% | Preserve momentum, slope, acceleration, forecast values. |",
        "| Competitor fidelity | 5% | Discuss only supplied competitor facts. |",
        "",
        "## Positive Fact Density",
        "",
        "- Each uncertainty case should include `3-6` known facts and only `1-2` missing facts.",
        "- Target known/missing fact ratio: at least `3:1` for uncertainty examples.",
        "- Training targets must state known facts first, then qualify missing facts narrowly.",
        "",
        "## Answer Length Strategy",
        "",
        "- Prefer concise three-part answers: known facts, narrow limitation, useful recommendation.",
        "- Avoid repeated caveats.",
        "- Avoid generic refusal language for ordinary business analysis.",
        "- Prevent outputs from learning long disclaimer templates.",
        "",
        "## Multilingual Strategy",
        "",
        "- French and Russian examples must use natural professional prose and localized labels.",
        "- Do not copy English section headers into FR/RU examples.",
        "- Technical terms may remain in English only when natural in context.",
        "",
        "## Structural Diversity Gate",
        "",
        "- No single response-template cluster should exceed `10%` of accepted records.",
        "- Split by scenario family and response-template family.",
        "- Do not place skeleton variants across both train and validation.",
        "",
        "## V2.1 Quality Gates",
        "",
        "- `known_fact_retention_under_uncertainty = 1.00` in target answers.",
        "- `unsupported_numeric_claims = 0`.",
        "- `exact_duplicates = 0`.",
        "- `near_duplicates <= 5%`.",
        "- `golden_leakage = 0`.",
        "- No current business, competitor, or trend facts are trained as model knowledge.",
        "",
        "## Future Experiment",
        "",
        "Use one controlled LoRA v2.1 run after the dataset is generated and audited. Keep the training setup comparable to v2 unless a separate versioned optimization experiment is explicitly approved.",
    ]
    _write_markdown(V2_1_DESIGN, lines)


def _write_v2_1_config() -> None:
    content = """# Prepared only. Do not train until qwen3_sft_v2_1 is generated,
# audited, split group-aware, frozen, and approved.
model: Qwen/Qwen3-1.7B
training_checkpoint: Qwen/Qwen3-1.7B-MLX-4bit
fine_tune_type: lora
data: ml/datasets/qwen3_sft_v2_1/splits
adapter_path: ml/outputs/adapters/qwen3_1_7b_lora_v2_1

# Keep comparable to v2 for the first dataset-only test.
lora_parameters:
  rank: 8
  dropout: 0.0
  scale: 16.0

optimizer: adamw
batch_size: 1
grad_accumulation_steps: 8
learning_rate: 0.00005
max_seq_length: 4096
iters: 240
val_batches: -1
steps_per_report: 10
steps_per_eval: 40
save_every: 120
num_layers: 16
mask_prompt: true
grad_checkpoint: true
seed: 20260922

goal: semantic_alignment_selective_uncertainty
not_goal:
  - JSON syntax learning
  - field order learning
  - enum formatting
  - seven-day structure
  - business fact memorization
  - trend fact memorization

future_command: >-
  python -m mlx_lm lora --train --model Qwen/Qwen3-1.7B-MLX-4bit
  --data ml/datasets/qwen3_sft_v2_1/splits --fine-tune-type lora
  --adapter-path ml/outputs/adapters/qwen3_1_7b_lora_v2_1 --batch-size 1
  --iters 240 --val-batches -1 --learning-rate 0.00005
  --steps-per-report 10 --steps-per-eval 40 --grad-accumulation-steps 8
  --save-every 120 --max-seq-length 4096 --num-layers 16 --mask-prompt
  --grad-checkpoint --seed 20260922

acceptance_gates:
  schema_validity: 1.0
  seven_day_validity: 1.0
  human_review_validity: 1.0
  critical_numeric_mutations: 0
  hallucination_failure_max: 0.02
  instruction_following_min: 0.8
  required_fact_recall_min: 0.9
  critical_required_fact_recall_min: 0.95
  numeric_preservation_min: 0.98
  language_match_min: 0.95
  insufficient_evidence_handling_min: 0.9
  known_fact_retention_under_uncertainty: 1.0
"""
    V2_1_CONFIG.write_text(content, encoding="utf-8")


def main() -> int:
    summary, rows = _pilot_forensics()
    dataset = _dataset_forensics()
    _write_output_forensics(summary, rows)
    _write_failure_analysis(summary, dataset)
    _write_structural_diversity(dataset)
    _write_v2_1_design()
    _write_v2_1_config()
    print(
        json.dumps(
            {
                "paired_case_count": summary["paired_case_count"],
                "lora_required_fact_failures": summary["fact_retention_failure_breakdown"],
                "lora_critical_fact_failures": summary["critical_fact_failure_breakdown"],
                "base_median_latency_ms": summary["base_output_stats"]["latency_ms"]["median"],
                "lora_median_latency_ms": summary["lora_output_stats"]["latency_ms"]["median"],
                "sft_v2_uncertainty_record_rate": dataset["uncertainty_record_rate"],
                "sft_v2_template_cluster_count": dataset["template_cluster_count"],
                "reports": [
                    str(OUTPUT_FORENSICS.relative_to(ROOT)),
                    str(FAILURE_ANALYSIS.relative_to(ROOT)),
                    str(STRUCTURAL_DIVERSITY.relative_to(ROOT)),
                    str(V2_1_DESIGN.relative_to(ROOT)),
                    str(V2_1_CONFIG.relative_to(ROOT)),
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
