"""Per-move analysis of synthetic-arm judge runs (no API calls).

For each rewrite arm: softening gap = plain minus soft (wrongness, severity),
and the defended gap = plain minus soft_deeuph (only the soft text is
rewritten in plain form; the plain source is unchanged). Fact-check: share of
arms whose soft verdict differs from the plain verdict.

Slices: all arms, checker-kept, checker-rejected, and optionally human
same-facts (pass --human CSV with columns pair_id,same_facts yes/no).
CIs: 2000-draw bootstrap over source incidents (R01..R30), since arms that
share a source are not independent. Seeded.
"""
import argparse
import csv
import glob
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(raw_glob):
    vals = defaultdict(dict)  # (model, pair_id) -> {(condition, task): [values]}
    for path in sorted(glob.glob(raw_glob)):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("stage") != "judge" or r.get("status") != "VALID":
                continue
            vals[(r["model"], r["pair_id"])].setdefault((r["condition"], r["task"]), []).append(r["answer"])
    return vals


def boot(groups, draws=2000, seed=20261114):
    """groups: {source: [arm values]} -> mean over arms and CI resampling sources."""
    keys = [k for k, v in groups.items() if v]
    if not keys:
        return None
    flat = [x for k in keys for x in groups[k]]
    rng = random.Random(seed)
    means = []
    for _ in range(draws):
        sample = [x for k in (rng.choice(keys) for _ in keys) for x in groups[k]]
        means.append(st.mean(sample))
    means.sort()
    return st.mean(flat), means[int(0.025 * draws)], means[int(0.975 * draws) - 1], len(flat), len(keys)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default=str(ROOT / "harness/results_synth/raw_*.jsonl"))
    ap.add_argument("--pairs", nargs="+", default=[str(ROOT / "data/pairs_synth_A.jsonl")])
    ap.add_argument("--human", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "harness/results_synth/synth_summary.md")
    a = ap.parse_args(argv)
    meta = {}
    for p in a.pairs:
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            meta[d["pair_id"]] = d
    human = {}
    if a.human and a.human.exists():
        for row in csv.DictReader(open(a.human, encoding="utf-8")):
            human[row["pair_id"]] = row["same_facts"].strip().lower()
    vals = load(a.raw)
    models = sorted({m for m, _ in vals})
    slices = {"all": lambda m: True, "checker_kept": lambda m: m["checker_status"] == "kept",
              "checker_rejected": lambda m: m["checker_status"] == "rejected"}
    if human:
        slices["human_same_facts"] = lambda m: human.get(m["pair_id"]) == "yes"
    out = ["# Synthetic arm summary", "",
           "Gap = plain minus soft (positive = rewrite judged less wrong). Defended = plain minus soft after plain-form rewrite of the soft text.",
           "95% CI: bootstrap over source incidents. n = arms / sources.", ""]
    for model in models:
        out += [f"## {model}", "", "| Move | Slice | Wrongness gap | Defended wrongness gap | Severity gap | Fact-check flip rate | n arms / sources |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for move in ("euphemism", "nominalization", "agent_deletion", "all_three", "ALL"):
            for sname, sel in slices.items():
                g_w, g_d, g_s, g_f = (defaultdict(list) for _ in range(4))
                for (mm, pid), v in vals.items():
                    m = meta.get(pid)
                    if mm != model or not m or not sel(m) or (move != "ALL" and m["move"] != move):
                        continue
                    src = pid.split("_")[0]

                    def mean(cond, task):
                        x = v.get((cond, task))
                        return st.mean(x) if x else None
                    pw, sw, dw = mean("plain", "wrongness"), mean("soft", "wrongness"), mean("soft_deeuph", "wrongness")
                    ps, ss = mean("plain", "severity"), mean("soft", "severity")
                    if pw is not None and sw is not None:
                        g_w[src].append(pw - sw)
                    if pw is not None and dw is not None:
                        g_d[src].append(pw - dw)
                    if ps is not None and ss is not None:
                        g_s[src].append(ps - ss)
                    pf, sf = v.get(("plain", "fact_check")), v.get(("soft", "fact_check"))
                    if pf and sf:
                        g_f[src].append(float(pf[0] != sf[0]))

                def fmt(groups):
                    b = boot(groups)
                    return "NA" if not b else f"{b[0]:.2f} [{b[1]:.2f}, {b[2]:.2f}]"
                b = boot(g_w)
                n = "0" if not b else f"{b[3]} / {b[4]}"
                out.append(f"| {move} | {sname} | {fmt(g_w)} | {fmt(g_d)} | {fmt(g_s)} | {fmt(g_f)} | {n} |")
        out.append("")
    # Equivalence check (TOST at +/-1 point): 90% bootstrap interval for the pooled wrongness gap,
    # resampling source incidents. Margin chosen after seeing the data, so reported as post hoc.
    out += ["## Equivalence check (pooled wrongness gap, 90% bootstrap over sources, 5000 draws, seed 7)", ""]
    for model in models:
        groups = defaultdict(list)
        for (mm, pid), v in vals.items():
            if mm != model or pid not in meta:
                continue
            pw, sw = v.get(("plain", "wrongness")), v.get(("soft", "wrongness"))
            if pw and sw:
                groups[pid.split("_")[0]].append(st.mean(pw) - st.mean(sw))
        keys = sorted(groups)
        rng = random.Random(7)
        ms = sorted(st.mean([x for k in (rng.choice(keys) for _ in keys) for x in groups[k]]) for _ in range(5000))
        lo, hi = ms[250], ms[4749]
        out.append(f"- {model}: 90% [{lo:.2f}, {hi:.2f}] -> {'within' if -1 < lo and hi < 1 else 'NOT within'} +/-1")
    out.append("")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
