# SFT Data Leakage Audit

- Golden evaluation version: `golden_eval_v2`
- Candidate set: `qwen3_sft_v1_candidates`
- Candidate count: `180`
- Exact duplicates removed: `0`
- Near duplicates reviewed: `0`
- Private/customer data: `none`
- Frozen golden examples copied into training: `none detected`

## Final Split

| Split | Count |
| --- | ---: |
| Train | 153 |
| Validation | 18 |
| Local MLX test | 9 |

The local MLX test split exists only because `mlx_lm.lora` requires a non-empty `test.jsonl` in local dataset directories. The independent product-quality evaluation remains the frozen `golden_eval_v2` set.

## Validation

- All records are synthetic behavior examples.
- All 54 content-plan assistant answers pass `content_plan_contract_v2`.
- Secret scans in the dataset builder reject obvious API keys and credential-bearing URLs.
- The dataset teaches behavior and schema discipline, not current business facts, competitor facts, trend facts, or private application data.
