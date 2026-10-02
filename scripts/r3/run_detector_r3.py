#!/usr/bin/env python3
"""Run one REAL detector on an R3 split and write a detector trace V2 plus
Gate-A metrics.

Detectors (--detector):
  lite0_squash        EfficientDet-Lite0 INT8 on the whole frame resized to
                      320x320 (the R2 configuration)
  lite0_tiled         EfficientDet-Lite0 INT8 on 3 horizontal tiles
                      (each ~ 1/3 width + 10 % overlap, near-square), boxes
                      shifted back and merged by class-wise NMS (IoU 0.5)
  lite2_squash        EfficientDet-Lite2 INT8, whole frame (R2 stage 2)
  yolo:<weights>@<W>  Ultralytics YOLO (official 8.3.40) at a letterboxed
                      W x (W*375/1242 rounded to 32) input, i.e. KITTI's native
                      aspect; COCO weights map person->person, car->car;
                      KITTI-fine-tuned weights have classes 0 person, 1 car.

Gate-A metrics (all on the split's ORIGINAL frames, frame-level, no timing):
pycocotools mAP50 / mAP50:95 / per-class / small-medium-large AP;
operating-point P/R/F1 at --det-thr; moving-track recall (track detected in
>= 1 frame) and timely track recall (detected within 1 s of its onset) when
the detector runs on EVERY frame. This is the frame-level always-on ceiling;
the simulated always-on ceiling (M7 cannot process every frame) is computed
by the simulator later.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
sys.path.insert(0, os.path.join(HERE, "..", "r2"))
import coco_eval  # noqa: E402
import data_r3  # noqa: E402
import trace_v2  # noqa: E402

COCO_KEEP = {"person": 1, "car": 2}


def nms(boxes, scores, iou=0.5):
    order = np.argsort(-scores)
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        b = boxes[order[1:]]
        xx1 = np.maximum(boxes[i, 0], b[:, 0])
        yy1 = np.maximum(boxes[i, 1], b[:, 1])
        xx2 = np.minimum(boxes[i, 2], b[:, 2])
        yy2 = np.minimum(boxes[i, 3], b[:, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        a = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        ab = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
        order = order[1:][inter / (a + ab - inter + 1e-9) < iou]
    return keep


class MP:
    def __init__(self, model: str, tiles: int):
        from run_real_detector import MediaPipeDetector
        import models
        p = models.model_path(os.path.join(data_r3.DATA_R2, "models"), model)
        self.det = MediaPipeDetector(p, 0.01)
        self.tiles = tiles
        self.hash = trace_v2.sha256_file(p)
        self.meta = dict(models.MODELS[model])
        self.meta.update(models.tflite_complexity(p))

    def __call__(self, img, timing: bool = True):
        H, W = img.shape[:2]
        if self.tiles == 1:
            dets, inf, post = self.det(img, timing=timing)
            return [(COCO_KEEP[n], s, x1, y1, x2, y2) for n, s, x1, y1, x2, y2 in dets if n in COCO_KEEP], inf, post
        tw = int(np.ceil(W / self.tiles * 1.1))
        starts = np.linspace(0, W - tw, self.tiles).astype(int)
        out, inf_t, post_t = [], 0.0, 0.0
        for x0 in starts:
            dets, inf, post = self.det(np.ascontiguousarray(img[:, x0:x0 + tw]), timing=timing)
            inf_t += inf
            post_t += post
            out += [(COCO_KEEP[n], s, x1 + x0, y1, x2 + x0, y2) for n, s, x1, y1, x2, y2 in dets if n in COCO_KEEP]
        t0 = time.perf_counter()
        merged = []
        for c in (1, 2):
            d = [o for o in out if o[0] == c]
            if not d:
                continue
            b = np.array([o[2:] for o in d])
            s = np.array([o[1] for o in d])
            merged += [d[i] for i in nms(b, s)]
        return merged, inf_t, post_t + (time.perf_counter() - t0) * 1000


class YOLO:
    def __init__(self, weights: str, width: int):
        from ultralytics import YOLO as Y
        import torch
        torch.set_num_threads(1)
        self.m = Y(weights)
        self.w = width
        self.h = int(round(width * 375 / 1242 / 32.0)) * 32
        names = self.m.names
        if "car" in names.values() and len(names) > 2:  # COCO
            self.map = {k: COCO_KEEP[v] for k, v in names.items() if v in COCO_KEEP}
        else:  # KITTI fine-tuned: 0 person, 1 car
            self.map = {0: 1, 1: 2}
        self.hash = trace_v2.sha256_file(weights)
        n = sum(p.numel() for p in self.m.model.parameters())
        try:
            from ultralytics.utils.torch_utils import get_flops
            gflops = get_flops(self.m.model, [self.h, self.w])
        except Exception:
            gflops = float("nan")
        self.meta = {"architecture": os.path.basename(weights), "parameters": int(n), "macs": gflops * 1e9 / 2,
                     "model_bytes": os.path.getsize(weights), "precision": "FP32", "input": [self.h, self.w]}

    def __call__(self, img):
        r = self.m.predict(img[:, :, ::-1], imgsz=(self.h, self.w), conf=0.01, iou=0.5, max_det=100, verbose=False,
                           device="cpu")[0]
        sp = r.speed
        out = []
        for (x1, y1, x2, y2), s, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            if int(c) in self.map:
                out.append((self.map[int(c)], float(s), x1, y1, x2, y2))
        return out, float(sp["inference"]), float(sp["preprocess"] + sp["postprocess"])


class TIY:
    """TinyissimoYOLO (MCU target) through the pinned upstream fork, on the same
    3 near-square tiles as lite0_tiled, 256x256 letterboxed. VOC checkpoints
    map VOC person/car; KITTI fine-tuned checkpoints have 0 person, 1 car."""

    def __init__(self, weights: str):
        up = os.path.join(os.environ.get("EXT", "/home/claude/ext"), "TinyissimoYOLO")
        sys.path.insert(0, up)
        cwd = os.getcwd()
        os.chdir(up)
        import torch
        from ultralytics import YOLO as Y
        torch.set_num_threads(1)
        self.m = Y(weights)
        os.chdir(cwd)
        names = self.m.names
        self.map = {14: 1, 6: 2} if len(names) == 20 else {0: 1, 1: 2}
        self.hash = trace_v2.sha256_file(weights)
        n = sum(p.numel() for p in self.m.model.parameters())
        self.meta = {"architecture": "TinyissimoYOLO v8-b (tiled x3)", "parameters": int(n), "macs": 3 * 184900608.0,
                     "model_bytes": os.path.getsize(weights), "precision": "FP32", "input": [256, 256], "tiles": 3,
                     "role": "mcu_target", "weights": weights}

    def __call__(self, img, timing: bool = True):
        H, W = img.shape[:2]
        tw = int(np.ceil(W / 3 * 1.1))
        out, inf_t, post_t = [], 0.0, 0.0
        for x0 in np.linspace(0, W - tw, 3).astype(int):
            r = self.m.predict(np.ascontiguousarray(img[:, x0:x0 + tw, ::-1]), imgsz=256, conf=0.01, iou=0.5,
                               max_det=100, verbose=False, device="cpu")[0]
            inf_t += float(r.speed["inference"])
            post_t += float(r.speed["preprocess"] + r.speed["postprocess"])
            for (x1, y1, x2, y2), sc, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
                if int(c) in self.map:
                    out.append((self.map[int(c)], float(sc), x1 + x0, y1, x2 + x0, y2))
        merged = []
        for c in (1, 2):
            d = [o for o in out if o[0] == c]
            if d:
                b = np.array([o[2:] for o in d])
                sc = np.array([o[1] for o in d])
                merged += [d[i] for i in nms(b, sc)]
        return merged, inf_t, post_t


def track_ceiling(frames, gt, pred, det_thr):
    """Moving-track recall when the detector sees every frame."""
    from build_workloads import moving_tracks
    from metrics_r2 import match_tracks
    tr = moving_tracks(gt)
    tr = tr[tr.moving]
    p = pred[pred.confidence >= det_thr]
    pb = {k: g for k, g in p.groupby("event_id")}
    gb = {k: g for k, g in gt.groupby("event_id")}
    first_hit = {}
    for eid in sorted(frames.event_id):
        if eid not in pb or eid not in gb:
            continue
        for tid in match_tracks(gb[eid], pb[eid]):
            key = (eid // 100000, tid)
            first_hit.setdefault(key, eid)
    det = timely = 0
    rows = []
    for t in tr.itertuples():
        h = first_hit.get((t.seq, t.track_id))
        ok = h is not None
        tl = ok and (h - t.first) <= 10
        det += ok
        timely += tl
        rows.append({"seq": t.seq, "track_id": t.track_id, "class_id": t.class_id, "first": t.first,
                     "detected": ok, "timely": tl, "latency_frames": (h - t.first) if ok else None})
    n = len(tr)
    return {"moving_tracks": n, "track_recall": det / n if n else float("nan"),
            "timely_track_recall": timely / n if n else float("nan")}, pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--split", required=True, choices=["development", "validation", "test"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--det-thr", type=float, default=0.3)
    ap.add_argument("--allow-test", action="store_true", help="only after the R3 configuration is frozen")
    a = ap.parse_args()
    if a.split == "test" and not a.allow_test:
        raise SystemExit("test split is locked until config/r3_frozen.json is committed")
    if os.path.exists(os.path.join(a.out, "metrics.json")):
        print("exists", a.out)
        return 0
    ds = data_r3.load(a.split)
    frames, gt = ds["frames"], ds["gt"]
    if a.detector.startswith("tiy:"):
        det = TIY(a.detector[4:])
    elif a.detector.startswith("yolo:"):
        w, width = a.detector[5:].split("@")
        det = YOLO(w, int(width))
    else:
        model, mode = {"lite0_squash": ("efficientdet_lite0_int8", 1), "lite0_tiled": ("efficientdet_lite0_int8", 3),
                       "lite2_squash": ("efficientdet_lite2_int8", 1)}[a.detector]
        det = MP(model, mode)
    from PIL import Image
    rows = []
    t0 = time.time()
    for fr in frames.itertuples():
        img = np.asarray(Image.open(fr.abs_path).convert("RGB"))
        dets, inf, post = det(img)
        pid = 0
        for cid, s, x1, y1, x2, y2 in dets:
            x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(float(fr.width), x2), min(float(fr.height), y2)
            if x2 <= x1 or y2 <= y1:
                continue
            pid += 1
            rows.append((fr.event_id, pid, cid, data_r3.CLASSES[cid], s, x1, y1, x2, y2, inf, post, a.detector,
                         det.hash))
        if pid == 0:
            rows.append((fr.event_id, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf, post, a.detector, det.hash))
    pred_all = pd.DataFrame(rows, columns=trace_v2.PRED_COLS)
    pred = pred_all[pred_all.prediction_id > 0]
    metrics = coco_eval.evaluate(frames, gt, pred, ds["classes"], score_thresholds=[a.det_thr, 0.5])
    ceil, per_track = track_ceiling(frames, gt, pred, a.det_thr)
    metrics["always_on_frame_ceiling"] = ceil
    tm = pred_all.drop_duplicates("event_id")
    metrics["host_timing_ms"] = {"inference_median": float(tm.host_inference_ms.median()),
                                 "inference_mean": float(tm.host_inference_ms.mean()),
                                 "note": "host CPU, 1 thread, NOT Portenta H7"}
    meta = dict(det.meta)
    meta.update({"detector_name": a.detector, "model_sha256": det.hash, "split": a.split, "det_thr": a.det_thr,
                 "portenta_inference_ms": "NOT MEASURED", "host": platform.platform(), "wall_s": time.time() - t0})
    fr_out = frames.drop(columns=["abs_path"])
    trace_v2.write_trace(a.out, fr_out, gt, pred_all, meta, metrics, {"split": a.split, "detector": a.detector})
    gt.to_csv(os.path.join(a.out, "ground_truth_tracks.csv"), index=False)
    per_track.to_csv(os.path.join(a.out, "track_ceiling.csv"), index=False)
    print(json.dumps({"detector": a.detector, "split": a.split, "mAP50": metrics["mAP50"],
                      "mAP50_95": metrics["mAP50_95"], **ceil,
                      "AP_s/m/l": [metrics["AP_small"], metrics["AP_medium"], metrics["AP_large"]],
                      "R@thr": metrics["operating_points"][0]["recall"],
                      "host_ms": metrics["host_timing_ms"]["inference_median"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
