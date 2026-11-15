# Synthetic arm summary

Gap = plain minus soft (positive = rewrite judged less wrong). Defended = plain minus soft after plain-form rewrite of the soft text.
95% CI: bootstrap over source incidents. n = arms / sources.

## gemma-4-31b-it

| Move | Slice | Wrongness gap | Defended wrongness gap | Severity gap | Fact-check flip rate | n arms / sources |
| --- | --- | --- | --- | --- | --- | --- |
| euphemism | all | 0.48 [-0.14, 1.38] | 0.33 [-0.86, 1.67] | 0.05 [0.00, 0.14] | 0.05 [0.00, 0.14] | 21 / 21 |
| euphemism | checker_kept | -0.25 [-1.50, 0.75] | -1.25 [-2.50, 0.00] | 0.25 [0.00, 0.75] | 0.00 [0.00, 0.00] | 4 / 4 |
| euphemism | checker_rejected | 0.65 [-0.06, 1.71] | 0.71 [-0.65, 2.18] | 0.00 [0.00, 0.00] | 0.06 [0.00, 0.18] | 17 / 17 |
| nominalization | all | -0.10 [-1.19, 1.10] | -1.43 [-2.76, -0.29] | 0.05 [-0.10, 0.19] | 0.05 [0.00, 0.14] | 21 / 21 |
| nominalization | checker_kept | 0.15 [-1.62, 1.92] | -1.23 [-3.08, 0.38] | 0.00 [-0.23, 0.23] | 0.08 [0.00, 0.23] | 13 / 13 |
| nominalization | checker_rejected | -0.50 [-1.00, -0.12] | -1.75 [-3.75, 0.00] | 0.12 [0.00, 0.38] | 0.00 [0.00, 0.00] | 8 / 8 |
| agent_deletion | all | 0.57 [-0.33, 1.71] | 0.00 [-0.71, 0.95] | -0.05 [-0.29, 0.19] | 0.05 [0.00, 0.14] | 21 / 21 |
| agent_deletion | checker_kept | -0.25 [-0.50, 0.00] | 0.25 [0.00, 0.62] | -0.12 [-0.50, 0.25] | 0.12 [0.00, 0.38] | 8 / 8 |
| agent_deletion | checker_rejected | 1.08 [-0.38, 2.77] | -0.15 [-1.23, 1.31] | 0.00 [-0.31, 0.31] | 0.00 [0.00, 0.00] | 13 / 13 |
| all_three | all | 1.20 [-0.30, 2.85] | -0.70 [-2.35, 0.75] | 0.25 [0.00, 0.55] | 0.05 [0.00, 0.15] | 20 / 20 |
| all_three | checker_kept | NA | NA | NA | NA | 0 |
| all_three | checker_rejected | 1.20 [-0.30, 2.85] | -0.70 [-2.35, 0.75] | 0.25 [0.00, 0.55] | 0.05 [0.00, 0.15] | 20 / 20 |
| ALL | all | 0.53 [-0.23, 1.43] | -0.45 [-1.28, 0.34] | 0.07 [-0.02, 0.19] | 0.05 [0.00, 0.13] | 83 / 21 |
| ALL | checker_kept | -0.04 [-0.95, 0.93] | -0.76 [-1.90, 0.12] | 0.00 [-0.12, 0.12] | 0.08 [0.00, 0.24] | 25 / 18 |
| ALL | checker_rejected | 0.78 [-0.11, 1.84] | -0.31 [-1.20, 0.55] | 0.10 [-0.03, 0.27] | 0.03 [0.00, 0.09] | 58 / 21 |

## qwen/qwen3.8-27b

| Move | Slice | Wrongness gap | Defended wrongness gap | Severity gap | Fact-check flip rate | n arms / sources |
| --- | --- | --- | --- | --- | --- | --- |
| euphemism | all | -0.52 [-1.29, 0.14] | -0.52 [-1.52, 0.43] | -0.05 [-0.29, 0.19] | 0.00 [0.00, 0.00] | 21 / 21 |
| euphemism | checker_kept | -0.75 [-1.50, 0.00] | 1.50 [-0.50, 3.75] | -0.25 [-1.00, 0.50] | 0.00 [0.00, 0.00] | 4 / 4 |
| euphemism | checker_rejected | -0.47 [-1.41, 0.29] | -1.00 [-2.12, -0.12] | 0.00 [-0.24, 0.24] | 0.00 [0.00, 0.00] | 17 / 17 |
| nominalization | all | 0.05 [-0.86, 0.86] | 0.10 [-0.95, 1.20] | -0.05 [-0.29, 0.19] | 0.20 [0.05, 0.40] | 21 / 21 |
| nominalization | checker_kept | -0.54 [-1.62, 0.46] | -0.33 [-1.67, 0.83] | 0.00 [-0.31, 0.31] | 0.08 [0.00, 0.25] | 13 / 13 |
| nominalization | checker_rejected | 1.00 [0.00, 2.38] | 0.75 [-0.88, 2.62] | -0.12 [-0.50, 0.25] | 0.38 [0.00, 0.75] | 8 / 8 |
| agent_deletion | all | -0.05 [-1.00, 0.90] | -0.15 [-1.10, 0.80] | 0.10 [-0.15, 0.35] | 0.15 [0.00, 0.35] | 20 / 20 |
| agent_deletion | checker_kept | -0.86 [-1.71, 0.00] | -0.57 [-1.43, 0.00] | 0.14 [-0.29, 0.57] | 0.14 [0.00, 0.43] | 7 / 7 |
| agent_deletion | checker_rejected | 0.38 [-0.92, 1.62] | 0.08 [-1.38, 1.46] | 0.08 [-0.15, 0.31] | 0.15 [0.00, 0.38] | 13 / 13 |
| all_three | all | 0.15 [-1.05, 1.35] | -0.15 [-1.55, 1.10] | 0.15 [-0.25, 0.60] | 0.30 [0.10, 0.50] | 20 / 20 |
| all_three | checker_kept | NA | NA | NA | NA | 0 |
| all_three | checker_rejected | 0.15 [-1.05, 1.35] | -0.15 [-1.55, 1.10] | 0.15 [-0.25, 0.60] | 0.30 [0.10, 0.50] | 20 / 20 |
| ALL | all | -0.10 [-0.87, 0.63] | -0.19 [-1.12, 0.73] | 0.04 [-0.18, 0.26] | 0.16 [0.09, 0.24] | 82 / 21 |
| ALL | checker_kept | -0.67 [-1.36, 0.00] | -0.09 [-1.00, 0.90] | 0.00 [-0.35, 0.35] | 0.09 [0.00, 0.24] | 24 / 18 |
| ALL | checker_rejected | 0.14 [-0.77, 1.02] | -0.22 [-1.25, 0.76] | 0.05 [-0.16, 0.27] | 0.19 [0.08, 0.32] | 58 / 21 |

## Equivalence check (pooled wrongness gap, 90% bootstrap over sources, 5000 draws, seed 7)

- gemma-4-31b-it: 90% [-0.14, 1.25] -> NOT within +/-1
- qwen/qwen3.8-27b: 90% [-0.72, 0.50] -> within +/-1

