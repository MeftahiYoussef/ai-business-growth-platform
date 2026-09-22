# Small LLM Baseline V2

- Evaluation date: `2026-09-21`
- Logical base model: `Qwen/Qwen3-1.7B`
- Runtime checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- Quantization: `4-bit`
- Runtime: `mlx-lm 0.31.3`
- Evaluation version: `golden_eval_v2`
- Content-plan contract: `content_plan_contract_v2`
- Final Qwen mode: `/no_think`, `temperature=0`, `EVAL_RESPONSE_FORMAT_MODE=none`
- Raw outputs: ignored local files under `ml/outputs/runs/` and `/private/tmp/`

## Evaluator Repairs

The original seven-day failure was a contract mismatch. The v1 benchmark used stale content-plan metadata and a partial evaluator gate that did not reuse the production content-plan validator.

V2 uses the Django-owned `content_plan_contract_v2` validator for production-compatible content-plan scoring. It also adds explicit evaluation-only contracts for non-content schemas (`business_report_v1`, `trend_explanation_v1`, `competitor_summary_v1`, and `strategy_v1`) so prompts and deterministic scoring agree.

Deterministic fixture tests now cover valid canonical plans, six-item plans, duplicate days, wrong enums, wrong array-field types, false human-review flags, extra top-level text, wrong top-level shape, and multilingual captions.

## Runtime Diagnostics

| Diagnostic | Result |
| --- | --- |
| Strict JSON sanity | Passed |
| English/French/Russian language sanity | Passed |
| No invented reach/impressions sanity | Passed |
| `/no_think` vs thinking | `/no_think` was faster and did not regress schema behavior |
| Temperature `0` vs `0.2` | No material quality improvement; `0` kept for deterministic baseline |
| MLX `response_format=json_object` | Accepted |
| MLX `response_format=json_schema` | Accepted but not enforced |
| Groq rate limits | Handled by checkpoint/resume; 429s are not scored as quality failures |

## Groq Reference

The clean Groq reference uses the same 10 representative case IDs as the Qwen pilot. Provider-side strict JSON Schema caused HTTP 400 on some non-content schemas, so the clean quality reference used prompt-only JSON mode and deterministic post-validation.

| Metric | Groq `openai/gpt-oss-20b` |
| --- | ---: |
| Cases | 10 |
| JSON parse validity | 0.9 |
| Schema validity | 1.0 |
| Seven-day validity | 1.0 |
| Human-review flag | 1.0 |
| Hallucination rate | 0.0 |
| Language match | 1.0 |
| Median latency ms | 1044 |
| P95 latency ms | 3110 |

Groq still had four required-fact misses in deterministic scoring, but no schema mismatch remains for the content-plan contract.

## Qwen Base 10-Case Pilot

| Metric | Qwen base |
| --- | ---: |
| Cases | 10 |
| JSON parse validity | 0.9 |
| Schema validity | 0.6 |
| Seven-day validity | 0.0 |
| Human-review flag | 1.0 |
| Hallucination rate | 0.1 |
| Language match | 1.0 |
| Median latency ms | 6588.5 |
| P95 latency ms | 51806 |

Main failures: three `FIELD_TYPE_FAILURE` content-plan outputs and two `MISSING_REQUIRED_FIELD` non-content outputs.

## Qwen Base 50-Case Frozen Benchmark

| Metric | Qwen base |
| --- | ---: |
| Cases | 50 |
| JSON parse validity | 0.8 |
| Schema validity | 0.76 |
| Seven-day validity | 0.0 |
| Human-review flag | 1.0 |
| Hallucination rate | 0.08 |
| Forbidden-claim rate | 0.06 |
| Language match | 0.98 |
| Median latency ms | 4929 |
| P95 latency ms | 44819 |

Failure counts:

```json
{
  "FIELD_TYPE_FAILURE": 8,
  "INVALID_7_DAY_PLAN": 3,
  "MISSING_REQUIRED_FIELD": 19
}
```

## Task Breakdown

| Task | Cases | Schema Validity | Instruction Following | Hallucination Rate | Median Latency ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| content_planning | 11 | 0.0 | 0.0 | 0.0 | 37888 |
| business_report | 8 | 0.875 | 0.5 | 0.125 | 3274 |
| trend_intelligence | 8 | 1.0 | 0.75 | 0.0 | 5895.5 |
| competitor_analysis | 6 | 1.0 | 0.6667 | 0.0 | 4682 |
| strategy | 6 | 1.0 | 0.8333 | 0.0 | 8118.5 |
| safety | 11 | 1.0 | 0.0909 | 0.2727 | 2043 |

## Language Breakdown

| Language | Cases | Schema Validity | Language Match | Hallucination Rate |
| --- | ---: | ---: | ---: | ---: |
| English | 34 | 0.7647 | 1.0 | 0.0588 |
| French | 9 | 0.7778 | 0.8889 | 0.1111 |
| Russian | 7 | 0.7143 | 1.0 | 0.1429 |

## Trainability Decision

The remaining Qwen failures are mostly behavioral: JSON field typing, exact top-level fields, seven unique items, and concise instruction following. These are reasonable LoRA targets. They are not RAG targets and should not be solved by weakening validators.

LoRA v1 was therefore allowed after this baseline, using synthetic behavior examples only and keeping the frozen golden set untouched.
