#!/usr/bin/env python3
"""Shifted / cropped / mixed replay (variants 20-25, 10-48 px, 95/90 % crops) on KITTI validation: gate with and without shift tolerance."""
import os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31, pandas as pd
thr = 0.45; C = {"detection_threshold": thr}
W = {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0}
def S(l, m, p): return (l, m, {"common": C, "params": {**W, **p}})
specs = [S("no_security", "event", {}), S("gate_r3", "event_ugs_gate", {})]
for gc in [0.25, 0.5, 1.0, 1.5]:
    specs.append(S(f"gate_grad{gc}", "event_ugs_gate", {"ug_grad_c": gc}))
    specs.append(S(f"gate_grad{gc}_shift", "event_ugs_gate", {"ug_grad_c": gc, "ug_shift_tol": 1, "ug_shift_try": 192}))
specs.append(("always_on", "always_on", {"common": C, "params": {}}))
root = os.path.join(lib31.D31, f"workloads_validation_{thr:.2f}"); fr = []
with ProcessPoolExecutor(2) as ex:
    for sc in ["clean", "noisy", "replay_shift", "replay_exact", "replay_perturbed"]:
        fr.append(lib31.run_campaign("validation", root, specs, [sc], [1.0], [1001, 1002, 1003], thr, executor=ex, datasets=("kitti",)))
d = pd.concat(fr); d.to_csv(sys.argv[1], index=False)
g = lib31.pool(d, ["mode", "scenario"]); rows = []
for m, x in g[g["mode"] != "always_on"].groupby("mode"):
    cn = x[x.scenario.isin(["clean", "noisy"])]; y = x[x.scenario == "replay_shift"].iloc[0]
    rows.append({"mode": m, "FRR_clean_noisy": cn.legit_gate_blocked.sum() / max(1, cn.legit_gate_evaluated.sum()),
                 "replay_shift_success": y.attack_started / y.attack_frames,
                 **{f"{k}_success": (lambda z: z.attack_started / z.attack_frames)(x[x.scenario == k].iloc[0]) for k in ["replay_exact", "replay_perturbed"]}, "clean_timely_recall": x[x.scenario == "clean"].iloc[0].timely_recall})
t = pd.DataFrame(rows); t.to_csv(sys.argv[2], index=False); print(t.round(3).to_string())
