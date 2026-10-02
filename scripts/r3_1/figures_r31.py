#!/usr/bin/env python3
"""12 required R3.1 VALIDATION figures (KITTI validation only; MEVA pending). Reads results/r3_1/validation/*.csv."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "r3_1")
V, F = os.path.join(R, "validation"), os.path.join(R, "figures")
os.makedirs(F, exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.figsize": (5.2, 3.4), "axes.grid": True, "grid.alpha": .3})
NOTE = "KITTI validation, modeled energy, host-simulated"
def save(n): plt.tight_layout(); plt.savefig(os.path.join(F, n + ".png"), dpi=170); plt.close()
fam_lab = {"event": "legacy event", "mog2_event": "MOG2", "robust_event": "R2 robust", "motion_only": "motion only", "fixed_threshold": "fixed thr.",
           "r3": "R3 scheduler", "nn": "R3.1 noise-norm", "hold": "R3.1 +hold", "vr": "R3.1 value rule", "all": "R3.1 all"}
P = pd.read_csv(os.path.join(V, "pareto_kitti_val_all.csv"))
# 1 detector ceiling
D = pd.read_csv(os.path.join(R, "..", "r3", "gate_a", "detectors_validation.csv"))
D = D.sort_values("timely_recall_ceiling")
plt.barh(D.detector, D.timely_recall_ceiling, color=["tab:red" if r == "mcu_target" else "tab:gray" for r in D.role])
plt.xlabel("timely-recall ceiling (validation tracks)"); plt.title("Detector ceiling (red = MCU-class, CPU-trained; gray = host reference)", fontsize=8); save("fig01_detector_ceiling")
# 2 pareto duty
def front(d, x, y):
    d = d.sort_values([x, y], ascending=[True, False]); best = -1; k = []
    for i, r in d.iterrows():
        if r[y] > best + 1e-12: k.append(i); best = r[y]
    return d.loc[k]
for xcol, name, xl in [("duty", "fig02_utility_vs_duty", "M7 duty (clean/noisy mean)"), ("energy", "fig03_utility_vs_energy", "modeled energy (J/min)")]:
    P["energy"] = (P.clean_energy + P.noisy_energy) / 2000.0
    for f, g in P.groupby("family"):
        fr = front(g, xcol, "UR"); plt.plot(fr[xcol], fr.UR, "o-", ms=3, label=fam_lab.get(f, f))
    if xcol == "duty": plt.axvline(.25, color="k", ls="--", lw=.8)
    plt.xlabel(xl); plt.ylabel("UR (timely tracks / always-on)"); plt.legend(fontsize=6, ncol=2); plt.title("Pareto frontiers per family; " + NOTE, fontsize=7); save(name)
# 4 clean vs noisy
for f, g in P.groupby("family"):
    plt.scatter(g.clean_UR, g.noisy_UR, s=8, label=fam_lab.get(f, f))
plt.plot([0, 1], [0, 1], "k--", lw=.7); plt.xlabel("UR clean"); plt.ylabel("UR noisy"); plt.legend(fontsize=6, ncol=2); plt.title("Clean vs noisy generalization (all configs)", fontsize=8); save("fig04_clean_vs_noisy")
# 5 burst, 11 energy per detection
O = pd.read_csv(os.path.join(V, "operating_points_kitti_val.csv"))
plt.bar(O.name, O.UR_burst, color="tab:blue"); plt.xticks(rotation=30, ha="right"); plt.ylabel("burst UR (timely)"); plt.title("Burst recall at best duty<=0.25 points", fontsize=8); save("fig05_burst_recall")
plt.bar(O.name, O.E_per_track_J, color="tab:green"); plt.xticks(rotation=30, ha="right"); plt.ylabel("modeled J per detected track"); plt.title("Energy per useful detection (modeled)", fontsize=8); save("fig11_energy_per_detection")
# security
S = pd.read_csv(os.path.join(V, "security_kitti_val_summary.csv"))
sh = pd.read_csv(os.path.join(V, "replay_shift_kitti_val.csv"))
modes = ["event", "plain_limit", "gate_r3"]
rep = S[S.sc.isin(["replay_exact", "replay_perturbed", "mixed"])]
w = 0.25; xs = np.arange(4)
for j, m in enumerate(modes):
    vals = [rep[(rep["mode"] == m) & (rep.sc == s)].atk_succ.iloc[0] for s in ["replay_exact", "replay_perturbed", "mixed"]]
    vals.append(sh[sh["mode"] == {"event": "no_security", "plain_limit": "no_security", "gate_r3": "gate_r3"}[m]].replay_shift_success.iloc[0])
    plt.bar(xs + j * w, vals, w, label=m)
g5 = sh[sh["mode"] == "gate_grad0.5"]
plt.bar(xs + 3 * w, [0.0, g5.replay_perturbed_success.iloc[0], np.nan, g5.replay_shift_success.iloc[0]], w, label="gate grad c=0.5", color="tab:red")
plt.xticks(xs + 1.5 * w, ["exact", "perturbed", "mixed", "shifted/crop"]); plt.ylabel("attack success (frames reaching M7)"); plt.legend(fontsize=6); plt.title("Replay robustness by perturbation", fontsize=8); save("fig06_replay_by_perturbation")
sp = S[S.sc == "spam"]
for m in ["event", "plain_limit", "plain_limit_tight", "gate_r3"]:
    d = sp[sp["mode"] == m].sort_values("k"); plt.plot(d.k, d.SUR, "o-", ms=3, label=m)
plt.xscale("log", base=2); plt.xlabel("spam rate multiplier"); plt.ylabel("SUR (timely recall / own clean)"); plt.legend(fontsize=6); plt.title("Spam rate vs legitimate utility", fontsize=8); save("fig07_spam_vs_utility")
for m in ["event", "plain_limit", "gate_r3"]:
    d = sp[sp["mode"] == m].sort_values("k"); plt.plot(d.k, d.atk_succ, "o-", ms=3, label=m)
plt.xscale("log", base=2); plt.xlabel("spam rate multiplier"); plt.ylabel("attack success"); plt.legend(fontsize=6); plt.title("Spam rate vs attack success", fontsize=8); save("fig08_spam_vs_attack_success")
for m in ["event", "plain_limit", "plain_limit_tight", "gate_r3", "legacy_secure"]:
    d = sp[sp["mode"] == m].sort_values("k"); plt.plot(d.k, d.frr, "o-", ms=3, label=m)
plt.xscale("log", base=2); plt.yscale("symlog", linthresh=0.01); plt.xlabel("spam rate multiplier"); plt.ylabel("FRR"); plt.axhline(.05, color="k", ls="--", lw=.8); plt.legend(fontsize=6); plt.title("FRR vs attack intensity", fontsize=8); save("fig09_frr_vs_intensity")
sc = S[S.sc.isin(["clean", "noisy", "mixed", "replay_exact", "replay_perturbed"])]
for j, m in enumerate(["event", "plain_limit", "gate_r3"]):
    d = sc[sc["mode"] == m]; plt.bar(np.arange(len(d)) + j * .27, d.SUR, .27, label=m)
plt.xticks(np.arange(5) + .27, list(sc[sc["mode"] == "event"].sc), rotation=20); plt.ylabel("SUR"); plt.legend(fontsize=6); plt.title("Secure utility retention (own-clean relative)", fontsize=8); save("fig10_secure_utility_retention")
A = pd.read_csv(os.path.join(V, "ablation_security_kitti_val.csv"))
A = A[A["mode"] != "minus_budget"]
x = np.arange(len(A)); plt.bar(x - .2, A.replay_perturbed_succ, .4, label="replay perturbed"); plt.bar(x + .2, A.mixed_succ, .4, label="mixed")
plt.xticks(x, A["mode"], rotation=35, ha="right", fontsize=6); plt.ylabel("attack success"); plt.legend(fontsize=6); plt.title("Ablation of the security stack", fontsize=8); save("fig12_ablation")
print("figures ->", F)
