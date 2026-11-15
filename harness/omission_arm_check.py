"""Score the matched omission arm from raw files (no API calls): plain minus omitted text."""
import glob
import json
import random
import statistics as st
from collections import Counter, defaultdict


def main():
    share = {json.loads(l)["pair_id"]: json.loads(l)["kept_token_share"] for l in open("data/omission_arm.jsonl")}
    for f in sorted(glob.glob("harness/results_omission_arm/raw_*.jsonl")):
        v = defaultdict(lambda: defaultdict(dict))
        model = None
        for l in open(f):
            r = json.loads(l)
            model = r["model"]
            if r.get("stage") == "judge" and r["status"] == "VALID":
                v[r["task"]][r["pair_id"]][r["condition"]] = r["answer"]
        print("##", model)
        for task in ("wrongness", "severity"):
            for label, keep in (("all", lambda p: True), ("kept share >= 0.3", lambda p: share[p.replace("_omission", "")] >= 0.3)):
                g = {p: d["plain"] - d["soft"] for p, d in v[task].items() if "plain" in d and "soft" in d and keep(p)}
                k = list(g)
                rng = random.Random(3)
                ms = sorted(st.mean(g[rng.choice(k)] for _ in k) for _ in range(4000))
                print(f"  {task} [{label}] {st.mean(g.values()):.2f} [{ms[100]:.2f}, {ms[3899]:.2f}] n={len(g)}")
        print("  fact-check (plain, omitted):", dict(Counter((d.get("plain"), d.get("soft")) for d in v["fact_check"].values())))


if __name__ == "__main__":
    main()
