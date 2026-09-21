# Small LLM Failure Analysis V2

- Evaluation version: `golden_eval_v2`
- Model: `Qwen/Qwen3-1.7B-MLX-4bit`
- Scope: corrected 10-case pilot only; full 50-case and LoRA were not run.

## Failure Taxonomy

```json
{
  "INVALID_7_DAY_PLAN": 3,
  "PASS": 1,
  "SCHEMA_FAILURE": 6
}
```

## Product-Relevant Failures

- `cp-en-001` (content_planning, en): `INVALID_7_DAY_PLAN` -> `FINE_TUNING`
- `cp-fr-001` (content_planning, fr): `INVALID_7_DAY_PLAN` -> `FINE_TUNING`
- `cp-ru-001` (content_planning, ru): `INVALID_7_DAY_PLAN` -> `FINE_TUNING`
- `report-en-001` (business_report, en): `SCHEMA_FAILURE` -> `DETERMINISTIC_CODE`
- `report-fr-001` (business_report, fr): `SCHEMA_FAILURE` -> `DETERMINISTIC_CODE`
- `trend-en-001` (trend_intelligence, en): `SCHEMA_FAILURE` -> `FINE_TUNING`
- `trend-ru-001` (trend_intelligence, ru): `SCHEMA_FAILURE` -> `FINE_TUNING`
- `competitor-en-001` (competitor_analysis, en): `SCHEMA_FAILURE` -> `FINE_TUNING`
- `strategy-fr-001` (strategy, fr): `SCHEMA_FAILURE` -> `FINE_TUNING`

## Fix Target Classification

- Fine-tuning candidates: strict JSON discipline, complete production content-plan field coverage, seven unique days, and multilingual structured formatting.
- RAG candidates: none from this pilot. The failures were not caused by missing dynamic business knowledge.
- Deterministic-code candidates: none from content planning. Numeric/report invariants should remain deterministic application checks.
- Prompt/evaluator candidates: Groq rate limiting prevented a complete 10-case reference run; retry after quota resets before training.
