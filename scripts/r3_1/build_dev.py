#!/usr/bin/env python3
"""Build R3.1 development/validation workloads (clean + noisy utility conditions)
for the requested datasets. Never the test split."""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
ap = argparse.ArgumentParser()
ap.add_argument("--split", default="validation"); ap.add_argument("--datasets", default="kitti,meva")
ap.add_argument("--scenarios", default="clean,noisy"); ap.add_argument("--intensities", default="1")
ap.add_argument("--seeds", default="1001-1005"); ap.add_argument("--thr", type=float, default=0.45)
ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()
lo, hi = (a.seeds.split("-") + [a.seeds])[:2] if "-" in a.seeds else (a.seeds, a.seeds)
seeds = list(range(int(lo), int(hi) + 1))
root = os.path.join(lib31.D31, f"workloads_{a.split}_{a.thr:.2f}")
t = time.time()
n = lib31.build_all(a.split, root, a.scenarios.split(","), [float(x) for x in a.intensities.split(",")], seeds, a.thr, a.workers, tuple(a.datasets.split(",")))
print("built", n, f"{time.time()-t:.0f}s", root)
