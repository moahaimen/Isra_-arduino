#!/usr/bin/env python3
"""E1 input generation: REAL mode-specific detector outputs and M4 features per frame.

For every frame of an R3 split, EfficientDet-Lite0 INT8 is run on
  LOW   : the whole frame squashed to the 320x320 model input (1 invocation)
  ROI_k : tile k of 3 near-square tiles (1/3 width + 10 % overlap), k = 0,1,2 (1 invocation each)
and FULL is the class-wise NMS merge of ROI_0..2 (exactly the R3 stage-1 'lite0_tiled' detector).
M4 features (no labels, no detector output): BASIC frame-difference fraction m_raw on the 96x32
grayscale image, the same fraction restricted to each tile's columns, and the MOG2 foreground fraction.

Outputs (in --out): preds.csv (mode, event_id, class_id, score, box), m4.csv, gt.csv, frames.csv,
timing.csv (host CPU ms, 1 thread, NOT Cortex-M7), meta.json.
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
for p in ("scripts/r3", "scripts/detector", "scripts/r2"):
    sys.path.insert(0, os.path.join(ROOT, p))
import data_r3  # noqa: E402
import frame_features as ff  # noqa: E402
import models  # noqa: E402
import trace_v2  # noqa: E402
from run_detector_r3 import COCO_KEEP, nms  # noqa: E402
from run_real_detector import MediaPipeDetector  # noqa: E402

NT = 3


def tiles(W):
    tw = int(np.ceil(W / NT * 1.1))
    return tw, np.linspace(0, W - tw, NT).astype(int)


def keep(dets, x0=0):
    return [(COCO_KEEP[n], s, x1 + x0, y1, x2 + x0, y2) for n, s, x1, y1, x2, y2 in dets if n in COCO_KEEP]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["development", "validation", "test"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--timing-every", type=int, default=10)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    import cv2
    from PIL import Image
    path = models.model_path(os.path.join(data_r3.DATA_R2, "models"), "efficientdet_lite0_int8")
    det = MediaPipeDetector(path, 0.01)
    ds = data_r3.load(a.split)
    frames, gt = ds["frames"], ds["gt"]
    rows, m4, tim = [], [], []
    prev_seq, mog, Lprev = None, None, None
    t0 = time.time()
    for i, fr in enumerate(frames.itertuples()):
        img = np.asarray(Image.open(fr.abs_path).convert("RGB"))
        H, W = img.shape[:2]
        timing = (i % a.timing_every) == 0
        out = {}
        d, inf, post = det(img, timing=timing)
        out["LOW"] = keep(d)
        if timing:
            tim.append({"event_id": fr.event_id, "mode": "LOW", "host_invoke_ms": inf})
        tw, starts = tiles(W)
        for k, x0 in enumerate(starts):
            d, inf, post = det(np.ascontiguousarray(img[:, x0:x0 + tw]), timing=timing)
            out[f"ROI{k}"] = keep(d, x0)
            if timing:
                tim.append({"event_id": fr.event_id, "mode": f"ROI{k}", "host_invoke_ms": inf})
        allt = out["ROI0"] + out["ROI1"] + out["ROI2"]
        full = []
        for c in (1, 2):
            dd = [o for o in allt if o[0] == c]
            if dd:
                full += [dd[j] for j in nms(np.array([o[2:] for o in dd]), np.array([o[1] for o in dd]))]
        out["FULL"] = full
        for mode, dl in out.items():
            for cid, s, x1, y1, x2, y2 in dl:
                x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(float(W), x2), min(float(H), y2)
                if x2 > x1 and y2 > y1:
                    rows.append((fr.event_id, mode, cid, s, x1, y1, x2, y2))
        # M4 features (causal, per segment)
        L, _ = ff.lowres_and_fp(img)
        if fr.source_sequence != prev_seq:
            mog = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16.0, detectShadows=False)
            Lprev, prev_seq = None, fr.source_sequence
        D = np.zeros_like(L, dtype=bool) if Lprev is None else (np.abs(L.astype(int) - Lprev.astype(int)) > ff.DELTA_D)
        rec = {"event_id": fr.event_id, "seg": fr.source_sequence, "m_raw": float(D.mean()),
               "mog2_fg": float((mog.apply(L) > 0).mean())}
        for k, x0 in enumerate(starts):
            c0, c1 = int(x0 * ff.LOWRES_W / W), int(np.ceil((x0 + tw) * ff.LOWRES_W / W))
            rec[f"m_tile{k}"] = float(D[:, c0:c1].mean())
        m4.append(rec)
        Lprev = L
        if i % 100 == 0:
            print(a.split, i, len(frames), round(time.time() - t0), flush=True)
    pd.DataFrame(rows, columns=["event_id", "mode", "class_id", "confidence", "x1", "y1", "x2", "y2"]).to_csv(
        os.path.join(a.out, "preds.csv"), index=False)
    pd.DataFrame(m4).to_csv(os.path.join(a.out, "m4.csv"), index=False)
    pd.DataFrame(tim).to_csv(os.path.join(a.out, "timing.csv"), index=False)
    gt.to_csv(os.path.join(a.out, "gt.csv"), index=False)
    frames.drop(columns=["abs_path", "image_path"]).to_csv(os.path.join(a.out, "frames.csv"), index=False)
    meta = {"split": a.split, "model": "efficientdet_lite0_int8", "model_sha256": trace_v2.sha256_file(path),
            "complexity": models.tflite_complexity(path), "tiles": NT, "tile_overlap": 0.1,
            "frames": int(len(frames)), "host": platform.platform(), "wall_s": time.time() - t0,
            "timing_note": "host CPU, 1 thread, NOT Cortex-M7 / Portenta H7"}
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print("done", a.split, len(frames), round(time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
