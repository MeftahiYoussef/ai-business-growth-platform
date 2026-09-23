# llama.cpp Constrained Decoding Diagnostic

- Date: `2026-09-22`
- Branch: `feature/constrained-decoding-v2`
- Logical base model: `Qwen/Qwen3-1.7B`
- Runtime: `llama.cpp 0.4.1`
- Runtime checkpoint: `ggml-org/Qwen3-1.7B-GGUF`, file `Qwen3-1.7B-Q4_K_M.gguf`
- Quantization: `Q4_K_M`
- Server binding: `127.0.0.1:8081`
- Reasoning mode: `--reasoning off` plus benchmark `/no_think`
- Temperature: `0`
- Context: `8192`
- Device result: `llama-server --list-devices` reported `BLAS: Accelerate`; no explicit Metal device was observed in this Homebrew build.

## Schema Enforcement Proof

The adversarial schema test asked the model to return `status=wrong` and an extra field under this schema:

```json
{
  "type": "object",
  "properties": {
    "status": {
      "const": "ok"
    }
  },
  "required": ["status"],
  "additionalProperties": false
}
```

llama.cpp returned:

```json
{"status": "ok"}
```

Result: `SUPPORTED_AND_ENFORCED`.

## 10-Case A/B

The same frozen first 10 `golden_eval_v2` cases were used for both runs.

| Metric | Unconstrained | JSON Schema constrained | Delta |
| --- | ---: | ---: | ---: |
| JSON parse validity | 1.0 | 1.0 | 0.0 |
| Schema validity | 0.1 | 1.0 | +0.9 |
| Seven-day validity | 0.0 | 1.0 | +1.0 |
| Required fields valid | 1.0 | 1.0 | 0.0 |
| Array fields valid | 0.0 | 1.0 | +1.0 |
| Enum valid | 1.0 | 1.0 | 0.0 |
| Unique days valid | 0.8889 | 1.0 | +0.1111 |
| Human review valid | 1.0 | 1.0 | 0.0 |
| Hallucination rate | 0.0 | 0.0 | 0.0 |
| Language match | 1.0 | 1.0 | 0.0 |
| Median latency ms | 47271.0 | 48430.0 | +1159.0 |
| P95 latency ms | 56629 | 59212 | +2583 |

The unconstrained failures were primarily `source_context`/`risk_flags` field typing and one seven-day structural failure. Enforced JSON Schema fixed those without changing the production validator.

## Language Diagnostic

The constrained 10-case run included English, French, and Russian content-plan cases.

| Language | Structure valid | Seven days valid | Human review valid | Language match | Hallucination |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| French | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| Russian | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |

## Full 50-Case Constrained Run

| Metric | Result |
| --- | ---: |
| Case count | 50 |
| Schema validity | 1.0 |
| Seven-day validity | 1.0 |
| Human-review flag rate | 1.0 |
| Hallucination rate | 0.06 |
| Forbidden-claim rate | 0.06 |
| Language match | 0.98 |
| Instruction-following rate | 0.58 |
| Required-field rate | 0.74 |
| Median latency ms | 3882.0 |
| P95 latency ms | 54037 |

Failure taxonomy:

```json
{
  "MISSING_REQUIRED_FIELD": 21
}
```

## By Task

| Task | Schema | Instruction following | Hallucination | Language match | Median latency ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Content planning | 1.0 | 0.6364 | 0.0 | 1.0 | 48924 |
| Business report | 1.0 | 0.5 | 0.0 | 0.875 | 3882 |
| Trend intelligence | 1.0 | 1.0 | 0.0 | 1.0 | 6724.5 |
| Competitor analysis | 1.0 | 0.8333 | 0.0 | 1.0 | 2187 |
| Strategy | 1.0 | 0.6667 | 0.0 | 1.0 | 3915.5 |
| Safety | 1.0 | 0.0909 | 0.2727 | 1.0 | 1019 |

## By Language

| Language | Schema | Instruction following | Hallucination | Language match | Median latency ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| English | 1.0 | 0.5588 | 0.0294 | 1.0 | 3429.0 |
| French | 1.0 | 0.5556 | 0.1111 | 0.8889 | 5565 |
| Russian | 1.0 | 0.7143 | 0.1429 | 1.0 | 4805 |

## Decision

Constrained serving should remain in the experimental track. It solves the product-critical structure failures that LoRA v1 did not fix, but it does not solve semantic quality, missing required facts, weak safety refusal behavior, or all hallucination cases.

Do not train LoRA v2 yet. First design a curriculum that targets semantic fidelity and safety behavior while treating JSON Schema as the structural guardrail.

Do not benchmark Qwen3-4B yet. The 1.7B constrained run shows enough structural viability to justify improving curriculum before increasing model size.

Do not start RAG yet. Dynamic business, trend, and competitor knowledge still belongs in a future RAG phase, but the current failures are primarily instruction/fact-use and safety behavior.
