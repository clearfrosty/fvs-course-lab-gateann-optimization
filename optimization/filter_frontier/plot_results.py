#!/usr/bin/env python3
"""Plot the Low-workload Recall-Latency frontier from summary.csv."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def main() -> int:
    with (HERE / "results" / "summary.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["bucket"] == "low"]

    fig, ax = plt.subplots(figsize=(6.8, 4.3), dpi=200)
    styles = {
        "baseline": ("#7f7f7f", "o", "GateANN baseline"),
        "optimized": ("#d62728", "s", "Adaptive tiered frontier"),
    }
    for variant in ("baseline", "optimized"):
        group = sorted((r for r in rows if r["variant"] == variant), key=lambda r: int(r["L"]))
        if variant == "optimized":
            group = [r for r in group if int(r["L"]) <= 640]
        color, marker, label = styles[variant]
        x = [float(r["mean_latency_us_median"]) / 1000.0 for r in group]
        y = [float(r["recall_percent_median"]) for r in group]
        ax.plot(x, y, marker=marker, color=color, lw=1.8, ms=5.5, label=label)
        for px, py, row in zip(x, y, group):
            label_points = {2560} if variant == "baseline" else {320, 360, 400}
            if int(row["L"]) in label_points:
                offsets = {320: (4, -13), 360: (4, 5), 400: (4, 15), 2560: (4, 5)}
                ax.annotate(f"L={row['L']}", (px, py), xytext=offsets[int(row["L"])],
                            textcoords="offset points", fontsize=7.5, color=color)

    ax.set_xlabel("Mean query latency (ms), median of 3 runs")
    ax.set_ylabel("Recall@10 (%)")
    ax.set_title("GateANN Low workload: Recall-Latency frontier")
    ax.grid(alpha=0.28)
    ax.legend(loc="lower right")
    fig.tight_layout()
    target = REPO / "report_figures" / "fig5_filter_frontier.png"
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
