#!/usr/bin/env python3
"""Tune every R2 method on the VALIDATION split only (never on test).

Procedure (docs/PREREGISTERED_R2_ANALYSIS.md, section "Tuning"), identical
for every method:

* conditions: clean, noisy, spam x1, spam x8, replay_exact, replay_perturbed,
  mixed x1; validation overlay seeds 1001..1010 (clean: 1001..1003, it has
  no overlay randomness), both validation segments, pooled per realization;
* objective J = mean_C timely_recall(C) - 0.5 * mean_C duty(C)
                - 0.5 * mean_{C attack} attack_success(C)
  (higher is better);
* search: coordinate descent over the method's declared parameter grid,
  starting from the R1 default configuration (secure variants start from the
  tuned watcher of their non-secure counterpart), two full passes, ties
  broken towards the earlier (default-side) grid value.

Writes results/r2/tuning/<method>.json and <method>_trace.csv.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import campaign_r2 as cr  # noqa: E402
import metrics_r2  # noqa: E402

CONDITIONS = [("clean", 1.0), ("noisy", 1.0), ("spam", 1.0), ("spam", 8.0), ("replay_exact", 1.0),
              ("replay_perturbed", 1.0), ("mixed", 1.0)]
VAL_SEEDS = list(range(1001, 1011))
CLEAN_SEEDS = [1001, 1002, 1003]
LAMBDA_DUTY, LAMBDA_ATTACK = 0.5, 0.5

WATCHER_FIXED = {"trigger_threshold": [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
                 "cooldown_ms": [500, 1000, 1500, 3000]}
GRIDS: Dict[str, Dict[str, List]] = {
    "always_on": {},
    "motion_only": {"motion_threshold": [0.10, 0.20, 0.30, 0.40, 0.55, 0.70, 0.85],
                    "cooldown_ms": [500, 1000, 1500, 3000]},
    "mog2_event": {"mog2_threshold": [0.0025, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16],
                   "cooldown_ms": [500, 1000, 1500, 3000]},
    "fixed_threshold": dict(WATCHER_FIXED),
    "event": {**WATCHER_FIXED, "adaptive_gain": [0.25, 0.5, 1.0, 2.0], "adaptive_noise_ref": [0.10, 0.15, 0.25]},
    "secure": {"rate_limit": [10, 20, 60, 120], "burst_threshold": [5, 10, 30, 60],
               "replay_feature_eps": [0.005, 0.01, 0.03, 0.05], "consistency_threshold": [0.0, 0.3, 0.5, 0.7],
               "duplicate_window_ms": [500, 2000]},
    "robust_event": {"robust_z_on": [2.0, 3.0, 4.0, 5.0, 6.0], "robust_theta_min": [0.10, 0.15, 0.20, 0.25, 0.30],
                     "robust_theta_max": [0.40, 0.45, 0.50, 0.55, 0.60, 0.70],
                     "robust_persist_k": [1, 2, 3], "content_cooldown_ms": [500, 1000, 2000, 3000],
                     "content_overlap_thr": [0.2, 0.3, 0.5]},
    # amended 2026-10-02 (docs/PREREGISTERED_R2_ANALYSIS.md, amendment 1): the
    # foreground-mask condition can be switched off (0.0), dHash grid extended
    # to small distances, fg_min tunable
    # The two replay-match parameters interact, so they form ONE joint
    # coordinate ("a|b": list of value pairs).
    "robust_secure": {"rg_fg_jaccard_thr|rg_dhash_max": [(j, h) for j in (0.0, 0.5, 0.6, 0.7, 0.8)
                                                         for h in (2, 4, 6, 8, 12, 16, 32)],
                      "rg_fg_min": [0, 12],
                      "rg_consistency_threshold": [0.0, 0.2, 0.3, 0.5],
                      "rg_content_capacity": [2, 3, 5], "rg_content_refill_per_s": [0.25, 0.5, 1.0],
                      "rg_global_capacity": [5, 10, 20], "rg_global_refill_per_s": [0.5, 1.0, 2.0],
                      "rg_z_emergency": [4.0, 6.0, 8.0]},
}
PARENT = {"secure": "event", "robust_secure": "robust_event"}
# mode-defining switches are not tunable
DEFAULTS = {m: {} for m in GRIDS}


def check_split(split: str) -> None:
    if split != "validation":
        print(f"refusing to tune on split '{split}': tuning uses the validation split only", file=sys.stderr)
        raise SystemExit(2)


def jobs_for(root: str, method: str, params: Dict, det_thr: float):
    import build_workloads as bw
    jobs = []
    for g in bw.segments("validation"):
        for sc, it in CONDITIONS:
            for sd in (CLEAN_SEEDS if sc == "clean" else VAL_SEEDS):
                jobs.append((cr.wl_dir(root, bw.seg_name(g), sc, it, sd), [method], {method: params, "common": {}},
                             "validation", det_thr))
    return jobs


def objective(pooled: pd.DataFrame) -> Dict:
    per = pooled.groupby(["scenario", "intensity"]).agg(
        timely=("timely_recall", "mean"), duty=("duty_cycle", "mean"), atk=("attack_success", "mean"),
        recall=("track_recall", "mean"), frr=("frr", "mean")).reset_index()
    atk = per[per.scenario != "clean"]
    atk = atk[atk.scenario != "noisy"]
    J = per.timely.mean() - LAMBDA_DUTY * per.duty.mean() - LAMBDA_ATTACK * atk.atk.mean()
    return {"J": float(J), "timely": float(per.timely.mean()), "duty": float(per.duty.mean()),
            "attack_success": float(atk.atk.mean()), "recall": float(per.recall.mean()),
            "per_condition": per.to_dict("records")}


def evaluate(ex, root, method, params, det_thr) -> Dict:
    rows = []
    for res in ex.map(cr._run_job, jobs_for(root, method, params, det_thr), chunksize=4):
        rows += res
    df = pd.DataFrame(rows)
    pooled = metrics_r2.pool(df, ["mode", "scenario", "intensity", "seed"])
    return objective(pooled)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--methods", default="always_on,motion_only,mog2_event,fixed_threshold,event,secure,"
                                         "robust_event,robust_secure")
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "r2", "tuning"))
    ap.add_argument("--workloads", default=os.path.join(cr.DATA, "workloads_validation"))
    ap.add_argument("--common", default=os.path.join(ROOT, "results", "r2", "tuning", "common.json"))
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    check_split(a.split)
    common = json.load(open(a.common)) if os.path.exists(a.common) else {}
    det_thr = float(common.get("detection_threshold", 0.5))
    os.makedirs(a.out, exist_ok=True)
    scen = sorted({c for c, _ in CONDITIONS})
    ints = sorted({i for _, i in CONDITIONS})
    t0 = time.time()
    cr.build_all("validation", a.workloads, scen, ints, sorted(set(VAL_SEEDS) | set(CLEAN_SEEDS)), det_thr, a.workers)
    print(f"validation workloads ready ({time.time() - t0:.0f} s)", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        for method in a.methods.split(","):
            params = dict(common.get("sim", {}))
            if method in PARENT:
                parent = json.load(open(os.path.join(a.out, f"{PARENT[method]}.json")))
                params.update(parent["best_params"])
            grid = GRIDS[method]
            cache: Dict[str, Dict] = {}
            trace = []

            def score(p):
                k = json.dumps(p, sort_keys=True)
                if k not in cache:
                    t1 = time.time()
                    cache[k] = evaluate(ex, a.workloads, method, p, det_thr)
                    trace.append({**{f"p_{kk}": vv for kk, vv in p.items()},
                                  **{kk: vv for kk, vv in cache[k].items() if kk != "per_condition"},
                                  "eval_s": time.time() - t1})
                return cache[k]["J"]

            best = dict(params)
            best_J = score(best)
            for _ in range(a.passes):
                for name, values in grid.items():
                    names = name.split("|")

                    def with_value(v):
                        p = dict(best)
                        for nm, x in zip(names, v if len(names) > 1 else (v,)):
                            p[nm] = x
                        return p

                    cand = [(score(with_value(v)), v) for v in values]
                    jb = max(c[0] for c in cand)
                    # ties: keep the current value if it is among the best, else the first best
                    cur = tuple(best.get(nm) for nm in names) if len(names) > 1 else best.get(name)
                    if not any(abs(c[0] - jb) < 1e-12 and c[1] == cur for c in cand):
                        best = with_value(next(c[1] for c in cand if abs(c[0] - jb) < 1e-12))
                    best_J = score(best)
                    print(f"{method}: {name} -> {[best.get(nm) for nm in names]}  J={best_J:.4f}", flush=True)
            res = cache[json.dumps(best, sort_keys=True)]
            out = {"method": method, "split": "validation", "best_params": best, "objective": res,
                   "grid": grid, "parent": PARENT.get(method), "conditions": CONDITIONS, "seeds": VAL_SEEDS,
                   "clean_seeds": CLEAN_SEEDS, "lambda_duty": LAMBDA_DUTY, "lambda_attack": LAMBDA_ATTACK,
                   "n_configs_evaluated": len(cache), "detection_threshold": det_thr}
            with open(os.path.join(a.out, f"{method}.json"), "w") as fh:
                json.dump(out, fh, indent=1)
            pd.DataFrame(trace).to_csv(os.path.join(a.out, f"{method}_trace.csv"), index=False)
            print(f"== {method}: J={res['J']:.4f} timely={res['timely']:.3f} duty={res['duty']:.3f} "
                  f"atk={res['attack_success']:.3f}  {best}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
