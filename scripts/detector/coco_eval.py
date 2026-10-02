"""Standard multi-object detection evaluation for detector trace V2.

mAP@0.5 and mAP@0.5:0.95 (and per-class AP) come from pycocotools' COCOeval,
the reference COCO implementation (101-point interpolation, greedy one-to-one
matching by descending score, crowd/ignore regions excluded). Boxes flagged
`ignore=1` (PASCAL "difficult", KITTI "DontCare") are passed as iscrowd=1 so
detections matched to them are neither TP nor FP.

Operating-point precision/recall/F1 at a confidence threshold use the same
one-to-one matching rule (IoU >= 0.5, same class, highest score first, each GT
matched at most once), implemented in `match_frame`.
"""
from __future__ import annotations

import contextlib
import io
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd


def iou_xyxy(a: Sequence[float], b: Sequence[float]) -> float:
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_frame(gt: pd.DataFrame, pred: pd.DataFrame, iou_thr: float = 0.5):
    """Greedy one-to-one matching inside one frame. Returns (tp, fp, fn).

    Predictions are processed by descending confidence; each is matched to the
    unmatched non-ignored GT box of the same class with the highest IoU >= thr.
    A prediction whose best overlap is an ignore region (and no regular GT) is
    discarded (neither TP nor FP)."""
    tp = fp = 0
    gt_reg = gt[gt["ignore"] == 0]
    gt_ign = gt[gt["ignore"] == 1]
    used = set()
    for _, p in pred.sort_values("confidence", ascending=False).iterrows():
        pb = (p.x1, p.y1, p.x2, p.y2)
        best, best_i = iou_thr, None
        for gi, g in gt_reg[gt_reg["class_id"] == p.class_id].iterrows():
            if gi in used:
                continue
            o = iou_xyxy(pb, (g.x1, g.y1, g.x2, g.y2))
            if o >= best:
                best, best_i = o, gi
        if best_i is not None:
            used.add(best_i)
            tp += 1
            continue
        ign = any(iou_xyxy(pb, (g.x1, g.y1, g.x2, g.y2)) >= iou_thr
                  for _, g in gt_ign[gt_ign["class_id"] == p.class_id].iterrows())
        if not ign:
            fp += 1
    fn = len(gt_reg) - len(used)
    return tp, fp, fn


def _to_coco(frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame, classes: Dict[int, str]):
    images = [{"id": int(r.event_id), "width": int(r.width), "height": int(r.height)} for r in frames.itertuples()]
    anns = []
    for i, r in enumerate(gt.itertuples(), 1):
        w, h = r.x2 - r.x1, r.y2 - r.y1
        anns.append({"id": i, "image_id": int(r.event_id), "category_id": int(r.class_id),
                     "bbox": [float(r.x1), float(r.y1), float(w), float(h)], "area": float(w * h),
                     "iscrowd": int(r.ignore), "ignore": int(r.ignore)})
    cats = [{"id": int(k), "name": v} for k, v in sorted(classes.items())]
    dets = [{"image_id": int(r.event_id), "category_id": int(r.class_id),
             "bbox": [float(r.x1), float(r.y1), float(r.x2 - r.x1), float(r.y2 - r.y1)],
             "score": float(r.confidence)} for r in pred.itertuples()]
    return {"images": images, "annotations": anns, "categories": cats}, dets


def coco_map(frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame, classes: Dict[int, str],
             max_dets: int = 100) -> Dict:
    """pycocotools evaluation. Returns mAP50, mAP50_95 and per-class AP."""
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    gt_json, dets = _to_coco(frames, gt, pred, classes)
    if not dets:
        return {"mAP50": 0.0, "mAP50_95": 0.0, "per_class": {v: {"AP50": 0.0, "AP50_95": 0.0} for v in classes.values()},
                "n_detections": 0}
    with contextlib.redirect_stdout(io.StringIO()):
        cg = COCO()
        cg.dataset = gt_json
        cg.createIndex()
        cd = cg.loadRes(dets)
        ev = COCOeval(cg, cd, "bbox")
        ev.params.maxDets = [1, 10, max_dets]
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
    prec = ev.eval["precision"]  # [T, R, K, A, M]
    per = {}
    for k_idx, cid in enumerate(ev.params.catIds):
        p_all = prec[:, :, k_idx, 0, -1]
        p50 = prec[0, :, k_idx, 0, -1]
        ap = float(np.mean(p_all[p_all > -1])) if (p_all > -1).any() else float("nan")
        ap50 = float(np.mean(p50[p50 > -1])) if (p50 > -1).any() else float("nan")
        per[classes[cid]] = {"AP50": ap50, "AP50_95": ap}
    return {"mAP50": float(ev.stats[1]), "mAP50_95": float(ev.stats[0]), "per_class": per,
            "AP_small": float(ev.stats[3]), "AP_medium": float(ev.stats[4]), "AP_large": float(ev.stats[5]),
            "n_detections": len(dets)}


def operating_point(frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame, score_thr: float,
                    iou_thr: float = 0.5) -> Dict:
    p = pred[pred["confidence"] >= score_thr]
    gt_by = dict(tuple(gt.groupby("event_id")))
    pr_by = dict(tuple(p.groupby("event_id")))
    empty_g = gt.iloc[0:0]
    empty_p = p.iloc[0:0]
    TP = FP = FN = 0
    for eid in frames["event_id"]:
        tp, fp, fn = match_frame(gt_by.get(eid, empty_g), pr_by.get(eid, empty_p), iou_thr)
        TP += tp
        FP += fp
        FN += fn
    prec = TP / (TP + FP) if TP + FP else 0.0
    rec = TP / (TP + FN) if TP + FN else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"score_threshold": score_thr, "iou_threshold": iou_thr, "TP": TP, "FP": FP, "FN": FN,
            "precision": prec, "recall": rec, "F1": f1}


def evaluate(frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame, classes: Dict[int, str],
             score_thresholds: List[float] = (0.3, 0.5)) -> Dict:
    out = coco_map(frames, gt, pred, classes)
    out["operating_points"] = [operating_point(frames, gt, pred, t) for t in score_thresholds]
    out["evaluator"] = "pycocotools COCOeval (bbox), ignore regions as iscrowd"
    return out
