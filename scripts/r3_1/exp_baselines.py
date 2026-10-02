#!/usr/bin/env python3
"""R3.1 baseline Pareto sweep under the corrected tiled cost (validation/development only): the R3 grids of the simple
baselines (motion_only, mog2_event, fixed_threshold, event, robust_event), same workloads/seeds as exp_sched.py."""
import argparse, os, sys, itertools, random
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r3"))
import lib31, tune_r3
ap = argparse.ArgumentParser()
ap.add_argument("--split", default="validation"); ap.add_argument("--datasets", default="kitti")
ap.add_argument("--thr", type=float, default=0.45); ap.add_argument("--workers", type=int, default=3)
ap.add_argument("--seeds", default="1001,1002,1003"); ap.add_argument("--out", required=True)
ap.add_argument("--cap", type=int, default=36)
a = ap.parse_args()
if a.split == "test": raise SystemExit("test locked")
specs = []
for m in ["motion_only", "mog2_event", "fixed_threshold", "event", "robust_event"]:
    for i, c in enumerate(tune_r3.configs(tune_r3.GRIDS[m], cap=a.cap)):
        specs.append((f"{m}|{i}|" + ",".join(f"{k}={v}" for k, v in c.items()), m, {"common": {"detection_threshold": a.thr}, "params": c}))
specs.append(("always_on", "always_on", {"common": {"detection_threshold": a.thr}, "params": {}}))
root = os.path.join(lib31.D31, f"workloads_{a.split}_{a.thr:.2f}")
with ProcessPoolExecutor(a.workers) as ex:
    df = lib31.run_campaign(a.split, root, specs, ["clean", "noisy"], [1.0], [int(x) for x in a.seeds.split(",")], a.thr, executor=ex, datasets=tuple(a.datasets.split(",")))
df.to_csv(a.out, index=False); print(len(df), "rows ->", a.out)
