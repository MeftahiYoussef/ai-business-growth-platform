# SFT v2 Quality Audit

- Dataset version: `qwen3_sft_v2`.
- Status: frozen for future LoRA v2 training readiness review; LoRA v2 has not been trained.
- Requested target count: `approximately 360`.
- Generated candidates: `372`.
- Accepted records: `360`.
- Rejected records: `12`.
- Rejection reasons: `{"Assistant answer cannot be empty": 2, "Record appears to contain a secret or credential-bearing URL": 2, "invented_unavailable_metric": 4, "numeric_mutation": 4}`.
- Exact duplicates: `0`.
- Near duplicates: `0`.
- Near-duplicate rate: `0.0`.
- Golden leakage findings: `0`.
- Train records: `324`.
- Validation records: `36`.
- Average input tokens approximation: `24.08`.
- Average output tokens approximation: `51.1`.
- Distinct numeric values: `124`.

## Distributions

```json
{
  "behavior": {
    "adversarial_fabrication_resistance": 200,
    "business_reports": 36,
    "competitor_fact_fidelity": 16,
    "difficult_multilingual": 36,
    "fact_vs_recommendation": 16,
    "hallucination_resistance": 72,
    "insufficient_evidence": 36,
    "numeric_preservation": 416,
    "required_fact_retention": 56,
    "safe_uncertainty": 360,
    "trend_metric_fidelity": 36
  },
  "difficulty": {
    "easy": 72,
    "hard": 108,
    "medium": 180
  },
  "language": {
    "en": 144,
    "fr": 108,
    "ru": 108
  },
  "task": {
    "business_report": 36,
    "competitor_analysis": 16,
    "safety": 144,
    "strategy": 72,
    "trend_intelligence": 92
  }
}
```

## Family Distribution

```json
{
  "BUSINESS_REPORTS_01": 4,
  "BUSINESS_REPORTS_02": 4,
  "BUSINESS_REPORTS_03": 4,
  "BUSINESS_REPORTS_04": 4,
  "BUSINESS_REPORTS_05": 4,
  "BUSINESS_REPORTS_06": 4,
  "BUSINESS_REPORTS_07": 4,
  "BUSINESS_REPORTS_08": 4,
  "BUSINESS_REPORTS_09": 4,
  "COMPETITOR_FACT_FIDELITY_01": 4,
  "COMPETITOR_FACT_FIDELITY_02": 4,
  "COMPETITOR_FACT_FIDELITY_03": 4,
  "COMPETITOR_FACT_FIDELITY_04": 4,
  "DIFFICULT_MULTILINGUAL_01": 4,
  "DIFFICULT_MULTILINGUAL_02": 4,
  "DIFFICULT_MULTILINGUAL_03": 4,
  "DIFFICULT_MULTILINGUAL_04": 4,
  "DIFFICULT_MULTILINGUAL_05": 4,
  "DIFFICULT_MULTILINGUAL_06": 4,
  "DIFFICULT_MULTILINGUAL_07": 4,
  "DIFFICULT_MULTILINGUAL_08": 4,
  "DIFFICULT_MULTILINGUAL_09": 4,
  "FACT_VS_RECOMMENDATION_01": 4,
  "FACT_VS_RECOMMENDATION_02": 4,
  "FACT_VS_RECOMMENDATION_03": 4,
  "FACT_VS_RECOMMENDATION_04": 4,
  "HALLUCINATION_RESISTANCE_01": 4,
  "HALLUCINATION_RESISTANCE_02": 4,
  "HALLUCINATION_RESISTANCE_03": 4,
  "HALLUCINATION_RESISTANCE_04": 4,
  "HALLUCINATION_RESISTANCE_05": 4,
  "HALLUCINATION_RESISTANCE_06": 4,
  "HALLUCINATION_RESISTANCE_07": 4,
  "HALLUCINATION_RESISTANCE_08": 4,
  "HALLUCINATION_RESISTANCE_09": 4,
  "HALLUCINATION_RESISTANCE_10": 4,
  "HALLUCINATION_RESISTANCE_11": 4,
  "HALLUCINATION_RESISTANCE_12": 4,
  "HALLUCINATION_RESISTANCE_13": 4,
  "HALLUCINATION_RESISTANCE_14": 4,
  "HALLUCINATION_RESISTANCE_15": 4,
  "HALLUCINATION_RESISTANCE_16": 4,
  "HALLUCINATION_RESISTANCE_17": 4,
  "HALLUCINATION_RESISTANCE_18": 4,
  "INSUFFICIENT_EVIDENCE_01": 4,
  "INSUFFICIENT_EVIDENCE_02": 4,
  "INSUFFICIENT_EVIDENCE_03": 4,
  "INSUFFICIENT_EVIDENCE_04": 4,
  "INSUFFICIENT_EVIDENCE_05": 4,
  "INSUFFICIENT_EVIDENCE_06": 4,
  "INSUFFICIENT_EVIDENCE_07": 4,
  "INSUFFICIENT_EVIDENCE_08": 4,
  "INSUFFICIENT_EVIDENCE_09": 4,
  "NUMERIC_PRESERVATION_01": 4,
  "NUMERIC_PRESERVATION_02": 4,
  "NUMERIC_PRESERVATION_03": 4,
  "NUMERIC_PRESERVATION_04": 4,
  "NUMERIC_PRESERVATION_05": 4,
  "NUMERIC_PRESERVATION_06": 4,
  "NUMERIC_PRESERVATION_07": 4,
  "NUMERIC_PRESERVATION_08": 4,
  "NUMERIC_PRESERVATION_09": 4,
  "NUMERIC_PRESERVATION_10": 4,
  "NUMERIC_PRESERVATION_11": 4,
  "NUMERIC_PRESERVATION_12": 4,
  "NUMERIC_PRESERVATION_13": 4,
  "NUMERIC_PRESERVATION_14": 4,
  "REQUIRED_FACT_RETENTION_01": 4,
  "REQUIRED_FACT_RETENTION_02": 4,
  "REQUIRED_FACT_RETENTION_03": 4,
  "REQUIRED_FACT_RETENTION_04": 4,
  "REQUIRED_FACT_RETENTION_05": 4,
  "REQUIRED_FACT_RETENTION_06": 4,
  "REQUIRED_FACT_RETENTION_07": 4,
  "REQUIRED_FACT_RETENTION_08": 4,
  "REQUIRED_FACT_RETENTION_09": 4,
  "REQUIRED_FACT_RETENTION_10": 4,
  "REQUIRED_FACT_RETENTION_11": 4,
  "REQUIRED_FACT_RETENTION_12": 4,
  "REQUIRED_FACT_RETENTION_13": 4,
  "REQUIRED_FACT_RETENTION_14": 4,
  "TREND_METRIC_FIDELITY_01": 4,
  "TREND_METRIC_FIDELITY_02": 4,
  "TREND_METRIC_FIDELITY_03": 4,
  "TREND_METRIC_FIDELITY_04": 4,
  "TREND_METRIC_FIDELITY_05": 4,
  "TREND_METRIC_FIDELITY_06": 4,
  "TREND_METRIC_FIDELITY_07": 4,
  "TREND_METRIC_FIDELITY_08": 4,
  "TREND_METRIC_FIDELITY_09": 4
}
```

## Readiness

- Exact duplicate gate: PASS.
- Near duplicate gate: PASS.
- Golden leakage gate: PASS.
- Numeric preservation validation: PASS.
- Unavailable metric validation: PASS.
- Critical fact validation: PASS.
- Group-aware split: PASS.

LoRA v2 is ready for a separate training task only after human review of this dataset.
