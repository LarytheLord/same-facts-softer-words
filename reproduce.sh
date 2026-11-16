#!/bin/bash
# Recompute every headline number in the report from saved raw outputs. No API calls.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
echo "== tests"; $PY -m pytest harness -q | tail -1
echo "== real pairs, 5 open judges (Table 4.1)"; $PY harness/score.py --results-dir harness/results_real5 | tail -1
echo "== real pairs, claude-opus-5-5"; $PY harness/score.py --results-dir harness/results_claude | tail -1
echo "== assumption checks (Appendix B)"; $PY harness/hypotheses.py | tail -6; $PY harness/hypotheses.py --task severity | tail -6
echo "== synthetic arm (4.2)"; $PY harness/analyze_synth.py
grep -E "\| ALL \| all " harness/results_synth/synth_summary.md
echo "== positive control (4.2)"; $PY harness/control_check.py
echo "== matched omission arm (4.2b)"; $PY harness/omission_arm_check.py
echo "== omission and scale probes (4.3, 4.4)"; $PY harness/rescore_probes.py --scale harness/results_scale harness/results_scale_glm harness/results_scale_claude --omission harness/results_omission harness/results_omission_claude harness/results_omission_groq harness/results_omission_glm
echo "== decision-level and two-step protocol (4.5)"; $PY harness/clearance.py; $PY harness/two_step.py
echo "== human fact-preservation check (Navya Nadimpalli)"; $PY harness/human_check_analysis.py; $PY harness/analyze_synth.py --human human_check/returned/human_same_facts.csv --out harness/results_synth/synth_summary_human.md; grep -E "human_same_facts" harness/results_synth/synth_summary_human.md | grep "| ALL"
echo "== figure 1"; $PY harness/figures.py --summary harness/results_real5/summary.json harness/results_claude/summary.json --out report/fig1_real_pairs.png
