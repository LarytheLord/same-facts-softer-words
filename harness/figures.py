"""Headline figure from a score.py summary.json (no API calls).

Per judge, three wrongness gaps with 95% bootstrap CIs:
  softening gap  = plain minus soft (company wording effect, real pairs)
  after defense  = same gap after both texts are rewritten in plain form
  real-fact gap  = plain minus contrast (one morally relevant fact changed)
Defense and softening use the common cohort score.py reports for the comparison.
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated categorical slots 1-3 (light surface #fcfcfb); slot 3 below 3:1 contrast,
# so every series also gets its own marker shape and a legend (relief rule).
SERIES = [
    ("Company vs regulator gap (regulator minus company)", "#2a78d6", "o"),
    ("Same gap after plain-language rewrite", "#eb6834", "s"),
    ("One-fact change (regulator minus contrast)", "#1baf7a", "D"),
]
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1e", "#6b6a63", "#e4e3dd"


def rows(summary):
    out = []
    for model, m in summary["models"].items():
        w = m["tasks"]["wrongness"]
        d = w["defense_comparison"]
        s = w["sensitivity_comparison"]["original_common_cohort"]
        out.append((model, [d["original_common_cohort"], d["defended_common_cohort"], s]))
    return sorted(out, key=lambda r: r[1][0]["estimate"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    data = sorted([r for f in a.summary for r in rows(json.loads(f.read_text()))],
                  key=lambda r: r[1][0]["estimate"])
    fig, ax = plt.subplots(figsize=(8.5, 1.0 + 0.62 * len(data)), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    offsets = (0.22, 0.0, -0.22)  # first series on top
    for i, (model, ests) in enumerate(data):
        for (label, color, marker), off, e in zip(SERIES, offsets, ests):
            lo, hi = e["ci95"]
            y = i + off
            ax.plot([lo, hi], [y, y], color=color, lw=2, solid_capstyle="round", zorder=2)
            ax.plot(e["estimate"], y, marker=marker, ms=8, color=color, mec=SURFACE, mew=2,
                    zorder=3, label=label if i == 0 else None, linestyle="none")
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([m.split(":", 1)[-1] + (" (n = 1)" if "claude" in m else "") for m, _ in data],
                       color=INK, fontsize=9)
    ax.axvline(0, color=MUTED, lw=1, zorder=1)
    ax.set_xlabel("Difference in wrongness rating (0-10 scale), 95% bootstrap CI over 11 incident pairs",
                  color=MUTED, fontsize=8.5)
    ax.tick_params(axis="x", colors=MUTED, labelsize=8.5)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.suptitle("Company statements are rated 4.4 to 6 points less wrong than regulator records on every judge",
                 x=0.01, ha="left", color=INK, fontsize=10.5)
    fig.legend(loc="upper left", bbox_to_anchor=(0.01, 0.96), ncol=1, frameon=False, fontsize=8,
               labelcolor=INK, handletextpad=0.4)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
