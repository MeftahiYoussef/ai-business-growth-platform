# Small LLM Constrained Decoding

This document records the first local constrained-decoding diagnostic for the
small-LLM track.

## Scope

This is local experimentation only.

It does not change:

- Groq production behavior
- staging deployments
- frontend feature flags
- Railway or Vercel infrastructure
- RAG status
- social publishing, scheduling, or approval behavior

## Runtime

| Field | Value |
| --- | --- |
| Logical base model | `Qwen/Qwen3-1.7B` |
| Runtime | `llama.cpp 0.4.1` |
| Runtime checkpoint | `ggml-org/Qwen3-1.7B-GGUF` |
| File | `Qwen3-1.7B-Q4_K_M.gguf` |
| Quantization | `Q4_K_M` |
| Host | `127.0.0.1` only |
| Port | `8081` |
| Reasoning | disabled with `--reasoning off` and benchmark `/no_think` |
| Temperature | `0` |

The Homebrew `llama.cpp` build reported `BLAS: Accelerate`; no explicit Metal
device was observed in `llama-server --list-devices` or logs.

## JSON Schema Enforcement

The adversarial enforcement test passed. The prompt requested an invalid value
and an extra field, while the schema required:

```json
{"status": "ok"}
```

The constrained runtime returned exactly the allowed object. Result:
`SUPPORTED_AND_ENFORCED`.

## Production Contract

The serving schema is derived from the Django-owned
`content_plan_contract_v2`. Production validation remains authoritative.

The diagnostic added an optional serving-only schema mode for ordered day
constraints. The standard schema was sufficient for the first run, so ordered
day constraints were not required.

## Results Summary

| Metric | Unconstrained 10-case | Constrained 10-case | Constrained 50-case |
| --- | ---: | ---: | ---: |
| Schema validity | 0.1 | 1.0 | 1.0 |
| Seven-day validity | 0.0 | 1.0 | 1.0 |
| Human-review validity | 1.0 | 1.0 | 1.0 |
| Array field validity | 0.0 | 1.0 | 1.0 |
| Hallucination rate | 0.0 | 0.0 | 0.06 |
| Language match | 1.0 | 1.0 | 0.98 |
| Instruction-following rate | 0.0 | 0.5 | 0.58 |
| Median latency ms | 47271.0 | 48430.0 | 3882.0 |
| P95 latency ms | 56629 | 59212 | 54037 |

## Interpretation

Constrained decoding solves the structural failures that LoRA v1 did not solve:

- JSON structure
- required content-plan fields
- array field types
- allowed enum values
- seven content-plan items
- unique days 1 through 7
- `requires_human_review=true`

It does not solve all semantic behavior:

- required supplied facts are still missed
- safety refusal behavior is weak
- some forbidden claims remain in safety cases
- French quality has one language-match miss
- long content-plan generation is slow

## Decision

Keep constrained serving in the experimental track.

Do not train LoRA v2 yet. Prepare SFT curriculum v2 around semantic fidelity,
safety refusals, multilingual instruction following, and required-fact coverage.

Do not benchmark Qwen3-4B yet. The 1.7B model has not exhausted the constrained
serving plus curriculum-improvement path.

Do not begin RAG yet. RAG remains the future solution for dynamic knowledge, not
for structural JSON enforcement.

## Detailed Reports

```text
ml/eval/reports/llama_cpp_constrained_decoding.md
ml/training/reports/lora_v1_failure_analysis.md
```
