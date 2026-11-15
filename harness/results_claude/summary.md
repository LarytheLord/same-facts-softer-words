# Evaluation summary

TOY MOCK rows check the pipeline only. They are not empirical findings.
Intervals resample pairs, not repeated calls. Missing estimates are NA.

| Model | Task | Original gap / flip | Defended gap / flip | Defense reduction | Plain-contrast | Defended plain-contrast | Invalid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| anthropic:claude-opus-5-5 | wrongness | 4.409 [3.227, 5.545]; N=11 | 3.136 [1.773, 4.500]; N=11 | 1.273 [0.455, 2.045]; N=11 | 3.364 [2.273, 4.500]; N=11 | 2.818 [1.726, 4.000]; N=11 | 0/198 |
| anthropic:claude-opus-5-5 | fact_check | 0.000 [0.000, 0.000]; N=11 | 0.000 [0.000, 0.000]; N=11 | 0.000 [0.000, 0.000]; N=11 | 0.091 [0.000, 0.273]; N=11 | 0.000 [0.000, 0.000]; N=11 | 0/198 |
| anthropic:claude-opus-5-5 | severity | 1.636 [1.000, 2.182]; N=11 | 1.545 [0.909, 2.182]; N=11 | 0.091 [-0.364, 0.545]; N=11 | 1.636 [1.091, 2.182]; N=11 | 1.727 [1.273, 2.273]; N=11 | 0/198 |

Numeric gaps are plain minus soft, or plain minus contrast. Defense reduction
is original minus defended. Fact-check cells are categorical disagreement rates;
they do not establish accuracy. Each comparison uses common valid repeat IDs.
A positive contrast gap assumes contrast was designed to reduce wrongdoing.
No automatic pass/fail threshold is imposed on sensitivity or defense effects.
Rewrite parsing checks structure only; factual preservation needs human review.
