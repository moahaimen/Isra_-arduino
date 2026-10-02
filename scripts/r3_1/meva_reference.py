#!/usr/bin/env python3
"""DETECTOR-REFERENCED tracks for the MEVA static-camera clips (no human box
annotation is available in this environment, see data/splits/r3_1_meva_splits.json).

Reference detector: Ultralytics YOLOv8s (COCO weights, pinned by SHA-256 in the
output), 1280x736 letterbox input, conf >= 0.25, classes person -> 1,
car/truck/bus -> 2 (vehicle); other classes are ignored. This detector is
different from, and stronger than, the cascade used as the simulated M7
detector (tiled EfficientDet-Lite0), so utility is measured against what a
strong always-on detector finds.

Tracks: greedy IoU association (IoU >= 0.3, same class, gap <= 5 frames, 10 fps).
A track is CONFIRMED (and then plays the role of a ground-truth track in all
metrics) iff it has >= 5 detections, mean confidence >= 0.45 and max confidence
>= 0.6. A confirmed track is MOVING iff its box centre moves >= 15 px (same rule
as scripts/r2/build_workloads.py). Unconfirmed detections are written with
ignore = 1 (never counted as a miss, never as a false positive).

These are REFERENCE tracks: errors of the reference detector (misses, false
tracks) are part of the "ground truth". Results on MEVA are therefore
detector-referenced utility, not annotation-based accuracy; no mAP is reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.environ.get("R31_DATA", "/home/claude/data_r3_1")
W, H = 1280, 720
CLS = {0: 1, 2: 2, 5: 2, 7: 2}  # COCO person, car, bus, truck
MIN_LEN, MIN_MEAN, MIN_MAX, IOU_T, GAP = 5, 0.45, 0.6, 0.3, 5


def seq_key(manifest, group):
    allg = sorted(s["group"] for s in manifest["segments"])
    return 2001 + allg.index(group)


def detect(group, weights, imgsz=1280):
    from ultralytics import YOLO
    import torch
    torch.set_num_threads(1)
    m = YOLO(weights)
    d = os.path.join(DATA, "meva", group)
    files = sorted(f for f in os.listdir(d) if f.endswith(".jpg"))
    rows = []
    for i, f in enumerate(files):
        r = m.predict(os.path.join(d, f), imgsz=imgsz, conf=0.25, iou=0.5, max_det=100, verbose=False, device="cpu")[0]
        for (x1, y1, x2, y2), s, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            if int(c) in CLS:
                rows.append((i, CLS[int(c)], s, x1, y1, x2, y2))
    return pd.DataFrame(rows, columns=["frame", "class_id", "conf", "x1", "y1", "x2", "y2"]), len(files)


def iou(a, b):
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def track(dets: pd.DataFrame):
    tracks, nxt = [], 1  # each: dict(id, cls, last_box, last_frame, rows)
    for f, g in dets.groupby("frame"):
        live = [t for t in tracks if f - t["last_frame"] <= GAP]
        used = set()
        cand = sorted(g.itertuples(), key=lambda r: -r.conf)
        for r in cand:
            box = (r.x1, r.y1, r.x2, r.y2)
            best, bt = IOU_T, None
            for t in live:
                if t["id"] in used or t["cls"] != r.class_id or t["last_frame"] == f:
                    continue
                o = iou(box, t["last_box"])
                if o >= best:
                    best, bt = o, t
            if bt is None:
                bt = {"id": nxt, "cls": r.class_id, "rows": []}
                nxt += 1
                tracks.append(bt)
            used.add(bt["id"])
            bt["last_box"], bt["last_frame"] = box, f
            bt["rows"].append((f, r.conf) + box)
    return tracks


def build(group, manifest, weights):
    sk = seq_key(manifest, group)
    out = os.path.join(DATA, "meva", group)
    dets, n = detect(group, weights)
    dets.to_csv(os.path.join(out, "ref_dets.csv"), index=False)
    tr = track(dets)
    gt, tmeta = [], []
    for t in tr:
        rows = t["rows"]
        confs = [r[1] for r in rows]
        ok = len(rows) >= MIN_LEN and np.mean(confs) >= MIN_MEAN and max(confs) >= MIN_MAX
        for f, c, x1, y1, x2, y2 in rows:
            gt.append({"event_id": sk * 100000 + f, "track_id": t["id"], "class_id": t["cls"],
                       "class_name": {1: "person", 2: "car"}[t["cls"]], "ignore": 0 if ok else 1,
                       "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        tmeta.append({"track_id": t["id"], "class_id": t["cls"], "n": len(rows), "mean_conf": float(np.mean(confs)),
                      "confirmed": bool(ok)})
    gt = pd.DataFrame(gt)
    gt.insert(1, "gt_id", range(1, len(gt) + 1))
    gt.to_csv(os.path.join(out, "reference_gt.csv"), index=False)
    pd.DataFrame(tmeta).to_csv(os.path.join(out, "reference_tracks.csv"), index=False)
    return n, len(tr), int(sum(1 for t in tmeta if t["confirmed"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="development,validation")
    ap.add_argument("--weights", default="/home/claude/data_r3/weights/yolov8s.pt")
    ap.add_argument("--only", default="", help="comma-separated group names (parallel sharding)")
    a = ap.parse_args()
    if "test" in a.splits.split(","):
        raise SystemExit("MEVA test split is locked")
    m = json.load(open(os.path.join(ROOT, "data", "splits", "r3_1_meva_splits.json")))
    for s in m["segments"]:
        if s["split"] not in a.splits.split(",") or os.path.exists(os.path.join(DATA, "meva", s["group"], "reference_gt.csv")):
            continue
        if a.only and s["group"] not in a.only.split(","):
            continue
        n, t, c = build(s["group"], m, a.weights)
        print(s["split"], s["group"], "frames", n, "tracks", t, "confirmed", c, flush=True)
    json.dump({"reference_detector": "ultralytics YOLOv8s COCO", "weights_sha256": hashlib.sha256(open(a.weights, "rb").read()).hexdigest(),
               "ultralytics": __import__("ultralytics").__version__, "imgsz": 1280, "conf": 0.25,
               "tracker": {"iou": IOU_T, "gap": GAP, "min_len": MIN_LEN, "min_mean": MIN_MEAN, "min_max": MIN_MAX}},
              open(os.path.join(DATA, "meva", "reference_meta.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
