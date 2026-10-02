#!/usr/bin/env bash
# Reproduce the complete default simulation study from a clean checkout.
#
# Prerequisites: a C++17 compiler, CMake >= 3.16, Python 3.9+ with
#   numpy pandas scipy matplotlib   (pip install -r requirements.txt)
#
# Usage: scripts/reproduce_all.sh [--quick]
#   --quick  runs a reduced campaign (3 seeds, 600 s) to check the pipeline.
#
# Each campaign is written to results/campaigns/<id>_<UTC timestamp>/ so
# earlier campaigns are never overwritten. Results are deterministic: the
# same configuration and seeds give byte-identical workloads and per-run
# outputs on the same platform/toolchain.
set -euo pipefail
cd "$(dirname "$0")/.."
QUICK=0; [[ "${1:-}" == "--quick" ]] && QUICK=1
TS="$(date -u +%Y%m%dT%H%M%SZ)"
JOBS="$(nproc 2>/dev/null || echo 2)"

echo "== 1. build"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$JOBS"

echo "== 2. tests"
bash tests/run_tests.sh

if [[ $QUICK == 1 ]]; then SEEDS=1:3; SECS=600; SSEEDS=1:2; SSECS=600; else SEEDS=1:10; SECS=3600; SSEEDS=1:5; SSECS=1800; fi

echo "== 3. main campaign (8 scenarios x 6 modes x seeds $SEEDS, $SECS s)"
python3 scripts/run_experiments.py --campaign-id "main_$TS" --seeds "$SEEDS" --seconds "$SECS" --jobs "$JOBS" \
  --scenarios quiet normal busy burst noisy trigger_spam replay mixed \
  --modes always_on motion_only fixed_threshold event event_no_early_exit secure

echo "== 4. ablation campaign"
python3 scripts/run_ablations.py --campaign-id "ablation_$TS" --seeds "$SEEDS" --seconds "$SECS" --jobs "$JOBS"

echo "== 5. sensitivity campaign"
python3 scripts/run_sensitivity.py --campaign-id "sensitivity_$TS" --seeds "$SSEEDS" --seconds "$SSECS" --jobs "$JOBS"

echo "== 6. results report"
python3 scripts/make_report.py --main "results/campaigns/main_$TS" --ablation "results/campaigns/ablation_$TS" \
  --sensitivity "results/campaigns/sensitivity_$TS" --out "results/campaigns/main_$TS/RESULTS_SUMMARY.md"
echo "done. See results/campaigns/*_$TS/"
