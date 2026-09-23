from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .metrics import CaseScore, score_case, summarize
from .runner import load_cases
from .schemas import EvaluationCase

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = ROOT / "ml" / "eval" / "cases" / "golden.jsonl"
DEFAULT_RECORDS = ROOT / "ml" / "outputs" / "runs" / "20260922-150511-local-Qwen3-1-7B-Q4_K_M" / "records.jsonl"
REPORT_DIR = ROOT / "ml" / "eval" / "reports"
MANIFEST_PATH = ROOT / "ml" / "eval" / "semantic_manifest_v3.json"

CLUSTER_BY_SIGNAL = {
    "forbidden": "HALLUCINATION_RESISTANCE",
    "numeric": "NUMERIC_PRESERVATION",
    "insufficient": "INSUFFICIENT_EVIDENCE",
    "language": "MULTILINGUAL_INSTRUCTION",
    "competitor": "COMPETITOR_FACT_FIDELITY",
    "trend": "TREND_METRIC_FIDELITY",
    "recommendation": "RECOMMENDATION_RELEVANCE",
    "fact": "REQUIRED_FACT_RECALL",
}


def _load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _old_score(record: dict[str, Any]) -> dict[str, Any]:
    return dict(record.get("score") or {})


def _new_score(case: EvaluationCase, record: dict[str, Any]) -> CaseScore:
    return score_case(case, str(record.get("output", "")), latency_ms=record.get("latency_ms"))


def _safety_failure_category(case: EvaluationCase, score: CaseScore) -> str | None:
    if score.forbidden_claim_failed:
        if score.numeric_mutation_rate is not None and score.numeric_mutation_rate > 0:
            return "NUMERIC_HALLUCINATION"
        return "FORBIDDEN_CLAIM"
    if score.insufficient_evidence_handled is False:
        return "FAILED_UNCERTAINTY"
    if score.critical_required_fact_recall < 1:
        return "REQUIRED_FACT_OMITTED"
    if score.required_fact_recall < 1:
        return "REQUIRED_FACT_OMITTED"
    if score.language_match is False:
        return "LANGUAGE_FAILURE"
    if case.grading_rules.get("must_refuse_fabrication") and score.safe_uncertainty is False:
        return "FAILED_REFUSAL"
    return None


def _cluster(case: EvaluationCase, score: CaseScore, safety_category: str | None) -> str | None:
    if safety_category in {"FORBIDDEN_CLAIM", "NUMERIC_HALLUCINATION", "FAILED_REFUSAL"}:
        return CLUSTER_BY_SIGNAL["forbidden"]
    if score.numeric_mutation_rate is not None and score.numeric_mutation_rate > 0:
        if case.task_type == "trend_intelligence":
            return CLUSTER_BY_SIGNAL["trend"]
        return CLUSTER_BY_SIGNAL["numeric"]
    if score.insufficient_evidence_handled is False:
        return CLUSTER_BY_SIGNAL["insufficient"]
    if not score.language_match:
        return CLUSTER_BY_SIGNAL["language"]
    if score.required_fact_recall < 1:
        if case.task_type == "competitor_analysis":
            return CLUSTER_BY_SIGNAL["competitor"]
        if case.task_type == "trend_intelligence":
            return CLUSTER_BY_SIGNAL["trend"]
        return CLUSTER_BY_SIGNAL["fact"]
    if case.task_type in {"business_report", "strategy"} and score.instruction_following is False:
        return CLUSTER_BY_SIGNAL["recommendation"]
    return None


def _audit_grading_modes(cases: list[EvaluationCase]) -> dict[str, Counter[str]]:
    modes: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        modes[case.task_type]["schema_contract"] += int(case.expected_schema != "freeform")
        modes[case.task_type]["exact_or_alias_required_fact"] += len(case.required_facts)
        modes[case.task_type]["exact_forbidden_claim"] += len(case.forbidden_claims)
        if case.grading_rules.get("preserve_numbers") or case.grading_rules.get("metrics_unchanged"):
            modes[case.task_type]["numeric_comparison"] += 1
        if case.grading_rules.get("language"):
            modes[case.task_type]["language_sensitive"] += 1
        if case.grading_rules.get("must_refuse_fabrication") or case.grading_rules.get("must_state_insufficient_evidence"):
            modes[case.task_type]["insufficient_evidence_concept"] += 1
    return modes


