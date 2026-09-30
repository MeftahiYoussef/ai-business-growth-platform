# Small LLM Claim Ledger V2

Status: local research validation.

## Objective

Claim ledger V1 proved that deterministic validation can catch unsafe semantic
claims, but live Qwen runs showed that models often selected relevant evidence
IDs while corrupting the same facts in free-form claim text.

Claim ledger V2 removes that duplicated factual expression.

Core rule:

> one authoritative representation per fact.

Trusted evidence owns factual values, units, availability, and categorical
state. The model selects evidence and relations. The deterministic renderer
writes factual prose.

## V2 Evidence

Known evidence:

```json
{
  "id": "F2",
  "subject": "trend",
  "predicate": "momentum",
  "status": "known",
  "value": 0.22,
  "value_type": "percentage",
  "display_value": "22%",
  "polarity": "positive"
}
```

Unavailable evidence:

```json
{
  "id": "U1",
  "subject": "content_performance",
  "predicate": "reach",
  "status": "unavailable"
}
```

## V2 Model Output

The model does not write fact text.

```json
{
  "facts": [{"evidence_id": "F2"}],
  "limitations": [{"evidence_id": "U1"}],
  "comparisons": [],
  "recommendations": []
}
```

For comparisons, the model may select a validated relation:

```json
{
  "relation_id": "R1"
}
```

The relation itself is supplied by trusted code:

```json
{
  "id": "R1",
  "left_evidence_id": "F1",
  "operator": "greater_than",
  "right_evidence_id": "F2",
  "predicate": "posts"
}
```

The validator checks that the trusted relation is true and compares the same
predicate. When trusted relations exist, the model cannot emit arbitrary
`left_evidence_id/operator/right_evidence_id` triples; it must select an allowed
`relation_id`.

## Schema Restrictions

The request-specific JSON Schema separates evidence classes:

- `facts[].evidence_id` can only use known evidence IDs.
- `limitations[].evidence_id` can only use unavailable evidence IDs.
- comparisons can only use known evidence IDs.
- when trusted relations are supplied, comparisons can only use `relation_id`
  values from the relation ledger.
- fact and limitation claims contain no model-authored factual text.

Schema-prevented invalidity classes:

- invented evidence ID
- fact citing unavailable evidence
- limitation citing known evidence
- model-generated fact value
- model-generated limitation text

## Deterministic Ownership

The model owns:

- evidence selection
- claim ordering
- relation selection
- optional recommendation action text

Deterministic code owns:

- authoritative values
- units and display values
- availability
- polarity when supplied or derivable
- factual wording
- numeric rendering
- relation truth validation
- relation affordance validation
- localization templates

## Rendering

Renderer examples:

EN:

```text
4 posts were published. Momentum is 22%. Reach data is unavailable.
```

FR:

```text
4 publications ont été publiées. Le momentum est de 22%. Les données de portée ne sont pas disponibles.
```

RU:

```text
Было опубликовано 4 публикации. Momentum составляет 22%. Данные по охвату недоступны.
```

The renderer validates before rendering. It does not repair invalid ledgers,
replace unsupported values, or add speculative facts.

## Live Result

Same 10-case local validation set as V1, using llama.cpp, Q4_K_M, temperature
0, and `/no_think`.

| Metric | 1.7B V1 | 1.7B V2 | 4B V1 | 4B V2 |
| --- | ---: | ---: | ---: | ---: |
| First-pass valid | 0.00 | 0.20 | 0.00 | 0.70 |
| Final valid after one retry | 0.00 | 0.20 | 0.20 | 0.80 |
| Required evidence selection | n/a | 1.00 | n/a | 1.00 |
| Critical evidence selection | n/a | 1.00 | n/a | 1.00 |
| Numeric mutation count | n/a | 0 | n/a | 0 |
| Unsupported claim count | n/a | 0 | n/a | 0 |
| Unavailable metric misuse | n/a | 0 | n/a | 0 |
| Invalid missed | 0 | 0 | 0 | 0 |
| Renderer additions | 0 | 0 | 0 | 0 |

V2 confirms the architecture works for factual rendering safety. Remaining
failures are mostly bad relation selection, especially false or unnecessary
comparisons.

## Decision

Claim ledger V2 is a stronger research direction than V1.

Qwen3-4B is the better candidate for the next claim-ledger research phase.
Qwen3-1.7B selects evidence correctly but over-produces invalid comparisons.

Do not deploy this yet. The next validation run should test the relation
affordance path live, especially competitor comparisons where the evidence
ledger supplies `R1` and the model only selects that relation.
