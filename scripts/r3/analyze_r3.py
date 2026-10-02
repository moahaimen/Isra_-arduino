#!/usr/bin/env python3
"""R3 final analysis, driven by the pre-registered hypothesis file
results/r3/prereg_hypotheses.json (committed with
docs/PREREGISTERED_R3_FINAL.md before the test campaign).

Unit of replication: an overlay realization (seed) with all test segments
pooled (counts summed, then ratios); matched pairs across methods (identical
workloads). Utility retention UR = pooled recall(method) / pooled recall
(always_on) of the SAME realization; secure utility retention SUR = timely
recall under attack / timely recall of the same method on clean.

For each hypothesis: mean, SD, median, 95 % t-CI of A, B and A-B, paired
Wilcoxon signed-rank (two-sided), matched-pairs rank-biserial, Holm within the
declared family, and the declared practical-size criterion.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "eval_energy"))
import stats  # noqa: E402


def add_derived(pooled: pd.DataFrame) -> pd.DataFrame:
    """UR (vs always_on of the same scenario/intensity/seed) and SUR (vs the
    method's own clean result of the same seed; clean has no overlay, so its
    seed only changes simulated timing)."""
    p = pooled.copy()
    ao = p[p["mode"] == "always_on"].set_index(["scenario", "intensity", "seed"])
    for col, num in (("UR_timely", "tracks_timely"), ("UR_track", "tracks_detected"), ("UR_burst", "burst_timely"),
                     ("UR_frame", "frame_hits")):
        p[col] = [r[num] / ao.loc[(r.scenario, r.intensity, r.seed), num]
                  if (r.scenario, r.intensity, r.seed) in ao.index and ao.loc[(r.scenario, r.intensity, r.seed), num]
                  else np.nan for _, r in p.iterrows()]
    clean = p[p.scenario == "clean"].set_index(["mode", "seed"])["timely_recall"]
    p["SUR"] = [r.timely_recall / clean.loc[(r["mode"], r.seed)]
                if (r["mode"], r.seed) in clean.index and clean.loc[(r["mode"], r.seed)] else np.nan
                for _, r in p.iterrows()]
    return p


def paired(df, scenario, intensity, metric, a, b):
    s = df[(df.scenario == scenario) & np.isclose(df.intensity, intensity)]
    A = s[s["mode"] == a].set_index("seed")[metric]
    B = s[s["mode"] == b].set_index("seed")[metric]
    idx = A.index.intersection(B.index)
    return A.loc[idx].values.astype(float), B.loc[idx].values.astype(float)


def evaluate(df, hyps):
    rows = []
    for h in hyps:
        if h.get("b") is None:  # one-sample criterion on A (e.g. UR >= 0.90)
            xa, _ = paired(df, h["scenario"], h["intensity"], h["metric"], h["a"], h["a"])
            xb = np.full_like(xa, h["reference"])
        else:
            xa, xb = paired(df, h["scenario"], h["intensity"], h["metric"], h["a"], h["b"])
        t = stats.paired_test(xa, xb)
        da = stats.describe(xa)
        dd = stats.describe(xa - xb)
        rows.append({**h, "n": int(len(xa)), "mean_a": da["mean"], "sd_a": da["std"], "median_a": da["median"],
                     "ci_a": [da["ci95_low"], da["ci95_high"]], "mean_b": float(np.mean(xb)) if len(xb) else np.nan,
                     "mean_diff": dd["mean"], "ci_diff": [dd["ci95_low"], dd["ci95_high"]],
                     "median_diff": t["median_diff"], "rank_biserial": t["rank_biserial"],
                     "n_nonzero": t["n_nonzero"], "W": t["W"], "p": t["p_value"]})
    out = pd.DataFrame(rows)
    out["p_holm"] = np.nan
    for fam, g in out.groupby("family"):
        out.loc[g.index, "p_holm"] = stats.holm(g.p.tolist())
    verdict = []
    for r in out.itertuples():
        kind = r.criterion
        if kind == "noninferior_upper":      # upper CI of (A - B) <= margin
            ok = r.ci_diff[1] == r.ci_diff[1] and r.ci_diff[1] <= r.margin
        elif kind == "mean_at_least":        # mean A >= reference and lower CI of A >= reference - margin
            ok = r.mean_a >= r.reference and r.ci_a[0] >= r.reference - r.margin
        elif kind == "mean_at_most":
            ok = r.mean_a <= r.reference and r.ci_a[1] <= r.reference + r.margin
        else:                                # "greater"/"less" by >= margin, significant after Holm
            sig = r.p_holm == r.p_holm and r.p_holm < 0.05
            dirok = r.mean_diff > 0 if kind == "greater" else r.mean_diff < 0
            ok = sig and dirok and abs(r.mean_diff) >= r.margin
        verdict.append("CONFIRMED" if ok else "NOT CONFIRMED")
    out["verdict"] = verdict
    return out


def descriptive(df, metrics):
    rows = []
    for (sc, it, md), g in df.groupby(["scenario", "intensity", "mode"]):
        for m in metrics:
            if m in g:
                rows.append({"scenario": sc, "intensity": it, "mode": md, "metric": m,
                             **stats.describe(g[m].astype(float).values)})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pooled", nargs="+", required=True)
    ap.add_argument("--hypotheses", default=os.path.join(ROOT, "results", "r3", "prereg_hypotheses.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "r3", "test"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    df = add_derived(pd.concat([pd.read_csv(p) for p in a.pooled], ignore_index=True))
    df.to_csv(os.path.join(a.out, "pooled_with_ur.csv.gz"), index=False)
    hyps = json.load(open(a.hypotheses))["hypotheses"]
    res = evaluate(df, hyps)
    res.to_csv(os.path.join(a.out, "confirmatory.csv"), index=False)
    mets = ["track_recall", "timely_recall", "burst_recall", "burst_timely_recall", "frame_recall", "UR_timely",
            "UR_track", "UR_burst", "UR_frame", "SUR", "duty_cycle", "wakes", "energy_mJ", "energy_per_min_mJ",
            "energy_per_detected_track_mJ", "mean_track_latency_ms", "mean_trigger_latency_ms", "attack_success",
            "spam_success", "replay_exact_success", "replay_pert_success", "replay_shift_success", "frr",
            "gate_attack_detection"]
    descriptive(df, mets).to_csv(os.path.join(a.out, "descriptive.csv"), index=False)
    print(res[["id", "family", "metric", "a", "b", "mean_a", "mean_b", "mean_diff", "p_holm", "verdict"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
