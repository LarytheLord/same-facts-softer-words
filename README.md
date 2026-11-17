# Softer words or missing facts?

Apart Research AI x Epistemics sprint, 13-15 Nov 2026. Question: when a company and a regulator describe the same incident, do LLM judges reach different verdicts, and does a plain-language rewrite remove the difference without hiding real factual differences?

Report: `report/REPORT_DRAFT.md` (PDF built from it), title "Softer Words or Missing Facts? How LLM Judges Score Company Statements Against Regulator Records". Figure 1: `report/fig1_real_pairs.png`.

## Check your own judge (one command)

If you use an LLM to score, screen or triage reports, run it on the 11 real incident pairs:

```sh
# any OpenAI-compatible endpoint
BASE_URL=https://api.groq.com/openai/v1 API_KEY=your_key \
  python3 harness/judge_check.py --live --model qwen/qwen3.8-27b
# Anthropic: ANTHROPIC_API_KEY=... python3 harness/judge_check.py --live --model anthropic:claude-opus-5-5
```

About 198 calls (roughly $1.20 on Claude Opus 5.5, free on Groq's free tier). It prints:
- leniency gap: regulator score minus company score for the same incident
- fact sensitivity: regulator score minus the score after one morally relevant fact changes
- abstention: how often the judge answers INSUFFICIENT on company versus regulator text
- triage: how many cases a "close if score <= 2" rule closes, one-step versus the two-step protocol (first ask whether the harm and its extent are stated; route "not stated" to INSUFFICIENT)

A large leniency gap means low scores on incomplete statements mean "not established", not "not wrong"; do not let such a score close a case without an evidence-sufficiency check. Without `--live` it runs a mock to show the output format.

## Pre-existing work (declared)

Sprint kickoff: 13 Nov 2026, 14:15 UTC (19:45 IST). File creation times on disk:

| Item | When | Status |
|---|---|---|
| Harness v1: `harness/run.py`, `harness/prompts.py`, `harness/score.py`, `harness/test_harness.py`, `harness/PLAN.md`, `BRIEF_HARNESS.md` | 13 Nov 12:38-12:52 IST | **Preexisting** (written before kickoff) |
| Synthetic-arm generator v1: `harness/synth.py`, `harness/test_synth.py`, `BRIEF_SYNTH.md` | started 13 Nov 13:15 IST, finished after kickoff | **Partly preexisting** |
| The author's earlier results on framing moves across 10 judge families (separate repository) | 2026 | **Preexisting**, cited as prior work only; no numbers from it are reused here |

Done during the sprint:
- Real paired corpus (`data/pairs.jsonl`, `data/pairs_A.jsonl`, `data/pairs_B.jsonl`, `data/PROVENANCE_A.md`, `data/PROVENANCE_B.md`) and regulator texts for the synthetic arm (`data/regulator_texts.jsonl`, `data/synth_sources.jsonl`).
- All live runs and results (`harness/results_real*`, `harness/results_synth`, `harness/results_omission`, `data/synthetic_live.jsonl`).
- Harness changes after kickoff: resume and retry-invalid (`harness/test_resume.py`), Adaption backend and per-role routing, reasoning-effort and token caps, rewrite parser fix (empty `other_facts`), synthetic resume with interrupted-run recovery, condition filter, pacing.
- New code: `harness/synth_to_pairs.py`, `harness/analyze_synth.py`, `harness/omission_probe.py`, `harness/scale_probe.py`, `harness/hypotheses.py`, `harness/judge_check.py`, `harness/omission_arm.py`, `harness/omission_arm_check.py`, `harness/rescore_probes.py`, `harness/control_check.py`, `harness/build_human_sheet.py`, `harness/figures.py`, Anthropic backend in `harness/run.py`.
- Human fact-preservation sheet (`human_check/`), returned and scored (`harness/human_check_analysis.py`), report and figure.

## Human check

Navya Nadimpalli blind-rated 40 items for fact preservation (`human_check/returned/`, scored by `harness/human_check_analysis.py`).

## Data

- 11 real pairs: company statement vs regulator record (OSHA, CSB, CPSC, FTC, SEC, FDA, EPA). Company names replaced with "Company A" in every model input; regulator verdict and penalty language removed (`plain_text`; original kept in `plain_original`). Source URLs per pair in `source_soft` and `source_plain`.
- 30 regulator incident descriptions for the synthetic arm, each rewritten one move at a time (euphemism, nominalization, agent deletion, all three).
- All inputs are public records. No personal data.

## Models

Judges: openai/gpt-oss-120b and qwen/qwen3.8-27b (Groq free tier); gemma-4-31b-it, deepseek-v4-flash, glm-53-flash (Adaption Labs hosted; model IDs as returned by the provider). glm-5.2 started but was paused for cost. Frontier check: claude-opus-5-5 (Anthropic API). Synthetic rewriter: openai/gpt-oss-120b; checker: openai/gpt-oss-20b for 76 of the 83 judged rewrites, qwen/qwen3.8-27b for 6 and deepseek-v4-flash for 1 (recorded per row).

## Multi-turn gate (mock only)

`harness/multiturn_gate.py` applies gate-before-score to multi-turn conversations (JSONL: `id`, `turns`, `reference_facts`). Step 1 checks that the assistant's final answer commits to a position and marks each reference fact STATED or MISSING. Step 2 scores only if every fact is STATED, otherwise the verdict is INSUFFICIENT and no score is requested. Only a toy mock backend ships; `--live` is refused (and stays refused even with `--allow-live`). Five synthetic conversations are in `data/examples/multiturn_synthetic.jsonl`.

```sh
python3 harness/multiturn_gate.py --input data/examples/multiturn_synthetic.jsonl --out harness/multiturn_gate_mock/out.jsonl
```

## Reproduce

Offline checks (no credentials):

```sh
python3 -m pytest harness -q
python3 harness/run.py --dry-run --pairs data/pairs_example.jsonl
```

Recompute every headline number in the report from raw outputs (no API calls): `./reproduce.sh`. Individual steps:

```sh
python3 harness/score.py --results-dir harness/results_real5
python3 harness/analyze_synth.py
python3 harness/figures.py --summary harness/results_real5/summary.json --out report/fig1_real_pairs.png
```

Live runs need your own keys; see `harness/README.md`, `harness/run_groq.sh`, `harness/run_adaption.sh`. Keys are read from local config files and redacted from every saved record.
