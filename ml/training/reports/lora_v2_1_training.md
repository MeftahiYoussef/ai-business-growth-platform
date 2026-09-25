# LoRA v2.1 Training Report

Status: `completed`

Promotion status: `rejected after pilot`

## Reproducibility

- Base model: `Qwen/Qwen3-1.7B`
- Training checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- MLX-LM version: `0.31.3`
- macOS: `26.2`
- Architecture: `arm64`
- Python: `3.11.8`
- Dataset version: `qwen3_sft_v2_1`
- Config: `ml/training/qwen3_1_7b_lora_v2_1.yaml`
- Config hash: `320b84962ca00a09b0339bf338c21bcf2a9e9b0d6c5189a69f9e5d64c7c3c8e1`
- Seed: `20260922`
- Adapter path: `ml/outputs/adapters/qwen3_1_7b_lora_v2_1/`

Dataset hashes:

- Accepted: `0a728f77941461be653c5f10f2acf3b9e3175d4d6ce8d70ae1a5b042ab94870e`
- Train: `f345b44453ab39f918df26be8def4e65ece07a9528bac1114a2dc688f68b1843`
- Validation: `4fbdb0101fb7de7fe6ddc6d6a6e28839c0f9ba3d0d7e50884f969063b70f8fc3`

## Configuration

- LoRA rank: `8`
- Scale: `16.0`
- Dropout: `0.0`
- Optimizer: `adamw`
- Learning rate: `0.00005`
- Batch size: `1`
- Gradient accumulation: `8`
- Max sequence length: `4096`
- Iterations: `240`
- Validation batches: `-1`
- Evaluation cadence: every `40` iterations
- Save cadence: every `120` iterations
- Fine-tuned layers: `16`
- Mask prompt: `true`
- Gradient checkpointing: `true`

This intentionally matches the LoRA v2 recipe except for the dataset path.

## Telemetry

- Trainable parameters: `4.981M / 1.720B`
- Trainable percentage: `0.289%`
- Approximate training duration: `~9-10 minutes`
- Peak memory: `1.868 GB`
- Final trained tokens: `27519`
- Final reported tokens/sec: `56.703`

Loss progression:

| Iteration | Train Loss | Validation Loss |
| ---: | ---: | ---: |
| 1 | n/a | `3.354` |
| 40 | `1.046` | `1.045` |
| 80 | `0.188` | `0.201` |
| 120 | `0.162` | `0.135` |
| 160 | `0.071` | `0.050` |
| 200 | `0.030` | `0.037` |
| 240 | `0.023` | `0.027` |

The low validation loss did not establish success. The semantic pilot remained
authoritative.

## Artifact Handling

Adapter files were written only to the ignored path:

`ml/outputs/adapters/qwen3_1_7b_lora_v2_1/`

No adapter weights, fused model files, model weights, GGUF files, or caches are
committed.
