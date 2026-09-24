# Qwen3-1.7B LoRA v2 Semantic Evaluation

Date: 2026-09-23

## Evaluation Design

LoRA v2 was compared against base Qwen through the same MLX runtime to avoid
confounding adapter effects with llama.cpp constrained decoding.

- Base model: `Qwen/Qwen3-1.7B-MLX-4bit`
- Adapter: `ml/outputs/adapters/qwen3_1_7b_lora_v2/`
- Temperature: `0`
- Thinking mode: `/no_think`
- Pilot case count: `10`
- Frozen benchmark source: `golden_eval_v3_semantic_grading` over the
  `golden_eval_v2` cases

The full 50-case semantic benchmark was not run because the 10-case pilot
failed the stop gate.

## Direct Sanity

Direct sanity did not show total collapse, but it exposed important regression
signals:

- Hallucination resistance passed for `reach unavailable`.
- Numeric preservation failed to retain `momentum = 0.22`.
- English unavailable-metric handling omitted the `revenue` subject.
- French output mixed a Russian section header with French content.
- Russian unavailable-data behavior passed.

## Pilot Metrics

| Metric | Base MLX | LoRA v2 MLX | Delta |
|---|---:|---:|---:|
| Instruction following | 0.0000 | 0.0000 | 0.0000 |
| Required-fact recall | 0.6750 | 0.3333 | -0.3417 |
| Critical required-fact recall | 0.7000 | 0.3000 | -0.4000 |
| Hallucination rate | 0.3000 | 0.1000 | -0.2000 |
| Forbidden-claim rate | 0.2000 | 0.0000 | -0.2000 |
| Numeric preservation | 0.7143 | 0.7143 | 0.0000 |
| Numeric mutation | 0.2857 | 0.2857 | 0.0000 |
| Insufficient-evidence handling | 0.4000 | 0.6000 | +0.2000 |
| Safe uncertainty | 0.4000 | 0.6000 | +0.2000 |
| Language match | 1.0000 | 0.9000 | -0.1000 |
| Median latency ms | 4896.5 | 31267.0 | +26370.5 |
| P95 latency ms | 18493 | 60572 | +42079 |

## Language Breakdown

| Language | Base required recall | LoRA required recall | Base language match | LoRA language match |
|---|---:|---:|---:|---:|
| EN | 0.7083 | 0.2778 | 1.0000 | 1.0000 |
| FR | 0.7500 | 0.5000 | 1.0000 | 0.5000 |
| RU | 0.5000 | 0.3333 | 1.0000 | 1.0000 |

## Failure Pattern

The adapter improved some safety-style refusal behavior, but did so by becoming
too generic and uncertainty-heavy. It lost supplied facts, dropped critical
numbers, produced longer outputs, and regressed French language behavior.

Observed regression classes:

- Required-fact recall regression
- Critical-fact recall regression
- Numeric omission in direct sanity
- French language/header regression
- Much higher latency and longer answers
- Over-uncertainty / generic insufficient-data phrasing

## Pilot Decision

The pilot stop gate failed. The full 50-case LoRA v2 benchmark was intentionally
not run.

Decision: `REJECT LORA V2`

Rationale:

- Required-fact recall regressed materially.
- Critical required-fact recall regressed materially.
- Language match regressed, especially French.
- Latency increased sharply.
- Semantic improvement was limited to lower hallucination and more uncertainty,
  but that came with loss of useful factual retention.

LoRA v2 should not be promoted or integrated with constrained serving.
