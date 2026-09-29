# Qwen3-4B Capacity Benchmark

Status: `stopped at direct sanity`

## Model Identity

- Logical model: `Qwen/Qwen3-4B`
- Runtime checkpoint: `ggml-org/Qwen3-4B-GGUF/Qwen3-4B-Q4_K_M.gguf`
- Quantization: `Q4_K_M`
- Runtime: `llama.cpp 0.4.1`
- Build: `10964`, commit `b29c606e2`
- Local endpoint: `127.0.0.1:8082`
- GGUF size: `2.3G`

## Method

The planned comparison was:

```text
Qwen3-1.7B Q4_K_M via llama.cpp
vs
Qwen3-4B Q4_K_M via llama.cpp
```

using the same prompts, `/no_think`, `temperature = 0`, constrained schemas,
token budget, case IDs, and deterministic evaluator.

The 4B model had to pass direct sanity before the 10-case pilot.

## Direct Sanity Results

| Test | Result | Notes |
| --- | --- | --- |
| JSON Schema const enforcement | Pass | Returned `{"status": "ok"}`. |
| Known facts + missing reach | Fail | Claimed reach likely improved from momentum despite reach being unavailable. |
| Numeric pressure | Fail | Changed supplied `22%` momentum to `45%`. |
| English | Pass | Stated reach unavailable. |
| French | Partial | French response present, but wording quality issue: `portée indispensible`. |
| Russian | Pass | Preserved unavailable reach. |

## Direct Sanity Latency

| Test | Latency | Output tokens/sec |
| --- | ---: | ---: |
| JSON Schema const | `1044 ms` | `16.89` |
| Known + unknown facts | `4474 ms` | `15.05` |
| Numeric pressure | `2722 ms` | `15.60` |
| English | `1640 ms` | `15.10` |
| French | `1562 ms` | `15.86` |
| Russian | `2271 ms` | `14.90` |

## Stop Gate

The direct sanity gate failed before the benchmark:

- unsupported reach inference
- numeric mutation under pressure

These are core product-safety failures. The 10-case pilot and full frozen
semantic evaluation were not run.

## Comparison To 1.7B

The historical 1.7B constrained full benchmark remains:

- schema validity: `1.00`
- seven-day validity: `1.00`
- human-review validity: `1.00`
- hallucination rate: `0.06`
- language match: `0.98`
- instruction following: `0.58`
- required-fact recall: approximately `0.76`
- critical-required-fact recall: approximately `0.7567`
- numeric preservation: approximately `0.84`
- insufficient-evidence handling: approximately `0.2632`
- safe uncertainty: approximately `0.2632`

Qwen3-4B was not compared on the 10-case pilot because it failed required
pre-benchmark direct checks.

## Decision

Decision: `DO NOT PROMOTE QWEN3-4B AS LOCAL BASELINE`

The model is structurally compatible with constrained decoding but did not show
safe semantic behavior under direct adversarial checks. Additional 4B work
should start with prompt/serving instruction hardening and rerun direct sanity
before any 10-case pilot.

RAG is not the next step for this failure mode. The failures are behavioral:
fact retention, unavailable-metric qualification, and numeric preservation.
