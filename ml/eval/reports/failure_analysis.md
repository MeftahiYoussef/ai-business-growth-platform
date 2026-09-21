# Small LLM Failure Analysis

Evaluation date: 2026-09-21

## Top Product-Relevant Qwen Failures

1. `cp-en-001` - `MISSING_REQUIRED_FIELD` - target: `PROMPT_FIX + FINE_TUNING`
   - task: `content_planning`, language: `en`

2. `cp-fr-001` - `MISSING_REQUIRED_FIELD` - target: `PROMPT_FIX + FINE_TUNING`
   - task: `content_planning`, language: `fr`

3. `cp-ru-001` - `MISSING_REQUIRED_FIELD` - target: `PROMPT_FIX + FINE_TUNING`
   - task: `content_planning`, language: `ru`

4. `report-en-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `business_report`, language: `en`

5. `report-fr-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `business_report`, language: `fr`

6. `trend-en-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `trend_intelligence`, language: `en`

7. `trend-ru-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `trend_intelligence`, language: `ru`

8. `competitor-en-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `competitor_analysis`, language: `en`

9. `strategy-fr-001` - `SCHEMA_FAILURE` - target: `FINE_TUNING`
   - task: `strategy`, language: `fr`

## Category Guidance

- FINE_TUNING: schema discipline, exact field names, human-review markers, multilingual structured output.
- RAG: no pilot failures require RAG; future business, competitor, trend, and historical facts should be retrieved rather than memorized.
- DETERMINISTIC_CODE: numeric metrics, forecasts, quotas, ownership, and application counts must remain code-owned.
- PROMPT_FIX: align `expected_schema` naming with the real application validators and include compact schema examples in evaluation prompts.

## SFT Candidate Set

- Candidate source: `ml/datasets/candidates/qwen3_sft_v1_candidates.jsonl`
- Candidate count: 120
- Accepted count: 120
- Rejected count after duplicate regeneration: 0
- Train split: 108
- Validation split: 12
- Test split: 0; the golden evaluation set remains separate.

## Future Training Command

Do not run until approved:

```bash
mlx_lm.lora --train --config ml/training/qwen3_1_7b_lora_v1.yaml
```
