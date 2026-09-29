# Small LLM Claim Ledger

Status: research design and deterministic validation foundation.

Live model validation has been run with local Qwen3-1.7B and Qwen3-4B through
llama.cpp constrained decoding. The validator caught critical invalid claim
ledgers, but the current contract is not yet usable as a serving format:
first-pass validity was 0/10 for both models, and one targeted retry recovered
0/10 for 1.7B and 2/10 for 4B. This remains research-only and is not promoted
to production.

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
    {"claim_type": "fact", "text": "Published posts were 4.", "evidence_ids": ["F1"]},
    {"claim_type": "fact", "text": "Momentum was 22%.", "evidence_ids": ["F2"]},
    {"claim_type": "limitation", "text": "Reach is unavailable.", "evidence_ids": ["U1"]},
    {
      "claim_type": "recommendation",
      "text": "Use the 4 published posts and 22% momentum to guide the next content review.",
      "evidence_ids": ["F1", "F2"]
    }
  ]
}
```

## Deterministic Rules

- `fact` claims may cite only known facts.
- `limitation` claims must cite unavailable evidence.
- `recommendation` claims must cite at least one known fact.
- Every cited evidence ID must exist in the source evidence ledger.
- Immutable numbers must be preserved exactly or as an allowed equivalent, such
  as `0.22` and `22%`.
- Unsupported numeric values are rejected.
- Required and critical evidence IDs can be enforced per request.
- Claims about unavailable metrics, such as "reach improved", are rejected even
  when the model cites a known fact instead of the unavailable evidence.
- Invalid claim ledgers must not be rendered into user-facing prose.

## Scope

This is local research tooling. It does not change Groq production behavior,
does not deploy Qwen, and does not implement RAG. RAG remains the future source
for changing knowledge; the claim ledger is a semantic grounding and validation
layer for supplied evidence.

## Live Validation Result

Final local validation results are tracked in
`ml/eval/reports/claim_ledger_live_validation.md`.

Decision:

- keep the claim-ledger concept as a safety architecture candidate
- do not promote the current contract
- do not deploy it
- do not train another adapter from these results
- refine the structured claim representation before more model benchmarking
