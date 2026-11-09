#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
gateann_repo="${1:-$repo_root/systems/GateANN-filter-frontier}"
run_root="${2:-$repo_root/course_runs}"
experiment_id="${3:-frontier-final-v2}"
repeats="${4:-3}"
dataset_root="$repo_root/datasets/yfcc_course_v1"

common=(
  --repo "$gateann_repo"
  --dataset-root "$dataset_root"
  --tier formal
  --run-root "$run_root"
  --threads 1
  --beamwidth 8
  --k 10
  --full-adj-neighbors 32
  --frontier-selectivity-threshold 0.015
)

run_variant() {
  local variant="$1"
  local repeat="$2"
  local reserve
  if [[ "$variant" == baseline ]]; then reserve=0; else reserve=0.15; fi
  local run_id="$experiment_id-r$repeat-$variant"

  python3 "$repo_root/adapters/gateann_adapter.py" search "${common[@]}" \
    --frontier-max-reserve "$reserve" --bucket low \
    --L 160 320 360 400 640 1280 2560 --run-id "$run_id"
  python3 "$repo_root/adapters/gateann_adapter.py" search "${common[@]}" \
    --frontier-max-reserve "$reserve" --bucket medium \
    --L 160 320 640 --run-id "$run_id"
  python3 "$repo_root/adapters/gateann_adapter.py" search "${common[@]}" \
    --frontier-max-reserve "$reserve" --bucket high \
    --L 160 320 640 --run-id "$run_id"
}

for repeat in $(seq 1 "$repeats"); do
  if (( repeat % 2 == 1 )); then
    run_variant baseline "$repeat"
    run_variant optimized "$repeat"
  else
    run_variant optimized "$repeat"
    run_variant baseline "$repeat"
  fi
done

python3 "$script_dir/analyze.py" \
  --run-root "$run_root" --experiment-id "$experiment_id" --repeats "$repeats"
