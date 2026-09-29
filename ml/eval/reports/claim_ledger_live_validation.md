# Claim Ledger Live Validation

Date: 2026-09-29

Branch: `feature/claim-ledger-model-validation`

## Summary

The evidence-grounded claim ledger was validated against live local Qwen
generation through llama.cpp constrained decoding.

The deterministic validator successfully blocked critical invalid semantic
content after tightening. No invalid semantic ledger was missed in the final
validation run.

The architecture is not yet usable as a generation pipeline:

- Qwen3-1.7B produced 0/10 final valid claim ledgers after one targeted retry.
- Qwen3-4B produced 2/10 final valid claim ledgers after one targeted retry.
- Both models had 0/10 first-pass valid ledgers.

The result supports the claim ledger as a safety/validation direction, but not
as a ready serving format for either model.

## Contract

Contract version: `claim_ledger_v1`

Allowed claim types:

- `fact`
- `limitation`
- `recommendation`

Claim shape:

```json
{
  "claim_type": "fact",
  "text": "Published posts were 4.",
  "evidence_ids": ["F1"]
}
```

Top-level shape:

```json
{
  "claims": []
}
```

Schema rules:

- `additionalProperties=false`
- `claims` must be a non-empty array
- `claim_type`, `text`, and `evidence_ids` are required
- `evidence_ids` are constrained to request-specific evidence IDs where the
  constrained runtime supports dynamic enums

## Deterministic Validator Rules

The validator rejects:

- invented evidence IDs
- empty evidence citations
- `fact` claims citing unavailable evidence
- `limitation` claims without unavailable evidence
- `recommendation` claims without known evidence
- immutable numeric mutation
- unsupported numeric values
- unsupported assertions about unavailable metrics
- required evidence omissions
- critical evidence omissions
- simple categorical contradictions, such as `fading` versus `emerging`
- recommendation text phrased as an observed fact
- FR/RU claim text that does not match the requested language

The safe renderer validates the payload first and renders only validated claims.
It does not repair invalid claims, replace numbers, or add new facts.

## Pre-Live Tests

Targeted pytest result:

- `37 passed`

Coverage added or verified:

- invented evidence ID
- unavailable evidence used as a fact
- limitation citing known-only evidence
- unsupported numeric value
- numeric equivalence: `0.22`, `22%`, `+22%`
- negative value preservation
- decimal preservation
- conflicting claims
- duplicate contradictory claims
- recommendation phrased as observation
- required fact omitted
- critical fact omitted
- known fact retained while another metric is unavailable
- invalid payload passed to renderer
- empty `evidence_ids`
- French claim metadata
- Russian claim metadata

## Runtime

Runtime: `llama.cpp`

Version: `0.4.1`

Build: `10964`

Commit: `b29c606e2`

Reasoning mode: disabled with the same `/no_think` convention used in prior
Qwen3 local runs.

Temperature: `0`

Models:

- `Qwen/Qwen3-1.7B`, GGUF `Q4_K_M`
- `Qwen/Qwen3-4B`, GGUF `Q4_K_M`

No LoRA adapters were used.

## Live Cases

The final run used 10 synthetic, non-private cases covering:

- known facts plus unavailable metrics
- numeric pressure
- unavailable engagement
- competitor engagement
- trend lifecycle conflict
- report interpretation
- recommendation/fact separation
- English
- French
- Russian

One targeted retry was allowed for validator-rejected claim ledgers. The retry
included only deterministic validation failures and did not mutate the evidence
ledger.

## Final Results

| Metric | Qwen3-1.7B | Qwen3-4B |
| --- | ---: | ---: |
| Cases | 10 | 10 |
| First-pass valid rate | 0.00 | 0.00 |
| Semantic validator pass rate | 0.00 | 0.20 |
| Final valid rate after one retry | 0.00 | 0.20 |
| Invalid but detected | 10 | 10 |
| Invalid and missed | 0 | 0 |
| Retry attempts | 10 | 10 |
| Retry successes | 0 | 2 |
| Language match | 0.90 | 0.90 |
| Renderer semantic additions | 0 | 0 |
| Average first-pass latency | 4969.3 ms | 9817.5 ms |

## 4B Valid-After-Retry Cases

Qwen3-4B recovered two cases after one targeted retry:

- known facts plus unavailable reach
- unavailable engagement

The recovered ledgers retained supplied facts or limitations and passed the safe
renderer. They do not establish production readiness because 8/10 cases still
failed after retry.

## Main Rejection Causes

Qwen3-1.7B final run:

- unavailable metric misuse: 14 validator findings
- numeric preservation failures: 7 validator findings
- recommendation/fact separation failures: 4 validator findings
- required evidence omissions: 2 findings
- critical evidence omissions: 1 finding

Qwen3-4B final run:

- numeric preservation failures: 6 validator findings
- recommendation/fact separation failures: 6 validator findings
- required evidence omissions: 4 findings
- critical evidence omissions: 3 findings
- language mismatches: 3 findings
- unavailable metric misuse: 2 findings

## Free-Form Comparison

The same 10 cases were run without the claim-ledger JSON contract as a direct
sanity comparison.

| Metric | Qwen3-1.7B free-form | Qwen3-4B free-form |
| --- | ---: | ---: |
| Oracle-valid rate | 0.30 | 0.50 |
| Average latency | 1345.1 ms | 5073.5 ms |

Free-form output occasionally looked better by the lightweight oracle, but it
does not provide deterministic claim-level validation or a safe renderer. The
claim-ledger pipeline is stricter and safer, but currently too difficult for
these base models to satisfy reliably.

## Gate Decision

The live validation gate failed.

Reasons:

- first-pass validity was 0.00 for both models
- final validity after one retry was 0.00 for 1.7B and 0.20 for 4B
- numeric mutation and recommendation/fact separation failures remained common
- 4B improved recoverability but not enough to justify promotion

No 50-case benchmark was run.

## Model Decision

Outcome: `ARCHITECTURE INSUFFICIENT`

The deterministic validator is useful and caught critical errors, but the
current claim-ledger contract and prompt are not yet generation-friendly enough
for base Qwen3-1.7B or Qwen3-4B.

Preferred local model: none for claim-ledger serving yet.

Qwen3-4B showed modest additional value through two retry recoveries, but the
resource cost and low final-valid rate do not justify making it the local base
model.

Further LoRA is not justified until the claim-ledger contract is stabilized and
the base models can produce valid ledgers at a much higher rate.

RAG is not justified as the immediate next phase. The remaining failures are
behavioral and validation-contract related, not missing dynamic knowledge.

## Recommended Next Phase

Refine the claim-ledger contract before more model work:

- separate model-generated semantic fields from rendered prose
- consider structured fields such as `subject`, `predicate`, `value`, and
  `polarity`
- make recommendations cite known facts while allowing collection/measurement
  recommendations for unavailable metrics
- keep deterministic validation as the authority
- keep the renderer deterministic and separate from model generation
- repeat a small 1.7B/4B live validation only after the contract becomes easier
  for constrained decoding

The production promotion boundary remains unchanged: if this architecture
eventually succeeds, move the contract into a production-owned backend module
in a later phase. Do not import `ml/eval/claim_ledger.py` into runtime Django
code directly.
