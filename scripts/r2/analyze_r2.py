#!/usr/bin/env python3
"""Statistical analysis of the R2 test campaign exactly as pre-registered in
docs/PREREGISTERED_R2_ANALYSIS.md (confirmatory family C1-C11, secondary
families S1/S2), plus descriptive tables and figures.

  python3 scripts/r2/analyze_r2.py --campaign <dir with main/ and sweep/> --out results/r2/test
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

MODES = ["always_on", "motion_only", "mog2_event", "fixed_threshold", "event", "secure", "robust_event",
         "robust_secure"]
METRICS = ["timely_recall", "track_recall", "burst_timely_recall", "burst_recall", "mean_track_latency_ms",
           "duty_cycle", "energy_mJ", "energy_per_min_mJ", "attack_success", "spam_success", "replay_success",
           "replay_exact_success", "replay_pert_success", "session_success", "frr", "frr_object",
           "spoofed_detections", "mean_trigger_latency_ms", "processed", "wakes"]

# id, scenario, intensity, metric, a, b, direction (+1: a higher), kind, threshold
CONFIRMATORY = [
    ("C1", "noisy", 1.0, "timely_recall", "robust_event", "event", +1, "abs", 0.10),
    ("C2", "noisy", 1.0, "track_recall", "robust_event", "event", +1, "abs", 0.10),
    ("C3", "noisy", 1.0, "burst_timely_recall", "robust_event", "event", +1, "abs", 0.10),
    ("C4", "mixed", 1.0, "burst_timely_recall", "robust_secure", "secure", +1, "abs", 0.10),
    ("C5", "replay_exact", 1.0, "replay_exact_success", "robust_secure", "secure", -1, "abs", 0.10),
    ("C6", "replay_perturbed", 1.0, "replay_pert_success", "robust_secure", "secure", -1, "abs", 0.10),
    ("C7", "spam", 8.0, "frr", "robust_secure", "secure", -1, "abs", 0.10),
    ("C8", "spam", 8.0, "timely_recall", "robust_secure", "secure", +1, "abs", 0.10),
    ("C9", "spam", 8.0, "spam_success", "robust_secure", "secure", 0, "noninf", 0.05),
    ("C10", "noisy", 1.0, "duty_cycle", "robust_event", "always_on", -1, "ratio", 0.5),
    ("C11", "noisy", 1.0, "energy_mJ", "robust_event", "always_on", -1, "ratio", 0.6),
]


def nan_to_none(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def paired(df, scenario, intensity, metric, a, b):
    s = df[(df.scenario == scenario) & (np.isclose(df.intensity, intensity))]
    A = s[s["mode"] == a].set_index("seed")[metric]
    B = s[s["mode"] == b].set_index("seed")[metric]
    idx = A.index.intersection(B.index)
    return A.loc[idx].values.astype(float), B.loc[idx].values.astype(float)


def ci_mean_diff(d):
    d = d[~np.isnan(d)]
    ds = stats.describe(d)
    return ds["mean"], ds["ci95_low"], ds["ci95_high"]


def confirmatory(df):
    rows = []
    for cid, sc, it, met, a, b, direction, kind, thr in CONFIRMATORY:
        xa, xb = paired(df, sc, it, met, a, b)
        t = stats.paired_test(xa, xb)
        md, lo, hi = ci_mean_diff(xa - xb)
        rows.append({"id": cid, "scenario": sc, "intensity": it, "metric": met, "a": a, "b": b,
                     "mean_a": t["mean_a"], "mean_b": t["mean_b"], "mean_diff": md, "ci95_diff_low": lo,
                     "ci95_diff_high": hi, "median_diff": t["median_diff"], "rank_biserial": t["rank_biserial"],
                     "n_pairs": t["n_pairs"], "n_nonzero": t["n_nonzero"], "W": t["W"], "p_value": t["p_value"],
                     "direction": direction, "kind": kind, "threshold": thr})
    out = pd.DataFrame(rows)
    fam = out["id"] != "C9"
    out["p_holm"] = np.nan
    out.loc[fam, "p_holm"] = stats.holm(out.loc[fam, "p_value"].tolist())
    verdict = []
    for r in out.itertuples():
        if r.kind == "noninf":
            ok = (not math.isnan(r.ci95_diff_high)) and r.ci95_diff_high <= r.threshold
        else:
            sig = (not math.isnan(r.p_holm)) and r.p_holm < 0.05
            right_dir = (r.mean_diff > 0) if r.direction > 0 else (r.mean_diff < 0)
            if r.kind == "abs":
                size = abs(r.mean_diff) >= r.threshold
            else:
                size = r.mean_a <= r.threshold * r.mean_b
            ok = sig and right_dir and size
        verdict.append("CONFIRMED" if ok else "NOT CONFIRMED")
    out["verdict"] = verdict
    return out


def descriptive(df):
    rows = []
    for (sc, it, md), g in df.groupby(["scenario", "intensity", "mode"]):
        for met in METRICS:
            if met not in g:
                continue
            d = stats.describe(g[met].astype(float).values)
            rows.append({"scenario": sc, "intensity": it, "mode": md, "metric": met, **d})
    return pd.DataFrame(rows)


def secondary_s1(df):
    rows = []
    for sc, it in df.groupby(["scenario", "intensity"]).size().index:
        for other in MODES:
            if other == "robust_secure":
                continue
            for met in ("timely_recall", "track_recall", "duty_cycle", "energy_mJ", "attack_success"):
                xa, xb = paired(df, sc, it, met, "robust_secure", other)
                if len(xa) == 0 or np.all(np.isnan(xa)):
                    continue
                t = stats.paired_test(xa, xb)
                rows.append({"scenario": sc, "intensity": it, "metric": met, "a": "robust_secure", "b": other,
                             **{k: t[k] for k in ("mean_a", "mean_b", "mean_diff", "median_diff", "rank_biserial",
                                                  "n_nonzero", "p_value")}})
    out = pd.DataFrame(rows)
    out["p_holm"] = stats.holm(out["p_value"].tolist())
    return out


def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return str(x)
    return f"{x:.{nd}f}"


def pivot_table(desc, scenario, intensity, metrics, modes=MODES, nd=3):
    lines = ["| method | " + " | ".join(metrics) + " |", "|---|" + "---|" * len(metrics)]
    for md in modes:
        cells = []
        for met in metrics:
            r = desc[(desc.scenario == scenario) & np.isclose(desc.intensity, intensity) & (desc["mode"] == md) &
                     (desc.metric == met)]
            if len(r) == 0 or r.iloc[0]["n"] == 0:
                cells.append("n/a")
                continue
            r = r.iloc[0]
            if met.startswith("energy"):
                cells.append(f"{r['mean']:.0f} ± {r['std']:.0f}")
            elif met.endswith("_ms"):
                cells.append(f"{r['mean']:.0f} ± {r['std']:.0f}")
            else:
                cells.append(f"{r['mean']:.{nd}f} ± {r['std']:.{nd}f}")
        lines.append(f"| {md} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def figures(sweep, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mets = [("spam_success", "spam attack success"), ("timely_recall", "timely track recall"),
            ("frr", "false rejection rate"), ("duty_cycle", "M7 duty cycle (simulated)"),
            ("energy_per_min_mJ", "modeled energy (mJ/min)")]
    fig, axes = plt.subplots(1, len(mets), figsize=(4.0 * len(mets), 3.4))
    for ax, (m, title) in zip(axes, mets):
        for md in MODES:
            g = sweep[sweep["mode"] == md].groupby("intensity")[m]
            mu, sd, n = g.mean(), g.std(), g.count()
            if mu.isna().all():
                continue
            x = mu.index.values
            ci = 2.045 * sd / np.sqrt(n)
            ax.plot(x, mu.values, marker="o", ms=3, label=md)
            ax.fill_between(x, (mu - ci).values, (mu + ci).values, alpha=0.15)
        ax.set_xscale("symlog", linthresh=0.5)
        ax.set_xlabel("spam intensity (x)")
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_spam_sweep.png"), dpi=150)
    plt.close(fig)


def figure_main(desc, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    scen = ["clean", "noisy", "replay_exact", "replay_perturbed", "mixed"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, met in zip(axes, ["timely_recall", "duty_cycle", "attack_success"]):
        w = 0.1
        for k, md in enumerate(MODES):
            vals, errs = [], []
            for sc in scen:
                r = desc[(desc.scenario == sc) & (desc["mode"] == md) & (desc.metric == met)]
                vals.append(r["mean"].iloc[0] if len(r) and r["n"].iloc[0] else np.nan)
                errs.append(r["std"].iloc[0] if len(r) and r["n"].iloc[0] else 0)
            ax.bar(np.arange(len(scen)) + (k - 3.5) * w, vals, w, yerr=errs, label=md, capsize=1)
        ax.set_xticks(range(len(scen)))
        ax.set_xticklabels(scen, rotation=20, fontsize=8)
        ax.set_title(met, fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_main.png"), dpi=150)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "r2", "test"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    main_df = pd.read_csv(os.path.join(a.campaign, "main", "runs_pooled.csv"))
    sweep = pd.read_csv(os.path.join(a.campaign, "sweep", "runs_pooled.csv"))
    df = pd.concat([main_df, sweep], ignore_index=True)
    desc = descriptive(df)
    desc.to_csv(os.path.join(a.out, "descriptive.csv"), index=False)
    conf = confirmatory(df)
    conf.to_csv(os.path.join(a.out, "confirmatory.csv"), index=False)
    s1 = secondary_s1(df)
    s1.to_csv(os.path.join(a.out, "secondary_S1.csv"), index=False)
    figures(sweep, a.out)
    figure_main(desc, a.out)
    with open(os.path.join(a.out, "confirmatory.json"), "w") as fh:
        json.dump([{k: nan_to_none(v) for k, v in r.items()} for r in conf.to_dict("records")], fh, indent=1)
    print(conf[["id", "metric", "a", "b", "mean_a", "mean_b", "mean_diff", "p_holm", "verdict"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
