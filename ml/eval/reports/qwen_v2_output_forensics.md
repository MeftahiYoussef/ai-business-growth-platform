# Qwen V2 Output Forensics

- Source run: `/private/tmp/qwen_eval_outputs_v2/local-Qwen_Qwen3-1.7B-MLX-4bit-20260921-080435.jsonl`
- Cases analyzed: `10`
- Full model outputs are intentionally not copied into this tracked report.
- The analysis uses `content_plan_contract_v2` and the production-compatible validator adapter.

## Counts

```json
{
  "numeric_or_forbidden_hallucination": 2,
  "schema_or_format": 6,
  "valid_json": 3,
  "wrong_array_field_type": 3
}
```

## Key Finding

- The three content-plan outputs were strict JSON and used the canonical top-level object.
- They each produced exactly seven unique days with valid enums and `requires_human_review=true`.
- They failed production validation because `source_context` was emitted as a string instead of an array on every item.
- This points to behavioral field-type/instruction following, not the earlier stale seven-day evaluator mismatch.

## Case Classification

| Case | Task | Language | Failure | Flags | Likely Root | Latency ms | Output chars |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| `cp-en-001` | `content_planning` | `en` | `FIELD_TYPE_FAILURE` | `wrong_array_field_type` | `FINE_TUNING_OR_PROMPT` | `42004` | `5975` |
| `cp-fr-001` | `content_planning` | `fr` | `FIELD_TYPE_FAILURE` | `wrong_array_field_type` | `FINE_TUNING_OR_PROMPT` | `43705` | `5518` |
| `cp-ru-001` | `content_planning` | `ru` | `FIELD_TYPE_FAILURE` | `wrong_array_field_type` | `FINE_TUNING_OR_PROMPT` | `50459` | `4764` |
| `report-en-001` | `business_report` | `en` | `SCHEMA_FAILURE` | `not_strict_json, hallucination_or_numeric_mutation, schema_or_format` | `FINE_TUNING` | `18486` | `3226` |
| `report-fr-001` | `business_report` | `fr` | `SCHEMA_FAILURE` | `not_strict_json, hallucination_or_numeric_mutation, schema_or_format` | `FINE_TUNING` | `5277` | `465` |
| `trend-en-001` | `trend_intelligence` | `en` | `SCHEMA_FAILURE` | `not_strict_json, schema_or_format` | `FINE_TUNING` | `3511` | `590` |
| `trend-ru-001` | `trend_intelligence` | `ru` | `SCHEMA_FAILURE` | `not_strict_json, schema_or_format` | `FINE_TUNING` | `4308` | `473` |
| `competitor-en-001` | `competitor_analysis` | `en` | `SCHEMA_FAILURE` | `not_strict_json, schema_or_format` | `FINE_TUNING` | `4289` | `536` |
| `strategy-fr-001` | `strategy` | `fr` | `SCHEMA_FAILURE` | `not_strict_json, schema_or_format` | `FINE_TUNING` | `23497` | `2872` |
| `safety-en-001` | `safety` | `en` | `PASS` | `not_strict_json` | `PASS` | `1805` | `288` |

## Truncation Notes

- The v2 pilot did not capture provider finish reasons before checkpoint hardening.
- Content-plan responses were complete parseable JSON despite their high latency and length.
- The longest non-content response was likely verbose prose, not a mid-JSON truncation.
- Future resumed runs persist per-case state and distinguish provider/rate-limit failures from model-quality failures.
