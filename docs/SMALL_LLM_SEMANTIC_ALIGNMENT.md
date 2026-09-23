# Small LLM Semantic Alignment V2

Status: local research only. No staging deployment, LoRA v2 training, RAG,
pgvector, or production-provider change has occurred.

## Dependency

This branch is based on the unmerged constrained-decoding work from PR #15
because semantic alignment depends on its llama.cpp schema-constrained
benchmarking code and `content_plan_contract_v2` serving-schema support.

## Current Finding

Constrained decoding solved the structural content-plan problem for
Qwen3-1.7B Q4_K_M:

- schema validity: 1.00
- seven-day validity: 1.00
- human-review validity: 1.00

The remaining problem is semantic behavior:

- instruction following: 0.58
- required fact recall: 0.76
- critical required fact recall: 0.7567
- hallucination/forbidden-claim rate: 0.06
- numeric preservation: 0.84
- insufficient-evidence handling: 0.2632
- language match: 0.98

## Semantic Evaluator Audit

The evaluator was audited and rescored against the existing constrained Qwen
outputs. The golden case content remains `golden_eval_v2`; the scoring layer is
versioned as `golden_eval_v3_semantic_grading`.

No evaluator false negatives were found in the existing constrained run. The low
safety score is therefore treated as a genuine model behavior issue rather than
a benchmark artifact.

## Product-Critical Failure Clusters

1. REQUIRED_FACT_RECALL: omits supplied business, metric, or limitation facts.
2. INSUFFICIENT_EVIDENCE: fails to clearly state when reach, followers,
   engagement, or conversion data is unavailable.
3. NUMERIC_PRESERVATION: omits or changes supplied numeric facts.
4. HALLUCINATION_RESISTANCE: sometimes follows user pressure to make unsupported
   claims.
5. COMPETITOR_FACT_FIDELITY: may omit supplied competitor facts in summaries.

## SFT Curriculum V2

The first SFT v2 dataset has been generated as `qwen3_sft_v2` and remains
local training preparation only. LoRA v2 has not been trained.

Dataset summary:

- generated candidates: 372
- accepted examples: 360
- rejected examples: 12
- train examples: 324
- validation examples: 36
- exact duplicates: 0
- near duplicates: 0
- golden leakage findings: 0
- English/French/Russian split: 144 / 108 / 108

LoRA v2, if approved later, should teach semantic behavior only:

- hallucination resistance;
- required-fact retention;
- numeric preservation;
- insufficient-evidence behavior;
- report interpretation;
- trend metric fidelity;
- competitor fact fidelity;
- recommendation-vs-fact separation;
- French and Russian semantic instruction following;
- adversarial requests to fabricate metrics.

It must not teach:

- JSON syntax;
- field order;
- enum formatting;
- seven-day structure;
- dynamic business facts;
- current trend knowledge.

## Fixed Acceptance Gates

Future LoRA v2 must be evaluated before any promotion:

| Metric | Gate |
| --- | ---: |
| schema validity under constrained serving | 1.00 |
| seven-day validity under constrained serving | 1.00 |
| human-review validity | 1.00 |
| critical numeric mutations | 0 |
| hallucination failure rate | <= 0.02 |
| instruction following | >= 0.80 |
| required fact recall | >= 0.90 |
| critical required fact recall | >= 0.95 |
| numeric preservation | >= 0.98 |
| language match | >= 0.95 |
| insufficient-evidence handling | >= 0.90 |

These targets are experimental and must not be moved after viewing LoRA v2
results without creating a new evaluation version.

## LoRA vs RAG Boundary

LoRA should teach durable behavior: refusing unsupported claims, preserving
numbers, separating facts from recommendations, and following multilingual task
instructions.

RAG should supply changing knowledge later: business profiles, brand voice,
approved content, current trends, trend predictions, competitor information,
historical reports, strategy records, and uploaded documents. Dynamic business
facts must not be baked into adapter weights.

## Next Step

Human-review the generated SFT v2 dataset, then decide whether to run the first
LoRA v2 training task. Do not train LoRA v2 in the dataset-generation task.
