"""Build the blind human fact-preservation sheet.

Items come from two places:
  defense   - plain-form rewrites (deeuphemize stage) from the real-pair runs
  synthetic - one-move rewrites from data/synthetic_live.jsonl, both kept and
              rejected by the automatic checker, so we can measure the checker

Writes sheet.csv (what the rater sees, no model or source info) and key.csv
(item id -> source, model, condition, checker verdict). Seeded, reproducible.
"""
import argparse
import csv
import glob
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import render_rewrite, parse_rewrite  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def defense_items(results_dir, models):
    out = []
    for path in sorted(glob.glob(str(results_dir / "raw_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("task") != "deeuphemize" or r.get("status") != "VALID":
                continue
            if models and r["model"] not in models:
                continue
            if str(r.get("repeat")) != "0":
                continue
            passage = json.loads(r["messages"][-1]["content"])["passage"]
            obj = parse_rewrite(r["raw_text"])
            if not obj:
                continue
            out.append({"source": "defense", "model": r["model"], "pair_id": r["pair_id"],
                        "condition": r["condition"], "checker": "none",
                        "original": passage, "reworded": render_rewrite(obj)})
    return out


def synthetic_items(path):
    out = []
    if not path.exists():
        return out
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        status = r.get("status") or ("kept" if r.get("kept") is True else "error")
        if status == "error" or not r.get("rewrite_text"):
            continue
        out.append({"source": "synthetic", "model": r["model"], "pair_id": r["pair_id"],
                    "condition": r["move"], "checker": status,
                    "original": r["source_text"], "reworded": r["rewrite_text"]})
    return out


def pick(items, n, key, rng):
    """Round-robin over strata so every stratum is represented; one item per (pair, condition)."""
    strata = {}
    for it in items:
        strata.setdefault(key(it), []).append(it)
    for v in strata.values():
        rng.shuffle(v)
    seen, chosen = set(), []
    while len(chosen) < n and any(strata.values()):
        for k in sorted(strata):
            while strata[k]:
                it = strata[k].pop()
                tag = (it["pair_id"], it["condition"], it["source"])
                if tag not in seen:
                    seen.add(tag)
                    chosen.append(it)
                    break
            if len(chosen) >= n:
                break
    return chosen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, default=ROOT / "harness/results_real")
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--synthetic", type=Path, default=ROOT / "data/synthetic_live.jsonl")
    ap.add_argument("--n-defense", type=int, default=20)
    ap.add_argument("--n-synthetic", type=int, default=20)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "human_check")
    ap.add_argument("--seed", type=int, default=20261114)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    d = pick(defense_items(a.results_dir, set(a.models)), a.n_defense,
             lambda it: (it["condition"], it["model"]), rng)
    s = pick(synthetic_items(a.synthetic), a.n_synthetic,
             lambda it: (it["checker"], it["condition"]), rng)
    items = d + s
    rng.shuffle(items)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    with open(a.out_dir / "sheet.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "original", "reworded", "same_facts (yes/no)", "if no: what changed"])
        for i, it in enumerate(items, 1):
            w.writerow([f"Q{i:02d}", it["original"], it["reworded"], "", ""])
    with open(a.out_dir / "key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "source", "model", "pair_id", "condition", "auto_checker"])
        for i, it in enumerate(items, 1):
            w.writerow([f"Q{i:02d}", it["source"], it["model"], it["pair_id"], it["condition"], it["checker"]])
    print(f"{len(items)} items ({len(d)} defense, {len(s)} synthetic) -> {a.out_dir}")


if __name__ == "__main__":
    main()
