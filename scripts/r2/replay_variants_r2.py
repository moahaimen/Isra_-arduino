#!/usr/bin/env python3
"""Secondary analysis S4: replay detection per perturbation variant, and the
gate's false rejection of legitimate frames, on the TEST replay workloads
of the main campaign (frozen parameters; secure vs robust_secure; plus the
robust_event baseline that has no gate).

For every replayed frame that reached the gate we record whether it was
blocked; detection rate = blocked / evaluated per variant, and the attack
success (frames that reached the M7) per variant.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import build_workloads as bw  # noqa: E402
import campaign_r2 as cr  # noqa: E402
from image_bank import VARIANTS  # noqa: E402
from run_test_campaign import verify_frozen  # noqa: E402

MODES = ["robust_event", "secure", "robust_secure"]


def job(args):
    wl, mode, params, det_thr = args
    tmp = tempfile.mkdtemp(prefix="r2s4_")
    try:
        cmd = [cr.SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", mode,
               "--workload", os.path.join(wl, "wl.jsonl"), "--detector-backend", "trace_replay",
               "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
               "--detection-threshold", str(det_thr), "--log-level", "none", "--out-dir", tmp] + \
            cr.sim_args(mode, params)
        subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
        o = pd.read_csv(os.path.join(tmp, "observations.csv"), keep_default_na=False)
        s = pd.read_csv(os.path.join(wl, "side.csv"))
        d = o[["event_id", "triggered", "sec_evaluated", "sec_accept", "sec_reason", "started"]].merge(
            s[["event_id", "attack_type", "variant"]], on="event_id")
        d["mode"] = mode
        d["workload"] = wl
        return d
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    frozen = verify_frozen()
    det_thr = float(frozen["common"]["detection_threshold"])
    root = os.path.join(cr.DATA, "test_campaign", "workloads")
    jobs = []
    for g in bw.segments("test"):
        for sc in ("replay_exact", "replay_perturbed"):
            for sd in range(1, 31):
                for m in MODES:
                    jobs.append((cr.wl_dir(root, bw.seg_name(g), sc, 1.0, sd), m,
                                 {"common": frozen["common"], m: frozen[m]}, det_thr))
    with ProcessPoolExecutor(4) as ex:
        d = pd.concat(list(ex.map(job, jobs, chunksize=8)), ignore_index=True)
    rep = d[d.attack_type == "replay"]
    rows = []
    for (m, v), g in rep.groupby(["mode", "variant"]):
        ev = g[g.sec_evaluated == 1]
        rows.append({"mode": m, "variant": int(v), "variant_name": VARIANTS[int(v)], "replay_frames": len(g),
                     "watcher_triggered": int(g.triggered.sum()), "gate_evaluated": len(ev),
                     "gate_blocked": int((ev.sec_accept == 0).sum()),
                     "gate_blocked_as_replay": int((ev.sec_reason == "REPLAY").sum()),
                     "gate_detection_rate": (ev.sec_accept == 0).mean() if len(ev) else float("nan"),
                     "reached_m7": int(g.started.sum()), "attack_success": g.started.mean()})
    out = os.path.join(ROOT, "results", "r2", "test")
    os.makedirs(out, exist_ok=True)
    tab = pd.DataFrame(rows)
    tab.to_csv(os.path.join(out, "replay_variants.csv"), index=False)
    leg = d[(d.attack_type == "none") & (d.sec_evaluated == 1)]
    frr = leg.groupby("mode").apply(lambda g: pd.Series({"legit_evaluated": len(g),
                                                          "legit_blocked": int((g.sec_accept == 0).sum()),
                                                          "frr": (g.sec_accept == 0).mean(),
                                                          "legit_blocked_as_replay": int((g.sec_reason == "REPLAY").sum())}))
    frr.to_csv(os.path.join(out, "replay_scenarios_frr.csv"))
    print(tab.round(3).to_string())
    print(frr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
