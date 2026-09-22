# Small LLM, Fine-Tuning, and RAG Foundation

This track is experimental. It does not replace the live Groq provider.

## Current Decision

- Production/staging provider: Groq
- Production/staging model: `openai/gpt-oss-20b`
- Experimental small model: `Qwen/Qwen3-1.7B`
- Local runtime checkpoint: `Qwen/Qwen3-1.7B-MLX-4bit`
- Local quantization: 4-bit
- Model family: `qwen3`
- Model role: `experimental_small_llm`
- Baseline version: `baseline`
- License: Apache-2.0

Future benchmark candidates are documented only:

- `HuggingFaceTB/SmolLM3-3B`
- `Qwen/Qwen3-4B`

Only `Qwen/Qwen3-1.7B` is selected for the first baseline.

## Why Qwen3-1.7B

`Qwen/Qwen3-1.7B` is small enough for local experimentation while still being
instruction-tuned for chat-style application tasks. The first objective is to
establish a reproducible local baseline for structured outputs, multilingual
behavior, refusal to fabricate metrics, and future LoRA/RAG work.

Use the instruction-tuned checkpoint for application evaluation. Do not switch
to `Qwen3-1.7B-Base` for this baseline.

## Local Runtime

On Apple Silicon, prefer MLX-LM:

```bash
pip install "mlx-lm[train]"
mlx_lm.server \
  --model Qwen/Qwen3-1.7B-MLX-4bit \
  --host 127.0.0.1 \
  --port 8080 \
  --chat-template-args '{"enable_thinking":false}'
```

The Django provider and model lab both expect an OpenAI-compatible local server:

```env
LOCAL_LLM_ENABLED=false
LOCAL_LLM_BASE_URL=http://127.0.0.1:8080/v1
LOCAL_LLM_MODEL=Qwen/Qwen3-1.7B
LOCAL_LLM_TIMEOUT_SECONDS=120
LOCAL_LLM_MAX_OUTPUT_TOKENS=2048
LOCAL_LLM_DISABLE_THINKING=true
```

These settings are server-side only. They must never use `NEXT_PUBLIC_`.

## Provider Boundary

The experimental provider is implemented in:

```text
django-backend/apps/ai/providers/local_llm_provider.py
```

It is intentionally separate from the production provider factory. Groq remains
the default, and a missing Groq key must not silently switch the application to
the local model.

## Evaluation

The model lab lives under:

```text
ml/
```

The golden evaluation dataset is synthetic and non-private:

```text
ml/eval/cases/golden.jsonl
```

Current baseline size:

```text
50 cases
```

Task categories:

- content planning
- business reports
- trend intelligence
- competitor analysis
- strategy
- safety / hallucination resistance

Languages:

- English
- French
- Russian

Run local Qwen evaluation:

```bash
python -m ml.eval.runner --provider local --model Qwen/Qwen3-1.7B-MLX-4bit --limit 10
```

Run a limited Groq comparison:

```bash
python -m ml.eval.runner --provider groq --model openai/gpt-oss-20b --limit 10
```

Use Groq comparison sparingly. Summaries are written under ignored result
directories and must not contain API keys or authorization material.

The first measured baseline is documented in:

```text
docs/SMALL_LLM_BASELINE.md
```

The corrected contract baseline is documented in:

```text
docs/SMALL_LLM_BASELINE_V2.md
```

Baseline v2 uses the production-owned content-plan contract
`content_plan_contract_v2` and freezes the corrected golden set as
`golden_eval_v2`. The clean Groq reference completed with prompt-only JSON mode
and deterministic post-validation. Qwen3-1.7B completed the full 50-case frozen
baseline, then LoRA v1 trained locally on synthetic behavior examples.

The LoRA v1 pilot did not improve the product-critical structural metrics, so
the full LoRA frozen evaluation was intentionally not run. Current reports:

```text
docs/SMALL_LLM_BASELINE_V2.md
docs/SMALL_LLM_LORA_V1.md
```

## Metrics

The deterministic evaluator measures:

- `schema_valid_rate`
- `required_field_rate`
- `hallucination_rate`
- `forbidden_claim_rate`
- `instruction_following_rate`
- `language_match_rate`
- `human_review_flag_rate`
- `seven_day_plan_valid_rate`

For JSON tasks, use deterministic checks first. An LLM judge may be added later
only as a secondary signal.

## Fine-Tuning Preparation

No fine-tuning has been run.

Future first experiment:

- model: `Qwen/Qwen3-1.7B`
- method: LoRA
- target: instruction following and project structured outputs
- non-goal: memorizing business data

The dataset builder accepts explicitly supplied JSONL chat examples and creates
deterministic train/validation/test splits. It rejects obvious secrets,
duplicate examples, and empty assistant answers.

## RAG Preparation

RAG is documented but not implemented. No embeddings, pgvector migrations, or
vector indexes exist in this phase.

Future sources:

- business profile
- brand voice
- approved content
- historical reports
- trend observations
- trend predictions
- competitor records
- strategy records
- uploaded business documents

Every retrieved record must be scoped to `business_id`.

## Privacy Rules

- Do not commit model weights.
- Do not commit Hugging Face caches.
- Do not commit private user data as training data.
- Do not pass application secrets to the local model.
- Do not expose local model config to the frontend.
- Do not fine-tune on production data without explicit approval and redaction.

## Production Caveat

`mlx_lm.server` is a local development server, not production infrastructure.
Future production serving should use a hardened OpenAI-compatible inference
server with authentication, monitoring, resource controls, and tenant-safe
data handling.
