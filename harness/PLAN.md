# Evaluation harness plan

Implement the supplied task in Python 3 with standard library and optional requests.
All writes stay in harness/ and data/. No real incident data, commits, or pushes.

1. Write unittest cases for strict parsing, ID-based matching, deterministic paired
   bootstrap, offline isolation, and empty responses. Run before implementation.
2. Build calibrated task prompts and a structured plain-language rewrite prompt.
3. Build a deterministic text-based mock and an explicitly gated chat API backend.
   Store every query, including failures and rewrite dependencies, with provenance.
4. Score pair means and repeat-matched categorical flips. Bootstrap pair clusters.
   Measure original and defended gaps on the same valid pair cohort when comparing
   defense effects. Include contrast_deeuph for the defended sensitivity control.
5. Document exact commands and limitations. Run the requested offline commands,
   read generated summaries, and run the full harness test suite.

Defaults: 3 repeats, 8192 output tokens, 2000 bootstrap draws, seed 42.
Outputs: harness/results/raw_<model>.jsonl and summary.{json,md}.
Refuse to overwrite existing raw files unless --overwrite is supplied.
Missing or invalid results are counted, never assigned a numeric score.
