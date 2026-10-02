#!/usr/bin/env python3
"""Publication figures, drawn ONLY from stored campaign CSV files.

matplotlib only (no seaborn). Each figure is saved as PNG (300 dpi) and PDF
(vector). Every figure reads the aggregate CSVs written by aggregate.py, so
it can be regenerated at any time with:

    python3 scripts/eval_energy/plots.py <main_campaign> [--ablation <dir>] [--sensitivity <dir>]
"""
from __future__ import annotations

import argparse
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import warnings  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aggregate import ATTACK_SCENARIOS, MODE_ORDER, SCENARIO_ORDER  # noqa: E402

# Validated categorical palette (fixed order, one hue per mode).
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#008300", "#e34948"]
MODE_COLOR = {m: PALETTE[i] for i, m in enumerate(MODE_ORDER)}
MODE_LABEL = {"always_on": "always-on", "motion_only": "motion-only", "fixed_threshold": "fixed-threshold",
              "event": "event (proposed)", "event_no_early_exit": "event, no early exit",
              "secure": "secure (proposed)"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "savefig.bbox": "tight", "pdf.fonttype": 42,
})

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

FOOT = "Simulated; energy is modeled from uncalibrated power assumptions."


def save(fig, outdir: str, name: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    fig.savefig(os.path.join(outdir, name + ".png"), dpi=300)
    fig.savefig(os.path.join(outdir, name + ".pdf"))
    plt.close(fig)


def _err(df, m, scale=1.0):
    mean = df[f"{m}__mean"].values * scale
    hi = df[f"{m}__ci95_high"].values * scale
    e = np.where(np.isnan(hi), 0.0, hi - mean)
    return mean, e


def grouped_bars(ax, sc: pd.DataFrame, metric: str, modes, scenarios, scale=1.0, log=False):
    width = 0.8 / len(modes)
    x = np.arange(len(scenarios))
    for i, mode in enumerate(modes):
        sub = sc[sc["mode"] == mode].set_index("scenario").reindex(scenarios)
        mean, e = _err(sub.reset_index(), metric, scale)
        ax.bar(x + (i - (len(modes) - 1) / 2) * width, mean, width * 0.92, yerr=e, color=MODE_COLOR[mode],
               label=MODE_LABEL[mode], error_kw={"elinewidth": 0.7, "capsize": 1.5, "ecolor": MUTED})
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios])
    if log:
        ax.set_yscale("log")


