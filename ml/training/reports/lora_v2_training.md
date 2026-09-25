# Qwen3-1.7B LoRA v2 Training

Date: 2026-09-23

## Scope

This was one controlled semantic-alignment LoRA experiment for `Qwen/Qwen3-1.7B`.
It did not implement RAG, did not deploy a model, and did not modify staging.

## Inputs

- Dataset version: `qwen3_sft_v2`
- Accepted hash: `d5585e53ef00db3d31871d015b0f975b10d6796f07b965c315573440c670bd18`
- Train hash: `82405f00422db433c0520683f9adbb9ba09922351f13422e7c4c70a6c0d6111d`
- Validation hash: `8b73713cf18b76d12f79ac245012e13b6f30d5049f76b7bb2c4a675d169b342b`
- Train records: `324`
- Validation records: `36`
- Config: `ml/training/qwen3_1_7b_lora_v2.yaml`
- Config SHA-256: `3a904c2aea362e476954b318f8bcd04dcbbf66401c8c57555cbf690c75203b70`

MLX-LM requires a non-empty `test.jsonl` while loading a local data directory.
The frozen repository dataset was not changed. Training used a temporary local
view under `/private/tmp/qwen3_sft_v2_mlx_lora_data` with unchanged train and
valid files and a copied validation file as `test.jsonl`; `--test` was not used.

## Environment

- macOS: `26.2`
- Architecture: `arm64`
- Python: `3.11.8`
- MLX-LM: `0.31.3`
- Training checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`

## Hyperparameters

- Fine-tune type: `lora`
- Rank: `8`
- Alpha / scale: `16.0`
- Dropout: `0.0`
- Optimizer: `adamw`
- Learning rate: `0.00005`
- Batch size: `1`
- Gradient accumulation: `8`
- Max sequence length: `4096`
- Iterations: `240`
- Validation cadence: every `40` steps
- Save cadence: every `120` steps
- Seed: `20260922`
- Adapter output: `ml/outputs/adapters/qwen3_1_7b_lora_v2/`

## Training Result

- Trainable parameters: `4.981M / 1720.575M`
- Trainable percentage: `0.289%`
- Start: `2026-09-23T07:08:11Z`
- End: `2026-09-23T07:18:51Z`
- Duration: approximately `10m40s`
- Final train loss: `0.025`
- Final validation loss: `0.023`
- Peak memory: `1.791 GB`
- Final trained tokens: `23876`
- Final tokens/sec: `68.143`

Loss was stable, but loss is diagnostic only. LoRA v1 already showed that low
loss does not imply benchmark improvement.

## Adapter Status

The adapter was written only to the ignored local path:

```text
ml/outputs/adapters/qwen3_1_7b_lora_v2/
```

The adapter is not committed and is not promoted.
