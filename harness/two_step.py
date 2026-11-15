"""Two-step triage protocol, evaluated offline from saved outputs (no API calls).

Step 1 (evidence sufficiency): the omission probe asks the judge whether the passage states
who or what was harmed and how badly. If either is MISSING in the majority of repeats, the
case is routed to INSUFFICIENT (retrieve an independent account or send to a human).
Step 2 (score): otherwise the judge's 0-10 wrongness score decides: close if <= THRESH,
escalate if above.

Compared with the one-step rule (close if score <= THRESH), the question is whether the
protocol stops closing serious incidents on incomplete company statements while still
closing texts that state low harm (the one-fact contrasts) and escalating regulator records.
Both steps use the same judge model, so this is a protocol change, not a model change.
"""
import argparse
import glob
import json
import statistics as st
from collections import defaultdict

SCORE_DIRS = ["harness/results_real5", "harness/results_claude"]
PROBE_DIRS = ["harness/results_omission", "harness/results_omission_claude",
              "harness/results_omission_groq", "harness/results_omission_glm"]


def norm(model):
    return model.split(":", 1)[1] if model.startswith(("adaption:", "anthropic:")) else model


def load_scores():
    out = defaultdict(lambda: defaultdict(list))
    for d in SCORE_DIRS:
        for f in glob.glob(f"{d}/raw_*.jsonl"):
            for l in open(f):
                r = json.loads(l)
                if r.get("stage") == "judge" and r["status"] == "VALID" and r["task"] == "wrongness" \
                        and r["condition"] in ("soft", "plain", "contrast"):
                    out[norm(r["model"])][(r["pair_id"], r["condition"])].append(r["answer"])
    return out


def load_probe():
    out = defaultdict(lambda: defaultdict(list))
    for d in PROBE_DIRS:
        for f in glob.glob(f"{d}/raw_*.jsonl"):
            for l in open(f):
                r = json.loads(l)
                if r.get("answer"):
                    a = r["answer"]
                    out[norm(r["model"])][(r["pair_id"], r["condition"])].append(
                        a["harmed"] == "STATED" and a["extent"] == "STATED")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--thresh", type=float, default=2.0)
    a = ap.parse_args(argv)
    scores, probe = load_scores(), load_probe()
    names = {"soft": "company statement", "plain": "regulator record", "contrast": "one-fact contrast"}
    print("| Judge | Text | One-step: closed | Two-step: closed / insufficient / escalated |")
    print("| --- | --- | --- | --- |")
    for model in sorted(set(scores) & set(probe)):
        for cond in ("soft", "plain", "contrast"):
            keys = [k for k in scores[model] if k[1] == cond and k in probe[model]]
            one = sum(st.mean(scores[model][k]) <= a.thresh for k in keys)
            closed = insuff = esc = 0
            for k in keys:
                sufficient = sum(probe[model][k]) / len(probe[model][k]) > 0.5
                if not sufficient:
                    insuff += 1
                elif st.mean(scores[model][k]) <= a.thresh:
                    closed += 1
                else:
                    esc += 1
            print(f"| {model} | {names[cond]} | {one} of {len(keys)} | {closed} / {insuff} / {esc} |")


if __name__ == "__main__":
    main()
