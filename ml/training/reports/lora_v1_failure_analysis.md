# LoRA V1 Curriculum Failure Analysis

- Date: `2026-09-22`
- Experiment: `qwen3_1_7b_lora_v1`
- Status: `completed`
- Promotion status: `rejected`
- Rejection reason: no meaningful 10-case pilot improvement over base Qwen.

## Evidence

LoRA v1 trained successfully and reached low train/validation loss:

| Metric | Value |
| --- | ---: |
| Train examples | 153 |
| Validation examples | 18 |
| Local MLX test examples | 9 |
| Final train loss | 0.063 |
| Final validation loss | 0.054 |

But the 10-case pilot did not improve product-critical structure:

| Metric | Base Qwen | LoRA v1 | Delta |
| --- | ---: | ---: | ---: |
| Schema validity | 0.6 | 0.6 | 0.0 |
| Seven-day validity | 0.0 | 0.0 | 0.0 |
| JSON parse validity | 0.9 | 0.9 | 0.0 |
| Human-review flag | 1.0 | 1.0 | 0.0 |
| Hallucination rate | 0.1 | 0.1 | 0.0 |

The full LoRA 50-case evaluation was intentionally not run because the pilot gate failed.

## Dataset Review

The v1 SFT dataset contains 180 synthetic, non-private examples.

| Task | Count |
| --- | ---: |
| Content planning | 54 |
| Business report | 36 |
| Trend intelligence | 27 |
| Competitor analysis | 18 |
| Strategy | 27 |
| Safety | 18 |

Languages are balanced: 60 English, 60 French, and 60 Russian records.

Assistant answer length:

| Measure | Characters |
| --- | ---: |
| Average | 1687.8 |
| Median | 440 |

Average answer length by task:

| Task | Average assistant characters |
| --- | ---: |
| Content planning | 4795.5 |
| Business report | 441.6 |
| Strategy | 466.4 |
| Competitor analysis | 343.3 |
| Trend intelligence | 304.2 |
| Safety | 109.4 |

## Failure Explanation

The validation set was too easy for the actual failure modes. It measured reconstruction of clean templates more than robust behavior under varied prompts.

Likely contributors:

- Content-plan examples are long and template-heavy, so loss can fall without teaching robust generalization.
- Safety examples are too short and underrepresented relative to observed hallucination/refusal failures.
- V1 lacked enough adversarial field-type examples, especially array fields such as `source_context` and `risk_flags`.
- V1 did not include enough malformed or competing instructions where the model must still satisfy the canonical schema.
- Validation examples resemble training templates, making validation loss over-optimistic.
- The experiment tried to use LoRA for structural guarantees that are better provided by constrained decoding plus the production validator.

## Curriculum V2 Design

Do not train LoRA v2 yet. Prepare a higher-diversity curriculum first.

Target range: 300-600 examples only if quality supports it.

Recommended distribution:

| Category | Purpose |
| --- | --- |
| Strict schemas | Teach exact top-level shapes and field names |
| Field-type adversarial cases | Teach arrays versus strings and booleans versus strings |
| Missing required fields | Teach completion of every required field |
| Forbidden extra fields | Teach `additionalProperties=false` discipline |
| Enum discipline | Teach allowed platform, objective, and content-type values |
| Insufficient-information handling | Teach safe refusal without losing required facts |
| Hallucination resistance | Prevent invented reach, impressions, revenue, and conversion claims |
| Numeric preservation | Preserve supplied metrics and trend values exactly |
| French structured output | Keep schema keys stable while content is French |
| Russian structured output | Keep schema keys stable while content is Russian |
| Business reports | Separate computed metrics from recommendations |
| Trend explanations | Preserve supplied evidence and lifecycle labels |
| Competitor summaries | Separate facts from recommendations |
| Strategy recommendations | Produce concrete actions without unsupported claims |

## Future Architecture

The next viable small-model architecture should be:

```text
Qwen3-1.7B
+ optional behavioral LoRA adapter
+ JSON Schema constrained decoding
+ production validator
```

The schema runtime should guarantee syntax, field presence, basic types, enums, and basic item counts.

The adapter should improve semantic quality, style, multilingual task following, and refusal behavior.

The application validator must still enforce product rules, deterministic metrics, ownership, quotas, and human-review requirements.
