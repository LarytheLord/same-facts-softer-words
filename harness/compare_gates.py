"""Compare the one-question gate with the per-fact gate, per pair.

Inputs are saved outputs only (no model calls):
  --per-fact   jsonl written by harness/per_fact_check.py
  --omission   raw omission probe jsonl (e.g. harness/results_omission/raw_<model>.jsonl)

One-question gate: INSUFFICIENT when, over the repeats for the chosen condition
(default soft), at most half of them mark both harmed and extent STATED (the same
rule judge_check.py uses). Per-fact gate: the gate field in the per-fact output.
Reads only; writes nothing.
"""
import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path):
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def one_question_gates(rows, condition="soft"):
    stated = {}
    for r in rows:
        if r.get("condition") != condition or not r.get("answer"):
            continue
        a = r["answer"]
        stated.setdefault(r["pair_id"], []).append(a["harmed"] == "STATED" and a["extent"] == "STATED")
    return {p: ("INSUFFICIENT" if sum(v) / len(v) <= 0.5 else "SUFFICIENT") for p, v in stated.items()}


def per_fact_gates(rows):
    return {r["pair_id"]: r["gate"] for r in rows if r.get("status") == "VALID" and r.get("gate")}


def compare(one, per):
    ids = sorted(set(one) & set(per))
    table = [(p, one[p], per[p], one[p] == per[p]) for p in ids]
    agree = sum(t[3] for t in table)
    return {"table": table, "n": len(ids), "agree": agree,
            "agreement": agree / len(ids) if ids else None,
            "only_one": sorted(set(one) - set(per)), "only_per": sorted(set(per) - set(one))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-fact", type=Path, required=True)
    ap.add_argument("--omission", type=Path, required=True)
    ap.add_argument("--condition", default="soft")
    a = ap.parse_args(argv)
    res = compare(one_question_gates(load_jsonl(a.omission), a.condition), per_fact_gates(load_jsonl(a.per_fact)))
    print(f"{'pair':8s} {'one-question':14s} {'per-fact':14s} agree")
    for p, o, f, ok in res["table"]:
        print(f"{p:8s} {o:14s} {f:14s} {'yes' if ok else 'NO'}")
    if res["n"]:
        print(f"agreement: {res['agree']}/{res['n']} = {res['agreement']:.0%}")
    else:
        print("no pairs in common")
    for key, label in (("only_one", "only in omission results"), ("only_per", "only in per-fact results")):
        if res[key]:
            print(f"{label}: {', '.join(res[key])}")


if __name__ == "__main__":
    main()
