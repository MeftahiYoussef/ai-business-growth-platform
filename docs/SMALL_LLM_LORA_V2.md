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

## Failure Forensics

Follow-up output forensics confirmed that LoRA v2 improved caution at the
expense of supplied-fact retention:

- Paired pilot outputs analyzed: `10`
- Required-fact failures in LoRA output:
  `FACT_DROPPED=9`, `FACT_MUTATED=2`,
  `FACT_REPLACED_WITH_RECOMMENDATION=9`
- Critical-fact failures in LoRA output:
  `FACT_DROPPED=5`, `FACT_MUTATED=2`,
  `FACT_REPLACED_WITH_RECOMMENDATION=8`
- Correct uncertainty improved from `0.4` to `0.6`, but selective uncertainty
  remained `0.0`.
- Known-fact retention under uncertainty regressed from `0.5` to `0.25`.
- Long digit-run cases increased from `0` to `3`.
- Median latency increased from `4896.5 ms` to `31267.0 ms`.

The latency regression is not treated as normal adapter overhead. Several LoRA
outputs show generation degeneration, including long numeric runs and repeated
fragments that likely ran to the token budget.

The SFT v2 dataset was lexically unique but semantically repetitive:

- Every accepted SFT v2 record included uncertainty language.
- `60%` of records included refusal-style language.
- The three localized fact/limitation/recommendation label skeletons covered
  the entire dataset.

This supports the conclusion that the adapter learned a broad caution template
instead of the desired policy:

1. preserve known facts,
2. qualify only missing facts,
3. remain helpful with concise recommendations.

## V2.1 Candidate Curriculum

`qwen3_sft_v2_1` has been prepared for review only. LoRA v2.1 has not been
trained.

- Candidate examples: `192`
- Accepted examples: `180`
- Rejected controls: `12`
- Train / validation: `162 / 18`
- EN / FR / RU: `72 / 54 / 54`
- Exact duplicates: `0`
- Near duplicates: `0`
- Golden leakage: `0`
- Max response-template share: `0.0444`

Frozen hashes:

- Accepted:
  `0a728f77941461be653c5f10f2acf3b9e3175d4d6ce8d70ae1a5b042ab94870e`
- Train:
  `f345b44453ab39f918df26be8def4e65ece07a9528bac1114a2dc688f68b1843`
- Validation:
  `4fbdb0101fb7de7fe6ddc6d6a6e28839c0f9ba3d0d7e50884f969063b70f8fc3`

The v2.1 curriculum targets selective uncertainty and known-fact retention under
missing data. It intentionally remains smaller than v2 and does not teach JSON
formatting.

## Next Research Direction

The next phase may train exactly one `LoRA v2.1` adapter only after reviewing
the candidate curriculum and confirming the group-aware split is acceptable.

Qwen3-4B is not yet justified. RAG is not yet justified for this failure mode;
the current regression is behavioral, not missing dynamic knowledge.
