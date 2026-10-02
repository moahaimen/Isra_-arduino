#!/usr/bin/env python3
"""R3.1 security sweep (validation/development only): watcher = validation-selected legacy event trigger; defences = none, plain global
token bucket, R3.1 gate (replay + budget), R3.1 gate + shift tolerance, legacy secure, plus ugs_secure/robust_secure with their own watchers.
Conditions: clean, noisy, spam {0.5..16}, replay_exact, replay_perturbed, mixed."""
import argparse, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
ap = argparse.ArgumentParser()
ap.add_argument("--split", default="validation"); ap.add_argument("--datasets", default="kitti")
ap.add_argument("--thr", type=float, default=0.45); ap.add_argument("--workers", type=int, default=3)
ap.add_argument("--seeds", default="1001,1002,1003"); ap.add_argument("--out", required=True)
a = ap.parse_args()
if a.split == "test": raise SystemExit("test locked")
W = {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0}   # event|15 (validation Pareto point, duty<=0.25)
C = {"detection_threshold": a.thr}
def S(label, mode, p): return (label, mode, {"common": C, "params": {**W, **p}})
specs = [S("event", "event", {}),
         S("plain_limit", "event_plain_limit", {"ug_capacity": 10, "ug_refill_per_s": 1.0}),
         S("plain_limit_tight", "event_plain_limit", {"ug_capacity": 5, "ug_refill_per_s": 0.3}),
         S("gate_r3", "event_ugs_gate", {}),
         S("gate_r31", "event_ugs_gate", {"ug_shift_tol": 1, "ug_shift_try": 192}),
         S("legacy_secure", "secure", {}),
         ("always_on", "always_on", {"common": C, "params": {}})]
root = os.path.join(lib31.D31, f"workloads_{a.split}_{a.thr:.2f}")
seeds = [int(x) for x in a.seeds.split(",")]
frames = []
with ProcessPoolExecutor(a.workers) as ex:
    for scen, ints in [("clean", [1.0]), ("noisy", [1.0]), ("spam", [0.5, 1, 2, 4, 8, 16]),
                       ("replay_exact", [1.0]), ("replay_perturbed", [1.0]), ("mixed", [1.0])]:
        frames.append(lib31.run_campaign(a.split, root, specs, [scen], ints, seeds, a.thr, executor=ex, datasets=tuple(a.datasets.split(","))))
import pandas as pd
pd.concat(frames).to_csv(a.out, index=False); print("done ->", a.out)
