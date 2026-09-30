# Claim Ledger V1 Failure Analysis

Date: 2026-09-29

Source outputs:

- `ml/outputs/claim_ledger_live_validation/qwen3_1_7b_claim_ledger_v2.json`
- `ml/outputs/claim_ledger_live_validation/qwen3_4b_claim_ledger_v2.json`

These raw files remain ignored. This report records safe aggregate findings.

## Question

The key question was whether V1 failed because models could not select the
right evidence IDs, or because they selected relevant evidence but corrupted the
free-form claim text.

Answer: V1 mostly failed because the model selected useful evidence IDs while
still rewriting facts unsafely in claim text.

Across the 20 first-pass outputs:

- invalid first-pass outputs: 20
- invalid first-pass outputs detected by the deterministic validator: 20
- invalid first-pass outputs missed by the deterministic validator: 0
- claim-level failures with evidence selected but unsafe text: 22

This supports the V2 design goal:

> remove redundant model-authored factual text and let deterministic rendering
> read values directly from trusted evidence.

## Root-Cause Categories

Case-level first-pass categories:

| Category | 1.7B | 4B | Total |
| --- | ---: | ---: | ---: |
| `UNAVAILABLE_FACT_ASSERTED` | 10 | 6 | 16 |
| `NUMERIC_MUTATION` | 6 | 5 | 11 |
| `RECOMMENDATION_AS_FACT` | 3 | 5 | 8 |
| `OMITTED_REQUIRED_EVIDENCE` | 4 | 2 | 6 |
| `WRONG_EVIDENCE` | 2 | 2 | 4 |
| `PREDICATE_CONTRADICTION` | 1 | 0 | 1 |
| `LANGUAGE_FAILURE` | 0 | 1 | 1 |

The dominant failure classes are exactly the classes caused by free-form claim
text:

- unavailable metrics being asserted as real observations
- immutable numbers being rewritten
- recommendations being phrased as factual observations
- categorical values being contradicted

## Correct Evidence, Wrong Text

Claim-level failures where the model cited evidence but wrote invalid text:

| Model | Claims |
| --- | ---: |
| Qwen3-1.7B | 13 |
| Qwen3-4B | 9 |
| Total | 22 |

Examples of the failure pattern:

- citing the momentum evidence but writing `45%`
- citing the lifecycle evidence but writing `emerging` when the evidence says
  `fading`
- citing known posting counts while asserting unavailable reach or engagement
  improved
- writing a recommendation-like claim as if it were an observed fact

## V1 Architectural Cause

V1 asked the model to output both:

- evidence references
- free-form claim text restating the evidence

That duplicated the same fact in two places:

1. the trusted evidence ledger
2. model-authored prose

Whenever those disagreed, the validator had to reject the output. The validator
worked, but validity remained poor because the model repeatedly corrupted the
duplicate free-form representation.

## V2 Design Requirement

V2 must apply this rule:

> one authoritative representation per fact.

For factual claims, the model should select evidence IDs only:

```json
{"evidence_id": "F2"}
```

The deterministic renderer should read:

- subject
- predicate
- value
- unit / display value
- availability
- polarity where trusted

from trusted evidence. The model should not regenerate authoritative numeric,
categorical, or availability values in free-form fact text.

## Expected V2 Impact

V2 should structurally prevent:

- numeric mutation in direct fact claims
- categorical mutation in direct fact claims
- invented unavailable-metric limitations
- `fact(U1)` where `U1` is unavailable
- `limitation(F1)` where `F1` is known
- factual renderer additions

The model remains responsible for:

- selecting relevant evidence
- selecting true comparison relations
- deciding which optional recommendation to include, if recommendations are
  enabled

The validator remains responsible for:

- required/critical evidence selection
- relation truth
- recommendation safety
- unsupported numeric values in advisory text
- final render safety
