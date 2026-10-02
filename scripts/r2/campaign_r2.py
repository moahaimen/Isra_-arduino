#!/usr/bin/env python3
"""Run an R2 real-frame campaign: build the matched workloads once, run every
operating mode on exactly the same workload (frames, GT, detector trace,
attack overlay), compute R2 metrics per (segment, run) and pool them per
realization (scenario, intensity, seed, mode).

  python3 scripts/r2/campaign_r2.py --split validation --out <dir> \
      --modes always_on,event,robust_event --scenarios clean,noisy --seeds 1-30 \
      --params results/r2/frozen_params.json

--params is a JSON object {"common": {...}, "<mode>": {...}} of simulator
parameter overrides (the frozen configuration of the test campaign).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import build_workloads as bw  # noqa: E402
import metrics_r2  # noqa: E402

SIM = os.path.join(ROOT, "build", "edge_sim")
R2_MODES = ["always_on", "motion_only", "fixed_threshold", "mog2_event", "event", "secure", "robust_event",
            "robust_secure"]
DATA = os.environ.get("R2_DATA", "/home/claude/data_r2")

_ctx = {}


def ctx_for(split: str, det_thr: float) -> metrics_r2.SplitContext:
    k = (split, det_thr)
    if k not in _ctx:
        _ctx[k] = metrics_r2.SplitContext(split, os.path.join(DATA, "bank"), os.path.join(DATA, "kitti"), det_thr,
                                          os.path.join(DATA, "cache"))
    return _ctx[k]


def parse_seeds(s: str) -> List[int]:
    if "-" in s and "," not in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def wl_dir(root: str, seg: str, sc: str, it: float, sd: int) -> str:
    return os.path.join(root, seg, sc, f"i{it:g}", f"s{sd}")


def _build_job(args):
    split, seg_idx, items, root, det_thr = args
    bank = _bank(split)
    pres = _pres(split)
    g = bw.segments(split)[seg_idx]
    for sc, it, sd in items:
        d = wl_dir(root, bw.seg_name(g), sc, it, sd)
        if os.path.exists(os.path.join(d, "side.csv")):
            continue
        bw.build(bank, pres, g, sc, it, sd, d, det_thr)
    return len(items)


_banks, _press = {}, {}


def _bank(split):
    if split not in _banks:
        _banks[split] = bw.Bank(os.path.join(DATA, "bank"), split)
    return _banks[split]


def _pres(split):
    if split not in _press:
        import kitti
        gt = kitti.load(os.path.join(DATA, "kitti"), split)["gt"]
        tr = bw.moving_tracks(gt)
        mv = {(int(r.seq), int(r.track_id), int(r.class_id)) for r in tr[tr.moving].itertuples()}
        _press[split] = bw.gt_presence(gt, mv)
    return _press[split]


def build_all(split, root, scenarios, intensities, seeds, det_thr, workers):
    jobs = []
    for i, g in enumerate(bw.segments(split)):
        items = []
        for sc in scenarios:
            for it in intensities:
                for sd in seeds:
                    items.append((sc, it, sd))
        # chunk per segment so each worker loads the bank once
        for k in range(0, len(items), 40):
            jobs.append((split, i, items[k:k + 40], root, det_thr))
    with ProcessPoolExecutor(workers) as ex:
        n = sum(ex.map(_build_job, jobs))
    return n


def sim_args(mode: str, params: Dict) -> List[str]:
    out = []
    for src in (params.get("common", {}), params.get(mode, {})):
        for k, v in src.items():
            if isinstance(v, bool):
                v = "true" if v else "false"
            out += [f"--{k.replace('_', '-')}", str(v)]
    return out


def run_one(wl: str, mode: str, params: Dict, split: str, det_thr: float) -> Dict:
    tmp = tempfile.mkdtemp(prefix="r2run_")
    try:
        cmd = [SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", mode,
               "--workload", os.path.join(wl, "wl.jsonl"), "--detector-backend", "trace_replay",
               "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
               "--detection-threshold", str(det_thr), "--log-level", "none", "--out-dir", tmp] + sim_args(mode, params)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"edge_sim failed ({' '.join(cmd)}): {r.stderr}")
        m = metrics_r2.run_metrics(tmp, wl, ctx_for(split, det_thr))
        cfg = open(os.path.join(tmp, "config.json"), "rb").read()
        m["config_sha256"] = hashlib.sha256(cfg).hexdigest()[:16]
        return m
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run_job(args):
    wl, modes, params, split, det_thr = args
    return [run_one(wl, md, params, split, det_thr) for md in modes]


def run_campaign(split, root, modes, scenarios, intensities, seeds, params, det_thr, workers) -> pd.DataFrame:
    jobs = []
    for g in bw.segments(split):
        for sc in scenarios:
            for it in intensities:
                for sd in seeds:
                    jobs.append((wl_dir(root, bw.seg_name(g), sc, it, sd), modes, params, split, det_thr))
    rows = []
    with ProcessPoolExecutor(workers) as ex:
        for res in ex.map(_run_job, jobs, chunksize=4):
            rows += res
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workloads", default="", help="workload root (default <out>/workloads)")
    ap.add_argument("--modes", default=",".join(R2_MODES))
    ap.add_argument("--scenarios", default="clean,noisy,spam,replay_exact,replay_perturbed,mixed")
    ap.add_argument("--intensities", default="1")
    ap.add_argument("--seeds", default="1-30")
    ap.add_argument("--params", default="")
    ap.add_argument("--det-thr", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    params = json.load(open(a.params)) if a.params else {}
    if "detection_threshold" in params.get("common", {}):
        a.det_thr = float(params["common"]["detection_threshold"])
    root = a.workloads or os.path.join(a.out, "workloads")
    scen = a.scenarios.split(",")
    ints = [float(x) for x in a.intensities.split(",")]
    seeds = parse_seeds(a.seeds)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    n = build_all(a.split, root, scen, ints, seeds, a.det_thr, a.workers)
    print(f"workloads ready: {n} ({time.time() - t0:.0f} s)", flush=True)
    t0 = time.time()
    df = run_campaign(a.split, root, a.modes.split(","), scen, ints, seeds, params, a.det_thr, a.workers)
    print(f"runs: {len(df)} ({time.time() - t0:.0f} s)", flush=True)
    df.to_csv(os.path.join(a.out, "runs_segments.csv"), index=False)
    pooled = metrics_r2.pool(df, ["mode", "scenario", "intensity", "seed"])
    pooled.to_csv(os.path.join(a.out, "runs_pooled.csv"), index=False)
    with open(os.path.join(a.out, "campaign.json"), "w") as fh:
        json.dump({"split": a.split, "modes": a.modes.split(","), "scenarios": scen, "intensities": ints,
                   "seeds": seeds, "params": params, "det_thr": a.det_thr, "n_runs": len(df),
                   "simulator": SIM}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
