#!/usr/bin/env python3
"""Aggregate the fixed-budget GateANN frontier A/B experiment."""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path


NUMERIC = (
    "L", "qps", "mean_latency_us", "recall_percent", "mean_ios",
    "filter_skips", "io_time_us", "tunnel_time_us", "process_time_us",
)


def median(values: list[float]) -> float:
    return statistics.median(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    all_rows: list[dict[str, str]] = []
    for repeat in range(1, args.repeats + 1):
      for variant in ("baseline", "optimized"):
        run_id = f"{args.experiment_id}-r{repeat}-{variant}"
        for bucket in ("low", "medium", "high"):
          path = (args.run_root / "results" / "gateann" / "formal_1000000" /
                  bucket / run_id / "results.csv")
          with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
              row["variant"] = variant
              row["repeat"] = str(repeat)
              all_rows.append(row)

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    all_fields = ["variant", "repeat", *[k for k in all_rows[0] if k not in ("variant", "repeat")]]
    with (output_dir / "all_runs.csv").open("w", newline="", encoding="utf-8") as handle:
      writer = csv.DictWriter(handle, fieldnames=all_fields)
      writer.writeheader()
      writer.writerows(all_rows)

    groups: dict[tuple[str, str, int], list[dict[str, str]]] = {}
    for row in all_rows:
      key = (row["variant"], row["bucket"], int(row["L"]))
      groups.setdefault(key, []).append(row)

    summary_rows = []
    for (variant, bucket, search_l), rows in sorted(groups.items()):
      out: dict[str, str | int | float] = {
          "variant": variant, "bucket": bucket, "L": search_l, "n": len(rows)
      }
      for name in NUMERIC[1:]:
        values = [float(row[name]) for row in rows if row.get(name, "") != ""]
        out[f"{name}_median"] = median(values)
        out[f"{name}_min"] = min(values)
        out[f"{name}_max"] = max(values)
      summary_rows.append(out)

    fields = list(summary_rows[0])
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
      writer = csv.DictWriter(handle, fieldnames=fields)
      writer.writeheader()
      writer.writerows(summary_rows)

    print(f"Wrote {output_dir / 'all_runs.csv'}")
    print(f"Wrote {output_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
