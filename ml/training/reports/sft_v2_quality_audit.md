# SFT v2 Quality Audit

Status: curriculum blueprint only. No SFT v2 training records have been generated,
split, or approved.

## Scope

The v2 curriculum targets semantic alignment failures from the constrained
Qwen3-1.7B run. It intentionally does not teach JSON syntax, field ordering,
enum formatting, or seven-day structure because llama.cpp JSON Schema
constrained decoding solved those structural requirements.

## Candidate Count

| Item | Count |
| --- | ---: |
| Proposed target examples | 360 |
| Generated SFT v2 records | 0 |
| Approved SFT v2 train records | 0 |
| Approved SFT v2 validation records | 0 |

## Planned Distribution

| Category | Target | Share |
| --- | ---: | ---: |
| hallucination_resistance | 72 | 20% |
| required_fact_retention | 54 | 15% |
| numeric_preservation | 54 | 15% |
| insufficient_evidence | 36 | 10% |
| business_reports | 36 | 10% |
| trend_metric_fidelity | 36 | 10% |
| competitor_fact_fidelity | 18 | 5% |
| fact_vs_recommendation_separation | 18 | 5% |
| difficult_multilingual | 36 | 10% |

Language target: 144 English, 108 French, 108 Russian.

## Duplicate Audit

Because no records have been generated yet, record-level duplicate rates are
not applicable. The blueprint defines the following pre-generation gates:

- Exact duplicate rate must be 0.
- Near-duplicate rate target is <= 5%.
- Examples must be grouped by hard-negative family before train/validation
  splitting.
- Near-identical templates must not be split across train and validation.
- Golden evaluation cases must remain excluded.
- Numeric patterns should vary across examples rather than reusing one small
  set of values.

## Known Risk From v1

LoRA v1 reached low validation loss but failed to improve the pilot benchmark.
The likely cause was a template-heavy curriculum that taught repeated surface
patterns and tried to solve structural JSON behavior better handled by
constrained decoding. The v2 curriculum therefore targets factual retention,
metric preservation, uncertainty handling, and refusal/qualification behavior.

## Approval Requirement

Before LoRA v2 training, a future generated dataset must pass:

- schema validation where schemas apply;
- deterministic numeric-preservation checks;
- secret scans;
- golden-test leakage checks;
- exact and near-duplicate checks;
- grouped train/validation split review.
