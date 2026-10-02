#!/usr/bin/env python3
"""Detector-level parameters shared by every mode, chosen on the VALIDATION
split original frames (no simulator, no attacks):

* detection_threshold: argmax over {0.30, 0.35, ..., 0.70} of the mean
  box-level F1 (IoU 0.5, one-to-one) of stage 1 (EfficientDet-Lite0 INT8)
  and stage 2 (EfficientDet-Lite2 INT8);
* early-exit thresholds (hi, lo): the cascade exits after stage 1 when the
  top stage-1 score >= hi or <= lo, else uses stage 2. Choose
  argmax_(hi, lo) F1(cascade) - 0.1 * (fraction of frames sent to stage 2),
  hi in {0.5, 0.6, 0.7, 0.8, 0.9}, lo in {0.05, 0.10, 0.15, 0.20, 0.30}.

Writes results/r2/tuning/common.json.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import coco_eval  # noqa: E402
from build_workloads import STAGE1, STAGE2  # noqa: E402
from tune_r2 import check_split  # noqa: E402

DATA = os.environ.get("R2_DATA", "/home/claude/data_r2")


def counts(frames, gt, pred, thr):
    p = pred[pred.confidence >= thr]
    gb = {k: g for k, g in gt.groupby("event_id")}
    pb = {k: g for k, g in p.groupby("event_id")}
    e_g, e_p = gt.iloc[0:0], p.iloc[0:0]
    out = {}
    for eid in frames.event_id:
        out[int(eid)] = coco_eval.match_frame(gb.get(eid, e_g), pb.get(eid, e_p))
    return out


def f1(c):
    tp, fp, fn = (sum(x[i] for x in c) for i in range(3))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def main() -> int:
    split = "validation"
    check_split(split)
    tr = {}
    for m in (STAGE1, STAGE2):
        d = os.path.join(DATA, "bank", f"{split}_{m}")
        fr = pd.read_csv(os.path.join(d, "frames.csv"))
        gt = pd.read_csv(os.path.join(d, "ground_truth.csv"))
        pr = pd.read_csv(os.path.join(d, "predictions.csv"))
        orig = fr[fr.event_id % 100 == 0]
        tr[m] = (orig, gt[gt.event_id.isin(orig.event_id)], pr[(pr.prediction_id > 0) & pr.event_id.isin(orig.event_id)])
    thr_grid = [round(x, 2) for x in np.arange(0.30, 0.701, 0.05)]
    rows = []
    for t in thr_grid:
        f = [f1(list(counts(*tr[m], t).values())) for m in (STAGE1, STAGE2)]
        rows.append({"thr": t, "f1_stage1": f[0], "f1_stage2": f[1], "mean": (f[0] + f[1]) / 2})
    thr_df = pd.DataFrame(rows)
    det_thr = float(thr_df.loc[thr_df["mean"].idxmax(), "thr"])
    c1, c2 = counts(*tr[STAGE1], det_thr), counts(*tr[STAGE2], det_thr)
    top1 = tr[STAGE1][2].groupby("event_id").confidence.max()
    ids = list(c1)
    ee = []
    for hi in (0.5, 0.6, 0.7, 0.8, 0.9):
        for lo in (0.05, 0.10, 0.15, 0.20, 0.30):
            cas, n2 = [], 0
            for i in ids:
                s = float(top1.get(i, 0.0))
                if s >= hi or s <= lo:
                    cas.append(c1[i])
                else:
                    cas.append(c2[i])
                    n2 += 1
            ee.append({"hi": hi, "lo": lo, "f1": f1(cas), "stage2_frac": n2 / len(ids),
                       "score": f1(cas) - 0.1 * n2 / len(ids)})
    ee_df = pd.DataFrame(ee)
    b = ee_df.loc[ee_df.score.idxmax()]
    out = {"split": split, "detection_threshold": det_thr, "early_exit_threshold": float(b.hi),
           "early_exit_low_threshold": float(b.lo),
           "sim": {"detection_threshold": det_thr, "early_exit_threshold": float(b.hi),
                   "early_exit_low_threshold": float(b.lo)},
           "threshold_grid": thr_df.to_dict("records"), "early_exit_grid": ee_df.to_dict("records"),
           "rule": __doc__}
    os.makedirs(os.path.join(ROOT, "results", "r2", "tuning"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "r2", "tuning", "common.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: out[k] for k in ("detection_threshold", "early_exit_threshold", "early_exit_low_threshold")}))
    print(thr_df.round(3).to_string())
    print(ee_df.sort_values("score", ascending=False).head(5).round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
