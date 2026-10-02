#!/usr/bin/env python3
"""R3.1 scheduler Pareto sweep (VALIDATION or DEVELOPMENT only), corrected tiled cost.
Variants x (a_on, z0) grid; each config evaluated once on all groups (clean + noisy); per-group pooled counts are stored so that
leave-one-group-out selection can be done afterwards. Never the test split."""
import argparse, itertools, json, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="validation"); ap.add_argument("--datasets", default="kitti")
ap.add_argument("--thr", type=float, default=0.45); ap.add_argument("--workers", type=int, default=3)
ap.add_argument("--seeds", default="1001,1002,1003"); ap.add_argument("--out", required=True)
a = ap.parse_args()
if a.split == "test": raise SystemExit("test locked")
base = json.load(open(os.path.join(lib31.ROOT, "results/r3/tuning/gateB_ugs_event.json")))["selected"]
V = {"r3": {}, "nn": {"ugs_noise_norm": 1}, "hold": {"ugs_hold_ms": 3000.0}, "vr": {"ugs_value_rule": 1},
     "all": {"ugs_noise_norm": 1, "ugs_hold_ms": 3000.0, "ugs_value_rule": 1}}
specs = []
for v, extra in V.items():
    for a_on, z0 in itertools.product([3.0, 4.5, 6.0, 8.0], [0.5, 1.0, 2.0]):
        p = {**base, **extra, "ugs_a_on": a_on, "ugs_z0": z0, "ugs_a_off": min(base.get("ugs_a_off", 2.0), a_on - 1)}
        specs.append((f"{v}|a{a_on:g}|z{z0:g}", "ugs_event", {"common": {"detection_threshold": a.thr}, "params": p}))
specs.append(("always_on", "always_on", {"common": {"detection_threshold": a.thr}, "params": {}}))
root = os.path.join(lib31.D31, f"workloads_{a.split}_{a.thr:.2f}")
seeds = [int(x) for x in a.seeds.split(",")]
with ProcessPoolExecutor(a.workers) as ex:
    df = lib31.run_campaign(a.split, root, specs, ["clean", "noisy"], [1.0], seeds, a.thr, executor=ex, datasets=tuple(a.datasets.split(",")))
os.makedirs(os.path.dirname(a.out), exist_ok=True)
df.to_csv(a.out, index=False)
print(len(df), "rows ->", a.out)
