#!/usr/bin/env python3
"""R3 campaign runner: builds matched workloads once and runs every mode on
exactly the same frames / GT / detector trace / overlay. Used for
validation development (Gates B, C) and, after the freeze, the final test
campaign (scripts/r3/run_test_r3.py)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import build_workloads_r3 as bw  # noqa: E402
import data_r3  # noqa: E402
import metrics_r3  # noqa: E402

SIM = os.path.join(ROOT, "build", "edge_sim")
MODES = ["always_on", "motion_only", "fixed_threshold", "mog2_event", "event", "secure", "robust_event",
         "robust_secure", "ugs_event", "ugs_secure"]
_ctx, _bank, _pres = {}, {}, {}


def ctx(split, thr):
    if (split, thr) not in _ctx:
        c = metrics_r3.Context(split, thr)
        c.det_thr = thr
        _ctx[(split, thr)] = c
    return _ctx[(split, thr)]


def wl_dir(root, seg, sc, it, sd):
    return os.path.join(root, seg, sc, f"i{it:g}", f"s{sd}")


def _pres_for(split):
    if split not in _pres:
        from build_workloads import moving_tracks
        gt = data_r3.load(split, with_images=False)["gt"]
        tr = moving_tracks(gt)
        mv = {(int(r.seq), int(r.track_id), int(r.class_id)) for r in tr[tr.moving].itertuples()}
        _pres[split] = bw.presence(gt, mv)
    return _pres[split]


def _build_job(a):
    split, gi, items, root, thr = a
    if (split, thr) not in _bank:
        _bank[(split, thr)] = bw.Bank(split, thr)
    g = data_r3.segments(split)[gi]
    for sc, it, sd in items:
        d = wl_dir(root, data_r3.seg_name(g), sc, it, sd)
        if not os.path.exists(os.path.join(d, "side.csv")):
            bw.build(_bank[(split, thr)], _pres_for(split), g, sc, it, sd, d, thr)
    return len(items)


def build_all(split, root, scen, ints, seeds, thr, workers=4):
    jobs = []
    for i, _g in enumerate(data_r3.segments(split)):
        items = [(sc, it, sd) for sc in scen for it in ints for sd in seeds]
        for k in range(0, len(items), 30):
            jobs.append((split, i, items[k:k + 30], root, thr))
    with ProcessPoolExecutor(workers) as ex:
        return sum(ex.map(_build_job, jobs))


def sim_args(mode: str, params: Dict) -> List[str]:
    out = []
    for src in (params.get("common", {}), params.get(mode, {})):
        for k, v in src.items():
            if isinstance(v, bool):
                v = "true" if v else "false"
            out += [f"--{k.replace('_', '-')}", str(v)]
    return out


def run_one(wl, mode, params, split, thr, label=None):
    tmp = tempfile.mkdtemp(prefix="r3run_")
    try:
        sim_mode = params.get("_mode_of", {}).get(mode, mode)
        cmd = [SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", sim_mode,
               "--workload", os.path.join(wl, "wl.jsonl"), "--detector-backend", "trace_replay",
               "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
               "--detection-threshold", str(thr), "--log-level", "none", "--out-dir", tmp] + sim_args(mode, params)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"edge_sim failed: {' '.join(cmd)}\n{r.stderr}")
        m = metrics_r3.run_metrics(tmp, wl, ctx(split, thr))
        m["mode"] = label or mode
        m["config_sha256"] = hashlib.sha256(open(os.path.join(tmp, "config.json"), "rb").read()).hexdigest()[:16]
        return m
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run_job(a):
    wl, modes, params, split, thr = a
    return [run_one(wl, md, params, split, thr) for md in modes]


def run_campaign(split, root, modes, scen, ints, seeds, params, thr, workers=4, executor=None):
    jobs = [(wl_dir(root, data_r3.seg_name(g), sc, it, sd), modes, params, split, thr)
            for g in data_r3.segments(split) for sc in scen for it in ints for sd in seeds]
    rows = []
    if executor is not None:
        for res in executor.map(_run_job, jobs, chunksize=4):
            rows += res
    else:
        with ProcessPoolExecutor(workers) as ex:
            for res in ex.map(_run_job, jobs, chunksize=4):
                rows += res
    return pd.DataFrame(rows)


def parse_seeds(s):
    if "-" in s and "," not in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["development", "validation"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--scenarios", default="clean,noisy,spam,replay_exact,replay_perturbed,mixed")
    ap.add_argument("--intensities", default="1")
    ap.add_argument("--seeds", default="1001-1005")
    ap.add_argument("--params", default="")
    ap.add_argument("--det-thr", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    params = json.load(open(a.params)) if a.params else {}
    root = os.path.join(data_r3.DATA, f"workloads_{a.split}_{a.det_thr:.2f}")
    scen, ints, seeds = a.scenarios.split(","), [float(x) for x in a.intensities.split(",")], parse_seeds(a.seeds)
    build_all(a.split, root, scen, ints, seeds, a.det_thr, a.workers)
    df = run_campaign(a.split, root, a.modes.split(","), scen, ints, seeds, params, a.det_thr, a.workers)
    os.makedirs(a.out, exist_ok=True)
    df.to_csv(os.path.join(a.out, "runs_segments.csv"), index=False)
    metrics_r3.pool(df, ["mode", "scenario", "intensity", "seed"]).to_csv(os.path.join(a.out, "runs_pooled.csv"),
                                                                         index=False)
    print("runs", len(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
