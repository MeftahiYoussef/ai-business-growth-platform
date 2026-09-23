# Semantic Failure Clusters

- Source: existing constrained Qwen run rescored with semantic evaluator v3.
- Frequency counts reflect deterministic checks, not a human quality review.

| Cluster | Frequency | Severity points | Example cases |
| --- | ---: | ---: | --- |
| `REQUIRED_FACT_RECALL` | `11` | `22` | `cp-en-001, cp-en-002, cp-fr-001, cp-ru-001, report-en-003` |
| `INSUFFICIENT_EVIDENCE` | `10` | `11` | `cp-en-003, cp-fr-002, cp-ru-002, report-en-001, report-en-002` |
| `NUMERIC_PRESERVATION` | `4` | `8` | `cp-safety-001, report-safety-001, competitor-en-002, competitor-safety-001` |
| `HALLUCINATION_RESISTANCE` | `3` | `6` | `strategy-safety-001, safety-fr-001, safety-ru-001` |
| `COMPETITOR_FACT_FIDELITY` | `1` | `2` | `competitor-en-003` |
