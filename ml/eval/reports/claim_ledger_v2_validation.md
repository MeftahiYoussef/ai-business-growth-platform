# Claim Ledger V2 Validation

Date: 2026-09-30

Branch: `feature/claim-ledger-v2`

## Summary

Claim ledger V2 tested the hypothesis that factual validity improves when the
model no longer writes authoritative fact text.

The result supports the hypothesis.

Compared with V1:

- Qwen3-1.7B improved from 0.00 to 0.20 final validity.
- Qwen3-4B improved from 0.20 to 0.80 final validity.
- required evidence selection reached 1.00 for both models.
- critical evidence selection reached 1.00 for both models.
- numeric mutation in rendered output was 0.
- unavailable metric misuse in rendered output was 0.
- invalid-and-missed remained 0.
- renderer semantic additions remained 0.

The remaining failure class is relation selection: models, especially 1.7B,
still emit unnecessary or false comparisons.

## V1 Failure Root Cause

V1 duplicated facts in two places:

1. trusted evidence IDs
2. model-authored free-form claim text

Across 20 V1 first-pass outputs, 22 claim-level failures occurred despite
evidence being selected. The model often selected relevant IDs but corrupted the
corresponding text through numeric mutation, unavailable-metric assertions, or
categorical contradiction.

## V2 Contract

Contract version: `claim_ledger_v2`

Top-level shape:

```json
{
  "facts": [],
  "limitations": [],
  "comparisons": [],
  "recommendations": []
}
```

Facts:

```json
{"evidence_id": "F2"}
```

Limitations:

```json
{"evidence_id": "U1"}
```

Comparisons:

```json
{
  "relation_id": "R1"
}
```

The relation ledger is trusted input:

```json
{
  "id": "R1",
  "left_evidence_id": "F1",
  "operator": "greater_than",
  "right_evidence_id": "F2",
  "predicate": "posts"
}
```

Recommendations:

```json
{
  "action": "review posting cadence",
  "rationale_evidence_ids": ["F1", "F2"]
}
```

## Responsibility Boundary

Model-owned:

- evidence selection
- claim ordering
- relation selection
- optional recommendation action text

Deterministic-owned:

- values
- units
- availability
- factual wording
- numeric rendering
- categorical state
- relation truth validation
- localization templates

## Schema Restrictions

Request-specific schema uses separate enums:

- known IDs for `facts`
- unavailable IDs for `limitations`
- known IDs for comparison operands
- relation IDs for comparisons when trusted relations are supplied
- known IDs for recommendation rationale

Schema-prevented invalidity classes:

- invented evidence ID
- fact referencing unavailable evidence
- limitation referencing known evidence
- model-generated fact value
- model-generated limitation text

## Deterministic Tests

Focused deterministic tests passed:

- `43 passed`

Covered:

- fact claim value rendering
- limitation rendering
- known/unavailable schema separation
- relation validation
- false comparison rejection
- cross-predicate comparison rejection
- categorical mutation prevention
- negative number rendering
- percent rendering
- FR rendering
- RU rendering
- required and critical evidence selection
- renderer semantic additions = 0
- unsupported recommendation number rejection

## Live Methodology

Runtime: `llama.cpp`

Version: `0.4.1`, build `10964`, commit `b29c606e2`

Models:

- `Qwen/Qwen3-1.7B`, GGUF `Q4_K_M`
- `Qwen/Qwen3-4B`, GGUF `Q4_K_M`

Settings:

- temperature `0`
- `/no_think`
- JSON Schema constrained decoding
- one targeted retry maximum
- same 10 synthetic, non-private direct cases as the V1 validation

No LoRA adapters were used.

## V1 vs V2 Results

| Metric | 1.7B V1 | 1.7B V2 | 4B V1 | 4B V2 |
| --- | ---: | ---: | ---: | ---: |
| First-pass valid rate | 0.00 | 0.20 | 0.00 | 0.70 |
| Retry success | 0/10 | 0/8 | 2/10 | 1/3 |
| Final valid rate | 0.00 | 0.20 | 0.20 | 0.80 |
| Required evidence selection | n/a | 1.00 | n/a | 1.00 |
| Critical evidence selection | n/a | 1.00 | n/a | 1.00 |
| Numeric mutation count | n/a | 0 | n/a | 0 |
| Unsupported claim count | n/a | 0 | n/a | 0 |
| Unavailable metric misuse | n/a | 0 | n/a | 0 |
| Renderer semantic additions | 0 | 0 | 0 | 0 |
| Invalid and missed | 0 | 0 | 0 | 0 |
| Average latency | 4969.3 ms | 5636.6 ms | 9817.5 ms | 7810.2 ms |

## Direct Case Outcomes

Numeric pressure:

- 1.7B V2: invalid detected because it emitted a false self-comparison.
- 4B V2: valid after retry; renderer preserved `22%`.

Unavailable reach:

- 1.7B V2: invalid detected because it emitted false comparisons.
- 4B V2: invalid detected in the EN case because it emitted a false comparison;
  the equivalent FR case also failed language/oracle validation.

Competitor:

- 1.7B V2: valid for EN and RU competitor cases.
- 4B V2: valid for EN and RU competitor cases.

Trend:

- 1.7B V2: invalid detected because it emitted a false comparison.
- 4B V2: valid first pass; renderer preserved `-8%` and `fading`.

## Comparison Correctness

| Model | Comparisons emitted | False comparison errors | Correctness |
| --- | ---: | ---: | ---: |
| 1.7B V2 | 13 | 11 | 0.1538 |
| 4B V2 | 4 | 2 | 0.5000 |

The validator now requires comparison operands to share the same predicate and
then checks the operator truth against trusted values.

## Language Rendering

Renderer localization was deterministic for validated outputs:

- EN: passed
- FR: passed for valid ledgers
- RU: passed for valid ledgers

Language failures in invalid outputs were caused by rejected ledgers with no
valid rendered prose.

## Gate Decision

The V2 architecture passes the safety gate:

- critical numeric mutation: 0
- invalid-and-missed: 0
- renderer additions: 0
- required evidence selection: 1.00
- critical evidence selection: 1.00
- factual rendering correctness: 1.00 for valid ledgers

It does not yet pass a production usability gate because 1.7B final validity is
only 0.20 and 4B final validity is 0.80 on the small direct set.

## Model Decision

Preferred local model for the next claim-ledger research phase: Qwen3-4B.

Reason:

- materially higher first-pass validity
- materially higher final validity
- fewer false comparisons
- same safety profile: invalid-and-missed = 0

Qwen3-1.7B should not be advanced for this architecture unless comparison
selection is made structurally simpler.

## RAG Readiness

RAG is not justified as the immediate next phase.

The remaining failures are not missing knowledge. They are relation-selection
and contract-affordance failures. Once claim-ledger selection and rendering are
reliable, RAG can supply normalized trusted evidence into this pipeline.

Future architecture:

```text
retriever
  -> normalized trusted evidence
  -> claim selection
  -> semantic validator
  -> deterministic renderer
```

## Recommended Next Phase

Run `claim_ledger_v2.1` focused on comparison affordances:

- allow comparisons only when the trusted evidence ledger declares comparable
  pairs
- make comparisons optional or disabled for tasks that do not need them
- add schema-level relation options per comparable pair where practical
- keep facts and limitations as evidence-only selections
- keep deterministic rendering and localization

Do not train, deploy, or implement RAG before this contract refinement.
