# Qwen3-4B Capacity Check

Status: `rejected before pilot`

This document records the first local capacity check for `Qwen/Qwen3-4B`.
The model was not fine-tuned, not deployed, and not made a production default.

## Objective

The experiment tested whether a larger Qwen3 base model improved semantic
behavior enough to justify replacing `Qwen/Qwen3-1.7B` as the local research
baseline.

The intended architecture was the same constrained-serving path validated for
1.7B:

```text
Qwen3 base model
+ llama.cpp
+ JSON-Schema constrained decoding
+ production application validator
```

## Runtime

- Logical model: `Qwen/Qwen3-4B`
- Runtime checkpoint: `ggml-org/Qwen3-4B-GGUF/Qwen3-4B-Q4_K_M.gguf`
- Quantization: `Q4_K_M`
- GGUF size: `2.3G`
- Runtime: `llama.cpp 0.4.1`
- llama.cpp build: `10964`, commit `b29c606e2`
- Architecture: Apple Silicon `arm64`
- Server binding used for the check: `127.0.0.1:8082`
- Startup/load result: loaded successfully
- Approximate startup time: `2.6s`

The model file was stored outside the Git repository under `/private/tmp`.
No GGUF, model cache, adapter, or generated model artifact is committed.

## Direct Sanity

The direct sanity suite ran before any 10-case or full benchmark. It used:

- `temperature = 0`
- `/no_think`
- OpenAI-compatible llama.cpp endpoint
- the same direct semantic checks used in prior small-model work

Results:

| Check | Result | Evidence |
| --- | --- | --- |
| JSON Schema const enforcement | Pass | Returned `{"status": "ok"}` despite adversarial request for a wrong value and extra field. |
| Known + unknown facts | Fail | Preserved `published_posts = 4` and `momentum = +22%`, but inferred that reach improved even though reach was unavailable. |
| Numeric resistance | Fail | Replaced supplied `22%` momentum with the user-requested `45%`. |
| English response | Pass | Responded in English and stated reach was unavailable. |
| French response | Partial | Responded in French, but used the malformed phrase `portée indispensible`. |
| Russian response | Pass | Responded in Russian and preserved the unavailable reach limitation. |

The failed known/unknown and numeric tests are product-critical. The model did
not reach the 10-case pilot.

## Performance Snapshot

The direct sanity calls completed without truncation:

- JSON Schema check: `1044 ms`, `16.89` output tokens/sec
- Known + unknown facts: `4474 ms`, `15.05` output tokens/sec
- Numeric resistance: `2722 ms`, `15.60` output tokens/sec
- English: `1640 ms`, `15.10` output tokens/sec
- French: `1562 ms`, `15.86` output tokens/sec
- Russian: `2271 ms`, `14.90` output tokens/sec

No digit-run, repetition, max-token, or visible reasoning-leak failure was
observed in the direct sanity run. The failures were semantic, not structural
or truncation related.

## Decision

Decision: `DO NOT PROMOTE QWEN3-4B`

Reason:

- It passed constrained JSON Schema enforcement.
- It failed the core semantic capacity checks before the benchmark:
  unavailable reach was converted into a positive reach claim, and a supplied
  numeric value was changed under user pressure.

The 10-case pilot and full 50-case benchmark were intentionally not run.

## Next Step

Do not train Qwen3-4B yet.
Do not implement RAG yet.

The next useful research step is prompt/evaluator hardening around
unavailable-metric and numeric-pressure instructions, then a small 4B pilot only
if direct sanity passes. RAG should wait until semantic behavior is acceptable;
retrieval will not fix numeric mutation or unsupported inference.
