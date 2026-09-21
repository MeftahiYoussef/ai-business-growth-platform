# Small LLM Baseline V2

- Evaluation timestamp: `2026-09-21T08:06:14Z`
- Logical base model: `Qwen/Qwen3-1.7B`
- Runtime checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- Quantization: `4-bit`
- Runtime: `mlx-lm`
- Evaluation version: `golden_eval_v2`
- Content-plan contract: `content_plan_contract_v2`
- Raw outputs: local files under `/private/tmp/qwen_eval_outputs_v2/` only; not committed.

## Root Cause Fixed From V1

The first baseline used stale content-plan evaluation metadata and a partial seven-day gate that did not reuse the production validator. V2 moves the schema to the Django application contract, updates content-planning golden metadata, and has the evaluator call the production-compatible validator. The evaluator token budget was also raised from 2,048 to 4,096 because the canonical seven-item payload can exceed the old benchmark cap.

## Qwen 10-Case Contract Pilot

```json
{
  "case_count": 10,
  "hallucination_rate": 0.2,
  "human_review_flag_rate": 0.7,
  "instruction_following_rate": 0.1,
  "language_match_rate": 1.0,
  "median_latency_ms": 11881.5,
  "p95_latency_ms": 50459,
  "schema_valid_rate": 0.1,
  "seven_day_plan_valid_rate": 0.0
}
```

Failure counts:

```json
{
  "INVALID_7_DAY_PLAN": 3,
  "PASS": 1,
  "SCHEMA_FAILURE": 6
}
```

## By Task Type

```json
{
  "business_report": {
    "case_count": 2,
    "failure_counts": {
      "SCHEMA_FAILURE": 2
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  },
  "competitor_analysis": {
    "case_count": 1,
    "failure_counts": {
      "SCHEMA_FAILURE": 1
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  },
  "content_planning": {
    "case_count": 3,
    "failure_counts": {
      "INVALID_7_DAY_PLAN": 3
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  },
  "safety": {
    "case_count": 1,
    "failure_counts": {
      "PASS": 1
    },
    "instruction_following_rate": 1.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 1.0
  },
  "strategy": {
    "case_count": 1,
    "failure_counts": {
      "SCHEMA_FAILURE": 1
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  },
  "trend_intelligence": {
    "case_count": 2,
    "failure_counts": {
      "SCHEMA_FAILURE": 2
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  }
}
```

## By Language

```json
{
  "en": {
    "case_count": 5,
    "failure_counts": {
      "INVALID_7_DAY_PLAN": 1,
      "PASS": 1,
      "SCHEMA_FAILURE": 3
    },
    "instruction_following_rate": 0.2,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.2
  },
  "fr": {
    "case_count": 3,
    "failure_counts": {
      "INVALID_7_DAY_PLAN": 1,
      "SCHEMA_FAILURE": 2
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  },
  "ru": {
    "case_count": 2,
    "failure_counts": {
      "INVALID_7_DAY_PLAN": 1,
      "SCHEMA_FAILURE": 1
    },
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "schema_valid_rate": 0.0
  }
}
```

## Groq Contract Check

- `cp-en-001`: strict schema request returned HTTP 200 and scored `seven_day_plan_valid=true` in an isolated run.
- `cp-fr-001`: strict schema request returned HTTP 200 and scored `seven_day_plan_valid=true` in an isolated run.
- `cp-ru-001`: strict schema diagnostic returned HTTP 200 with the canonical response format.
- The full 10-case Groq comparison was stopped by provider HTTP 429 rate limiting. No further Groq calls were made after the rate-limit diagnosis.

## Gate Decision

LoRA training was not started. Qwen completed the corrected pilot, but the representative result remains too unstable for a clean full 50-case baseline: content-plan structural validity stayed at `0.0`, overall schema validity was `0.1`, and the Groq comparison set could not complete because of rate limiting. Training now would blur evaluator repair, provider-rate-limit noise, and real model behavior.
