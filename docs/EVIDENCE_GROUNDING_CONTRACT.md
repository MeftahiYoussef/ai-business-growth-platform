# Evidence Grounding Contract

Status: production-owned contract foundation.

Contract version: `evidence_grounding_v1`

## Why This Exists

Small-model research showed that free-form factual generation is the wrong
place to preserve business facts. Even when a model selected the right evidence
IDs, it could still mutate numbers, overstate unavailable metrics, or invent
comparison logic in prose.

The reliable architecture is:

```text
trusted data
↓
evidence ledger
↓
deterministic trusted relations
↓
model or system selects evidence/relation IDs
↓
deterministic validator
↓
deterministic renderer
```

This backend package promotes that contract into production-owned code without
deploying any local model and without changing current Groq behavior.

## Ownership Boundary

Research-only:

- `ml/eval/claim_ledger.py`
- local llama.cpp validation runners
- Qwen benchmark reports

Production-owned:

- `django-backend/apps/ai/contracts/evidence_grounding/`

Production code must not import the research module. The production contract is
model-agnostic and provider-agnostic.

## Evidence Model

Evidence is trusted, normalized server-side data.

Fields:

- `id`
- `subject`
- `predicate`
- `status`
- `value`
- `value_type`
- `display_value`
- `unit`
- `time_window`
- `metadata`

Supported statuses:

- `known`
- `unavailable`

Supported value types:

- `integer`
- `decimal`
- `percentage`
- `string`
- `enum`
- `boolean`

Unavailable evidence is first-class. It cannot be rendered as a factual
observation or used in deterministic comparisons. It can support a limitation.

## Numeric Normalization

Authoritative values remain singular. Numeric helper code can recognize exact
representational equivalence when evidence metadata supports it.

Examples:

- `0.22`
- `22%`
- `+22%`

These can represent the same percentage value.

Non-equivalent values remain failures:

- `22% != 23%`
- `22% != 45%`

No fuzzy numeric matching is used for materially different values.

## Trusted Relations

Relations are deterministic and trusted only when built from normalized
evidence.

Fields:

- `id`
- `relation_type`
- `predicate`
- `left_evidence_id`
- `operator`
- `right_evidence_id`
- `provenance`

Supported operators:

- `greater_than`
- `less_than`
- `equal`

The relation builder validates:

- evidence exists
- both operands are known
- predicates are compatible
- value types are compatible
- units are compatible
- time windows are compatible where required
- relation truth is deterministic

An LLM must never be trusted to provide authoritative operands, operators, or
relation truth.

## Selection Model

Selections are intentionally small:

- `FactSelection(evidence_id)`
- `LimitationSelection(evidence_id)`
- `RelationSelection(relation_id)`

Selections do not include:

- factual values
- units
- predicates
- availability
- relation operands
- relation operators
- factual prose

This prevents a model response from overriding trusted data.

## Request-Specific Allowlists

The contract can derive:

- known evidence IDs
- unavailable evidence IDs
- trusted relation IDs

These allowlists power deterministic validation today and can power constrained
provider schemas later.

## Schema Generation

The production schema constrains:

- facts to known evidence IDs
- limitations to unavailable evidence IDs
- relations to trusted relation IDs

When no trusted relations exist, relation selection is structurally disabled
with `maxItems: 0`.

No provider integration is activated by this schema in the current phase.

## Validator

The validator checks:

- selected evidence exists
- facts use known evidence
- limitations use unavailable evidence
- relation IDs exist
- relation definitions remain trusted and true
- required evidence is selected
- critical evidence is selected
- duplicate selections are rejected
- contradictory selections are rejected

Errors use explicit safe codes such as:

- `UNKNOWN_EVIDENCE_ID`
- `INVALID_FACT_EVIDENCE`
- `INVALID_LIMITATION_EVIDENCE`
- `UNKNOWN_RELATION_ID`
- `INVALID_RELATION`
- `MISSING_REQUIRED_EVIDENCE`
- `MISSING_CRITICAL_EVIDENCE`
- `DUPLICATE_SELECTION`
- `CONTRADICTORY_SELECTION`

## Renderer

The renderer receives only:

- trusted evidence
- trusted relations
- validated selections
- requested language

It adds zero new facts, zero new numbers, and zero speculative interpretation.
It resolves all factual values from the evidence ledger.

Supported deterministic factual rendering languages:

- English
- French
- Russian

Duplicate rendering is handled conservatively. If a selected relation already
communicates both operands, separate selected fact sentences for those operands
are omitted because the relation preserves their meaning and values.

## Trust Boundary

Trusted:

- server-side deterministic business data
- validated report metrics
- validated trend calculations
- approved business profile data

Not automatically trusted:

- LLM-generated claims
- raw external text
- future retrieved documents
- user-supplied assertions that have not been normalized and validated

Raw LLM output must never become trusted evidence merely because it is
well-formed.

## Groq Boundary

Current Groq prompts and provider behavior are unchanged.

A future integration could be:

```text
provider response
↓
structured selection
↓
evidence contract validation
↓
deterministic renderer
```

That path is not active in this phase.

## Future Local Model Boundary

A future local-model integration could use:

```text
request-specific schema
+
Qwen3-1.7B
+
constrained decoding
```

No Qwen, llama.cpp, or MLX runtime dependency is added to Django by this
contract foundation.

## Future RAG Boundary

Future RAG should provide normalized evidence, not final claims:

```text
retriever
↓
normalized trusted evidence
↓
trusted relation builder
↓
claim selection
↓
validator
↓
renderer
```

This phase does not implement retrieval, embeddings, pgvector, vector tables, or
document chunking.

## Current Product Impact

This is foundational code only.

No current endpoint response changes. No database migration. No provider switch.
No model deployment. Existing content-plan generation, async content generation,
reports, drafts, notifications, exports, and human-review behavior remain
unchanged.
