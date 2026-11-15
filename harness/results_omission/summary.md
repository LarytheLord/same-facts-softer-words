# Omission-detection probe (exploratory)

Mean number of core facts (of 3) marked MISSING. Diff CIs: bootstrap over pairs.

| Model | soft | plain | contrast | soft minus plain | contrast minus plain | invalid |
| --- | --- | --- | --- | --- | --- | --- |
| adaption:deepseek-v4-flash | 2.09 [1.55, 2.59] | 0.77 [0.36, 1.23] | 1.23 [0.73, 1.82] | 1.32 [0.73, 1.91] | 0.45 [-0.05, 1.09] | 0/66 |
| adaption:gemma-4-31b-it | 1.77 [1.18, 2.36] | 0.55 [0.27, 0.82] | 0.91 [0.45, 1.45] | 1.23 [0.73, 1.77] | 0.36 [0.00, 0.82] | 0/66 |
