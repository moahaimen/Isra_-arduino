#!/usr/bin/env python3
"""Secondary analysis S3 (exploratory): component ablations of robust_event
and robust_secure on the TEST split with the frozen parameters, on the same
workloads as the main campaign (noisy, mixed x1, replay_perturbed, spam x8;
seeds 1..30). Each ablation changes exactly one component."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_workloads as bw  # noqa: E402
import campaign_r2 as cr  # noqa: E402
import metrics_r2  # noqa: E402
from run_test_campaign import verify_frozen  # noqa: E402

ABLATIONS = {
    "robust_event": {
        "full": {},
        "basic_frontend": {"watcher_frontend": "basic"},
        "no_persistence": {"robust_persist_k": 1},
        "global_cooldown": {"content_cooldown": False},
        "fixed_threshold": {"robust_threshold": False},
    },
    "robust_secure": {
        "full": {},
        "no_replay_check": {"rg_replay": False},
        "no_content_bucket": {"rg_content_bucket": False},
        "no_global_bucket": {"rg_global_bucket": False},
        "no_emergency": {"rg_emergency": False},
    },
}
CONDS = [("noisy", 1.0), ("mixed", 1.0), ("replay_perturbed", 1.0), ("spam", 8.0)]


def job(args):
    wl, mode, label, params, det_thr = args
    m = cr.run_one(wl, mode, params, "test", det_thr)
    m["ablation"] = label
    return m


def main() -> int:
    out = os.path.join(cr.DATA, "test_campaign", "ablation")
    os.makedirs(out, exist_ok=True)
    frozen = verify_frozen()
    det_thr = float(frozen["common"]["detection_threshold"])
    root = os.path.join(cr.DATA, "test_campaign", "workloads")
    jobs = []
    for mode, abl in ABLATIONS.items():
        for label, over in abl.items():
            params = {"common": frozen["common"], mode: {**frozen[mode], **over}}
            for g in bw.segments("test"):
                for sc, it in CONDS:
                    for sd in range(1, 31):
                        jobs.append((cr.wl_dir(root, bw.seg_name(g), sc, it, sd), mode, label, params, det_thr))
    cr.build_all("test", root, sorted({c for c, _ in CONDS}), sorted({i for _, i in CONDS}), list(range(1, 31)),
                 det_thr, 4)
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(job, jobs, chunksize=8))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out, "runs_segments.csv"), index=False)
    pooled = metrics_r2.pool(df, ["mode", "ablation", "scenario", "intensity", "seed"])
    pooled.to_csv(os.path.join(out, "runs_pooled.csv"), index=False)
    with open(os.path.join(out, "campaign.json"), "w") as fh:
        json.dump({"ablations": ABLATIONS, "conditions": CONDS, "frozen_sha256": frozen["_frozen_sha256"],
                   "n_runs": len(df)}, fh, indent=1)
    print(f"ablation runs: {len(df)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
