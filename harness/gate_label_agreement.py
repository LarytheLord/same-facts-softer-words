"""Agreement between human gate labels and the omission-probe answers.

Inputs: the returned label sheet (CSV), the key file, and the raw_*.jsonl
files in harness/results_omission. The probe fields map as
harmed -> harmed_stated, extent -> extent_stated, responsible -> responsible_stated.
Each probe repeat is one observation. Cohen's kappa per field and per model,
with a bootstrap CI that resamples incidents (pair_id). Offline, read-only.
"""
import argparse
import csv
import glob
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = {"harmed": "harmed_stated", "extent": "extent_stated", "responsible": "responsible_stated"}
VALID = ("STATED", "MISSING")


def kappa(pairs):
    """Cohen's kappa over (a, b) label pairs. None if undefined."""
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    pe = 0.0
    for lab in VALID:
        pe += (sum(a == lab for a, _ in pairs) / n) * (sum(b == lab for _, b in pairs) / n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def load_labels(sheet_path, key_path):
    """Return {(pair_id, condition): {field: label}}. Blank or invalid labels are skipped."""
    key = {r["item_id"]: r for r in csv.DictReader(open(key_path, encoding="utf-8", newline=""))}
    out = {}
    for r in csv.DictReader(open(sheet_path, encoding="utf-8", newline="")):
        k = key.get(r["item_id"])
        if not k:
            continue
        labs = {}
        for f, col in FIELDS.items():
            v = (r.get(col) or "").strip().upper()
            if v in VALID:
                labs[f] = v
        out[(k["pair_id"], k["condition"])] = labs
    return out


def load_probe(results_dir):
    """Return {model: [(pair_id, condition, answer_dict), ...]} for VALID rows."""
    out = defaultdict(list)
    for path in sorted(glob.glob(str(Path(results_dir) / "raw_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            ans = r.get("answer")
            if r.get("status") == "VALID" and isinstance(ans, dict):
                out[r["model"]].append((r["pair_id"], r["condition"], ans))
    return out


def by_incident(labels, probe_rows, field):
    groups = defaultdict(list)
    for pid, cond, ans in probe_rows:
        h = labels.get((pid, cond), {}).get(field)
        m = ans.get(field)
        if h in VALID and m in VALID:
            groups[pid].append((h, m))
    return groups


def boot_kappa(groups, draws=2000, seed=20261117):
    keys = sorted(groups)
    point = kappa([p for k in keys for p in groups[k]])
    if not keys:
        return point, None, None
    rng = random.Random(seed)
    ks = []
    for _ in range(draws):
        sample = [p for _ in keys for p in groups[rng.choice(keys)]]
        v = kappa(sample)
        if v is not None:
            ks.append(v)
    if len(ks) < 20:
        return point, None, None
    ks.sort()
    return point, ks[int(0.025 * len(ks))], ks[int(0.975 * len(ks)) - 1]


def fmt(x):
    return "n/a" if x is None else "%.2f" % x


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, required=True, help="returned label sheet CSV")
    ap.add_argument("--key", type=Path, required=True, help="key CSV from build_gate_label_sheet")
    ap.add_argument("--results-dir", type=Path, default=ROOT / "harness/results_omission")
    ap.add_argument("--draws", type=int, default=2000)
    a = ap.parse_args(argv)
    labels = load_labels(a.labels, a.key)
    probe = load_probe(a.results_dir)
    lines = ["| model | field | n | kappa | 95% CI (incidents) |", "| --- | --- | --- | --- | --- |"]
    for model in sorted(probe):
        for f in FIELDS:
            g = by_incident(labels, probe[model], f)
            k, lo, hi = boot_kappa(g, a.draws)
            n = sum(len(v) for v in g.values())
            lines.append("| %s | %s | %d | %s | [%s, %s] |" % (model, f, n, fmt(k), fmt(lo), fmt(hi)))
    print("\n".join(lines))
    return lines


if __name__ == "__main__":
    main()
