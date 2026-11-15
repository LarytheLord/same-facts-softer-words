"""Recompute paired estimates from raw text, keeping invalid counts visible."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics
import sys

if __package__:
    from .prompts import TASKS, CONDITIONS, parse_answer, parse_rewrite
else:
    from prompts import TASKS, CONDITIONS, parse_answer, parse_rewrite

DEFAULT_RESULTS = Path(__file__).resolve().parent / "results"


def _quantile(values, p):
    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def bootstrap(values, seed=42, draws=2000):
    """Percentile paired-cluster bootstrap of per-pair statistics, with replacement."""
    if draws < 1:
        raise ValueError("Bootstrap draws must be positive")
    values = sorted(values)
    if not values:
        return {"estimate": None, "ci95": None, "n_pairs": 0}
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(draws))
    return {"estimate": statistics.fmean(values),
            "ci95": [_quantile(means, .025), _quantile(means, .975)],
            "n_pairs": len(values)}


def _comparison(table, conditions, fn, seed, draws):
    by_pair = defaultdict(dict)
    for (pair, condition), values in table.items():
        if condition in conditions:
            by_pair[pair][condition] = values
    values, matched = [], 0
    for pair in sorted(by_pair):
        cells = by_pair[pair]
        if any(c not in cells for c in conditions):
            continue
        repeats = set.intersection(*(set(cells[c]) for c in conditions))
        if not repeats:
            continue
        differences = [fn(*(cells[c][r] for c in conditions)) for r in sorted(repeats)]
        values.append(statistics.fmean(differences))
        matched += len(repeats)
    result = bootstrap(values, seed, draws)
    result["n_matched_repeats"] = matched
    return result


def _validated(row):
    parser = parse_rewrite if row.get("stage") == "rewrite" else None
    answer = parser(row.get("raw_text")) if parser else parse_answer(row["task"], row.get("raw_text"))
    if row.get("status") == "INVALID" or row.get("finish_reason") in ("length", "content_filter"):
        return None
    return answer


def summarize(rows, seed=42, draws=2000):
    models = defaultdict(list)
    seen = set()
    for row in rows:
        if row.get("stage") not in ("judge", "rewrite") or row.get("condition") not in CONDITIONS:
            raise ValueError("Unknown stage or condition in raw record")
        if row.get("task") not in TASKS + ("deeuphemize",):
            raise ValueError("Unknown task in raw record")
        if (row["stage"] == "rewrite") != (row["task"] == "deeuphemize"):
            raise ValueError("Task and stage disagree")
        key = tuple(row[k] for k in ("model", "pair_id", "condition", "repeat", "task"))
        if key in seen:
            raise ValueError("Duplicate query identity in raw results")
        seen.add(key)
        models[row["model"]].append(row)
    result = {}
    for model in sorted(models):
        records = models[model]
        run_ids = {r.get("run_id") for r in records}
        digests = {r.get("pairs_sha256") for r in records}
        if len(run_ids) > 1 or len(digests) > 1:
            raise ValueError("Mixed runs or input datasets for one model")
        # A persisted run must contain every expected query, including failed calls.
        declared = {r.get("n") for r in records}
        pair_counts = {r.get("pair_count") for r in records}
        if None not in declared and None not in pair_counts:
            if len(declared) != 1 or len(pair_counts) != 1:
                raise ValueError("Inconsistent run metadata")
            n, pair_count = next(iter(declared)), next(iter(pair_counts))
            pair_ids = {r["pair_id"] for r in records}
            actual = {(r["pair_id"], r["condition"], r["repeat"], r["task"]) for r in records}
            expected = {(p, c, i, t) for p in pair_ids for c in CONDITIONS for i in range(n)
                        for t in TASKS + (("deeuphemize",) if c.endswith("_deeuph") else ())}
            if len(pair_ids) != pair_count or actual != expected:
                raise ValueError("Incomplete raw run: missing or unexpected queries; do not score partial files")
        judges = [r for r in records if r["stage"] == "judge"]
        rewrites = [r for r in records if r["stage"] == "rewrite"]
        parsed = [(r, _validated(r)) for r in judges]
        invalid = sum(v is None for _, v in parsed)
        bad_rewrites = sum(_validated(r) is None for r in rewrites)
        report = {"backend": sorted({r.get("backend", "unknown") for r in records}),
                  "run_id": records[0].get("run_id"),
                  "pairs_sha256": records[0].get("pairs_sha256"),
                  "total_judge_records": len(judges), "invalid_count": invalid,
                  "invalid_rate": invalid / len(judges) if judges else None,
                  "rewrite_records": len(rewrites), "rewrite_invalid_count": bad_rewrites,
                  "rewrite_invalid_rate": bad_rewrites / len(rewrites) if rewrites else None,
                  "invalid_reasons": dict(sorted(Counter(
                      r.get("error") or "unparseable_output" for r, v in parsed if v is None).items())),
                  "tasks": {}}
        for task in TASKS:
            table = defaultdict(dict)
            task_rows = [(r, v) for r, v in parsed if r["task"] == task]
            for r, value in task_rows:
                if value is not None:
                    table[(r["pair_id"], r["condition"])][r["repeat"]] = value
            task_report = {"conditions": {}}
            for condition in CONDITIONS:
                vals = [r for r, v in task_rows if r["condition"] == condition]
                valid = [v for r, v in task_rows if r["condition"] == condition and v is not None]
                cell = {"total": len(vals), "valid": len(valid), "invalid": len(vals) - len(valid)}
                pair_values = {pair: list(v.values()) for (pair, c), v in sorted(table.items()) if c == condition}
                if task == "fact_check":
                    cell["verdict_counts"] = dict(sorted(Counter(valid).items()))
                else:
                    cell["mean_of_pair_means"] = statistics.fmean(
                        statistics.fmean(v) for v in pair_values.values()) if pair_values else None
                    cell["within_pair_repeat_sd"] = {p: statistics.stdev(v) if len(v) > 1 else None
                                                      for p, v in pair_values.items()}
                task_report["conditions"][condition] = cell
            def compare(conditions, fn):
                return _comparison(table, conditions, fn, seed, draws)
            if task == "fact_check":
                diff = lambda a, b: float(a != b)
                task_report["soft_plain_flip_rate"] = compare(("plain", "soft"), diff)
                task_report["sensitivity_flip_rate"] = compare(("plain", "contrast"), diff)
                task_report["defended_flip_rate"] = compare(("plain_deeuph", "soft_deeuph"), diff)
                task_report["defended_sensitivity_flip_rate"] = compare(("plain_deeuph", "contrast_deeuph"), diff)
                original = lambda p, s, pd, sd: diff(p, s)
                defended = lambda p, s, pd, sd: diff(pd, sd)
                reduction = lambda p, s, pd, sd: diff(p, s) - diff(pd, sd)
            else:
                diff = lambda a, b: a - b
                task_report["softening_gap"] = compare(("plain", "soft"), diff)
                task_report["sensitivity_gap"] = compare(("plain", "contrast"), diff)
                task_report["defended_gap"] = compare(("plain_deeuph", "soft_deeuph"), diff)
                task_report["defended_sensitivity_gap"] = compare(("plain_deeuph", "contrast_deeuph"), diff)
                original = lambda p, s, pd, sd: p - s
                defended = lambda p, s, pd, sd: pd - sd
                reduction = lambda p, s, pd, sd: (p - s) - (pd - sd)
            cohort = ("plain", "soft", "plain_deeuph", "soft_deeuph")
            task_report["defense_comparison"] = {
                "original_common_cohort": compare(cohort, original),
                "defended_common_cohort": compare(cohort, defended),
                "reduction": compare(cohort, reduction)}
            sensitivity_cohort = ("plain", "contrast", "plain_deeuph", "contrast_deeuph")
            task_report["sensitivity_comparison"] = {
                "original_common_cohort": compare(sensitivity_cohort, original),
                "defended_common_cohort": compare(sensitivity_cohort, defended),
                "reduction": compare(sensitivity_cohort, reduction)}
            report["tasks"][task] = task_report
        result[model] = report
    return result


def markdown(summary):
    lines = ["# Evaluation summary", "", "TOY MOCK rows check the pipeline only. They are not empirical findings.",
             "Intervals resample pairs, not repeated calls. Missing estimates are NA.", "",
             "| Model | Task | Original gap / flip | Defended gap / flip | Defense reduction | Plain-contrast | Defended plain-contrast | Invalid |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    def fmt(m):
        if m["estimate"] is None:
            return "NA (0 pairs)"
        lo, hi = m["ci95"]
        return f'{m["estimate"]:.3f} [{lo:.3f}, {hi:.3f}]; N={m["n_pairs"]}'
    for model, report in summary["models"].items():
        label = model.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        if "mock" in report["backend"]:
            label += " (TOY MOCK)"
        for task, r in report["tasks"].items():
            defense, sensitivity = r["defense_comparison"], r["sensitivity_comparison"]
            cells = [label, task, fmt(defense["original_common_cohort"]),
                     fmt(defense["defended_common_cohort"]), fmt(defense["reduction"]),
                     fmt(sensitivity["original_common_cohort"]),
                     fmt(sensitivity["defended_common_cohort"]),
                     f'{report["invalid_count"]}/{report["total_judge_records"]}']
            lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "Numeric gaps are plain minus soft, or plain minus contrast. Defense reduction",
              "is original minus defended. Fact-check cells are categorical disagreement rates;",
              "they do not establish accuracy. Each comparison uses common valid repeat IDs.",
              "A positive contrast gap assumes contrast was designed to reduce wrongdoing.",
              "No automatic pass/fail threshold is imposed on sensitivity or defense effects.",
              "Rewrite parsing checks structure only; factual preservation needs human review.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap", type=int, default=2000, dest="draws")
    args = parser.parse_args(argv)
    if args.draws < 1:
        parser.error("--bootstrap must be positive")
    files = sorted(args.results_dir.glob("raw_*.jsonl"))
    if not files:
        parser.error("No raw_*.jsonl files in results directory")
    rows = []
    try:
        for path in files:
            with path.open(encoding="utf-8") as handle:
                file_rows = []
                for line_no, line in enumerate(handle, 1):
                    if line.strip():
                        try:
                            file_rows.append(json.loads(line))
                        except ValueError:
                            raise ValueError(f"Malformed JSON: {path.name}:{line_no}") from None
                if not file_rows:
                    raise ValueError("Empty raw file: " + path.name)
                rows.extend(file_rows)
        models = summarize(rows, args.seed, args.draws)
        if not any(r["total_judge_records"] for r in models.values()):
            raise ValueError("No judge records to score")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    summary = {"schema_version": 1, "seed": args.seed, "bootstrap_draws": args.draws,
               "ci_method": "percentile paired bootstrap over pair means; 95%",
               "pairing": "pair_id and common valid repeat index; equal weight per pair",
               "models": models}
    (args.results_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    (args.results_dir / "summary.md").write_text(markdown(summary), encoding="utf-8")
    print("Scored " + str(len(models)) + " model(s); summaries in " + str(args.results_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
