#!/usr/bin/env python3
"""Validation Pareto figures from the stored Gate-B/C grids (results/r3/tuning)."""
import glob, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
T = os.path.join(ROOT, "results", "r3", "tuning"); O = os.path.join(ROOT, "results", "r3", "figures"); os.makedirs(O, exist_ok=True)
COL = {"ugs_event": "#d62728", "event": "#9467bd", "fixed_threshold": "#1f77b4", "motion_only": "#ff7f0e",
       "mog2_event": "#2ca02c", "robust_event": "#e377c2", "ugs_secure": "#d62728", "secure": "#8c564b", "robust_secure": "#7f7f7f"}
def front(t, x, y, maxy=True):
    d = t.sort_values([x, y], ascending=[True, not maxy]); best = -1e9 if maxy else 1e9; keep = []
    for i, r in d.iterrows():
        if (r[y] > best + 1e-12) if maxy else (r[y] < best - 1e-12): keep.append(i); best = r[y]
    return t.loc[keep].sort_values(x)
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
for m in ["ugs_event", "event", "fixed_threshold", "motion_only", "mog2_event", "robust_event"]:
    t = pd.read_csv(os.path.join(T, f"gateB_{m}_grid.csv"))
    for a, col, ttl in zip(ax, ["UR_timely", "UR_track", "noisy_UR_timely"], ["timely utility retention (clean+noisy)", "track utility retention (clean+noisy)", "timely utility retention (noisy only)"]):
        f = front(t, "duty", col); a.plot(f.duty, f[col], marker="o", ms=3, color=COL[m], label=m); a.set_title(ttl, fontsize=9)
        a.set_xlabel("M7 duty (simulated)"); a.set_ylabel(col); a.grid(alpha=.3); a.axhline(.9, color="k", ls=":", lw=.8); a.axvline(.25, color="k", ls=":", lw=.8)
fig.legend(*ax[0].get_legend_handles_labels(), loc="lower center", ncol=6, fontsize=8, frameon=False); fig.tight_layout(rect=(0, .07, 1, 1))
fig.savefig(os.path.join(O, "fig_pareto_duty_utility_validation.png"), dpi=150); plt.close(fig)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for m in ["ugs_secure", "secure", "robust_secure"]:
    t = pd.read_csv(os.path.join(T, f"gateC_{m}_grid.csv"))
    ax[0].scatter(t.attack_success, t.SUR, s=14, color=COL[m], label=m, alpha=.7)
    ax[1].scatter(t.FRR, t.SUR, s=14, color=COL[m], label=m, alpha=.7)
ax[0].set_xlabel("attack success (frames reaching the M7)"); ax[1].set_xlabel("false rejection rate"); 
for a in ax: a.set_ylabel("secure utility retention"); a.grid(alpha=.3)
ax[1].axvline(.05, color="k", ls=":", lw=.8); ax[0].legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(O, "fig_secure_utility_validation.png"), dpi=150)
