#!/usr/bin/env bash
# Smoke test: short runs (default 300 simulated s) of the main scenarios in
# every mode on shared workloads, followed by structural validation of every
# run. Output goes to a fresh campaign directory (never overwritten).
set -euo pipefail
cd "$(dirname "$0")/.."
SECONDS_SIM="${1:-300}"
ID="${2:-smoke_$(date -u +%Y%m%dT%H%M%SZ)}"
python3 scripts/run_experiments.py --campaign-id "$ID" --seeds 1:2 --seconds "$SECONDS_SIM" \
  --scenarios normal busy trigger_spam replay mixed \
  --modes always_on motion_only fixed_threshold event event_no_early_exit secure
python3 - "$ID" <<'PY'
import sys, pandas as pd
c = f"results/campaigns/{sys.argv[1]}"
v = pd.read_csv(f"{c}/logs/validation.csv"); w = pd.read_csv(f"{c}/logs/workload_equality.csv")
print(f"runs={len(v)} validation_pass={int(v.validation_pass.sum())} workloads_shared_ok={bool(w.all_runs_match.all())}")
sys.exit(0 if v.validation_pass.all() and w.all_runs_match.all() else 1)
PY
