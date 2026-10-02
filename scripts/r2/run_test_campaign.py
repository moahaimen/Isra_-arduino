#!/usr/bin/env python3
"""Final R2 test campaign with the FROZEN parameters (run once).

Refuses to start unless results/r2/frozen_params.json matches the SHA-256
committed in results/r2/frozen_params.sha256 and that hash file is part of
the git history (i.e. the parameters were committed before this run).

Campaigns (all 8 modes, 5 test segments, seeds 1..30, matched workloads):
  main   clean, noisy, replay_exact, replay_perturbed, mixed   (intensity 1)
  sweep  spam at intensity 0, 0.5, 1, 2, 4, 8, 16
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import campaign_r2 as cr  # noqa: E402
import metrics_r2  # noqa: E402

FROZEN = os.path.join(ROOT, "results", "r2", "frozen_params.json")
LOCK = os.path.join(ROOT, "results", "r2", "frozen_params.sha256")
SEEDS = list(range(1, 31))
CAMPAIGNS = {
    "main": (["clean", "noisy", "replay_exact", "replay_perturbed", "mixed"], [1.0]),
    "sweep": (["spam"], [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]),
}


def verify_frozen() -> dict:
    h = hashlib.sha256(open(FROZEN, "rb").read()).hexdigest()
    want = open(LOCK).read().split()[0]
    if h != want:
        raise SystemExit(f"frozen_params.json hash {h} != committed {want}")
    r = subprocess.run(["git", "log", "--format=%H %cI", "-1", "--", "results/r2/frozen_params.sha256"], cwd=ROOT,
                       capture_output=True, text=True)
    if not r.stdout.strip():
        raise SystemExit("frozen_params.sha256 is not committed; commit the frozen parameters first")
    st = subprocess.run(["git", "status", "--porcelain", "--", "results/r2/frozen_params.json",
                         "results/r2/frozen_params.sha256"], cwd=ROOT, capture_output=True, text=True).stdout
    if st.strip():
        raise SystemExit("frozen parameter files have uncommitted changes")
    p = json.load(open(FROZEN))
    p["_frozen_sha256"] = h
    p["_frozen_commit"] = r.stdout.strip()
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(cr.DATA, "test_campaign"))
    ap.add_argument("--campaigns", default="main,sweep")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    params = verify_frozen()
    det_thr = float(params["common"]["detection_threshold"])
    for name in a.campaigns.split(","):
        scen, ints = CAMPAIGNS[name]
        out = os.path.join(a.out, name)
        os.makedirs(out, exist_ok=True)
        t0 = time.time()
        cr.build_all("test", os.path.join(a.out, "workloads"), scen, ints, SEEDS, det_thr, a.workers)
        df = cr.run_campaign("test", os.path.join(a.out, "workloads"), cr.R2_MODES, scen, ints, SEEDS, params,
                             det_thr, a.workers)
        df.to_csv(os.path.join(out, "runs_segments.csv"), index=False)
        metrics_r2.pool(df, ["mode", "scenario", "intensity", "seed"]).to_csv(
            os.path.join(out, "runs_pooled.csv"), index=False)
        with open(os.path.join(out, "campaign.json"), "w") as fh:
            json.dump({"split": "test", "campaign": name, "scenarios": scen, "intensities": ints, "seeds": SEEDS,
                       "modes": cr.R2_MODES, "frozen_sha256": params["_frozen_sha256"],
                       "frozen_commit": params["_frozen_commit"], "n_runs": len(df),
                       "wall_s": time.time() - t0}, fh, indent=1)
        print(f"{name}: {len(df)} runs in {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
