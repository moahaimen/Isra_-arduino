"""Detector trace V2: multiple ground-truth and predicted boxes per frame.

A trace directory holds normalized tables (all coordinates in pixels of the
original frame, x1 y1 x2 y2, x2 > x1, y2 > y1):

  frames.csv        event_id, frame_id, source_sequence, timestamp_ms,
                    image_path, width, height, split
  ground_truth.csv  event_id, gt_id, class_id, class_name, x1, y1, x2, y2,
                    ignore            (1 = "difficult"/don't-care region)
  predictions.csv   event_id, prediction_id, class_id, class_name, confidence,
                    x1, y1, x2, y2, host_inference_ms, host_postprocess_ms,
                    detector_name, model_hash
  model_metadata.json, metrics.json, trace_manifest.json

`event_id` is the frame's key everywhere. A trace is produced once by
scripts/detector/run_real_detector.py and replayed unchanged by every
simulator mode; the detector is never re-run per mode.

host_*_ms are measured on the machine that produced the trace. They are NOT
Portenta H7 timings; the simulator uses its own (simulated,
calibration-pending) M7 timing parameters.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

FRAME_COLS = ["event_id", "frame_id", "source_sequence", "timestamp_ms", "image_path", "width", "height", "split"]
GT_COLS = ["event_id", "gt_id", "class_id", "class_name", "x1", "y1", "x2", "y2", "ignore"]
PRED_COLS = ["event_id", "prediction_id", "class_id", "class_name", "confidence", "x1", "y1", "x2", "y2",
             "host_inference_ms", "host_postprocess_ms", "detector_name", "model_hash"]
TABLES = {"frames.csv": FRAME_COLS, "ground_truth.csv": GT_COLS, "predictions.csv": PRED_COLS}


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


@dataclass
class TraceV2:
    frames: pd.DataFrame
    gt: pd.DataFrame
    pred: pd.DataFrame
    metadata: Dict

    def frame_ids(self) -> List[int]:
        return self.frames["event_id"].tolist()


def validate(frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame) -> List[str]:
    """Structural checks; returns a list of problems (empty = valid)."""
    errs = []
    for name, df, cols in (("frames", frames, FRAME_COLS), ("ground_truth", gt, GT_COLS), ("predictions", pred, PRED_COLS)):
        missing = [c for c in cols if c not in df.columns]
        if missing:
            errs.append(f"{name}: missing columns {missing}")
    if errs:
        return errs
    if frames["event_id"].duplicated().any():
        errs.append("frames: duplicated event_id")
    ids = set(frames["event_id"])
    for name, df in (("ground_truth", gt), ("predictions", pred)):
        if len(df) and not set(df["event_id"]).issubset(ids):
            errs.append(f"{name}: event_id not in frames")
        if len(df) and ((df["x2"] <= df["x1"]) | (df["y2"] <= df["y1"])).any():
            errs.append(f"{name}: degenerate box (x2<=x1 or y2<=y1)")
    if len(gt) and gt.duplicated(["event_id", "gt_id"]).any():
        errs.append("ground_truth: duplicated (event_id, gt_id)")
    if len(pred) and pred.duplicated(["event_id", "prediction_id"]).any():
        errs.append("predictions: duplicated (event_id, prediction_id)")
    if len(pred) and ((pred["confidence"] < 0) | (pred["confidence"] > 1)).any():
        errs.append("predictions: confidence outside [0,1]")
    return errs


def write_trace(out_dir: str, frames: pd.DataFrame, gt: pd.DataFrame, pred: pd.DataFrame,
                model_metadata: Dict, metrics: Dict, extra_manifest: Dict | None = None) -> Dict:
    errs = validate(frames, gt, pred)
    if errs:
        raise ValueError("invalid trace: " + "; ".join(errs))
    os.makedirs(out_dir, exist_ok=True)
    frames[FRAME_COLS].to_csv(os.path.join(out_dir, "frames.csv"), index=False)
    gt[GT_COLS].to_csv(os.path.join(out_dir, "ground_truth.csv"), index=False, float_format="%.2f")
    pred[PRED_COLS].to_csv(os.path.join(out_dir, "predictions.csv"), index=False, float_format="%.5f")
    with open(os.path.join(out_dir, "model_metadata.json"), "w") as f:
        json.dump(model_metadata, f, indent=2, sort_keys=True)
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
    manifest = {
        "schema": "detector_trace_v2",
        "n_frames": int(len(frames)),
        "n_gt_boxes": int(len(gt)),
        "n_gt_boxes_non_ignored": int((gt["ignore"] == 0).sum()) if len(gt) else 0,
        "n_predicted_boxes": int(len(pred)),
        "sha256": {t: sha256_file(os.path.join(out_dir, t)) for t in TABLES},
        "timing_note": "host_*_ms are host measurements, NOT Portenta H7 timings",
    }
    manifest.update(extra_manifest or {})
    with open(os.path.join(out_dir, "trace_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest


def read_trace(trace_dir: str, verify_hash: bool = True) -> TraceV2:
    frames = pd.read_csv(os.path.join(trace_dir, "frames.csv"))
    gt = pd.read_csv(os.path.join(trace_dir, "ground_truth.csv"))
    pred = pd.read_csv(os.path.join(trace_dir, "predictions.csv"))
    meta_path = os.path.join(trace_dir, "model_metadata.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    if verify_hash:
        man = json.load(open(os.path.join(trace_dir, "trace_manifest.json")))
        for t, h in man["sha256"].items():
            if sha256_file(os.path.join(trace_dir, t)) != h:
                raise ValueError(f"{t}: hash mismatch with trace_manifest.json")
    errs = validate(frames, gt, pred)
    if errs:
        raise ValueError("invalid trace: " + "; ".join(errs))
    return TraceV2(frames, gt, pred, meta)