def _format_summary(title: str, summary: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", "", "```json", json.dumps(summary, indent=2, sort_keys=True), "```", ""]
    return lines


def _write_safety_report(
    *,
    cases_by_id: dict[str, EvaluationCase],
    scores_by_id: dict[str, CaseScore],
    old_scores_by_id: dict[str, dict[str, Any]],
) -> Path:
    safety_cases = [case for case in cases_by_id.values() if case.task_type == "safety" or case.id.endswith("-safety-001")]
    rows: list[tuple[str, str | None, float, float, bool | None, bool | None, bool]] = []
    false_negatives = 0
    for case in safety_cases:
        if case.id not in scores_by_id:
            continue
        score = scores_by_id[case.id]
        old = old_scores_by_id.get(case.id, {})
        old_instruction = bool(old.get("instruction_following"))
        if not old_instruction and score.instruction_following:
            false_negatives += 1
        rows.append(
            (
                case.id,
                _safety_failure_category(case, score),
                score.required_fact_recall,
                score.critical_required_fact_recall,
                score.insufficient_evidence_handled,
                score.safe_uncertainty,
                score.forbidden_claim_failed,
            )
        )

    path = REPORT_DIR / "semantic_safety_forensics.md"
    lines = [
        "# Semantic Safety Forensics",
        "",
        "- Source: existing constrained Qwen run `20260922-150511-local-Qwen3-1-7B-Q4_K_M`.",
        "- No model calls were made for this report.",
        f"- Safety-like cases reviewed: `{len(safety_cases)}`.",
        f"- Evaluator false negatives corrected by alias/concept matching: `{false_negatives}`.",
        "",
        "| Case | Primary category | Required recall | Critical recall | Insufficient evidence handled | Safe uncertainty | Forbidden claim |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for case_id, category, recall, critical_recall, insufficient, uncertainty, forbidden in rows:
        lines.append(
            f"| `{case_id}` | `{category or 'PASS'}` | `{recall:.2f}` | `{critical_recall:.2f}` | "
            f"`{insufficient}` | `{uncertainty}` | `{forbidden}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_cluster_report(*, cases_by_id: dict[str, EvaluationCase], scores: list[CaseScore]) -> Path:
    clusters: Counter[str] = Counter()
    severity: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for score in scores:
        case = cases_by_id[score.case_id]
        safety_category = _safety_failure_category(case, score)
        cluster = _cluster(case, score, safety_category)
        if cluster:
            clusters[cluster] += 1
            if score.forbidden_claim_failed or score.critical_required_fact_recall < 1 or (score.numeric_mutation_rate or 0) > 0:
                severity[cluster] += 2
            else:
                severity[cluster] += 1
            if len(examples[cluster]) < 5:
                examples[cluster].append(score.case_id)

    path = REPORT_DIR / "semantic_failure_clusters.md"
    lines = [
        "# Semantic Failure Clusters",
        "",
        "- Source: existing constrained Qwen run rescored with semantic evaluator v3.",
        "- Frequency counts reflect deterministic checks, not a human quality review.",
        "",
        "| Cluster | Frequency | Severity points | Example cases |",
        "| --- | ---: | ---: | --- |",
    ]
    for cluster, count in sorted(clusters.items(), key=lambda item: (-severity[item[0]], -item[1], item[0])):
        lines.append(f"| `{cluster}` | `{count}` | `{severity[cluster]}` | `{', '.join(examples[cluster])}` |")
    if not clusters:
        lines.append("| `NONE` | `0` | `0` |  |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_audit_report(
    *,
    cases: list[EvaluationCase],
    scores: list[CaseScore],
    old_scores_by_id: dict[str, dict[str, Any]],
) -> Path:
    new_summary = summarize(scores)
    old_instruction = sum(1 for score in old_scores_by_id.values() if score.get("instruction_following")) / len(old_scores_by_id)
    old_required = sum(float(score.get("required_field_rate", 0)) for score in old_scores_by_id.values()) / len(old_scores_by_id)
    false_negatives = [
        score.case_id
        for score in scores
        if not bool(old_scores_by_id.get(score.case_id, {}).get("instruction_following")) and score.instruction_following
    ]
    modes = {task: dict(counter) for task, counter in _audit_grading_modes(cases).items()}
    path = REPORT_DIR / "semantic_evaluator_audit.md"
    lines = [
        "# Semantic Evaluator Audit",
        "",
        "- Evaluation version: `golden_eval_v3_semantic_grading`.",
        "- Golden case content remains `golden_eval_v2`; this version changes deterministic semantic scoring only.",
        "- No model outputs were edited and no new model calls were made.",
        "",
        "## Old vs Rescored",
        "",
        f"- Old instruction-following rate: `{old_instruction:.4f}`.",
        f"- New instruction-following rate: `{new_summary['instruction_following_rate']}`.",
        f"- Old required-field/fact average: `{old_required:.4f}`.",
        f"- New required-fact recall: `{new_summary['required_fact_recall']}`.",
        f"- Evaluator false negatives corrected: `{len(false_negatives)}`.",
        f"- Corrected case IDs: `{', '.join(false_negatives) or 'none'}`.",
        "",
    ]
    lines.extend(_format_summary("Semantic Metrics", new_summary))
    lines.extend(_format_summary("Grading Mode Audit", modes))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_manifest(*, cases: list[EvaluationCase]) -> None:
    payload = {
        "evaluation_version": "golden_eval_v3_semantic_grading",
        "case_source": "ml/eval/cases/golden.jsonl",
        "case_count": len(cases),
        "case_ids": [case.id for case in cases],
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "changes_from_v2": [
            "case payloads unchanged",
            "required-fact grading now supports deterministic alias/concept matching",
            "numeric preservation and mutation rates are explicit",
            "insufficient-evidence and safe-uncertainty rates are explicit",
            "safety cases receive primary failure categories",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rescore existing benchmark outputs with semantic evaluator v3.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases(Path(args.cases))
    cases_by_id = {case.id: case for case in cases}
    records = _load_records(Path(args.records))

    scores: list[CaseScore] = []
    old_scores_by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        case = cases_by_id[str(record["case_id"])]
        old_scores_by_id[case.id] = _old_score(record)
        scores.append(_new_score(case, record))
    scores_by_id = {score.case_id: score for score in scores}

    audit_path = _write_audit_report(cases=cases, scores=scores, old_scores_by_id=old_scores_by_id)
    safety_path = _write_safety_report(cases_by_id=cases_by_id, scores_by_id=scores_by_id, old_scores_by_id=old_scores_by_id)
    clusters_path = _write_cluster_report(cases_by_id=cases_by_id, scores=scores)
    _write_manifest(cases=cases)
    print(
        json.dumps(
            {
                "summary": summarize(scores),
                "audit_report": str(audit_path),
                "safety_report": str(safety_path),
                "clusters_report": str(clusters_path),
                "manifest": str(MANIFEST_PATH),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
