"""Rebuild the scale-probe and omission-probe tables from saved raw files (no API calls).

Uses the same bootstrap (seed, draws, key order) as scale_probe.py and omission_probe.py,
so the output should match the summaries written during the live runs exactly.
"""
import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_probe as sp  # noqa: E402
import omission_probe as op  # noqa: E402


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def scale_rows(raw_dir):
    out = []
    files = sorted(raw_dir.glob("raw_*_A_original.jsonl"))
    for fa in files:
        model = load(fa)[0]["model"]
        for var in sp.VARIANTS:
            recs = load(fa.with_name(fa.name.replace("_A_original", "_" + var)))
            got = defaultdict(lambda: defaultdict(list))
            invalid = 0
            for r in recs:
                if r["answer"] is None:
                    invalid += 1
                else:
                    got[r["pair_id"]][r["condition"]].append(r["answer"])

            def ins(c):
                return {p: (st.mean(float(x == "INSUFFICIENT") for x in v[c]) if v[c] else None) for p, v in got.items()}

            def num(c):
                return {p: [x for x in v[c] if x != "INSUFFICIENT"] for p, v in got.items()}

            def gap(c1, c2):
                a, b = num(c1), num(c2)
                return {p: (st.mean(a[p]) - st.mean(b[p]) if a[p] and b[p] else None) for p in a}
            out.append(f"| {model} | {var} | {sp.fmt(sp.boot(ins('soft')))} | {sp.fmt(sp.boot(ins('plain')))} | "
                       f"{sp.fmt(sp.boot(ins('contrast')))} | {sp.fmt(sp.boot(gap('plain', 'soft')))} | "
                       f"{sp.fmt(sp.boot(gap('plain', 'contrast')))} | {invalid}/{len(recs)} |")
    return out


def omission_rows(raw_dir):
    out = []
    for f in sorted(raw_dir.glob("raw_*.jsonl")):
        recs = load(f)
        model = recs[0]["model"]
        per = defaultdict(lambda: defaultdict(list))
        invalid = 0
        for r in recs:
            if r["answer"] is None:
                invalid += 1
            else:
                per[r["pair_id"]][r["condition"]].append(sum(v == "MISSING" for v in r["answer"].values()))

        def m(c):
            return {p: (st.mean(v[c]) if v[c] else None) for p, v in per.items()}

        def diff(c1, c2):
            return {p: (st.mean(v[c1]) - st.mean(v[c2]) if v[c1] and v[c2] else None) for p, v in per.items()}

        def f_(b):
            return "NA" if not b else f"{b[0]:.2f} [{b[1]:.2f}, {b[2]:.2f}]"
        out.append(f"| {model} | {f_(op.boot(m('soft')))} | {f_(op.boot(m('plain')))} | {f_(op.boot(m('contrast')))} | "
                   f"{f_(op.boot(diff('soft', 'plain')))} | {f_(op.boot(diff('contrast', 'plain')))} | {invalid}/{len(recs)} |")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scale", nargs="*", type=Path, default=[])
    ap.add_argument("--omission", nargs="*", type=Path, default=[])
    a = ap.parse_args(argv)
    for d in a.scale:
        print(f"## scale {d}")
        print("\n".join(scale_rows(d)))
    for d in a.omission:
        print(f"## omission {d}")
        print("\n".join(omission_rows(d)))


if __name__ == "__main__":
    main()
