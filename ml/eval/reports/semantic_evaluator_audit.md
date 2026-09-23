# Semantic Evaluator Audit

- Evaluation version: `golden_eval_v3_semantic_grading`.
- Golden case content remains `golden_eval_v2`; this version changes deterministic semantic scoring only.
- No model outputs were edited and no new model calls were made.

## Old vs Rescored

- Old instruction-following rate: `0.5800`.
- New instruction-following rate: `0.58`.
- Old required-field/fact average: `0.7400`.
- New required-fact recall: `0.76`.
- Evaluator false negatives corrected: `0`.
- Corrected case IDs: `none`.

## Semantic Metrics

```json
{
  "array_fields_valid_rate": 1.0,
  "average_latency_ms": 12420.62,
  "caption_constraints_valid_rate": 1.0,
  "case_count": 50,
  "critical_required_fact_recall": 0.7567,
  "day_number_valid_rate": 1.0,
  "enum_valid_rate": 1.0,
  "extra_field_rate": 0.0,
  "forbidden_claim_rate": 0.06,
  "hallucination_rate": 0.06,
  "hashtag_constraints_valid_rate": 1.0,
  "human_review_flag_rate": 1.0,
  "human_review_valid_rate": 1.0,
  "instruction_following_rate": 0.58,
  "insufficient_evidence_handling_rate": 0.2632,
  "item_count_valid_rate": 1.0,
  "json_parse_valid_rate": 0.82,
  "language_match_rate": 0.98,
  "median_latency_ms": 3882.0,
  "numeric_mutation_rate": 0.16,
  "numeric_preservation_rate": 0.84,
  "p95_latency_ms": 54037,
  "required_fact_recall": 0.76,
  "required_field_rate": 0.76,
  "required_fields_valid_rate": 1.0,
  "safe_uncertainty_rate": 0.2632,
  "schema_valid_rate": 1.0,
  "seven_day_plan_valid_rate": 1.0,
  "top_level_shape_valid_rate": 1.0,
  "unique_days_valid_rate": 1.0
}
```

## Grading Mode Audit

```json
{
  "business_report": {
    "exact_forbidden_claim": 19,
    "exact_or_alias_required_fact": 19,
    "language_sensitive": 3,
    "numeric_comparison": 8,
    "schema_contract": 8
  },
  "competitor_analysis": {
    "exact_forbidden_claim": 12,
    "exact_or_alias_required_fact": 22,
    "language_sensitive": 2,
    "schema_contract": 6
  },
  "content_planning": {
    "exact_forbidden_claim": 23,
    "exact_or_alias_required_fact": 32,
    "language_sensitive": 4,
    "schema_contract": 11
  },
  "safety": {
    "exact_forbidden_claim": 20,
    "exact_or_alias_required_fact": 23,
    "insufficient_evidence_concept": 8,
    "language_sensitive": 2,
    "schema_contract": 0
  },
  "strategy": {
    "exact_forbidden_claim": 12,
    "exact_or_alias_required_fact": 19,
    "language_sensitive": 2,
    "schema_contract": 6
  },
  "trend_intelligence": {
    "exact_forbidden_claim": 16,
    "exact_or_alias_required_fact": 29,
    "language_sensitive": 3,
    "numeric_comparison": 7,
    "schema_contract": 8
  }
}
```

