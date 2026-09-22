# Fine-Tuning Preparation

No fine-tuning has been run.

Future first experiment:

- Model: `Qwen/Qwen3-1.7B`
- Method: LoRA
- Goal: improve instruction following and project structured outputs
- Non-goal: memorizing business, customer, trend, or competitor data

Factual business knowledge belongs in future RAG, not in model weights.

Use separate train, validation, and test files. Never train and evaluate on the
same records.
