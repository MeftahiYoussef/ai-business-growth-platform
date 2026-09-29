# Small LLM Claim Ledger

Status: research design and deterministic validation foundation.

The Qwen3 experiments showed that schema-constrained decoding solves JSON
structure, but not semantic grounding. The next safe serving pattern is a claim
ledger between model output and user-facing prose:

```text
source facts + unavailable metrics
        |
        v
evidence ledger
        |
        v
schema-constrained claim ledger
        |
        v
deterministic semantic validator
        |
        v
user-facing prose renderer
```

## Example

Input evidence:

```text
F1 published_posts = 4
F2 momentum = 22%
U1 reach = unavailable

IMMUTABLE NUMBERS
momentum = 22%
```

Valid constrained output:

```json
{
  "claims": [
    {"claim_type": "FACT", "text": "Published posts were 4.", "evidence": ["F1"]},
    {"claim_type": "FACT", "text": "Momentum was 22%.", "evidence": ["F2"]},
    {"claim_type": "LIMITATION", "text": "Reach is unavailable.", "evidence": ["U1"]},
    {
      "claim_type": "RECOMMENDATION",
      "text": "Use the 4 published posts and 22% momentum to guide the next content review.",
      "evidence": ["F1", "F2"]
    }
  ]
}
```

## Deterministic Rules

- `FACT` claims may cite only known facts.
- `LIMITATION` claims must cite unavailable evidence.
- `RECOMMENDATION` claims must cite at least one known fact.
- Every cited evidence ID must exist in the source evidence ledger.
- Immutable numbers must be preserved exactly or as an allowed equivalent, such
  as `0.22` and `22%`.
- Unsupported numeric values are rejected.
- Invalid claim ledgers must not be rendered into user-facing prose.

## Scope

This is local research tooling. It does not change Groq production behavior,
does not deploy Qwen, and does not implement RAG. RAG remains the future source
for changing knowledge; the claim ledger is a semantic grounding and validation
layer for supplied evidence.
