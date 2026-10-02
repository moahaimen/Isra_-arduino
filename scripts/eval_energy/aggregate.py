#!/usr/bin/env python3
"""Aggregate per-run metrics of a campaign into CSV summaries and tables.

Usage:
    python3 scripts/eval_energy/aggregate.py results/campaigns/<campaign_id> [--kind main|ablation|sensitivity]

Outputs (in <campaign>/aggregate/):
    main:        results_summary.csv, scenario_level.csv, mode_level.csv,
                 paired_comparisons.csv, security.csv, energy.csv,
                 communication.csv, latency_cdf.csv, tables/*.csv|md
    ablation:    ablation.csv, ablation_paired.csv, tables/table_F_ablation.*
    sensitivity: sensitivity.csv, tables/table_G_sensitivity.*
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from metrics import load_observations  # noqa: E402
from stats import describe, holm, paired_test  # noqa: E402
import warnings  # noqa: E402

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

KEY_METRICS = [
    "duty_cycle", "wakeups", "energy_total_mJ", "energy_per_min_mJ", "energy_saving_vs_always_on",
    "energy_per_useful_detection_mJ", "energy_per_correct_detection_mJ", "energy_per_accepted_trigger_mJ",
    "energy_m4_mJ", "energy_m7_mJ", "security_energy_mJ",
    "episode_recall", "missed_episode_rate", "observation_recall", "useful_detections", "correct_detections",
    "onset_latency_ms_mean", "onset_latency_ms_median", "onset_latency_ms_p95", "onset_latency_ms_p99",
    "trigger_latency_ms_mean", "trigger_latency_ms_median", "trigger_latency_ms_std", "trigger_latency_ms_p90",
    "trigger_latency_ms_p95", "trigger_latency_ms_p99", "trigger_latency_ms_min", "trigger_latency_ms_max",
    "episode_latency_ms_mean", "episode_latency_ms_p95",
    "watcher_precision", "watcher_recall", "watcher_f1", "false_trigger_rate", "missed_event_rate",
    "trigger_precision",
    "detector_precision", "detector_recall", "detector_f1", "classification_accuracy", "conf_object_mean",
    "early_exit_rate", "second_pass_rate", "false_alarms", "false_alarms_attack", "false_alarms_per_hour",
    "background_false_alarms",
    "attack_attempts", "attacks_blocked", "attacks_accepted", "attack_detection_rate", "attack_success_rate",
    "attacks_reached_m7", "false_rejection_rate", "false_rejection_rate_object", "security_precision",
    "security_recall", "security_f1", "security_block_rate", "security_latency_overhead_ms",
    "block_rate_limit", "block_replay", "block_duplicate", "block_burst", "block_consistency_failure",
    "legit_object_suppressed_cooldown",
    "rpc_latency_ms_mean", "rpc_latency_ms_median", "rpc_latency_ms_p95", "rpc_latency_ms_p99",
    "queue_delay_ms_mean", "queue_delay_ms_p95", "rpc_drops", "rpc_drops_loss", "rpc_drops_queue_full",
    "throughput_results_per_min",
]

MODE_ORDER = ["always_on", "motion_only", "fixed_threshold", "event", "event_no_early_exit", "secure"]
SCENARIO_ORDER = ["quiet", "normal", "busy", "burst", "noisy", "trigger_spam", "replay", "mixed"]
ATTACK_SCENARIOS = ["trigger_spam", "replay", "mixed"]

PAIRED_METRICS = ["energy_total_mJ", "duty_cycle", "onset_latency_ms_p95", "episode_recall",
                  "false_alarms", "attack_success_rate", "false_rejection_rate_object"]
PAIRED_COMPARISONS = [("secure", "always_on"), ("secure", "motion_only"), ("secure", "fixed_threshold"),
                      ("secure", "event"), ("event", "fixed_threshold"), ("event", "event_no_early_exit"),
                      ("event", "always_on")]


def add_saving(df: pd.DataFrame, keys: List[str], ref_col: str = "mode", ref_val: str = "always_on") -> pd.DataFrame:
    """Modeled energy saving relative to always_on on the same workload."""
    ref = df[df[ref_col] == ref_val][keys + ["energy_total_mJ"]].rename(columns={"energy_total_mJ": "_e_ref"})
    out = df.merge(ref, on=keys, how="left").copy()
    out["energy_saving_vs_always_on"] = 1.0 - out["energy_total_mJ"] / out["_e_ref"]
    return out.drop(columns=["_e_ref"])


def summarize(df: pd.DataFrame, by: List[str], metrics: List[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        for m in metrics:
            if m not in g.columns:
                continue
            d = describe(pd.to_numeric(g[m], errors="coerce").tolist())
            for k, v in d.items():
                row[f"{m}__{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def order_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "scenario" in df.columns:
        df["scenario"] = pd.Categorical(df["scenario"], [s for s in SCENARIO_ORDER if s in set(df["scenario"])])
    if "mode" in df.columns:
        df["mode"] = pd.Categorical(df["mode"], [m for m in MODE_ORDER if m in set(df["mode"])])
    cols = [c for c in ("scenario", "mode") if c in df.columns]
    return df.sort_values(cols).reset_index(drop=True) if cols else df


def fmt_ci(row: pd.Series, m: str, scale: float = 1.0, digits: int = 3) -> str:
    mean = row.get(f"{m}__mean", math.nan)
    lo, hi = row.get(f"{m}__ci95_low", math.nan), row.get(f"{m}__ci95_high", math.nan)
    if mean is None or (isinstance(mean, float) and math.isnan(mean)):
        return "n/a"
    s = f"{mean * scale:.{digits}f}"
    if not (isinstance(lo, float) and math.isnan(lo)):
        s += f" ± {(hi - mean) * scale:.{digits}f}"
    return s


def write_table(df: pd.DataFrame, path_base: str, title: str, note: str) -> None:
    df.to_csv(path_base + ".csv", index=False)
    with open(path_base + ".md", "w") as fh:
        fh.write(f"# {title}\n\n{note}\n\n")
        cols = list(df.columns)
        fh.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
        for _, r in df.iterrows():
            fh.write("| " + " | ".join(str(r[c]) for c in cols) + " |\n")


TABLE_NOTE = ("Generated by scripts/eval_energy/aggregate.py from per_run/metrics.csv. Values are mean ± half-width "
              "of the 95% t confidence interval over seeds. Energy is MODELED (uncalibrated simulation-assumption "
              "power states); latencies are SIMULATED.")


def paired_comparisons(df: pd.DataFrame, comps, metrics, group_col: str = "mode") -> pd.DataFrame:
    rows = []
    for sc in [s for s in SCENARIO_ORDER if s in set(df["scenario"])]:
        sub = df[df["scenario"] == sc]
        for a, b in comps:
            A = sub[sub[group_col] == a].set_index("seed")
            B = sub[sub[group_col] == b].set_index("seed")
            seeds = sorted(set(A.index) & set(B.index))
            if not seeds:
                continue
            # Matched pairs must share the workload.
            same_wl = bool((A.loc[seeds, "workload_hash"].values == B.loc[seeds, "workload_hash"].values).all())
            for m in metrics:
                res = paired_test(A.loc[seeds, m].astype(float).values, B.loc[seeds, m].astype(float).values)
                rows.append({"scenario": sc, "a": a, "b": b, "metric": m, "same_workload": same_wl, **res})
    out = pd.DataFrame(rows)
    if len(out):
        # Family = all comparisons of one metric in one scenario (the
        # question "which modes differ on metric M in scenario S"). Holm is
        # applied within each family. A campaign-wide Holm correction is also
        # reported; with 10 seeds the smallest attainable exact two-sided
        # Wilcoxon p-value is 2/2^10 = 0.00195, so a campaign-wide correction
        # over hundreds of tests cannot reject any hypothesis by construction.
        out["p_holm"] = np.nan
        for _, idx in out.groupby(["scenario", "metric"]).groups.items():
            out.loc[idx, "p_holm"] = holm(out.loc[idx, "p_value"].tolist())
        out["p_holm_campaign"] = holm(out["p_value"].tolist())
        out["significant_holm_0.05"] = out["p_holm"] < 0.05
        out["significant_holm_campaign_0.05"] = out["p_holm_campaign"] < 0.05
    return out


def latency_cdf(cdir: str, df: pd.DataFrame, scenarios=("normal", "mixed", "busy")) -> pd.DataFrame:
    """Empirical CDF data of onset-to-result latency, pooled over seeds."""
    rows = []
    for sc in scenarios:
        for mode in MODE_ORDER:
            vals = []
            for rid in df[(df["scenario"] == sc) & (df["mode"] == mode)]["run_id"]:
                obs = load_observations(os.path.join(cdir, "raw", rid))
                d = obs[obs["result_delivered_ms"] >= 0]
                vals.extend((d["result_delivered_ms"] - d["timestamp_ms"]).tolist())
            if not vals:
                continue
            v = np.sort(np.asarray(vals))
            qs = np.linspace(0, 1, 201)
            for q in qs:
                rows.append({"scenario": sc, "mode": mode, "quantile": q,
                             "latency_ms": float(np.quantile(v, q)), "n": len(v)})
    return pd.DataFrame(rows)


def aggregate_main(cdir: str) -> None:
    agg = os.path.join(cdir, "aggregate")
    tdir = os.path.join(agg, "tables")
    os.makedirs(tdir, exist_ok=True)
    df = pd.read_csv(os.path.join(cdir, "per_run", "metrics.csv"))
    df = add_saving(df, ["scenario", "seed"])
    df.to_csv(os.path.join(agg, "results_summary.csv"), index=False)
    metrics = [m for m in KEY_METRICS if m in df.columns]
    sc = order_frame(summarize(df, ["scenario", "mode"], metrics))
    sc.to_csv(os.path.join(agg, "scenario_level.csv"), index=False)
    md = order_frame(summarize(df, ["mode"], metrics))
    md.to_csv(os.path.join(agg, "mode_level.csv"), index=False)
    pc = paired_comparisons(df, PAIRED_COMPARISONS, PAIRED_METRICS)
    pc.to_csv(os.path.join(agg, "paired_comparisons.csv"), index=False)
    sec_cols = ["scenario", "mode"] + [c for c in sc.columns if any(c.startswith(p) for p in (
        "attack_", "attacks_", "false_rejection", "security_", "block_", "legit_object_suppressed"))]
    sc[sec_cols].to_csv(os.path.join(agg, "security.csv"), index=False)
    en_cols = ["scenario", "mode"] + [c for c in sc.columns if c.startswith("energy_") or c.startswith("duty_cycle")]
    sc[en_cols].to_csv(os.path.join(agg, "energy.csv"), index=False)
    co_cols = ["scenario", "mode"] + [c for c in sc.columns if c.startswith("rpc_") or c.startswith("queue_")]
    sc[co_cols].to_csv(os.path.join(agg, "communication.csv"), index=False)
    latency_cdf(cdir, df).to_csv(os.path.join(agg, "latency_cdf.csv"), index=False)

    # ---------------- Table A: overall system performance (per scenario x mode)
    rows = []
    for _, r in sc.iterrows():
        rows.append({"scenario": r["scenario"], "mode": r["mode"], "n_seeds": int(r["duty_cycle__n"]),
                     "duty_cycle_%": fmt_ci(r, "duty_cycle", 100, 2),
                     "wakeups": fmt_ci(r, "wakeups", 1, 1),
                     "energy_per_hour_J": fmt_ci(r, "energy_per_min_mJ", 60 / 1000, 1),
                     "episode_recall": fmt_ci(r, "episode_recall", 1, 3),
                     "onset_latency_p95_ms": fmt_ci(r, "onset_latency_ms_p95", 1, 1),
                     "false_alarms_per_hour": fmt_ci(r, "false_alarms_per_hour", 1, 2)})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_A_overall"), "Table A - Overall system performance",
                TABLE_NOTE)
    # ---------------- Table B: detection / trigger quality (pooled over scenarios)
    rows = []
    for _, r in md.iterrows():
        rows.append({"mode": r["mode"], "n_runs": int(r["duty_cycle__n"]),
                     "watcher_precision": fmt_ci(r, "watcher_precision"), "watcher_recall": fmt_ci(r, "watcher_recall"),
                     "watcher_F1": fmt_ci(r, "watcher_f1"), "false_trigger_rate": fmt_ci(r, "false_trigger_rate"),
                     "detector_precision": fmt_ci(r, "detector_precision"),
                     "detector_recall": fmt_ci(r, "detector_recall"), "detector_F1": fmt_ci(r, "detector_f1"),
                     "class_accuracy": fmt_ci(r, "classification_accuracy"),
                     "episode_recall": fmt_ci(r, "episode_recall"), "early_exit_rate": fmt_ci(r, "early_exit_rate"),
                     "mAP": "not computed (no bounding-box data)"})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_B_detection_quality"),
                "Table B - Trigger and detection quality (pooled over all scenarios)", TABLE_NOTE)
    # ---------------- Table C: security performance (attack scenarios)
    rows = []
    for _, r in sc[sc["scenario"].isin(ATTACK_SCENARIOS)].iterrows():
        if r["mode"] == "always_on":
            continue
        rows.append({"scenario": r["scenario"], "mode": r["mode"],
                     "attack_attempts": fmt_ci(r, "attack_attempts", 1, 1),
                     "attack_success_rate": fmt_ci(r, "attack_success_rate"),
                     "attack_detection_rate": fmt_ci(r, "attack_detection_rate"),
                     "security_precision": fmt_ci(r, "security_precision"),
                     "security_F1": fmt_ci(r, "security_f1"),
                     "false_rejection_rate": fmt_ci(r, "false_rejection_rate"),
                     "FRR_real_objects": fmt_ci(r, "false_rejection_rate_object"),
                     "spoofed_detections": fmt_ci(r, "false_alarms_attack", 1, 2),
                     "episode_recall": fmt_ci(r, "episode_recall")})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_C_security"), "Table C - Security performance",
                TABLE_NOTE + " Attack success = fraction of attack observations that reached M7 detector execution.")
    # ---------------- Table D: modeled energy
    rows = []
    for _, r in sc.iterrows():
        rows.append({"scenario": r["scenario"], "mode": r["mode"],
                     "energy_per_hour_J": fmt_ci(r, "energy_per_min_mJ", 60 / 1000, 1),
                     "saving_vs_always_on_%": fmt_ci(r, "energy_saving_vs_always_on", 100, 1),
                     "M4_share_%": f"{100 * r['energy_m4_mJ__mean'] / r['energy_total_mJ__mean']:.1f}",
                     "energy_per_useful_detection_J": fmt_ci(r, "energy_per_useful_detection_mJ", 1 / 1000, 2),
                     "security_energy_J": fmt_ci(r, "security_energy_mJ", 1 / 1000, 4),
                     "duty_cycle_%": fmt_ci(r, "duty_cycle", 100, 2)})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_D_energy"), "Table D - Modeled energy", TABLE_NOTE)
    # ---------------- Table E: communication
    rows = []
    for _, r in sc.iterrows():
        if r["mode"] == "always_on":
            continue
        rows.append({"scenario": r["scenario"], "mode": r["mode"],
                     "rpc_mean_ms": fmt_ci(r, "rpc_latency_ms_mean", 1, 3),
                     "rpc_median_ms": fmt_ci(r, "rpc_latency_ms_median", 1, 3),
                     "rpc_p95_ms": fmt_ci(r, "rpc_latency_ms_p95", 1, 3),
                     "rpc_p99_ms": fmt_ci(r, "rpc_latency_ms_p99", 1, 3),
                     "queue_delay_mean_ms": fmt_ci(r, "queue_delay_ms_mean", 1, 2),
                     "queue_delay_p95_ms": fmt_ci(r, "queue_delay_ms_p95", 1, 2),
                     "drops": fmt_ci(r, "rpc_drops", 1, 2)})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_E_communication"), "Table E - Communication performance",
                TABLE_NOTE)
    # Significance summary for the paired comparisons.
    if len(pc):
        keep = pc[["scenario", "a", "b", "metric", "n_pairs", "n_nonzero", "mean_a", "mean_b", "median_diff",
                   "rank_biserial", "p_value", "p_holm", "significant_holm_0.05", "p_holm_campaign",
                   "same_workload"]].copy()
        for c in ("mean_a", "mean_b", "median_diff", "rank_biserial"):
            keep[c] = keep[c].map(lambda x: f"{x:.4g}")
        for c in ("p_value", "p_holm", "p_holm_campaign"):
            keep[c] = keep[c].map(lambda x: "n/a" if pd.isna(x) else f"{x:.4g}")
        write_table(keep, os.path.join(tdir, "table_paired_tests"), "Paired Wilcoxon signed-rank tests",
                    "Matched pairs = same scenario and seed (identical workload). p_holm: Holm correction within each "
                    "(scenario, metric) family of comparisons; p_holm_campaign: Holm over every row. "
                    "diff = a - b. Rank-biserial effect size in [-1, 1].")


def aggregate_ablation(cdir: str) -> None:
    agg = os.path.join(cdir, "aggregate")
    tdir = os.path.join(agg, "tables")
    os.makedirs(tdir, exist_ok=True)
    df = pd.read_csv(os.path.join(cdir, "per_run", "metrics.csv"))
    df = add_saving(df, ["scenario", "seed"], ref_col="label", ref_val="always_on")
    df["mode"] = df["label"]
    metrics = [m for m in KEY_METRICS if m in df.columns]
    s = summarize(df, ["scenario", "label"], metrics)
    s.to_csv(os.path.join(agg, "ablation.csv"), index=False)
    labels = [l for l in df["label"].unique() if l != "full_secure"]
    pc = paired_comparisons(df, [("full_secure", l) for l in labels],
                            ["energy_total_mJ", "episode_recall", "attack_success_rate", "false_rejection_rate_object",
                             "onset_latency_ms_p95"])
    pc.to_csv(os.path.join(agg, "ablation_paired.csv"), index=False)
    rows = []
    for _, r in s.iterrows():
        rows.append({"scenario": r["scenario"], "variant": r["label"],
                     "energy_per_hour_J": fmt_ci(r, "energy_per_min_mJ", 60 / 1000, 1),
                     "duty_cycle_%": fmt_ci(r, "duty_cycle", 100, 2),
                     "episode_recall": fmt_ci(r, "episode_recall"),
                     "onset_p95_ms": fmt_ci(r, "onset_latency_ms_p95", 1, 1),
                     "attack_success_rate": fmt_ci(r, "attack_success_rate"),
                     "FRR_real_objects": fmt_ci(r, "false_rejection_rate_object"),
                     "false_alarms_per_hour": fmt_ci(r, "false_alarms_per_hour", 1, 2)})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_F_ablation"), "Table F - Ablation results", TABLE_NOTE)


def aggregate_sensitivity(cdir: str) -> None:
    agg = os.path.join(cdir, "aggregate")
    tdir = os.path.join(agg, "tables")
    os.makedirs(tdir, exist_ok=True)
    df = pd.read_csv(os.path.join(cdir, "per_run", "metrics.csv"))
    df["sweep_value"] = pd.to_numeric(df["sweep_value"], errors="coerce")
    metrics = [m for m in KEY_METRICS if m in df.columns]
    s = summarize(df, ["sweep_param", "sweep_value", "scenario", "mode"], metrics)
    s = s.sort_values(["sweep_param", "scenario", "mode", "sweep_value"]).reset_index(drop=True)
    s.to_csv(os.path.join(agg, "sensitivity.csv"), index=False)
    rows = []
    for _, r in s.iterrows():
        rows.append({"parameter": r["sweep_param"], "value": r["sweep_value"], "scenario": r["scenario"],
                     "mode": r["mode"], "energy_per_hour_J": fmt_ci(r, "energy_per_min_mJ", 60 / 1000, 1),
                     "episode_recall": fmt_ci(r, "episode_recall"),
                     "onset_p95_ms": fmt_ci(r, "onset_latency_ms_p95", 1, 1),
                     "attack_success_rate": fmt_ci(r, "attack_success_rate"),
                     "attack_detection_rate": fmt_ci(r, "attack_detection_rate"),
                     "FRR_real_objects": fmt_ci(r, "false_rejection_rate_object"),
                     "rpc_drops": fmt_ci(r, "rpc_drops", 1, 2)})
    write_table(pd.DataFrame(rows), os.path.join(tdir, "table_G_sensitivity"), "Table G - Sensitivity analysis",
                TABLE_NOTE)


def energy_model_sensitivity(cdir: str, factors=(0.25, 0.5, 1.0, 2.0, 4.0)) -> pd.DataFrame:
    """Re-weight stored state times with scaled power assumptions (no re-simulation).

    Modeled energy is linear in the power parameters, so scaling a state's
    power and recomputing E = sum P_s T_s from the stored state times is exact.
    """
    df = pd.read_csv(os.path.join(cdir, "per_run", "metrics.csv"))
    import json
    with open(os.path.join(cdir, "config", "power_model.json")) as fh:
        pm = json.load(fh)["states"]
    rows = []
    for state in ("M4_MONITOR", "M7_INFERENCE", "M7_SLEEP", "M7_WAKEUP"):
        for f in factors:
            e = sum(df[f"time_{s}_ms"] * pm[s]["power_mW"] * (f if s == state else 1.0) / 1000.0 for s in pm)
            tmp = df[["scenario", "seed", "mode"]].copy()
            tmp["energy"] = e
            ref = tmp[tmp["mode"] == "always_on"][["scenario", "seed", "energy"]].rename(columns={"energy": "ref"})
            tmp = tmp.merge(ref, on=["scenario", "seed"])
            tmp["saving"] = 1.0 - tmp["energy"] / tmp["ref"]
            for (mode,), g in tmp.groupby(["mode"]):
                d = describe(g["saving"].tolist())
                rows.append({"state": state, "power_factor": f, "power_mW": pm[state]["power_mW"] * f, "mode": mode,
                             "saving_mean": d["mean"], "saving_ci95_low": d["ci95_low"],
                             "saving_ci95_high": d["ci95_high"], "n": d["n"]})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(cdir, "aggregate", "energy_model_sensitivity.csv"), index=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_dir")
    ap.add_argument("--kind", default="main", choices=["main", "ablation", "sensitivity"])
    a = ap.parse_args()
    if a.kind == "main":
        aggregate_main(a.campaign_dir)
        energy_model_sensitivity(a.campaign_dir)
    elif a.kind == "ablation":
        aggregate_ablation(a.campaign_dir)
    else:
        aggregate_sensitivity(a.campaign_dir)
    print(f"aggregated {a.campaign_dir} ({a.kind})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
