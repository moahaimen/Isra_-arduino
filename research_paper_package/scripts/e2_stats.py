#!/usr/bin/env python3
"""Segment-clustered bootstrap for the E2 comparison on test: validation-selected controller vs best feasible baseline."""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import oracle_gate as og
S = og.Split(sys.argv[1])
fz = json.load(open(os.path.join(HERE, "..", "04_experiments/controller_results/frozen_controllers.json")))
cands = {k: v for k, v in fz.items() if isinstance(v, dict) and v.get("met_0.90_oof")}
sel = min(cands, key=lambda k: cands[k]["oof_cost_per_frame"])
pc = pd.read_csv(os.path.join(HERE, "..", "04_experiments/controller_results/per_frame_cost_test.csv"))
pt = pd.read_csv(os.path.join(HERE, "..", "04_experiments/controller_results/per_track_test.csv"))
fb = json.load(open(os.path.join(HERE, "..", "03_oracle_gate/frozen_baselines.json")))["families"]["mog2_full"]["params"]
tl_b, c_b = S.evaluate(og.policy(S, "mog2_full", fb))
c_c, tl_c = pc[sel].to_numpy(), pt[f"timely_{sel}"].to_numpy().astype(bool)
rng = np.random.default_rng(og.SEED); segs = S.seg_names
tk = {s: np.where(S.track_seg == s)[0] for s in segs}; fr = {s: np.where(S.seg == s)[0] for s in segs}
ratio, dR = [], []
for _ in range(10000):
    pick = rng.choice(len(segs), len(segs))
    fi = np.concatenate([fr[segs[j]] for j in pick]); ti = np.concatenate([tk[segs[j]] for j in pick])
    if c_b[fi].sum() > 0: ratio.append(c_c[fi].sum() / c_b[fi].sum())
    if len(ti): dR.append(tl_c[ti].mean() - tl_b[ti].mean())
out = {"selected_controller": sel, "baseline": "mog2_full", "test_cost_ratio": float(c_c.sum() / c_b.sum()),
       "test_cost_ratio_95ci": [float(np.percentile(ratio, 2.5)), float(np.percentile(ratio, 97.5))],
       "test_R_controller": float(tl_c.mean()), "test_R_baseline": float(tl_b.mean()),
       "test_dR_95ci": [float(np.percentile(dR, 2.5)), float(np.percentile(dR, 97.5))],
       "paired_tracks_controller_only": int((tl_c & ~tl_b).sum()), "paired_tracks_baseline_only": int((~tl_c & tl_b).sum()),
       "E2_threshold_cost_ratio": 0.60, "E2_pass": bool(tl_c.mean() >= max(0.90, tl_b.mean()) and c_c.sum() <= 0.60 * c_b.sum())}
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(HERE, "..", "07_statistics/e2_test_comparison.json"), "w"), indent=1)
