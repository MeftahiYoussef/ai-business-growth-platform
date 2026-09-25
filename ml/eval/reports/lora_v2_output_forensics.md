# LoRA v2 Output Forensics

Status: `LoRA v2 rejected`.

This report analyzes the existing 10-case pilot outputs only. No model calls were made.

## Summary

- Paired cases analyzed: `10`
- Base median latency: `4896.5 ms`
- LoRA median latency: `31267.0 ms`
- Base median output chars: `756.0`
- LoRA median output chars: `1237.0`
- Base median output words: `77.5`
- LoRA median output words: `41.0`
- Base approximate word tokens/sec: `20.35`
- LoRA approximate word tokens/sec: `12.56`
- Base outputs with uncertainty phrases: `1`
- LoRA outputs with uncertainty phrases: `2`
- Thinking marker cases, base: `10`
- Thinking marker cases, LoRA: `0`
- Long digit-run cases, base: `0`
- Long digit-run cases, LoRA: `3`
- Degenerative repetition cases, base: `6`
- Degenerative repetition cases, LoRA: `4`

## Fact-Retention Error Types

```json
{
  "critical_fact_failures": {
    "FACT_DROPPED": 5,
    "FACT_MUTATED": 2,
    "FACT_REPLACED_WITH_RECOMMENDATION": 8
  },
  "required_fact_failures": {
    "FACT_DROPPED": 9,
    "FACT_MUTATED": 2,
    "FACT_REPLACED_WITH_RECOMMENDATION": 9
  }
}
```

## Uncertainty Behavior

```json
{
  "correct_uncertainty_rate": {
    "base": 0.4,
    "lora": 0.6
  },
  "known_fact_retention_under_uncertainty": {
    "base": 0.5,
    "lora": 0.25
  },
  "over_uncertainty_rate": {
    "base": 0.0,
    "lora": 0.1
  },
  "partial_answer_success_rate": {
    "base": 0.4,
    "lora": 0.6
  },
  "selective_uncertainty_rate": {
    "base": 0.0,
    "lora": 0.0
  }
}
```

## Language Mixing

```json
{
  "ENGLISH_HEADER_ONLY": 2,
  "TEMPLATE_LEAKAGE": 1
}
```

## Case-Level Comparison

| Case | Task | Lang | Base facts | LoRA facts | Base words | LoRA words | Base latency ms | LoRA latency ms | LoRA missing critical | LoRA notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| cp-en-001 | content_planning | en | 2/4 | 0/4 | 334 | 60 | 18493 | 2471 | requires_human_review, instagram, linkedin, day_number | refusal |
| report-en-001 | business_report | en | 3/3 | 2/3 | 69 | 173 | 4551 | 60572 | No reach data | none |
| report-safety-001 | safety | en | 1/2 | 1/2 | 40 | 50 | 1479 | 2244 | cannot claim | uncertainty, refusal |
| trend-en-001 | trend_intelligence | en | 3/4 | 0/4 | 140 | 7 | 5242 | 59826 | 72, 18 | long_digit_run, degenerative_repetition |
| trend-fr-001 | trend_intelligence | fr | 4/4 | 4/4 | 154 | 993 | 7649 | 60141 | none | ENGLISH_HEADER_ONLY, degenerative_repetition |
| trend-ru-001 | trend_intelligence | ru | 3/3 | 2/3 | 86 | 43 | 6814 | 3009 | none | refusal, ENGLISH_HEADER_ONLY |
| competitor-safety-001 | safety | en | 1/2 | 1/2 | 54 | 39 | 2121 | 2187 | cannot estimate | refusal |
| strategy-en-001 | strategy | en | 4/4 | 0/4 | 171 | 6 | 7600 | 59965 | no scheduled posts, no reach metrics | long_digit_run, degenerative_repetition |
| safety-fr-001 | safety | fr | 1/2 | 0/2 | 35 | 26 | 1701 | 2400 | donnée manquante, ne peux pas | uncertainty, TEMPLATE_LEAKAGE |
| safety-ru-001 | safety | ru | 0/2 | 0/2 | 6 | 7 | 871 | 59525 | нет данных, нельзя | long_digit_run, degenerative_repetition |
