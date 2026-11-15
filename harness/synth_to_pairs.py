"""Turn synthetic rewrites into judge pairs for run.py.

Each non-error arm becomes one pair: soft_text = the one-move rewrite,
plain_text = the untouched source, contrast_text = the source's contrast.
The checker verdict (kept / rejected) is stored in source_soft so analysis can
slice by it; it is never shown to the judge.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _status(r):
    status = r.get("status") or ("kept" if r.get("kept") is True else "error")
    if status == "kept" and r.get("kept") is False:
        status = "rejected"  # an explicit kept=False wins over a stale status
    return status


def convert(rows, sources, include_rejected=False, sep="__"):
    """Arms -> judge pairs. Refuses to invent a contrast text or to pair a rewrite with a
    source whose text differs from the one the rewrite was made from."""
    src = {s["pair_id"]: s for s in sources}
    out = []
    for r in rows:
        status = _status(r)
        if status == "error" or not str(r.get("rewrite_text", "")).strip():
            continue
        if status != "kept" and not include_rejected:
            continue
        s = src.get(r["pair_id"])
        if s is None:
            raise ValueError("no source for " + r["pair_id"])
        source_text = s.get("plain_text") or s.get("plain_neutral") or s.get("text") or ""
        if r.get("source_text") and r["source_text"].strip() != source_text.strip():
            raise ValueError("rewrite source for " + r["pair_id"] + " does not match the source file")
        if not str(s.get("contrast_text", "")).strip():
            raise ValueError("source " + r["pair_id"] + " has no contrast_text; refusing to invent one")
        out.append({
            "pair_id": f'{r["pair_id"]}{sep}{r["move"]}',
            "domain": s.get("domain", "unknown"),
            "incident": s.get("incident") or s["pair_id"],
            "soft_text": r["rewrite_text"],
            "plain_text": s["plain_text"],
            "plain_neutral": s.get("plain_neutral") or s["plain_text"],
            "contrast_text": s["contrast_text"],
            "source_soft": f'synthetic:{r["move"]}:{status}:{r.get("model")}',
            "source_plain": s.get("source_url") or s.get("source_plain") or "regulator",
            "move": r["move"],
            "checker_status": status,
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", type=Path, default=ROOT / "data/synthetic_live.jsonl")
    ap.add_argument("--sources", type=Path, default=ROOT / "data/synth_sources.jsonl")
    ap.add_argument("--output", type=Path, default=ROOT / "data/pairs_synthetic.jsonl")
    ap.add_argument("--kept-only", action="store_true", help="Drop checker-rejected rewrites")
    a = ap.parse_args(argv)
    load = lambda path: [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = load(a.synthetic)
    pairs = convert(rows, load(a.sources), include_rejected=not a.kept_only, sep="_")
    with a.output.open("w", encoding="utf-8") as out:
        for p in pairs:
            out.write(json.dumps(p, ensure_ascii=True) + "\n")
    print(f"{len(pairs)} pairs written from {len(rows)} arms -> {a.output}")


if __name__ == "__main__":
    main()
