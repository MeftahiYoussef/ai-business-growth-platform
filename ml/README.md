# Small LLM Model Lab

This directory contains the local experimental foundation for evaluating small
models without changing production behavior.

Current baseline:

- `model_family`: `qwen3`
- `model_id`: `Qwen/Qwen3-1.7B`
- `model_role`: `experimental_small_llm`
- `model_version`: `baseline`

Groq remains the live application provider. This lab is for local evaluation,
future LoRA/QLoRA preparation, and future RAG design only.

## Local Inference

On Apple Silicon, prefer MLX-LM for development:

```bash
pip install "mlx-lm[train]"
mlx_lm.server --model Qwen/Qwen3-1.7B --port 8080
```

Then run:

```bash
python -m ml.eval.runner --provider local --model Qwen/Qwen3-1.7B --limit 10
```

For Groq comparison, use the existing provider only from an explicitly
configured shell:

```bash
python -m ml.eval.runner --provider groq --model openai/gpt-oss-20b --limit 10
```

Do not commit downloaded weights, Hugging Face caches, adapters, or evaluation
outputs. The repository ignore rules exclude those paths.

## Future Candidates

Documented for future benchmark comparison only:

- `HuggingFaceTB/SmolLM3-3B`
- `Qwen/Qwen3-4B`

Do not download these candidates during the baseline task.