def plot_main(cdir: str) -> None:
    agg = os.path.join(cdir, "aggregate")
    out = os.path.join(cdir, "figures")
    sc = pd.read_csv(os.path.join(agg, "scenario_level.csv"))
    scenarios = [s for s in SCENARIO_ORDER if s in set(sc["scenario"])]
    modes = [m for m in MODE_ORDER if m in set(sc["mode"])]

    # 1 duty cycle
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    grouped_bars(ax, sc, "duty_cycle", modes, scenarios, 100, log=True)
    ax.set_ylabel("M7 duty cycle (%, log scale)")
    ax.set_title("Fig. 1  Detector duty cycle by scenario and mode (mean, 95% CI)")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    save(fig, out, "fig01_duty_cycle")

    # 2 modeled energy
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    grouped_bars(ax, sc, "energy_per_min_mJ", modes, scenarios, 60 / 1000)
    ax.set_ylabel("Modeled energy per hour (J)")
    ax.set_title("Fig. 2  Modeled energy by scenario and mode (mean, 95% CI)")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.text(0.01, -0.12, FOOT, fontsize=7, color=MUTED)
    save(fig, out, "fig02_modeled_energy")

    # 3 latency CDF
    cdf = pd.read_csv(os.path.join(agg, "latency_cdf.csv"))
    cdf_sc = [s for s in ("normal", "mixed", "busy") if s in set(cdf["scenario"])]
    if cdf_sc:
        fig, axes = plt.subplots(1, len(cdf_sc), figsize=(7.2, 2.6), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, s in zip(axes, cdf_sc):
            for mode in modes:
                d = cdf[(cdf["scenario"] == s) & (cdf["mode"] == mode)]
                if len(d):
                    ax.plot(d["latency_ms"], d["quantile"], color=MODE_COLOR[mode], lw=1.6, label=MODE_LABEL[mode])
            ax.set_xscale("log")
            ax.set_title(s)
            ax.set_xlabel("Onset-to-result latency (ms)")
        axes[0].set_ylabel("Empirical CDF")
        axes[-1].legend(frameon=False, fontsize=7, loc="lower right")
        fig.suptitle("Fig. 3  Latency CDF (pooled over seeds)", y=1.02)
        save(fig, out, "fig03_latency_cdf")

    # 4 p95 latency
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    grouped_bars(ax, sc, "onset_latency_ms_p95", modes, scenarios)
    ax.set_ylabel("p95 onset-to-result latency (ms)")
    ax.set_title("Fig. 4  95th-percentile latency (mean over seeds, 95% CI)")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    save(fig, out, "fig04_p95_latency")

    # 5 trigger precision / recall / F1. event, event_no_early_exit and secure
    # share the same (adaptive) watcher, so only distinct watchers are shown.
    trig_modes = [m for m in ("motion_only", "fixed_threshold", "event") if m in modes]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.6), sharex=True)
    for ax, (m, lab) in zip(axes, [("watcher_precision", "Precision"), ("watcher_recall", "Recall"),
                                   ("watcher_f1", "F1")]):
        grouped_bars(ax, sc, m, trig_modes, scenarios)
        ax.set_ylabel(f"Trigger {lab.lower()}")
        ax.set_ylim(0, 1.05)
    from matplotlib.container import BarContainer
    bars = [c for c in axes[0].containers if isinstance(c, BarContainer)]
    axes[0].legend(handles=bars,
                   labels=["motion-only", "fixed threshold", "adaptive score (event / secure)"][:len(trig_modes)],
                   ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.35))
    fig.suptitle("Fig. 5  Watcher trigger quality, observation level (mean, 95% CI)", y=1.0)
    save(fig, out, "fig05_trigger_quality")

    # 6 attack detection performance (secure mode, attack scenarios)
    att = [s for s in ATTACK_SCENARIOS if s in scenarios]
    if att and "secure" in modes:
        sub = sc[(sc["mode"] == "secure")].set_index("scenario").reindex(att).reset_index()
        metrics = [("attack_detection_rate", "Attack detection rate"), ("security_precision", "Security precision"),
                   ("security_f1", "Security F1"), ("false_rejection_rate", "False rejection rate"),
                   ("false_rejection_rate_object", "FRR (real objects)")]
        fig, ax = plt.subplots(figsize=(7.2, 2.8))
        x = np.arange(len(att))
        w = 0.8 / len(metrics)
        for i, (m, lab) in enumerate(metrics):
            mean, e = _err(sub, m)
            ax.bar(x + (i - (len(metrics) - 1) / 2) * w, mean, w * 0.92, yerr=e, color=PALETTE[i], label=lab,
                   error_kw={"elinewidth": 0.7, "capsize": 1.5, "ecolor": MUTED})
        ax.set_xticks(x)
        ax.set_xticklabels(att)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Rate")
        ax.set_title("Fig. 6  Security-gate performance, secure mode (gate-level, mean, 95% CI)")
        ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=7)
        save(fig, out, "fig06_attack_detection")

    # 8 energy vs latency trade-off
    md = pd.read_csv(os.path.join(agg, "mode_level.csv"))
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for mode in modes:
        d = sc[sc["mode"] == mode]
        ax.scatter(d["onset_latency_ms_p95__mean"], d["energy_per_min_mJ__mean"] * 60 / 1000, s=22,
                   color=MODE_COLOR[mode], label=MODE_LABEL[mode], edgecolor="white", linewidth=0.8)
    ax.set_yscale("log")
    ax.set_xlabel("p95 onset-to-result latency (ms)")
    ax.set_ylabel("Modeled energy per hour (J, log)")
    ax.set_title("Fig. 8  Energy-latency trade-off\n(one point per scenario)")
    ax.legend(frameon=False, fontsize=7)
    save(fig, out, "fig08_energy_latency_tradeoff")

    # 9 detection quality vs energy
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for mode in modes:
        d = sc[sc["mode"] == mode]
        ax.scatter(d["energy_per_min_mJ__mean"] * 60 / 1000, d["episode_recall__mean"], s=22,
                   color=MODE_COLOR[mode], label=MODE_LABEL[mode], edgecolor="white", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("Modeled energy per hour (J, log)")
    ax.set_ylabel("Object-episode recall")
    ax.set_title("Fig. 9  Detection quality vs modeled energy\n(one point per scenario)")
    ax.legend(frameon=False, fontsize=7)
    save(fig, out, "fig09_quality_vs_energy")
    _ = md


def _sweep_lines(ax, s, param, scenario, metric, modes, scale=1.0):
    for mode in modes:
        d = s[(s["sweep_param"] == param) & (s["scenario"] == scenario) & (s["mode"] == mode)].sort_values(
            "sweep_value")
        if not len(d):
            continue
        mean = d[f"{metric}__mean"] * scale
        lo, hi = d[f"{metric}__ci95_low"] * scale, d[f"{metric}__ci95_high"] * scale
        ax.plot(d["sweep_value"], mean, marker="o", ms=4, lw=1.6, color=MODE_COLOR.get(mode, INK),
                label=MODE_LABEL.get(mode, mode))
        ax.fill_between(d["sweep_value"], lo, hi, color=MODE_COLOR.get(mode, INK), alpha=0.12, lw=0)


def plot_sensitivity(cdir: str) -> None:
    s = pd.read_csv(os.path.join(cdir, "aggregate", "sensitivity.csv"))
    out = os.path.join(cdir, "figures")
    params = set(s["sweep_param"])
    # 7 security effectiveness vs attack intensity
    if "attack_intensity" in params:
        scen = [x for x in ATTACK_SCENARIOS if x in set(s[s["sweep_param"] == "attack_intensity"]["scenario"])]
        fig, axes = plt.subplots(2, len(scen), figsize=(7.2, 4.6), sharex=True, squeeze=False)
        for j, sc in enumerate(scen):
            _sweep_lines(axes[0, j], s, "attack_intensity", sc, "attack_success_rate",
                         ["fixed_threshold", "event", "secure"])
            _sweep_lines(axes[1, j], s, "attack_intensity", sc, "attack_detection_rate", ["secure"])
            axes[0, j].set_title(sc)
            axes[1, j].set_xlabel("Attack intensity (x default)")
            axes[0, j].set_ylim(-0.02, 1.02)
            axes[1, j].set_ylim(-0.02, 1.02)
        axes[0, 0].set_ylabel("Attack success rate")
        axes[1, 0].set_ylabel("Attack detection rate\n(secure gate)")
        axes[0, -1].legend(frameon=False, fontsize=7)
        fig.suptitle("Fig. 7  Security effectiveness vs attack intensity (mean, 95% CI)", y=1.01)
        save(fig, out, "fig07_security_vs_intensity")
        # 11 attack-intensity sensitivity: energy and recall
        fig, axes = plt.subplots(2, len(scen), figsize=(7.2, 4.6), sharex=True, squeeze=False)
        for j, sc in enumerate(scen):
            _sweep_lines(axes[0, j], s, "attack_intensity", sc, "energy_per_min_mJ",
                         ["fixed_threshold", "event", "secure"], 60 / 1000)
            _sweep_lines(axes[1, j], s, "attack_intensity", sc, "episode_recall",
                         ["fixed_threshold", "event", "secure"])
            axes[0, j].set_title(sc)
            axes[1, j].set_xlabel("Attack intensity (x default)")
        axes[0, 0].set_ylabel("Modeled energy per hour (J)")
        axes[1, 0].set_ylabel("Object-episode recall")
        axes[0, -1].legend(frameon=False, fontsize=7)
        fig.suptitle("Fig. 11  Attack-intensity sensitivity (mean, 95% CI)", y=1.01)
        save(fig, out, "fig11_attack_intensity_sensitivity")
    # 10 threshold sensitivity
    if "trigger_threshold" in params:
        scen = sorted(set(s[s["sweep_param"] == "trigger_threshold"]["scenario"]),
                      key=lambda x: SCENARIO_ORDER.index(x))
        modes = ["fixed_threshold", "event", "secure"]
        fig, axes = plt.subplots(3, len(scen), figsize=(7.2, 6.0), sharex=True, squeeze=False)
        for j, sc in enumerate(scen):
            _sweep_lines(axes[0, j], s, "trigger_threshold", sc, "watcher_precision", modes)
            _sweep_lines(axes[1, j], s, "trigger_threshold", sc, "episode_recall", modes)
            _sweep_lines(axes[2, j], s, "trigger_threshold", sc, "energy_per_min_mJ", modes, 60 / 1000)
            axes[0, j].set_title(sc)
            axes[2, j].set_xlabel("Trigger threshold θ")
        axes[0, 0].set_ylabel("Trigger precision")
        axes[1, 0].set_ylabel("Episode recall")
        axes[2, 0].set_ylabel("Energy per hour (J)")
        axes[0, -1].legend(frameon=False, fontsize=7)
        fig.suptitle("Fig. 10  Trigger-threshold sensitivity (mean, 95% CI)", y=1.0)
        save(fig, out, "fig10_threshold_sensitivity")
    # Supplementary sweeps: one panel per remaining parameter.
    other = [p for p in sorted(params) if p not in ("attack_intensity", "trigger_threshold")]
    if other:
        n = len(other)
        cols = 3
        rows = math.ceil(n / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(7.2, 2.2 * rows), squeeze=False)
        for k, p in enumerate(other):
            ax = axes[k // cols, k % cols]
            # (scenario, metric) shown for each swept parameter.
            sc, metric = {
                "rpc_latency_ms": ("busy", "trigger_latency_ms_p95"), "rpc_jitter_ms": ("busy", "trigger_latency_ms_p95"),
                "rpc_loss": ("normal", "episode_recall"), "rpc_queue_capacity": ("busy", "rpc_drops"),
                "inference_ms": ("normal", "energy_per_min_mJ"), "cooldown_ms": ("normal", "episode_recall"),
                "early_exit_threshold": ("normal", "episode_recall"), "arrival_scale": ("normal", "energy_per_min_mJ"),
                "consistency_threshold": ("trigger_spam", "attack_success_rate"),
                "rate_limit": ("busy", "false_rejection_rate_object"),
                "burst_threshold": ("burst", "false_rejection_rate_object"),
                "replay_window_ms": ("replay", "attack_success_rate"),
            }.get(p, (sorted(set(s[s["sweep_param"] == p]["scenario"]))[0], "energy_per_min_mJ"))
            modes = [m for m in MODE_ORDER if m in set(s[s["sweep_param"] == p]["mode"])]
            scale = 0.06 if metric == "energy_per_min_mJ" else 1.0
            _sweep_lines(ax, s, p, sc, metric, modes, scale)
            ax.set_title(f"{p} ({sc})", fontsize=8)
            label = "energy per hour (J)" if scale != 1.0 else metric.replace("_", " ")
            ax.set_ylabel(label, fontsize=7)
            if p == "inference_ms" or p == "arrival_scale":
                ax.set_yscale("log")
        for k in range(n, rows * cols):
            axes[k // cols, k % cols].axis("off")
        axes[0, 0].legend(frameon=False, fontsize=6)
        fig.suptitle("Supplementary: one-at-a-time parameter sweeps (mean, 95% CI)", y=1.0)
        fig.tight_layout()
        save(fig, out, "figS1_parameter_sweeps")


def plot_ablation(cdir: str) -> None:
    a = pd.read_csv(os.path.join(cdir, "aggregate", "ablation.csv"))
    out = os.path.join(cdir, "figures")
    labels = [l for l in ["full_secure", "no_security", "no_cooldown", "no_early_exit", "no_adaptive_trigger",
                          "no_replay_protection", "no_rate_limit", "no_burst_detection", "no_consistency_check"]
              if l in set(a["label"])]
    scen = [s for s in SCENARIO_ORDER if s in set(a["scenario"])]
    metrics = [("energy_per_min_mJ", "Energy / hour (J)", 60 / 1000), ("episode_recall", "Episode recall", 1.0),
               ("attack_success_rate", "Attack success rate", 1.0),
               ("false_rejection_rate_object", "FRR (real objects)", 1.0)]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(7.2, 8.0), sharex=True)
    x = np.arange(len(scen))
    w = 0.8 / len(labels)
    colors = ["#0b0b0b"] + PALETTE
    for ax, (m, lab, scale) in zip(axes, metrics):
        for i, l in enumerate(labels):
            sub = a[a["label"] == l].set_index("scenario").reindex(scen).reset_index()
            mean, e = _err(sub, m, scale)
            ax.bar(x + (i - (len(labels) - 1) / 2) * w, mean, w * 0.92, yerr=e, color=colors[i % len(colors)],
                   label=l.replace("_", " "), error_kw={"elinewidth": 0.6, "capsize": 1, "ecolor": MUTED})
        ax.set_ylabel(lab)
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(scen)
    axes[0].legend(ncol=3, frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.45))
    fig.suptitle("Fig. 12  Ablation: secure system with one component removed (mean, 95% CI)", y=0.995)
    save(fig, out, "fig12_ablation")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("main_campaign", nargs="?")
    ap.add_argument("--ablation")
    ap.add_argument("--sensitivity")
    a = ap.parse_args()
    if a.main_campaign:
        plot_main(a.main_campaign)
    if a.ablation:
        plot_ablation(a.ablation)
    if a.sensitivity:
        plot_sensitivity(a.sensitivity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
