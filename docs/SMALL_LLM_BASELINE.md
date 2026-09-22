# Small LLM Baseline Evaluation

Evaluation date: 2026-09-21

## Models

| Field | Value |
| --- | --- |
| Logical family | Qwen3 |
| Logical base model | `Qwen/Qwen3-1.7B` |
| Runtime checkpoint | `Qwen/Qwen3-1.7B-MLX-4bit` |
| Quantization | 4-bit |
| Runtime | `mlx-lm 0.31.3` on Apple Silicon Metal |
| Production provider | Groq remains unchanged |
| Production Groq model | `openai/gpt-oss-20b` |

## Execution Scope

The direct local sanity tests passed after adding Qwen3 `/no_think` prompt handling. The 10-case pilot completed, but the full 50-case Qwen run was intentionally not executed because pilot schema validity was only `0.4` and seven-day plan validity was `0.0`.

Raw output JSONL files were written under `/private/tmp/*_eval_outputs` and are not tracked.

## Qwen Pilot vs Groq Subset

| Metric | Qwen3-1.7B local | Groq GPT-OSS-20B |
| --- | ---: | ---: |
| Cases | 10 | 10 |
| Schema validity | 0.4 | 1.0 |
| Required-field rate | 0.6667 | 0.7167 |
| Hallucination failure rate | 0.2 | 0.0 |
| Instruction-following rate | 0.1 | 0.5 |
| Language match rate | 1.0 | 1.0 |
| Human-review flag rate | 0.7 | 0.7 |
| Seven-day plan validity | 0.0 | 0.0 |
| Median latency ms | 12899 | 955 |
| P95 latency ms | 22439 | 1591 |

## Qwen Results By Task Type

```json
{
  "business_report": {
    "case_count": 2,
    "hallucination_rate": 1.0,
    "human_review_flag_rate": 1.0,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 19479,
    "p95_latency_ms": 19479,
    "required_field_rate": 1.0,
    "schema_valid_rate": 0.0,
    "seven_day_plan_valid_rate": null
  },
  "competitor_analysis": {
    "case_count": 1,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 1.0,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 3744,
    "p95_latency_ms": 3744,
    "required_field_rate": 0.5,
    "schema_valid_rate": 0.0,
    "seven_day_plan_valid_rate": null
  },
  "content_planning": {
    "case_count": 3,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 0.0,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 17938,
    "p95_latency_ms": 20744,
    "required_field_rate": 0.3889,
    "schema_valid_rate": 1.0,
    "seven_day_plan_valid_rate": 0.0
  },
  "safety": {
    "case_count": 1,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 1.0,
    "instruction_following_rate": 1.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 2022,
    "p95_latency_ms": 2022,
    "required_field_rate": 1.0,
    "schema_valid_rate": 1.0,
    "seven_day_plan_valid_rate": null
  },
  "strategy": {
    "case_count": 1,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 1.0,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 22439,
    "p95_latency_ms": 22439,
    "required_field_rate": 1.0,
    "schema_valid_rate": 0.0,
    "seven_day_plan_valid_rate": null
  },
  "trend_intelligence": {
    "case_count": 2,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 1.0,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 7341,
    "p95_latency_ms": 7341,
    "required_field_rate": 0.5,
    "schema_valid_rate": 0.0,
    "seven_day_plan_valid_rate": null
  }
}
```

## Qwen Results By Language

```json
{
  "en": {
    "case_count": 5,
    "hallucination_rate": 0.2,
    "human_review_flag_rate": 0.8,
    "instruction_following_rate": 0.2,
    "language_match_rate": 1.0,
    "median_latency_ms": 7341,
    "p95_latency_ms": 20744,
    "required_field_rate": 0.8,
    "schema_valid_rate": 0.4,
    "seven_day_plan_valid_rate": 0.0
  },
  "fr": {
    "case_count": 3,
    "hallucination_rate": 0.3333,
    "human_review_flag_rate": 0.6667,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 12899,
    "p95_latency_ms": 22439,
    "required_field_rate": 0.6667,
    "schema_valid_rate": 0.3333,
    "seven_day_plan_valid_rate": 0.0
  },
  "ru": {
    "case_count": 2,
    "hallucination_rate": 0.0,
    "human_review_flag_rate": 0.5,
    "instruction_following_rate": 0.0,
    "language_match_rate": 1.0,
    "median_latency_ms": 17938,
    "p95_latency_ms": 17938,
    "required_field_rate": 0.3333,
    "schema_valid_rate": 0.5,
    "seven_day_plan_valid_rate": 0.0
  }
}
```

## Failure Counts

| Failure category | Qwen | Groq subset |
| --- | ---: | ---: |
| MISSING_REQUIRED_FIELD | 3 | 5 |
| SCHEMA_FAILURE | 6 | 0 |

## Interpretation

Qwen3-1.7B-MLX-4bit runs locally and is responsive enough for experimentation, but the first pilot is not application-ready. It follows language instructions well and avoids the tested forbidden metric claims, but it often emits prose or alternate JSON shapes instead of the application schema.

Groq is materially stronger on schema validity in the same subset, but it also failed the current seven-day content-plan structural gate. That shared failure indicates a prompt/evaluation contract issue: the golden cases name `content_plan_v1`, while the deterministic evaluator expects the application shape with `items`, `day_number`, and `requires_human_review`.

## Viability Gates

| Gate | Threshold | Qwen pilot | Status |
| --- | ---: | ---: | --- |
| Structured JSON validity | >= 0.90 | {qsum['schema_valid_rate']} | Fail |
| Required-field compliance | >= 0.95 | {qsum['required_field_rate']} | Fail |
| Human-review flag | 1.00 | {qsum['human_review_flag_rate']} | Fail |
| Forbidden metric hallucination | 0 critical | {qsum['hallucination_rate']} | Needs review |
| 7-day structural validity | >= 0.90 | {qsum['seven_day_plan_valid_rate']} | Fail |
| Language match | >= 0.90 | {qsum['language_match_rate']} | Pass |

## Cost and Operations

Qwen local inference uses local Mac CPU/GPU, memory, disk, and time. Groq uses an external API. No billing data was measured in this evaluation, so no monetary estimate is stated.

## Recommendation

Do not deploy Qwen3-1.7B yet. Revise the evaluation/prompt schema contract first, then continue with a small LoRA experiment targeting schema discipline, human-review flags, and concise project-specific structured outputs. Keep Groq as production provider.
