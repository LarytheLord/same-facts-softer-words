# Omission-detection probe (exploratory)

Mean number of core facts (of 3) marked MISSING. Diff CIs: bootstrap over pairs.

| Model | soft | plain | contrast | soft minus plain | contrast minus plain | invalid |
| --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.8-27b | 1.73 [1.18, 2.27] | 0.64 [0.27, 1.00] | 0.91 [0.36, 1.55] | 1.09 [0.55, 1.64] | 0.27 [-0.09, 0.73] | 0/66 |
| openai/gpt-oss-120b | 2.45 [2.09, 2.82] | 1.14 [0.77, 1.59] | 1.59 [1.14, 2.09] | 1.32 [0.82, 1.91] | 0.45 [0.00, 0.95] | 0/66 |
