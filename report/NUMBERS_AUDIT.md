# Numbers audit: report/REPORT_DRAFT.md

Audited against the output of ./reproduce.sh (exit 0; 56 tests passed, 17 subtests) and the files it writes
(harness/results_*/summary.md and summary.json, harness/results_synth/synth_summary*.md), plus the saved raw
outputs (harness/results_*/raw_*.jsonl) and data/*.jsonl read directly where reproduce.sh does not print a number.
No script was run with --live and no API key was used. No file under harness/results_*/ or data/*.jsonl was changed.

Verdicts: match, mismatch, not reproducible offline.

Result: 0 mismatches. 0 edits to REPORT_DRAFT.md. One wording note (not a numeric mismatch) is listed at the end.

Interval cells are written in the report exactly as in the source; "all cells" means every point estimate and
both interval ends were compared and agree to the printed precision.

| # | Location | Claim | Source file and value | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Abstract | 11 real incidents | data/pairs.jsonl: 11 rows | match |
| 2 | Abstract, 4.1, 4.2b, App A | judges rate company account 4.4 to 6.0 less wrong | results_real5/summary.md and results_claude/summary.md wrongness gaps: 4.682, 6.000, 5.432, 5.636, 4.545, 4.409 | match |
| 3 | Abstract, 4.5 | closing rule closes 7 to 9 of 11 on company statement, 0 to 2 on regulator | harness/clearance.py: 9, 8, 7, 9, 8, 9 and 2, 0, 1, 1, 0, 1 | match |
| 4 | Abstract, 4.1, 5 | company statements contain 10 to 40% of core facts; mean 0.24 | data/pairs.jsonl fact_coverage_soft: min 0.1, max 0.4, mean 2.6/11 = 0.236 | match |
| 5 | Abstract, 4.2b, 5 | deleting harm facts lowers ratings about 2 points, significant on one of two | omission_arm_check.py: qwen 2.11 [0.78, 3.50], gemma 1.83 [-0.28, 3.94] | match |
| 6 | Abstract, 4.4 | insufficient-information option works on one of four judges | 4.4 / C.2: gemma 0.82 vs 0.09; claude 0.68 vs 0.32; deepseek 0.27 vs 0.27; glm 0.23 vs 0.09 | match |
| 7 | Abstract, 4.5, 5 | two-step cuts false clearances from 7 to 9 to 0 to 2 of 11 on all six judges | two_step.py company rows: one-step 9, 9, 8, 7, 9, 8; two-step 1, 1, 1, 0, 0, 2 | match |
| 8 | 1 | A03: company statement 0 on all six judges | raw judge records, wrongness, soft, A03: 0 on all six | match |
| 9 | 1 | A03 regulator record 7 to 9, mean 8.0 | raw: 8, 8, 9, 8, 8, 7 (per-judge means 7 to 9), mean 8.0 | match |
| 10 | 1 | A03 contrast mean 5.2 | raw: per-judge means 5.5, 6, 4, 5, 6, 4.5; mean 5.17 | match |
| 11 | 3.1 | OSHA 2, CSB 1, FTC 3, CPSC 2, SEC 1, FDA 1, EPA 1 | data/pairs.jsonl source_plain domains | match |
| 12 | 3.1 | domains: data 3, consumer 3, chemical 2, workplace, finance, animal 1 each | data/pairs.jsonl domain | match |
| 13 | 3.1 | tiers good 5, medium 1, weak 4, not euphemistic 1 | data/pairs.jsonl tier (good_check8k counted as good; weak_date as weak) | match |
| 14 | 3.1 | 7 of 11 famous | data/pairs.jsonl famous | match |
| 15 | 3.1, 4.3 | probe: 3 generic questions | harness/omission_probe.py rubric (who responsible, who harmed, how badly) | match |
| 16 | 3.2 | 30 regulator descriptions: workplace 12, consumer 10, chemical 8 | data/synth_sources.jsonl | match |
| 17 | 3.2, App A | 83 rewrites judged, 21 sources | data/pairs_synth_A.jsonl: 83 arms, 21 sources | match |
| 18 | 3.2, App A | checker: 76 gpt-oss-20b, 6 qwen, 1 deepseek | data/synthetic_batchA.jsonl checker_model | match |
| 19 | 3.2, 4.2 | checker accepted 25 of 83 | data/pairs_synth_A.jsonl checker_status: kept 25, rejected 58 | match |
| 20 | 3.3 | n = 2 open-weight, n = 1 frontier and synthetic | raw records n field: 396 judge calls per open judge, 198 claude, synthetic 830 total records | match |
| 21 | 3.3 | claude: effort low, 0 refusals | harness/run.py default effort low; claude raw: 231 of 231 VALID, finish_reason end_turn. Effort is a code default, not recorded per record | match |
| 22 | 3.3 | temperature 0 where supported | harness/run.py payload temperature 0 | match |
| 23 | 3.3 | glm-5.2 started and paused for cost | no saved output | not reproducible offline |
| 24 | 3.2 | analysis plan decided 14 Nov 2026 | project log, not in repo outputs | not reproducible offline |
| 25 | 4.1 | invalid: deepseek 6, gemma 8, glm 14, qwen 2, gpt-oss 0 of 396; claude 0 of 198 | summary.md Invalid column | match |
| 26 | 4.1 | rewrites failed to parse: 1 gemma, 2 glm | raw records stage rewrite, status not VALID: gemma 1, glm 2, others 0 | match |
| 27 | 4.1 | synthetic: qwen 13 invalid of 830, gemma 0 | results_synth raw: qwen 13 INVALID of 830 (12 judge, 1 rewrite), gemma 0 | match |
| 28 | Table 4.1, all 6 rows x 4 columns | wrongness gap, defense reduction, plain minus contrast, fact-check disagreement | results_real5/summary.md and results_claude/summary.md; all cells | match |
| 29 | Table 4.1, claude row | fact-check 0.00, UNCLEAR on all 11 company and 11 regulator | results_claude/summary.json verdict_counts soft and plain: UNCLEAR 11 each | match |
| 30 | 4.1 | one-fact gap 3.1 to 5.6 | plain-contrast column: min 3.136, max 5.591 | match |
| 31 | 4.1 | defense reductions -0.36 to 0.14 on four of five judges | 0.000, -0.227, 0.136, -0.364 | match |
| 32 | 4.1 | qwen reduction interval excludes zero (wrong direction) | -0.364 [-0.636, -0.091] | match |
| 33 | 4.1 | glm: reduction 2.05; plain-contrast 3.77 to 2.43 | 2.045; 3.773 and 2.432 | match |
| 34 | 4.1 | claude: reduction 1.27; sensitivity drop 0.55 [-0.59, 1.50]; defended gap 3.14 | summary.json sensitivity_comparison reduction 0.545 [-0.591, 1.500]; defended gap 3.136 | match |
| 35 | 4.1 | mean coverage 0.24, range 10 to 40% | see row 4 | match |
| 36 | 4.2 table | all 6 rows x 3 gap/flip columns, arm counts 21, 21, 20-21, 20, 82-83 | results_synth/synth_summary.md; all cells | match |
| 37 | 4.2 table | positive control qwen 3.14 [1.24, 4.76], gemma 4.14 [1.90, 6.05]; 17 of 21, 14 of 21 | control_check.py | match |
| 38 | 4.2 | qwen pooled -0.10, 90% [-0.72, 0.50] within +/-1; gemma 0.53, 90% [-0.14, 1.25] not within | synth_summary.md equivalence section | match |
| 39 | 4.2 | gemma largest for combined move, 1.20 | synth_summary.md all_three gemma 1.20 | match |
| 40 | 4.2 | checker-accepted (24-25 arms): qwen -0.67 [-1.36, 0.00], gemma -0.04 [-0.95, 0.93] | synth_summary.md ALL checker_kept: 24 and 25 arms | match |
| 41 | 4.2 | defended gaps -0.19 and -0.45 | synth_summary.md ALL all, defended column | match |
| 42 | 4.2, App A | human rater: 40 items; 10 of 20 synthetic same facts; checker agreed 11 of 20; 6 of 6 agent deletion "no" | human_check_analysis.py: answers 24 yes, 16 no; synthetic 10 of 20; agreement 11 of 20; agent_deletion no 6, yes 0 | match |
| 43 | 4.2 | on the 10 confirmed rewrites: gemma 0.00 [-2.67, 2.25], qwen -0.50 [-1.90, 1.00] | synth_summary_human.md human_same_facts rows, n 10 / 8 | match |
| 44 | 4.2, 5, App A | plain-language rewrite lost or altered a fact in 6 of 20 | human_check_analysis.py: defense same facts 14 of 20 | match |
| 45 | 4.2 | qwen noise 0.05 on identical text; gemma 0.85 | raw plain-condition wrongness, mean pairwise absolute difference over repeated identical source text: qwen 0.049, gemma 0.846 | match |
| 46 | 4.2, 5 | qwen changes by 2 or more on 35% (29 of 82), up 15, down 14 | raw: 29 of 82; rewrite rated higher 15, lower 14 | match |
| 47 | 4.2, 5 | gemma 25% (21 of 83), up 9, down 12 | raw: 21 of 83; higher 9, lower 12 | match |
| 48 | 4.2 | gemma fact-check flips 4 of 83 balanced; qwen 10 TRUE to UNCLEAR, 3 reverse | raw: gemma 2 and 2; qwen 10 and 3 | match |
| 49 | 4.2 | ratings span 0 to 9 (qwen), 0 to 10 (gemma) | raw plain and soft wrongness min and max | match |
| 50 | 4.2b | 18 of 21 passed the mechanical check | data/omission_arm.jsonl status: kept 18, rejected 3 | match |
| 51 | 4.2b table | qwen 2.11 [0.78, 3.50], 1.06 [0.33, 1.83], 6 of 18; gemma 1.83 [-0.28, 3.94], 0.78 [0.28, 1.39], 9 of 18 | omission_arm_check.py | match |
| 52 | 4.2b | excluding 3 most aggressive (under 30% kept): 1.67 and 1.20 | omission_arm_check.py kept share >= 0.3, n = 15: qwen 1.67, gemma 1.20 | match |
| 53 | 4.2b | "no fact-check moves to FALSE" | omission_arm_check.py fact-check pairs: no FALSE entry | match |
| 54 | 4.3 | 0 invalid of 66 per judge, n = 2, 11 pairs | rescore_probes.py invalid column 0/66 on all rows | match |
| 55 | 4.3 | open-weight flag 1.1 to 1.3 more missing facts, claude 1.8 | company minus regulator: 1.32, 1.23, 1.32, 1.09, 1.18 and 1.77 | match |
| 56 | App C.1, 6 rows x 5 columns | all cells | rescore_probes.py omission output | match |
| 57 | 4.4 | 11 pairs, n = 2, 0 invalid | rescore_probes.py scale output 0/66 | match |
| 58 | 4.4 | gemma abstains 82% company, 9% regulator; 2 pairs keep numeric scores | 0.82 and 0.09; (n=2) | match |
| 59 | 4.4 | claude 68% vs 32% | 0.68 and 0.32 | match |
| 60 | App C.2, 8 rows | all cells and pair counts | rescore_probes.py scale output; all cells | match |
| 61 | 4.5 | closes 7 to 9 and 0 to 2 | see row 3 | match |
| 62 | 4.5 table, 6 rows x 3 text types | one-step and two-step closed (routed) | two_step.py; all 18 cells | match |
| 63 | 4.5 | B01 still closed on three judges, A01 on two | recomputed from two_step.py functions: B01 claude, deepseek, qwen; A01 gemma, qwen | match |
| 64 | 4.5 | pooled 50 of 66 one-step, 5 of 66 two-step | 9+9+8+7+9+8 = 50; 1+1+1+0+0+2 = 5 | match |
| 65 | 4.5 | cutoff 1 or 3: one-step 47 or 52, two-step still 5 | clearance.py --thresh 1: 47; --thresh 3: 52; two_step.py --thresh 1 and 3: 5 each | match |
| 66 | 4.5 | 20 of 66 regulator records routed; 2 to 3 per judge, 6 on gpt-oss-120b | 2+3+3+3+6+3 = 20 | match |
| 67 | 5 | fact-check: 101 of 107 UNCLEAR (4 TRUE, 2 FALSE) on open judges; claude all 11 | raw soft fact_check VALID: UNCLEAR 101, TRUE 4, FALSE 2, total 107; claude 11 of 11 | match |
| 68 | 5 | defended gaps 3.1 to 6.2 on five judges other than glm | defended gaps: 4.682, 6.227, 5.295, 6.000, 3.136 | match |
| 69 | 5 | glm gap down 2.05, sensitivity down 1.34; claude 1.27 and 0.55 | summary.json sensitivity_comparison reduction glm 1.341, claude 0.545 | match |
| 70 | App B | leave-one-out 4.97 to 5.73 | hypotheses.py H5 | match |
| 71 | App B | length Spearman -0.06; coverage vs wrongness -0.14, p = 0.67; coverage vs severity -0.69, p = 0.02 | hypotheses.py wrongness and --task severity | match |
| 72 | App B | famous 5.57 (n = 7) vs 4.73 (n = 4); good 6.06 (n = 5) vs 4.60 (n = 6) | hypotheses.py H3, H4 | match |
| 73 | App B | B04 gap 0.62 | hypotheses.py per-pair table: B04 0.62 | match |
| 74 | App A | 11 incidents, n = 40 human items, 6 of 20, 11 of 20 | see rows 42 and 44 | match |
| 75 | Fig 1 caption | 95% bootstrap CIs over 11 pairs | harness/figures.py regenerated; figure bytes differ run to run (png reverted, not part of this change) | match (not pixel-checked) |
| 76 | 2 | Hwang 14 judges, 28.6%; Fox 0.50-0.63, 0.79-0.94, 24.6-36.9%; Huang GPT-5.5 2 of 200; JANUS 98.5-99.6% | cited papers, no offline copy | not reproducible offline |
| 77 | 2 | prior work: 10 model families from 7 labs | author's earlier project, not in repo | not reproducible offline |
| 78 | References | arXiv IDs, years, volumes | report/CITATIONS_VERIFIED.json is a separate record; not part of this audit | not reproducible offline |
| 79 | 3.1, 3.3 | sources, retrieval, "we cannot verify the served weights" | provider side | not reproducible offline |

## Wording note (not a numeric mismatch, text left unchanged)

1. Appendix B says per-pair gaps are "averaged over the five judges". harness/hypotheses.py defaults to
   harness/results_real5 (the five open-weight judges), so the statement and the script agree.
1. Section 4.2b "gives 1.67 and 1.20" is qwen and gemma wrongness respectively (both verified); the sentence does not
   name the judges, but the numbers are right.

## Not checked

Fig 1 pixels, the PDF (report/report.pdf) and SUBMISSION_FORM.md were not compared to the draft.
