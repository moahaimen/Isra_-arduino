#!/usr/bin/env python3
"""Shared detector-level parameters for the R3 tiled cascade, chosen on the
VALIDATION original frames with the R2 rule (scripts/r2/tune_common.py):
detection threshold = argmax mean box F1 of stage 1 and stage 2 over
{0.20, 0.25, ..., 0.70}; early exit (hi, lo) = argmax F1(cascade) - 0.1 x
stage-2 fraction. Writes results/r3/tuning/common.json."""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "r2")); sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import data_r3
from tune_common import counts, f1
from build_workloads_r3 import STAGE1, STAGE2
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
tr = {}
for m in (STAGE1, STAGE2):
    d = os.path.join(data_r3.DATA, "bank", f"validation_{m}")
    fr, gt, pr = (pd.read_csv(os.path.join(d, x)) for x in ("frames.csv", "ground_truth.csv", "predictions.csv"))
    o = fr[fr.event_id % 100 == 0]
    tr[m] = (o, gt[gt.event_id.isin(o.event_id)], pr[(pr.prediction_id > 0) & pr.event_id.isin(o.event_id)])
rows = []
for t in [round(x, 2) for x in np.arange(0.20, 0.701, 0.05)]:
    f = [f1(list(counts(*tr[m], t).values())) for m in (STAGE1, STAGE2)]
    rows.append({"thr": t, "f1_stage1": f[0], "f1_stage2": f[1], "mean": sum(f) / 2})
th = pd.DataFrame(rows); thr = float(th.loc[th["mean"].idxmax(), "thr"])
c1, c2 = counts(*tr[STAGE1], thr), counts(*tr[STAGE2], thr)
top1 = tr[STAGE1][2].groupby("event_id").confidence.max()
ee = []
for hi in (0.5, 0.6, 0.7, 0.8, 0.9):
    for lo in (0.05, 0.10, 0.15, 0.20, 0.30):
        cas, n2 = [], 0
        for i in c1:
            s = float(top1.get(i, 0.0))
            if s >= hi or s <= lo: cas.append(c1[i])
            else: cas.append(c2[i]); n2 += 1
        ee.append({"hi": hi, "lo": lo, "f1": f1(cas), "stage2_frac": n2 / len(c1), "score": f1(cas) - 0.1 * n2 / len(c1)})
ee = pd.DataFrame(ee); b = ee.loc[ee.score.idxmax()]
out = {"split": "validation", "detection_threshold": thr, "early_exit_threshold": float(b.hi), "early_exit_low_threshold": float(b.lo),
       "sim": {"detection_threshold": thr, "early_exit_threshold": float(b.hi), "early_exit_low_threshold": float(b.lo)},
       "threshold_grid": th.to_dict("records"), "early_exit_grid": ee.to_dict("records")}
os.makedirs(os.path.join(ROOT, "results", "r3", "tuning"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "results", "r3", "tuning", "common.json"), "w"), indent=1)
print(th.round(3).to_string()); print(ee.sort_values("score", ascending=False).head(4).round(3).to_string()); print(out["sim"])
