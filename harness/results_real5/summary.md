# Evaluation summary

TOY MOCK rows check the pipeline only. They are not empirical findings.
Intervals resample pairs, not repeated calls. Missing estimates are NA.

| Model | Task | Original gap / flip | Defended gap / flip | Defense reduction | Plain-contrast | Defended plain-contrast | Invalid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek-v4-flash | wrongness | 4.682 [2.500, 6.636]; N=11 | 4.682 [2.772, 6.409]; N=11 | 0.000 [-1.636, 1.500]; N=11 | 3.955 [2.227, 5.682]; N=11 | 4.136 [2.500, 5.773]; N=11 | 6/396 |
| deepseek-v4-flash | fact_check | 0.273 [0.045, 0.500]; N=11 | 0.136 [0.000, 0.273]; N=11 | 0.136 [-0.045, 0.364]; N=11 | 0.409 [0.182, 0.682]; N=11 | 0.364 [0.136, 0.591]; N=11 | 6/396 |
| deepseek-v4-flash | severity | 1.955 [1.227, 2.727]; N=11 | 2.409 [1.773, 3.045]; N=11 | -0.455 [-1.318, 0.227]; N=11 | 2.000 [1.227, 2.727]; N=11 | 2.091 [1.591, 2.500]; N=11 | 6/396 |
| gemma-4-31b-it | wrongness | 6.000 [4.273, 7.545]; N=11 | 6.227 [4.362, 7.818]; N=11 | -0.227 [-0.818, 0.364]; N=11 | 5.591 [4.591, 6.636]; N=11 | 4.955 [3.636, 6.227]; N=11 | 8/396 |
| gemma-4-31b-it | fact_check | 0.636 [0.409, 0.864]; N=11 | 0.727 [0.455, 1.000]; N=11 | -0.091 [-0.273, 0.091]; N=11 | 0.500 [0.227, 0.773]; N=11 | 0.545 [0.273, 0.818]; N=11 | 8/396 |
| gemma-4-31b-it | severity | 1.364 [0.773, 1.909]; N=11 | 1.500 [0.682, 2.227]; N=11 | -0.136 [-0.818, 0.455]; N=11 | 1.909 [1.500, 2.318]; N=11 | 1.682 [1.000, 2.318]; N=11 | 8/396 |
| glm-53-flash | wrongness | 4.545 [3.045, 6.000]; N=11 | 2.500 [1.455, 3.637]; N=11 | 2.045 [0.227, 3.773]; N=11 | 3.773 [2.364, 5.182]; N=11 | 2.432 [1.182, 3.818]; N=11 | 14/396 |
| glm-53-flash | fact_check | 0.227 [0.045, 0.409]; N=11 | 0.000 [0.000, 0.000]; N=11 | 0.227 [0.045, 0.409]; N=11 | 0.318 [0.091, 0.545]; N=11 | 0.000 [0.000, 0.000]; N=11 | 14/396 |
| glm-53-flash | severity | 1.727 [1.000, 2.500]; N=11 | 1.455 [0.591, 2.227]; N=11 | 0.273 [-0.500, 0.955]; N=11 | 1.773 [1.273, 2.318]; N=11 | 1.545 [1.091, 2.000]; N=11 | 14/396 |
| openai/gpt-oss-120b | wrongness | 5.432 [3.544, 7.114]; N=11 | 5.295 [3.205, 7.182]; N=11 | 0.136 [-0.591, 0.932]; N=11 | 3.136 [1.682, 4.774]; N=11 | 3.750 [1.840, 5.636]; N=11 | 0/396 |
| openai/gpt-oss-120b | fact_check | 0.636 [0.364, 0.909]; N=11 | 0.727 [0.545, 0.909]; N=11 | -0.091 [-0.273, 0.091]; N=11 | 0.545 [0.273, 0.818]; N=11 | 0.682 [0.455, 0.909]; N=11 | 0/396 |
| openai/gpt-oss-120b | severity | 2.227 [1.636, 2.818]; N=11 | 1.955 [1.273, 2.636]; N=11 | 0.273 [-0.045, 0.591]; N=11 | 1.864 [1.272, 2.455]; N=11 | 1.591 [0.773, 2.274]; N=11 | 0/396 |
| qwen/qwen3.8-27b | wrongness | 5.636 [4.000, 7.091]; N=11 | 6.000 [4.273, 7.545]; N=11 | -0.364 [-0.636, -0.091]; N=11 | 5.000 [3.816, 6.182]; N=11 | 5.455 [4.182, 6.818]; N=11 | 2/396 |
| qwen/qwen3.8-27b | fact_check | 0.364 [0.091, 0.636]; N=11 | 0.545 [0.273, 0.818]; N=11 | -0.182 [-0.455, 0.000]; N=11 | 0.455 [0.182, 0.727]; N=11 | 0.545 [0.273, 0.818]; N=11 | 2/396 |
| qwen/qwen3.8-27b | severity | 1.682 [0.909, 2.500]; N=11 | 2.273 [1.318, 3.136]; N=11 | -0.591 [-1.364, 0.136]; N=11 | 2.000 [1.455, 2.545]; N=11 | 2.136 [1.727, 2.500]; N=11 | 2/396 |

Numeric gaps are plain minus soft, or plain minus contrast. Defense reduction
is original minus defended. Fact-check cells are categorical disagreement rates;
they do not establish accuracy. Each comparison uses common valid repeat IDs.
A positive contrast gap assumes contrast was designed to reduce wrongdoing.
No automatic pass/fail threshold is imposed on sensitivity or defense effects.
Rewrite parsing checks structure only; factual preservation needs human review.
