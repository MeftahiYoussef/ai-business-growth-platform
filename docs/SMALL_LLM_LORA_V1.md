# Qwen3-1.7B LoRA V1 Experiment

- Date: `2026-09-21`
- Base model identity: `Qwen/Qwen3-1.7B`
- Training/runtime checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- Runtime: `mlx-lm 0.31.3`
- Adapter path: `ml/outputs/adapters/qwen3_1_7b_lora_v1/` (ignored, not committed)
- Goal: behavior alignment for schemas, JSON-only output, multilingual structure, no invented metrics
- Not a goal: knowledge injection, business fact memorization, RAG, production deployment

## Dataset

The stale 120-record SFT candidate set was rejected because content-plan examples used the old partial shape. It was replaced with 180 deterministic synthetic examples.

| Split | Count |
| --- | ---: |
| Train | 153 |
| Validation | 18 |
| Local MLX test | 9 |

Distribution:

| Task | Count |
| --- | ---: |
| content_planning | 54 |
| business_report | 36 |
| trend_intelligence | 27 |
| competitor_analysis | 18 |
| strategy | 27 |
| safety | 18 |

Languages are balanced: 60 English, 60 French, 60 Russian. All 54 content-plan assistant answers pass `content_plan_contract_v2`.

The frozen `golden_eval_v2` test set was not used for training.

## Training Settings

| Setting | Value |
| --- | --- |
| Fine-tune type | LoRA |
| Trainable parameters | 4.981M / 1.720B, about 0.289% |
| Batch size | 1 |
| Gradient accumulation | 8 |
| Iterations | 120 |
| Learning rate | 0.0001 |
| Max sequence length | 4096 |
| Layers | 16 |
| Mask prompt | true |
| Gradient checkpointing | true |
| Seed | 20260921 |
| Peak memory | about 3.764 GB |

Loss telemetry:

| Iteration | Train Loss | Validation Loss |
| ---: | ---: | ---: |
| 1 | n/a | 0.880 |
| 40 | 0.677 | 0.336 |
| 80 | 0.074 | 0.128 |
| 120 | 0.063 | 0.054 |

Training loss is not treated as quality proof. The frozen evaluator decides quality.

## Post-Training Sanity

The adapter passed direct sanity checks:

- strict JSON
- English response
- French response
- Russian response
- no invented reach or impressions when unavailable

## 10-Case Pilot Comparison

The adapter was evaluated on the same 10-case subset as the base Qwen pilot and Groq reference.

| Metric | Base Qwen | LoRA v1 | Delta |
| --- | ---: | ---: | ---: |
| Schema validity | 0.6 | 0.6 | 0.0 |
| Seven-day validity | 0.0 | 0.0 | 0.0 |
| JSON parse validity | 0.9 | 0.9 | 0.0 |
| Human-review flag | 1.0 | 1.0 | 0.0 |
| Hallucination rate | 0.1 | 0.1 | 0.0 |
| Language match | 1.0 | 1.0 | 0.0 |
| Median latency ms | 6588.5 | 3058 | improved |
| P95 latency ms | 51806 | 24463 | improved |

Failure counts remained unchanged:

```json
{
  "FIELD_TYPE_FAILURE": 3,
  "MISSING_REQUIRED_FIELD": 2
}
```

## Groq Reference

On the same 10 cases, Groq in prompt-only JSON mode scored:

| Metric | Groq |
| --- | ---: |
| Schema validity | 1.0 |
| Seven-day validity | 1.0 |
| Hallucination rate | 0.0 |
| Language match | 1.0 |
| Median latency ms | 1044 |

## Decision

Do not continue with this LoRA v1 adapter as-is. The adapter did not improve the product-critical structural failures, despite lower latency in the pilot.

Recommended next step: fix the SFT curriculum and prompt contract before another LoRA run. Add more examples that directly teach:

- `source_context` and `risk_flags` as arrays
- exact top-level fields for non-content contracts
- seven unique day objects
- no prose around JSON
- safety responses that still include required facts without forbidden claims

Do not benchmark Qwen3-4B yet. The current failure mode remains mostly curriculum/prompt/serving-constraint related, not proven model-capacity failure.

## Constrained-Decoding Follow-Up

The next experiment used base `Qwen/Qwen3-1.7B` through `llama.cpp` with
`Qwen3-1.7B-Q4_K_M.gguf` and enforced JSON Schema. It did not load or evaluate
the LoRA v1 adapter.

That experiment showed:

- 10-case schema validity: `0.1` unconstrained -> `1.0` constrained
- 10-case seven-day validity: `0.0` unconstrained -> `1.0` constrained
- 10-case hallucination rate remained `0.0`
- full 50-case constrained schema validity: `1.0`
- full 50-case constrained instruction-following rate: `0.58`

This confirms that LoRA v1 tried to solve a structural problem better handled
by constrained decoding. LoRA v2 should not be trained until the SFT curriculum
is redesigned around semantic fidelity, safety refusal behavior, multilingual
instruction following, and required-fact coverage.

Detailed follow-up reports:

```text
ml/eval/reports/llama_cpp_constrained_decoding.md
ml/training/reports/lora_v1_failure_analysis.md
```
