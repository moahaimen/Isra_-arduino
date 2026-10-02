#!/usr/bin/env python3
"""R3 validation-only parameter search with Pareto analysis (Gates B and C).

Identical procedure for every method (docs/R3_GATE_B.md):

Gate B (watcher / scheduler, no security):
  conditions  clean (seeds 1001-1003, no overlay randomness), noisy (1001-1010)
  per config  UR_timely = pooled timely-tracks(method) / pooled timely-tracks(always_on),
              UR_track analogous, duty = pooled M7 awake / pooled time, modeled energy
  selection   operating point = max UR_timely subject to duty <= DUTY_MAX (0.25),
              ties -> lower duty; the full (UR, duty) Pareto frontier is stored.
Gate C (security; watcher frozen at its Gate-B point):
  conditions  clean, noisy, spam x1, spam x8, replay_exact, replay_perturbed, mixed x1
  per config  SUR = timely recall under attack / timely recall of the same method on clean
              (pooled over attack conditions), FRR (legit requests blocked / evaluated),
              attack success
  selection   max SUR subject to FRR <= FRR_MAX (0.05), ties -> lower attack success.

Grids are full factorial (or a seeded random subset of MAX_CONFIGS when larger).
Refuses any split other than validation.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import campaign_r3 as cr  # noqa: E402
import data_r3  # noqa: E402
import metrics_r3  # noqa: E402

DUTY_MAX, FRR_MAX, MAX_CONFIGS = 0.25, 0.05, 120
SEEDS = list(range(1001, 1011))
CLEAN_SEEDS = [1001, 1002, 1003]
B_CONDS = [("clean", 1.0), ("noisy", 1.0)]
C_CONDS = [("clean", 1.0), ("noisy", 1.0), ("spam", 1.0), ("spam", 8.0), ("replay_exact", 1.0),
           ("replay_perturbed", 1.0), ("mixed", 1.0)]

GRIDS = {
    "motion_only": {"motion_threshold": [0.1, 0.2, 0.3, 0.4, 0.55, 0.7], "cooldown_ms": [300, 500, 1000, 2000]},
    "mog2_event": {"mog2_threshold": [0.0025, 0.005, 0.01, 0.02, 0.04, 0.08], "cooldown_ms": [300, 500, 1000, 2000]},
    "fixed_threshold": {"trigger_threshold": [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7],
                        "cooldown_ms": [300, 500, 1000, 2000]},
    "event": {"trigger_threshold": [0.25, 0.3, 0.4, 0.5, 0.6], "cooldown_ms": [300, 500, 1000, 2000],
              "adaptive_gain": [0.25, 0.5, 1.0, 2.0]},
    "robust_event": {"robust_z_on": [2, 3, 4, 5, 6], "robust_theta_max": [0.4, 0.5, 0.55, 0.6, 0.7],
                     "robust_theta_min": [0.1, 0.2, 0.3], "content_cooldown_ms": [500, 1000, 2000]},
    "ugs_event": {"ugs_z0": [0.5, 1.0, 2.0], "ugs_a_on": [4.5, 5.0, 6.0, 8.0], "ugs_dt_retry_ms": [200, 300, 500],
                  "ugs_dt_track_ms": [500, 1000, 2000], "ugs_k_retry": [2, 3, 5], "ugs_awake_factor": [0.5, 1.0]},
    # Gate C (watcher parameters inherited from the Gate-B point of the non-secure counterpart)
    "secure": {"rate_limit": [10, 20, 60, 120], "burst_threshold": [10, 30, 60],
               "replay_feature_eps": [0.005, 0.01, 0.03], "consistency_threshold": [0.0, 0.3, 0.5]},
    "robust_secure": {"rg_dhash_max": [2, 4, 6, 8], "rg_fg_jaccard_thr": [0.0, 0.7],
                      "rg_global_capacity": [5, 10, 20], "rg_global_refill_per_s": [0.5, 1.0, 2.0]},
    "ugs_secure": {"ug_k_match": [1, 2, 4, 8], "ug_k_jump": [2, 4, 8], "ug_margin": [1, 2, 4],
                   "ug_d_rel": [0.05, 0.08, 0.12], "ug_capacity": [5, 10, 20], "ug_refill_per_s": [1.0, 2.0]},
}
PARENT = {"secure": "event", "robust_secure": "robust_event", "ugs_secure": "ugs_event"}


def check_split(split: str) -> None:
    if split != "validation":
        raise SystemExit(f"refusing to tune on split '{split}'")


def configs(grid, seed=0):
    keys = list(grid)
    allc = [dict(zip(keys, v)) for v in itertools.product(*[grid[k] for k in keys])]
    if len(allc) > MAX_CONFIGS:
        random.Random(seed).shuffle(allc)
        allc = allc[:MAX_CONFIGS]
    return allc


def jobs(root, mode, params, conds, thr):
    out = []
    for g in data_r3.segments("validation"):
        for sc, it in conds:
            for sd in (CLEAN_SEEDS if sc == "clean" else SEEDS):
                out.append((cr.wl_dir(root, data_r3.seg_name(g), sc, it, sd), [mode], params, "validation", thr))
    return out


def run(ex, root, mode, params, conds, thr):
    rows = []
    for r in ex.map(cr._run_job, jobs(root, mode, params, conds, thr), chunksize=6):
        rows += r
    return pd.DataFrame(rows)


def tot(df, num, den):
    return df[num].sum() / df[den].sum() if df[den].sum() else float("nan")


def summarize_b(df, ref):
    d = df[df.scenario.isin(["clean", "noisy"])]
    r = ref[ref.scenario.isin(["clean", "noisy"])]
    return {"UR_timely": d.tracks_timely.sum() / r.tracks_timely.sum(),
            "UR_track": d.tracks_detected.sum() / r.tracks_detected.sum(),
            "UR_burst": d.burst_timely.sum() / max(1, r.burst_timely.sum()),
            "UR_frame": d.frame_hits.sum() / r.frame_hits.sum(),
            "timely_recall": tot(d, "tracks_timely", "moving_tracks"), "duty": d.m7_active_ms.sum() / (d.seconds.sum() * 1000),
            "energy_per_min_mJ": d.energy_mJ.sum() / (d.seconds.sum() / 60), "noisy_UR_timely":
                d[d.scenario == "noisy"].tracks_timely.sum() / r[r.scenario == "noisy"].tracks_timely.sum()}


def summarize_c(df, ref):
    s = summarize_b(df, ref)
    clean = df[df.scenario == "clean"]
    atk = df[~df.scenario.isin(["clean", "noisy"])]
    rc = tot(clean, "tracks_timely", "moving_tracks")
    # per attack condition: timely recall / clean timely recall, then mean
    surs = []
    for (sc, it), g in atk.groupby(["scenario", "intensity"]):
        surs.append(tot(g, "tracks_timely", "moving_tracks") / rc if rc else float("nan"))
    s.update({"SUR": float(np.nanmean(surs)), "SUR_min": float(np.nanmin(surs)),
              "FRR": tot(df, "legit_gate_blocked", "legit_gate_evaluated") if df.legit_gate_evaluated.sum() else 0.0,
              "attack_success": tot(atk, "attack_started", "attack_frames"),
              "duty_attack": atk.m7_active_ms.sum() / (atk.seconds.sum() * 1000)})
    return s


def pareto(df, x="duty", y="UR_timely"):
    d = df.sort_values([x, y], ascending=[True, False])
    best, keep = -1e9, []
    for i, r in d.iterrows():
        if r[y] > best + 1e-12:
            keep.append(i)
            best = r[y]
    return df.loc[keep].sort_values(x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--gate", choices=["B", "C"], required=True)
    ap.add_argument("--methods", required=True)
    ap.add_argument("--det-thr", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "r3", "tuning"))
    a = ap.parse_args()
    check_split(a.split)
    os.makedirs(a.out, exist_ok=True)
    conds = B_CONDS if a.gate == "B" else C_CONDS
    root = os.path.join(data_r3.DATA, f"workloads_validation_{a.det_thr:.2f}")
    t0 = time.time()
    cr.build_all("validation", root, sorted({c for c, _ in conds}), sorted({i for _, i in conds}),
                 sorted(set(SEEDS) | set(CLEAN_SEEDS)), a.det_thr, a.workers)
    print(f"workloads ready {time.time() - t0:.0f}s", flush=True)
    common = {"detection_threshold": a.det_thr}
    with ProcessPoolExecutor(a.workers) as ex:
        ref = run(ex, root, "always_on", {"common": common}, conds, a.det_thr)
        ref.to_csv(os.path.join(a.out, f"gate{a.gate}_always_on_runs.csv"), index=False)
        for method in a.methods.split(","):
            base = {}
            if a.gate == "C" and method in PARENT:
                base = json.load(open(os.path.join(a.out, f"gateB_{PARENT[method]}.json")))["selected"]
            rows = []
            for k, cfg in enumerate(configs(GRIDS[method])):
                p = {**base, **cfg}
                df = run(ex, root, method, {"common": common, method: p}, conds, a.det_thr)
                s = summarize_b(df, ref) if a.gate == "B" else summarize_c(df, ref)
                rows.append({**{f"p_{kk}": vv for kk, vv in p.items()}, **s})
                if (k + 1) % 10 == 0:
                    print(f"{method}: {k + 1} configs {time.time() - t0:.0f}s", flush=True)
            tab = pd.DataFrame(rows)
            tab.to_csv(os.path.join(a.out, f"gate{a.gate}_{method}_grid.csv"), index=False)
            if a.gate == "B":
                ok = tab[tab.duty <= DUTY_MAX]
                sel = (ok if len(ok) else tab).sort_values(["UR_timely", "duty"], ascending=[False, True]).iloc[0]
                pareto(tab).to_csv(os.path.join(a.out, f"gateB_{method}_pareto.csv"), index=False)
            else:
                ok = tab[tab.FRR <= FRR_MAX]
                sel = (ok if len(ok) else tab).sort_values(["SUR", "attack_success"], ascending=[False, True]).iloc[0]
                pareto(tab, "attack_success", "SUR").to_csv(os.path.join(a.out, f"gateC_{method}_pareto.csv"),
                                                            index=False)
            chosen = {k[2:]: (v.item() if hasattr(v, "item") else v) for k, v in sel.items() if k.startswith("p_")}
            res = {"method": method, "gate": a.gate, "split": "validation", "selected": chosen,
                   "selected_metrics": {k: float(v) for k, v in sel.items() if not k.startswith("p_")},
                   "constraint_met": bool(len(ok)), "n_configs": len(tab), "grid": GRIDS[method],
                   "rule": "max UR_timely s.t. duty<=0.25" if a.gate == "B" else "max SUR s.t. FRR<=0.05",
                   "det_thr": a.det_thr}
            json.dump(res, open(os.path.join(a.out, f"gate{a.gate}_{method}.json"), "w"), indent=1)
            print(f"== {method}: {json.dumps(res['selected_metrics'])} {chosen}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
