"""Positive control on synthetic sources (no API calls): plain minus contrast per source."""
import glob
import json
import random
import statistics as st
from collections import defaultdict


def main():
    for f in sorted(glob.glob("harness/results_synth_control/raw_*.jsonl")):
        v = defaultdict(lambda: defaultdict(dict))
        model = None
        for l in open(f):
            r = json.loads(l)
            model = r["model"]
            if r.get("stage") == "judge" and r["status"] == "VALID":
                v[r["task"]][r["pair_id"]][r["condition"]] = r["answer"]
        print("##", model)
        for task in ("wrongness", "severity"):
            g = {p: d["plain"] - d["contrast"] for p, d in v[task].items() if "plain" in d and "contrast" in d}
            keys = list(g)
            rng = random.Random(3)
            ms = sorted(st.mean(g[rng.choice(keys)] for _ in keys) for _ in range(4000))
            print(f"  {task} plain-contrast {st.mean(g.values()):.2f} [{ms[100]:.2f}, {ms[3899]:.2f}] n={len(g)}")
        fc = v["fact_check"]
        print(f"  fact-check differs {sum(1 for d in fc.values() if d.get('plain') != d.get('contrast'))} / {len(fc)}")


if __name__ == "__main__":
    main()
