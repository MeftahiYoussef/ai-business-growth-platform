# Small LLM Claim Ledger V2.1

Status: local research validation.

## Purpose

Claim ledger V2 removed model-authored factual values from the factual plane.
V2.1 extends that idea to comparisons.

The model no longer constructs arbitrary comparison triples. Trusted code builds
true relation affordances first, then the model selects a `relation_id` only
when that relation is relevant to the user request.

## Relation Contract

Trusted relation metadata:

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

Valid model output:

```json
{
  "comparisons": [{"relation_id": "R1"}]
}
```

Invalid model output:

```json
{
  "comparisons": [
    {
      "left_evidence_id": "F1",
      "operator": "greater_than",
      "right_evidence_id": "F2"
    }
  ]
}
```

If no trusted relation exists, `comparisons` is constrained to `maxItems: 0`.

## Deterministic Relation Builder

The relation builder rejects:

- false comparisons
- incompatible predicates
- incompatible units
- incompatible value types
- unavailable operands
- meaningless self-comparisons
- incompatible time windows for non-temporal comparisons

It accepts true `greater_than`, `less_than`, and `equal` relations for supported
trusted evidence.

## Responsibility Boundary

The model owns:

- selecting known evidence IDs
- selecting unavailable evidence IDs
- selecting trusted relation IDs
- optional recommendation text

Deterministic code owns:

- relation construction
- relation truth
- authoritative values
- units
- factual wording
- numeric rendering
- localization
- final validation

## Live Validation

Runtime:

- llama.cpp `0.4.1`, build `10964`, commit `b29c606e2`
- Q4_K_M quantization
- temperature `0`
- `/no_think`
- localhost only

10-case pilot:

| Metric | Qwen3-1.7B | Qwen3-4B |
| --- | ---: | ---: |
| First-pass valid | 1.00 | 0.90 |
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
| Renderer additions | 0 | 0 |
| Average latency | 2083.5 ms | 2807.0 ms |

4B selected a true but irrelevant relation on the engagement-only competitor
case, and one targeted retry removed it. 1.7B passed the pilot first-pass, but
some rendered outputs contained repeated facts or low-value recommendation
phrases. Those are presentation/selection-quality issues, not semantic safety
misses.

## Decision

The trusted-relation architecture passes the local research gate.

The preferred efficiency baseline for this narrow relation-selection contract is
Qwen3-1.7B, because it matched or exceeded Qwen3-4B on first-pass relation
metrics and had lower latency. Qwen3-4B remains useful as a stronger fallback for
broader semantic tasks, but this architecture materially narrows the model-size
need for relation safety.

Do not deploy this research module directly. The next phase should extract a
production-owned claim/evidence/relation contract under the Django backend,
while preserving Groq as the production AI provider until a separate deployment
decision is made.
