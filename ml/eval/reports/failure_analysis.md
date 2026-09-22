# Small LLM Failure Analysis

Evaluation date: 2026-09-21

## Corrected Root Cause

The old seven-day gate failure was primarily an evaluator/schema-contract mismatch. After `content_plan_contract_v2`, Groq content-plan outputs pass the production validator.

Qwen base v2 still fails product-critical content planning because it emits `source_context` as a string instead of an array and sometimes misses seven-day completeness. That is a model behavior/curriculum issue, not a production-validator bug.

## Qwen Base V2 Failure Counts

```json
{
  "FIELD_TYPE_FAILURE": 8,
  "INVALID_7_DAY_PLAN": 3,
  "MISSING_REQUIRED_FIELD": 19
}
```

## Top Product-Relevant Failures

1. Content plans: `source_context` and sometimes `risk_flags` must be arrays, not strings.
2. Content plans: every output must keep exactly seven `items`.
3. Content plans: day numbers must cover 1 through 7 exactly once.
4. Report tasks: some outputs miss required top-level contract fields.
5. Safety tasks: required facts are often omitted even when the answer refuses unsupported claims.
6. French tasks: one language-match failure remains in the frozen 50-case run.
7. Russian tasks: hallucination and forbidden-claim failures still appear in safety-style prompts.
8. Long content-plan generations are slow and remain the highest-latency category.
9. Provider-side strict JSON Schema is not portable across local MLX and Groq; deterministic post-validation remains required.
10. LoRA v1 did not improve structural behavior on the 10-case pilot.

## Failure Target Classification

| Target | Failures |
| --- | --- |
| Fine-tuning/curriculum | exact JSON fields, array field typing, seven-item discipline, required facts, multilingual structure |
| Prompt/code contract | concise schema reminders, prompt-only JSON mode for fair local/Groq comparison |
| Deterministic code | numeric metrics, trend scores, quotas, ownership, business counts |
| RAG | dynamic business facts, current trends, competitors, historical reports, uploaded documents |

No current failure justifies implementing RAG before improving schema/curriculum quality.

## SFT Candidate Set

- Candidate source: `ml/datasets/candidates/qwen3_sft_v1_candidates.jsonl`
- Candidate count: `180`
- Content-plan examples: `54`, all pass `content_plan_contract_v2`
- Train split: `153`
- Validation split: `18`
- Local MLX test split: `9`
- Frozen golden evaluation set: untouched and not used for training

## LoRA V1 Result

LoRA v1 trained successfully but did not improve the 10-case structural pilot:

| Metric | Base Qwen | LoRA v1 |
| --- | ---: | ---: |
| Schema validity | 0.6 | 0.6 |
| Seven-day validity | 0.0 | 0.0 |
| Hallucination rate | 0.1 | 0.1 |
| Language match | 1.0 | 1.0 |

The next model phase should revise the SFT curriculum and prompt contract before another LoRA run. Qwen3-4B should wait until the 1.7B curriculum is no longer the obvious blocker.
