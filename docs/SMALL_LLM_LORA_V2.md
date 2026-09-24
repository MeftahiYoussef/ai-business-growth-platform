# Small LLM LoRA v2 Experiment

Status: `rejected`

This document records the first semantic-alignment LoRA v2 experiment for
`Qwen/Qwen3-1.7B`. The adapter is not deployed, not promoted, and not committed.

## Context

Constrained llama.cpp decoding solved structural generation for Qwen3-1.7B:

- Schema validity: `1.00`
- Seven-day validity: `1.00`
- Human-review validity: `1.00`

The remaining problem was semantic behavior: fact retention, numeric
preservation, insufficient-evidence handling, and multilingual reliability.

## Dataset

- Dataset version: `qwen3_sft_v2`
- Accepted examples: `360`
- Train examples: `324`
- Validation examples: `36`
- EN / FR / RU: `144 / 108 / 108`
- Exact duplicates: `0`
- Near duplicate rate: `0.0`
- Golden leakage: `0`

Frozen hashes:

- Accepted: `d5585e53ef00db3d31871d015b0f975b10d6796f07b965c315573440c670bd18`
- Train: `82405f00422db433c0520683f9adbb9ba09922351f13422e7c4c70a6c0d6111d`
- Validation: `8b73713cf18b76d12f79ac245012e13b6f30d5049f76b7bb2c4a675d169b342b`

## Training

- Runtime: MLX-LM `0.31.3`
- Training checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- LoRA rank: `8`
- Scale: `16.0`
- Dropout: `0.0`
- Learning rate: `0.00005`
- Batch size: `1`
- Gradient accumulation: `8`
- Iterations: `240`
- Final train loss: `0.025`
- Final validation loss: `0.023`
- Peak memory: `1.791 GB`

Loss was stable but did not predict semantic improvement.

## Evaluation

The fair pilot compared:

- Base Qwen3-1.7B via MLX
- Qwen3-1.7B + LoRA v2 via the same MLX runtime

Historical llama.cpp constrained scores were not used as the control arm because
that would confound runtime and adapter effects.

The 10-case pilot failed the stop gate:

- Required-fact recall regressed from `0.6750` to `0.3333`.
- Critical required-fact recall regressed from `0.7000` to `0.3000`.
- Language match regressed from `1.0000` to `0.9000`.
- Median latency increased from `4896.5 ms` to `31267.0 ms`.
- Hallucination improved from `0.3000` to `0.1000`, but the improvement came
  with over-uncertainty and loss of supplied facts.

The full 50-case benchmark was not run.

## Decision

Decision: `REJECT LORA V2`

Do not integrate this adapter with constrained serving.
Do not deploy it.
Do not use it as a base for production behavior.

## Next Research Direction

The next phase should not train another adapter immediately.

Recommended next work:

1. Inspect LoRA v2 outputs for over-uncertainty and phrase memorization.
2. Build a smaller adversarial validation set specifically for fact retention
   versus safe uncertainty.
3. Revise the semantic SFT curriculum to reward retaining supplied facts while
   still refusing unsupported claims.
4. Only then consider `LoRA v2.1`.

Qwen3-4B is not yet justified. RAG is not yet justified for this failure mode;
the current regression is behavioral, not missing dynamic knowledge.
