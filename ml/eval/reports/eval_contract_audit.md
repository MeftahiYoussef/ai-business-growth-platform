# Evaluation Contract Audit

- Evaluation version: `golden_eval_v2`
- Content-plan contract: `content_plan_contract_v2`
- Total cases: `50`
- Valid cases: `50`
- Corrected cases: `11`
- Rejected cases: `0`

## Cases By Task

```json
{
  "business_report": 8,
  "competitor_analysis": 6,
  "content_planning": 11,
  "safety": 11,
  "strategy": 6,
  "trend_intelligence": 8
}
```

## Corrections

- `cp-en-001`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-002`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-003`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-004`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-005`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-fr-001`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-fr-002`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-ru-001`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-ru-002`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-006`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)
- `cp-en-007`: `content_plan_v1` -> `content_plan_contract_v2` (stale content-plan schema metadata)

## Root Cause

The v1 baseline used content-planning case metadata and prompts that did not state the full production schema. The evaluator then applied a partial seven-day gate that was disconnected from the production validator. v2 freezes the application-owned content-plan contract as the benchmark source of truth.
