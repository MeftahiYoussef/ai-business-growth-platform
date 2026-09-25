# SFT v2.1 Curriculum Design

Status: `design prepared`; dataset generation and training are deferred.

## Objective

Teach semantic behavior, not JSON syntax. Constrained decoding remains responsible for structural output.

## Candidate Size

- Candidate generation target: `180-220`
- Accepted target: `150-190`
- Rationale: higher information density and less template repetition than the 360-record v2 curriculum.

## Proposed Distribution

| Category | Target Share | Purpose |
| --- | ---: | --- |
| Known + unknown selective uncertainty | 25% | Preserve known facts while qualifying only missing metrics. |
| Required/critical fact retention | 20% | Keep 3-6 relevant facts in the answer. |
| Numeric preservation | 20% | Preserve integers, decimals, percentages, negative growth, and zero values. |
| Adversarial fabrication resistance | 10% | Resist requests to inflate or invent values. |
| Multilingual semantic fidelity | 10% | Natural EN/FR/RU answers with localized labels. |
| Report interpretation | 5% | Separate observed metrics from recommendations. |
| Trend metric fidelity | 5% | Preserve momentum, slope, acceleration, forecast values. |
| Competitor fidelity | 5% | Discuss only supplied competitor facts. |

## Positive Fact Density

- Each uncertainty case should include `3-6` known facts and only `1-2` missing facts.
- Target known/missing fact ratio: at least `3:1` for uncertainty examples.
- Training targets must state known facts first, then qualify missing facts narrowly.

## Answer Length Strategy

- Prefer concise three-part answers: known facts, narrow limitation, useful recommendation.
- Avoid repeated caveats.
- Avoid generic refusal language for ordinary business analysis.
- Prevent outputs from learning long disclaimer templates.

## Multilingual Strategy

- French and Russian examples must use natural professional prose and localized labels.
- Do not copy English section headers into FR/RU examples.
- Technical terms may remain in English only when natural in context.

## Structural Diversity Gate

- No single response-template cluster should exceed `10%` of accepted records.
- Split by scenario family and response-template family.
- Do not place skeleton variants across both train and validation.

## V2.1 Quality Gates

- `known_fact_retention_under_uncertainty = 1.00` in target answers.
- `unsupported_numeric_claims = 0`.
- `exact_duplicates = 0`.
- `near_duplicates <= 5%`.
- `golden_leakage = 0`.
- No current business, competitor, or trend facts are trained as model knowledge.

## Future Experiment

Use one controlled LoRA v2.1 run after the dataset is generated and audited. Keep the training setup comparable to v2 unless a separate versioned optimization experiment is explicitly approved.
