"""Assumption checks on the real-pair runs (no API calls).

Per pair: wrongness gap = mean(plain) - mean(soft), averaged over all judges and
repeats in a results dir. Then:
  H1 omission: gap vs fact_coverage_soft (expect negative correlation)
  H2 length:   gap vs log word-count ratio plain/soft (a length confound if strong)
  H3 famous:   gap for famous vs not famous pairs (memorization)
  H4 tier:     gap for good vs other tiers (alignment quality)
  H5 leave-one-out: does any single pair drive the mean gap?
Spearman with a 10k permutation p-value; small n, so read as descriptive.
"""
import argparse
import glob
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def perm_p(x, y, n=10000, seed=1):
    obs = abs(spearman(x, y))
    rng = random.Random(seed)
    yy = list(y)
    hits = 0
    for _ in range(n):
        rng.shuffle(yy)
        if abs(spearman(x, yy)) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n + 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, default=ROOT / "harness/results_real5")
    ap.add_argument("--pairs", type=Path, default=ROOT / "data/pairs.jsonl")
    ap.add_argument("--task", default="wrongness")
    a = ap.parse_args(argv)
    pairs = {json.loads(l)["pair_id"]: json.loads(l) for l in open(a.pairs) if l.strip()}
    vals = defaultdict(lambda: defaultdict(list))
    for path in glob.glob(str(a.results_dir / "raw_*.jsonl")):
        for line in open(path):
            r = json.loads(line)
            if r.get("stage") == "judge" and r.get("status") == "VALID" and r.get("task") == a.task \
                    and r["condition"] in ("soft", "plain", "contrast"):
                vals[r["pair_id"]][r["condition"]].append(r["answer"])
    rows = []
    for pid, p in sorted(pairs.items()):
        v = vals[pid]
        if not v["soft"] or not v["plain"]:
            continue
        gap = st.mean(v["plain"]) - st.mean(v["soft"])
        lr = math.log(len(p["plain_text"].split()) / len(p["soft_text"].split()))
        rows.append((pid, gap, p["fact_coverage_soft"], lr, bool(p.get("famous")), p.get("tier", ""),
                     st.mean(v["soft"]), st.mean(v["plain"])))
    print(f"task={a.task}  pairs={len(rows)}  mean gap={st.mean(r[1] for r in rows):.2f}")
    print("pair  gap   cov  logLenRatio famous tier   soft  plain")
    for r in rows:
        print(f"{r[0]}  {r[1]:5.2f} {r[2]:.2f}  {r[3]:6.2f}     {str(r[4]):5}  {r[5]:<16} {r[6]:.2f} {r[7]:.2f}")
    g = [r[1] for r in rows]
    for name, x in (("H1 gap vs coverage", [r[2] for r in rows]), ("H2 gap vs log length ratio", [r[3] for r in rows])):
        print(f"{name}: spearman={spearman(x, g):.2f}  perm p={perm_p(x, g):.3f}")
    fam = [r[1] for r in rows if r[4]]
    nof = [r[1] for r in rows if not r[4]]
    print(f"H3 famous: mean gap {st.mean(fam) if fam else float('nan'):.2f} (n={len(fam)}) vs not famous {st.mean(nof) if nof else float('nan'):.2f} (n={len(nof)})")
    good = [r[1] for r in rows if str(r[5]).startswith("good")]
    oth = [r[1] for r in rows if not str(r[5]).startswith("good")]
    print(f"H4 tier: good mean gap {st.mean(good):.2f} (n={len(good)}) vs other {st.mean(oth):.2f} (n={len(oth)})")
    loo = [(r[0], st.mean([x[1] for x in rows if x[0] != r[0]])) for r in rows]
    print("H5 leave-one-out mean gap range: %.2f to %.2f (dropping %s / %s)" % (
        min(l[1] for l in loo), max(l[1] for l in loo),
        min(loo, key=lambda l: l[1])[0], max(loo, key=lambda l: l[1])[0]))
    print("pairs with gap <= 0:", [r[0] for r in rows if r[1] <= 0])


if __name__ == "__main__":
    main()
