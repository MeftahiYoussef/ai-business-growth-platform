# LoRA v2 Failure Analysis

Status: `completed`; promotion status: `rejected`; reason: `semantic pilot regression`.

## Root Cause

The dominant failure is a curriculum-induced selective-uncertainty problem. The adapter learned to become safer and more cautious, but it did not preserve known supplied facts while qualifying only missing metrics. This explains the hallucination improvement and the simultaneous collapse in required-fact recall.

The latency increase is primarily a generation-pathology issue: several LoRA outputs contain long digit runs or repeated fragments and likely ran to the token budget. Exact token-level throughput and finish reasons were not recorded by the pilot runner, so this report does not claim a precise adapter kernel overhead.

## Evidence

- LoRA required-fact failure breakdown: `{"FACT_DROPPED": 9, "FACT_MUTATED": 2, "FACT_REPLACED_WITH_RECOMMENDATION": 9}`
- LoRA critical-fact failure breakdown: `{"FACT_DROPPED": 5, "FACT_MUTATED": 2, "FACT_REPLACED_WITH_RECOMMENDATION": 8}`
- Correct uncertainty rate, base -> LoRA: `0.4` -> `0.6`
- Selective uncertainty rate, base -> LoRA: `0.0` -> `0.0`
- Known-fact retention under uncertainty, base -> LoRA: `0.5` -> `0.25`
- Median output words, base -> LoRA: `77.5` -> `41.0`
- Median output chars, base -> LoRA: `756.0` -> `1237.0`
- Degenerative repetition cases, base -> LoRA: `6` -> `4`
- Long digit-run cases, base -> LoRA: `0` -> `3`
- Median latency ms, base -> LoRA: `4896.5` -> `31267.0`

## Dataset Findings

- SFT v2 uncertainty phrase record rate: `1.0`
- SFT v2 refusal phrase record rate: `0.6`
- SFT v2 max template-cluster share: `0.0028`
- SFT v2 max label-pattern share: `0.4`
- Shared train/validation skeleton count: `0`
- Shared train/validation label-pattern count: `3`
- Validation max similarity to train: `{"average": 0.84, "count": 36, "max": 0.9215686274509803, "median": 0.84}`

## Semantic Response Policy V1

1. Every supplied critical fact relevant to the answer must be retained.
2. Supplied numeric values must remain unchanged unless deterministic code explicitly calculates a derived value.
3. Only unsupported or missing facts receive uncertainty language.
4. Missing one metric does not invalidate available metrics.
5. Recommendations must be phrased as recommendations, not reported facts.
6. Do not invent evidence.
7. Remain helpful after stating a limitation.
8. Do not over-refuse ordinary business analysis.
9. Answer in the requested language, including labels and headers.
10. Prefer concise output unless detail is requested.

## Dataset vs Optimization

Conclusion: `BOTH`, with dataset design as the primary cause.

The dataset over-rewards uncertainty and repeats response skeletons. The low train/validation loss indicates that the validation split was too semantically similar to training despite family-level splitting. The 240-iteration rank-8 run may have amplified these templates, but the observed regression is not explainable by optimization intensity alone.

## Decision

A smaller `qwen3_sft_v2_1` dataset experiment is justified. It should target selective uncertainty, known-fact retention under missing data, concise answers, and multilingual labels. Do not train until the v2.1 candidates are generated, audited, and frozen.
