# LoRA v2.1 Semantic Evaluation

Status: `pilot failed`

The full frozen 50-case semantic evaluation was not run because the 10-case
pilot triggered the stop gate.

## Pilot Design

Cases:

- `cp-en-001`
- `report-en-001`
- `report-safety-001`
- `trend-en-001`
- `trend-fr-001`
- `trend-ru-001`
- `competitor-safety-001`
- `strategy-en-001`
- `safety-fr-001`
- `safety-ru-001`

Arms:

1. Base `Qwen/Qwen3-1.7B-MLX-4bit`
2. Rejected LoRA v2, same MLX runtime
3. LoRA v2.1, same MLX runtime

The LoRA v2 rerun reproduced the runaway generation path and was interrupted
after exceeding the expected control window. The existing identical v2 pilot
outputs from PR #17 are used for the v2 metrics below.

## Direct Sanity

LoRA v2.1 direct sanity results:

- Selective uncertainty EN: passed.
- Numeric preservation EN: partial fail; retained `0.22 / 22%` but still
  mentioned `45%` while negating it.
- French: passed structurally and retained known facts; no English header leak.
- Russian: passed structurally and retained known facts; no English header leak.
- Digit runs: `0`
- Repeated sentences: `0`
- Thinking leakage: `0`

The numeric sanity warning was enough to require a strict pilot before any full
benchmark.

## Pilot Metrics

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
| P95 latency | `18642 ms` | `60572 ms` | `4111 ms` |
| Digit-run failures | `0` | `3` | `0` |
| Repetition failures | `0` | `1` | `0` |
| Thinking leakage cases | `10` | `0` | `0` |

## Language Breakdown

Required-fact recall:

| Language | Base | LoRA v2 | LoRA v2.1 |
| --- | ---: | ---: | ---: |
| EN | `0.7083` | `0.2778` | `0.7083` |
| FR | `0.7500` | `0.5000` | `0.3750` |
| RU | `0.5000` | `0.3333` | `0.5000` |

Critical-fact recall:

| Language | Base | LoRA v2 | LoRA v2.1 |
| --- | ---: | ---: | ---: |
| EN | `0.7500` | `0.1667` | `0.6667` |
| FR | `0.7500` | `0.5000` | `0.5000` |
| RU | `0.5000` | `0.5000` | `0.5000` |

## Task Breakdown

Required-fact recall for LoRA v2.1:

| Task | Count | Required Recall | Critical Recall |
| --- | ---: | ---: | ---: |
| `business_report` | `1` | `1.0000` | `1.0000` |
| `content_planning` | `1` | `0.5000` | `0.5000` |
| `safety` | `4` | `0.2500` | `0.2500` |
| `strategy` | `1` | `0.7500` | `0.5000` |
| `trend_intelligence` | `3` | `0.9167` | `1.0000` |

The weakest cluster remains safety and adversarial missing-data behavior.

## Pilot Gate Decision

Result: `FAIL`

Reasons:

- Required-fact recall regressed versus base: `0.6750 -> 0.6000`.
- Critical-fact recall regressed versus base: `0.7000 -> 0.6000`.
- Hallucination worsened versus base: `0.3000 -> 0.4000`.
- Forbidden-claim rate worsened versus base: `0.2000 -> 0.3000`.
- Language match regressed versus base: `1.0000 -> 0.9000`.
- Selective uncertainty improved but remained low: `0.2000`.

Positive observations:

- Numeric preservation improved versus base: `0.7143 -> 0.8571`.
- Numeric mutation decreased versus base: `0.2857 -> 0.1429`.
- Insufficient-evidence handling improved versus base: `0.4000 -> 0.8000`.
- The v2 digit-run/repetition degeneration was removed.
- Latency improved substantially versus both base and v2.

The positives are not sufficient because the primary objective was semantic
fact retention under uncertainty.

## Final Decision

Decision: `REJECT LORA V2.1`

Do not proceed to the full 50-case evaluation.
Do not promote this adapter.
Do not deploy it.

The next evidence-based step is to test whether `Qwen/Qwen3-4B` has enough
capacity for the semantic policy before investing in another 1.7B SFT
curriculum.
