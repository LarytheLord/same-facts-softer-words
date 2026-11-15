"""Decision-level view (no API calls): share of incidents a triage rule would auto-close.

Rule: close a case if the judge's wrongness score is <= THRESH (default 2, "minor wrongdoing"
on the rubric). For each judge, report the share of incidents closed when the judge reads the
company statement, the regulator record, and the one-fact contrast. All 11 incidents are
serious enough for a regulator to act, so closing on the regulator text is a false clearance
by design of the corpus.
"""
import argparse
import glob
import json
import statistics as st
from collections import defaultdict


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dirs", nargs="+", default=["harness/results_real5", "harness/results_claude"])
    ap.add_argument("--thresh", type=float, default=2.0)
    a = ap.parse_args(argv)
    print(f"| Judge | Closed on company statement | Closed on regulator record | Closed on one-fact contrast |")
    print("| --- | --- | --- | --- |")
    for d in a.dirs:
        for f in sorted(glob.glob(f"{d}/raw_*.jsonl")):
            v = defaultdict(lambda: defaultdict(list))
            model = None
            for l in open(f):
                r = json.loads(l)
                model = r["model"]
                if r.get("stage") == "judge" and r["status"] == "VALID" and r["task"] == "wrongness" \
                        and r["condition"] in ("soft", "plain", "contrast"):
                    v[r["pair_id"]][r["condition"]].append(r["answer"])

            def closed(c):
                ps = [p for p in v if v[p][c]]
                return sum(st.mean(v[p][c]) <= a.thresh for p in ps), len(ps)
            cells = []
            for c in ("soft", "plain", "contrast"):
                k, n = closed(c)
                cells.append(f"{k} of {n}")
            print(f"| {model} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
