#!/usr/bin/env python3
"""mAP@0.5 and mAP@0.5:0.95 for detector traces WITH bounding boxes.

This is only meaningful for traces produced by a real object detector on
images with real bounding-box annotations (data/detector_traces/README.md).
The synthetic_distribution backend produces no boxes, so the campaign never
calls this module on synthetic data.

Expected columns: event_id, ground_truth_class, predicted_class, confidence,
gt_x, gt_y, gt_w, gt_h, pred_x, pred_y, pred_w, pred_h (one GT box and at most
one predicted box per row; empty pred_* means no prediction; ground_truth_class
"none" means no GT object).
AP uses COCO-style 101-point interpolation of the precision-recall curve.
"""
from __future__ import annotations

import sys
from typing import Dict

import numpy as np
import pandas as pd

BOX_COLS = ["gt_x", "gt_y", "gt_w", "gt_h", "pred_x", "pred_y", "pred_w", "pred_h"]


def has_boxes(df: pd.DataFrame) -> bool:
    return all(c in df.columns for c in BOX_COLS) and df[["gt_w", "pred_w"]].notna().any().all()


def iou(a, b) -> float:
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def average_precision(df: pd.DataFrame, cls: str, thr: float) -> float:
    gt = df[df["ground_truth_class"] == cls]
    n_gt = len(gt)
    preds = df[(df["predicted_class"] == cls) & df["pred_w"].notna()].sort_values("confidence", ascending=False)
    if n_gt == 0:
        return float("nan")
    tp = []
    for _, r in preds.iterrows():
        ok = (r["ground_truth_class"] == cls and not np.isnan(r["gt_w"]) and
              iou((r["gt_x"], r["gt_y"], r["gt_w"], r["gt_h"]), (r["pred_x"], r["pred_y"], r["pred_w"], r["pred_h"]))
              >= thr)
        tp.append(1 if ok else 0)
    if not tp:
        return 0.0
    tp = np.asarray(tp)
    ctp, cfp = np.cumsum(tp), np.cumsum(1 - tp)
    rec = ctp / n_gt
    prec = ctp / (ctp + cfp)
    for i in range(len(prec) - 2, -1, -1):
        prec[i] = max(prec[i], prec[i + 1])
    ap = 0.0
    for r in np.linspace(0, 1, 101):
        idx = np.searchsorted(rec, r, side="left")
        ap += prec[idx] if idx < len(prec) else 0.0
    return ap / 101.0


def compute_map(df: pd.DataFrame) -> Dict[str, float]:
    if not has_boxes(df):
        raise ValueError("mAP requires bounding-box ground truth and predictions (gt_*/pred_* columns)")
    classes = sorted(c for c in df["ground_truth_class"].astype(str).unique() if c != "none")
    out = {}
    for thr_name, thrs in (("map50", [0.5]), ("map50_95", list(np.arange(0.5, 0.96, 0.05)))):
        aps = [average_precision(df, c, t) for c in classes for t in thrs]
        aps = [a for a in aps if not np.isnan(a)]
        out[thr_name] = float(np.mean(aps)) if aps else float("nan")
    return out


if __name__ == "__main__":
    print(compute_map(pd.read_csv(sys.argv[1], comment="#")))
