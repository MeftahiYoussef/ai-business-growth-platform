# Claim Ledger Trusted Relation Validation

Date: 2026-09-30

Contract: `claim_ledger_v2_trusted_relations`

## Methodology

This validation tests whether local Qwen models can select trusted relation IDs
without constructing relation semantics themselves.

Runtime:

- llama.cpp `0.4.1`
- build `10964`
- commit `b29c606e2`
- Q4_K_M quantization
- temperature `0`
- `/no_think`
- localhost only

Models:

- `Qwen3-1.7B-Q4_K_M`
- `Qwen3-4B-Q4_K_M`

No training, deployment, RAG, staging access, or paid resources were used.

Raw local outputs were written under ignored `ml/outputs/`.

## Relation Contract

Trusted relation:

```json
{
  "id": "R1",
  "relation_type": "comparison",
  "predicate": "published_posts",
  "left_evidence_id": "F1",
  "operator": "greater_than",
  "right_evidence_id": "F2",
  "provenance": "deterministic"
}
```

Model-owned output:

```json
{
  "comparisons": [{"relation_id": "R1"}]
}
```

If no trusted relation is supplied, `comparisons` has `maxItems: 0`.

## Deterministic Builder Coverage

Deterministic tests cover:

- no-relation schema
- single-relation schema
- multi-relation schema
- false comparison rejection
- incompatible predicate rejection
- incompatible unit rejection
- incompatible value-type rejection
- unavailable operand rejection
- self-comparison rejection
- incompatible time-window rejection
- temporal comparison allowance
- invented relation ID rejection
- expanded triple rejection when relations exist

Focused test result: `50 passed`.

## Direct Gate Results

8 direct cases:

- relevant relation
- irrelevant relation
- optional supporting relation
- equality
- no relation
- adversarial opposite direction
- multi-relation narrow request
- French relation request

| Metric | Qwen3-1.7B | Qwen3-4B |
| --- | ---: | ---: |
| First-pass valid | 1.00 | 0.875 |
| Final valid | 1.00 | 1.00 |
| Required evidence selection | 1.00 | 1.00 |
| Critical evidence selection | 1.00 | 1.00 |
| Relation precision | 1.00 | 1.00 |
| Relation recall | 1.00 | 1.00 |
| Relation relevance | 1.00 | 1.00 |
| Relation truth | 1.00 | 1.00 |
| Unnecessary relation rate | 0.00 | 0.00 |
| Missing relation rate | 0.00 | 0.00 |
| Invalid missed | 0 | 0 |
| Retry attempts | 0 | 1 |
| Retry successes | 0 | 1 |
| Average latency | 2366.5 ms | 3507.0 ms |

The direct gate passed.

## 10-Case Pilot Results

Additional pilot cases:

- Russian relation selection
- French no-relation summary

| Metric | Qwen3-1.7B | Qwen3-4B |
| --- | ---: | ---: |
| First-pass valid | 1.00 | 0.90 |
| Final valid | 1.00 | 1.00 |
| Required evidence selection | 1.00 | 1.00 |
| Critical evidence selection | 1.00 | 1.00 |
| Relation selection precision | 1.00 | 1.00 |
| Relation selection recall | 1.00 | 1.00 |
| Relation relevance rate | 1.00 | 1.00 |
| Relation truth rate | 1.00 | 1.00 |
| Unnecessary relation rate | 0.00 | 0.00 |
| Missing required relation rate | 0.00 | 0.00 |
| Language match | 1.00 | 1.00 |
| Invalid detected | 0 | 1 |
| Invalid missed | 0 | 0 |
| Retry attempts | 0 | 1 |
| Retry successes | 0 | 1 |
| Renderer additions | 0 | 0 |
| Average latency | 2083.5 ms | 2807.0 ms |

## Case-Level Notes

Relevant comparison:

- Both models selected `R1`.

Irrelevant comparison:

- 4B initially selected true but irrelevant `R1` for an engagement question.
- The validator classified this as selection failure, not hallucination.
- One targeted retry removed `R1`.
- 1.7B omitted `R1` first-pass.

Optional relation:

- Both models selected `R1` when the request asked to compare known competitor
  facts.

Equality:

- Both models selected the trusted equality relation.

No relation:

- Neither model fabricated a relation claim.

Adversarial opposite direction:

- Both models selected the trusted increase relation instead of creating or
  implying the requested decrease.

Multi-relation:

- Both models selected only the requested publishing-frequency relation and did
  not dump unrelated follower or competitor relations.

EN/FR/RU:

- All requested languages passed.
- Rendering remains deterministic and may need copy polish before production.

## V2 vs Trusted-Relation Result

Previous V2 allowed the model to construct or select comparisons too freely.
Known V2 4B final valid rate was `0.80`.

Trusted relation affordances improved 4B final validity to `1.00` on the
relation pilot and preserved `invalid_missed = 0`.

Most importantly, relation truth is now deterministic. Remaining failures are
selection/relevance errors, not relation-truth errors.

## Model Decision

For this relation-selection contract, Qwen3-1.7B is the preferred efficiency
baseline:

- first-pass valid `1.00`
- final valid `1.00`
- lower average latency than 4B
- no invalid missed cases

Qwen3-4B remains viable, but did not show a relation-selection advantage in this
small pilot.

## Remaining Failure Class

Primary remaining class:

- presentation and selection polish

Observed examples:

- duplicated known fact rendering when the model selects the same fact multiple
  times
- low-value recommendation strings from 1.7B
- awkward deterministic relation wording for same-subject comparisons

These are not safety failures because the renderer adds no unsupported facts and
the validator catches relevance errors.

## Decisions

- LoRA is not justified for relation truth or numeric preservation.
- A model larger than 4B is not justified by this experiment.
- RAG is not next while contract extraction and production ownership remain
  incomplete.
- Production contract promotion is justified as the next research-to-product
  phase, but the current `ml/eval` implementation should not be imported into
  Django runtime directly.
