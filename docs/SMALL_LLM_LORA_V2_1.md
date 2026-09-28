# Small LLM LoRA v2.1 Experiment

Status: `rejected`

This document records the second semantic-alignment LoRA experiment for
`Qwen/Qwen3-1.7B`. The adapter is not deployed, not promoted, and not committed.

## Context

LoRA v2 was rejected because it improved caution while collapsing supplied-fact
retention and causing generation degeneration. The v2.1 experiment changed the
SFT curriculum only:

- v2 dataset: `qwen3_sft_v2`
- v2.1 dataset: `qwen3_sft_v2_1`

The training recipe remained comparable to v2.

## Dataset

- Dataset version: `qwen3_sft_v2_1`
- Accepted examples: `180`
- Train examples: `162`
- Validation examples: `18`
- EN / FR / RU: `72 / 54 / 54`
- Exact duplicates: `0`
- Near duplicates: `0`
- Golden leakage: `0`
- Max response-template share: `0.0444`

Frozen hashes:

- Accepted: `0a728f77941461be653c5f10f2acf3b9e3175d4d6ce8d70ae1a5b042ab94870e`
- Train: `f345b44453ab39f918df26be8def4e65ece07a9528bac1114a2dc688f68b1843`
- Validation: `4fbdb0101fb7de7fe6ddc6d6a6e28839c0f9ba3d0d7e50884f969063b70f8fc3`

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
- Final train loss: `0.023`
- Final validation loss: `0.027`
- Peak memory: `1.868 GB`
- Adapter path: `ml/outputs/adapters/qwen3_1_7b_lora_v2_1/`

Loss is recorded only as telemetry. It is not evidence of quality.

## Pilot Result

The 10-case pilot compared base Qwen, rejected LoRA v2, and LoRA v2.1 under the
same MLX runtime where possible.

| Metric | Base MLX | LoRA v2 | LoRA v2.1 |
| --- | ---: | ---: | ---: |
| Required-fact recall | `0.6750` | `0.3333` | `0.6000` |
| Critical-fact recall | `0.7000` | `0.3000` | `0.6000` |
| Hallucination rate | `0.3000` | `0.1000` | `0.4000` |
| Forbidden-claim rate | `0.2000` | `0.0000` | `0.3000` |
| Numeric preservation | `0.7143` | `0.7143` | `0.8571` |
| Numeric mutation | `0.2857` | `0.2857` | `0.1429` |
| Insufficient-evidence handling | `0.4000` | `0.6000` | `0.8000` |
| Safe uncertainty | `0.4000` | `0.6000` | `0.4000` |
| Selective uncertainty | `0.0000` | `0.0000` | `0.2000` |
| Known-fact retention under uncertainty | `0.5000` | `0.4444` | `0.5000` |
| Language match | `1.0000` | `0.9000` | `0.9000` |
| Median latency | `4958.5 ms` | `31267.0 ms` | `2299.5 ms` |
| Digit-run failures | `0` | `3` | `0` |
| Repetition failures | `0` | `1` | `0` |

LoRA v2.1 fixed the obvious v2 generation degeneration and improved numeric
preservation. It still failed the pilot gate because required-fact recall and
critical-fact recall regressed versus base, hallucination worsened versus base,
and selective uncertainty remained far below target.

The full 50-case evaluation was intentionally not run.

## Decision

Decision: `REJECT LORA V2.1`

Do not integrate this adapter with constrained serving.
Do not deploy it.
Do not use it as a base for production behavior.

## Next Research Direction

Another 1.7B SFT iteration is not justified immediately. Two SFT curricula have
failed to produce useful semantic behavior under the current setup:

- v2 over-learned global caution and degenerated.
- v2.1 removed degeneration but did not beat base on the primary semantic gate.

The next phase should benchmark whether the same semantic benchmark is
capacity-limited by testing `Qwen/Qwen3-4B` locally before designing another
training curriculum.

RAG is not the immediate next phase. The current failure is behavioral and
capacity-related, not missing dynamic business knowledge.
