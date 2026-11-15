"""Check your LLM judge in one command.

Runs the 11 real company-vs-regulator incident pairs through your judge twice:
once with a standard 0-10 wrongness rubric, once with the same rubric plus an
INSUFFICIENT option. Reports three numbers:

  leniency gap      regulator score minus company score (same incident)
  fact sensitivity  regulator score minus one-fact-changed score
  abstention        how often the judge says INSUFFICIENT on company vs regulator text
  triage            cases a "close if score <= 2" rule would close, one-step vs a two-step
                    protocol that first asks whether the harm facts are stated

About 198 calls with --n 2. Offline mock by default; add --live to call a model.

Model naming:
  anthropic:<model>   needs ANTHROPIC_API_KEY
  adaption:<model>    needs ADAPTION_API_KEY
  <model>             any OpenAI-compatible chat endpoint: set BASE_URL, API_KEY

Example:
  BASE_URL=https://api.groq.com/openai/v1 API_KEY=... \\
      python3 harness/judge_check.py --live --model qwen/qwen3.8-27b
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_probe  # noqa: E402
import omission_probe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def summarize(raw_dir, model):
    tag = model.replace("/", "_").replace(":", "_")
    out = {}
    for var in scale_probe.VARIANTS:
        rows = [json.loads(l) for l in open(raw_dir / f"raw_{tag}_{var}.jsonl", encoding="utf-8")]
        by = {}
        for r in rows:
            by.setdefault((r["pair_id"], r["condition"]), []).append(r["answer"])
        out[var] = by
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="mock")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--pairs", type=Path, default=ROOT / "data/pairs.jsonl")
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args(argv)
    tag = a.model.replace("/", "_").replace(":", "_")
    out_dir = a.out_dir or ROOT / "harness" / ("judge_check_" + tag + ("" if a.live else "_mock"))
    if not a.live and "mock" not in out_dir.name:
        ap.error("mock runs must write to a folder whose name contains 'mock' (protects real results)")
    if out_dir.exists() and any(out_dir.glob("raw_*.jsonl")):
        ap.error(f"{out_dir} already has results; pass a new --out-dir (never overwrite real runs)")
    args = ["--pairs", str(a.pairs), "--models", a.model, "--n", str(a.n), "--out-dir", str(out_dir)]
    if a.live:
        args.insert(0, "--live")
    scale_probe.main(args)
    s = summarize(out_dir, a.model)
    pairs = sorted({p for p, _ in s["A_original"]})

    def gap(var, c1, c2):
        d = []
        for p in pairs:
            x = [v for v in s[var].get((p, c1), []) if v not in (None, "INSUFFICIENT")]
            y = [v for v in s[var].get((p, c2), []) if v not in (None, "INSUFFICIENT")]
            if x and y:
                d.append(mean(x) - mean(y))
        return mean(d), len(d)

    def insuff(cond):
        vals = [v for p in pairs for v in s["B_insufficient"].get((p, cond), []) if v is not None]
        return mean([float(v == "INSUFFICIENT") for v in vals])

    lg, n1 = gap("A_original", "plain", "soft")
    fs, n2 = gap("A_original", "plain", "contrast")
    ic, ir = insuff("soft"), insuff("plain")
    print("\nJudge check:", a.model, "(MOCK, not a real result)" if not a.live else "")
    print(f"  leniency gap      {lg:+.2f} points on 0-10 over {n1} incidents (regulator minus company)")
    print(f"  fact sensitivity  {fs:+.2f} points over {n2} incidents (regulator minus one-fact change)")
    print(f"  abstention        INSUFFICIENT on {ic:.0%} of company texts vs {ir:.0%} of regulator texts")
    if lg is not None and fs is not None and lg > 2:
        print("  -> Low scores on company statements here mostly mean 'not established', not 'not wrong'.")
        print("     Do not let a low score close a case without an evidence-sufficiency check.")
    if ic is not None and ir is not None:
        print("  -> " + ("This judge abstains selectively when allowed: use the INSUFFICIENT option."
                         if ic - ir >= 0.4 else
                         "This judge does not abstain selectively: an INSUFFICIENT option alone will not fix it."))
    # Two-step protocol: omission probe (are harm facts stated?) then score.
    probe_dir = out_dir / "omission"
    oargs = ["--pairs", str(a.pairs), "--models", a.model, "--n", str(a.n), "--out-dir", str(probe_dir)]
    if a.live:
        oargs.insert(0, "--live")
    omission_probe.main(oargs)
    tag2 = a.model.replace("/", "_")
    probe = {}
    for l in open(probe_dir / f"raw_{tag2}.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r.get("answer"):
            probe.setdefault((r["pair_id"], r["condition"]), []).append(
                r["answer"]["harmed"] == "STATED" and r["answer"]["extent"] == "STATED")
    print("  triage (close if score <= 2):")
    for cond, name in (("soft", "company statements"), ("plain", "regulator records"), ("contrast", "one-fact contrasts")):
        one = closed = insuff = 0
        for p in pairs:
            sc = [v for v in s["A_original"].get((p, cond), []) if v not in (None, "INSUFFICIENT")]
            if not sc:
                continue
            low = mean(sc) <= 2
            one += low
            pr = probe.get((p, cond), [])
            if pr and sum(pr) / len(pr) <= 0.5:
                insuff += 1
            elif low:
                closed += 1
        print(f"    {name:20s} one-step closes {one:2d}; two-step closes {closed:2d}, routes {insuff:2d} to INSUFFICIENT")
    print("  Raw outputs and a summary table:", out_dir)


if __name__ == "__main__":
    main()
