#!/usr/bin/env python3
"""Run a REAL pretrained object detector on REAL annotated frames and write a
detector trace V2 (scripts/detector/trace_v2.py).

  python3 scripts/detector/run_real_detector.py --dataset voc2007 --split test \
      --model efficientdet_lite0_int8 --model-dir <dir> --data-root <dir> \
      --out data/detector_traces/real/<experiment_id>

Steps: load model (SHA-256 checked) -> load frames and ground-truth boxes ->
run inference on every frame -> keep every predicted box above
--min-score (0.01 by default, so mAP sees the full PR curve) -> write
frames/ground_truth/predictions -> compute standard metrics (pycocotools) ->
record model metadata and hashes.

Timing columns are HOST measurements:
  host_inference_ms   raw LiteRT interpreter invoke() on a pre-resized input
                      (1 CPU thread, XNNPACK), measured per frame;
  host_postprocess_ms MediaPipe end-to-end detect() minus host_inference_ms
                      (resize, anchor decoding, NMS), clipped at 0.
They are NOT Portenta H7 timings (docs/R2_DETECTOR.md).
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
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coco_eval  # noqa: E402
import datasets  # noqa: E402
import models  # noqa: E402
import trace_v2  # noqa: E402


class MediaPipeDetector:
    def __init__(self, path: str, min_score: float, max_results: int = 100):
        import mediapipe as mp
        from ai_edge_litert.interpreter import Interpreter
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision

        self.mp = mp
        opts = vision.ObjectDetectorOptions(base_options=mpt.BaseOptions(model_asset_path=path),
                                            max_results=max_results, score_threshold=min_score,
                                            running_mode=vision.RunningMode.IMAGE)
        self.det = vision.ObjectDetector.create_from_options(opts)
        self.it = Interpreter(model_path=path, num_threads=1)
        self.it.allocate_tensors()
        self.inp = self.it.get_input_details()[0]
        self.h, self.w = int(self.inp["shape"][1]), int(self.inp["shape"][2])

    def _raw_invoke_ms(self, img: np.ndarray) -> float:
        x = np.asarray(Image.fromarray(img).resize((self.w, self.h), Image.BILINEAR))
        if self.inp["dtype"] == np.uint8:
            x = x.astype(np.uint8)
        else:
            x = (x.astype(np.float32) - 127.5) / 127.5
        self.it.set_tensor(self.inp["index"], x[None])
        t0 = time.perf_counter()
        self.it.invoke()
        return (time.perf_counter() - t0) * 1000.0

    def __call__(self, img: np.ndarray, timing: bool = True):
        t0 = time.perf_counter()
        r = self.det.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
        total = (time.perf_counter() - t0) * 1000.0
        # timing=False skips the separate raw-invoke measurement (used for
        # attack/noise variants, whose host timing is never used).
        inf = self._raw_invoke_ms(img) if timing else float("nan")
        out = []
        for d in r.detections:
            b = d.bounding_box
            c = d.categories[0]
            out.append((c.category_name, float(c.score), float(b.origin_x), float(b.origin_y),
                        float(b.origin_x + b.width), float(b.origin_y + b.height)))
        return out, inf, (max(0.0, total - inf) if timing else total)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(datasets.LOADERS))
    ap.add_argument("--split", required=True)
    ap.add_argument("--model", required=True, choices=sorted(models.MODELS))
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-score", type=float, default=0.01)
    ap.add_argument("--limit", type=int, default=0, help="first N frames only (0 = all)")
    ap.add_argument("--sequences", default="", help="dataset-specific sequence selection")
    a = ap.parse_args()

    if os.path.exists(a.out) and os.listdir(a.out):
        print(f"refusing to overwrite existing trace {a.out}", file=sys.stderr)
        return 2
    spec = models.MODELS[a.model]
    mpath = models.model_path(a.model_dir, a.model)
    mhash = trace_v2.sha256_file(mpath)
    if mhash != spec["sha256"]:
        print(f"model hash mismatch: {mhash} != {spec['sha256']}", file=sys.stderr)
        return 2
    ds = datasets.LOADERS[a.dataset](a.data_root, a.split, a.sequences)
    frames, gt = ds["frames"], ds["gt"]
    if a.limit:
        frames = frames.head(a.limit)
        gt = gt[gt["event_id"].isin(frames["event_id"])]
    label_map = ds["coco_to_class_id"]
    det = MediaPipeDetector(mpath, a.min_score)
    rows = []
    t_start = time.time()
    for k, fr in enumerate(frames.itertuples()):
        img = np.asarray(Image.open(os.path.join(a.data_root, fr.image_path)).convert("RGB"))
        dets, inf_ms, post_ms = det(img)
        pid = 0
        for name, score, x1, y1, x2, y2 in dets:
            cid = label_map.get(name)
            if cid is None:
                continue  # COCO label outside the evaluated class set
            x1, y1 = max(0.0, x1), max(0.0, y1)
            x2, y2 = min(float(fr.width), x2), min(float(fr.height), y2)
            if x2 <= x1 or y2 <= y1:
                continue
            pid += 1
            rows.append((fr.event_id, pid, cid, ds["classes"][cid], score, x1, y1, x2, y2, inf_ms, post_ms, a.model, mhash))
        if pid == 0:  # keep the frame's timing even when nothing was predicted
            rows.append((fr.event_id, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf_ms, post_ms, a.model, mhash))
        if (k + 1) % 500 == 0:
            print(f"  {k + 1}/{len(frames)} frames, {time.time() - t_start:.0f} s", flush=True)
    pred_all = pd.DataFrame(rows, columns=trace_v2.PRED_COLS)
    # prediction_id 0 rows are timing placeholders for frames without boxes;
    # they are kept in predictions.csv (class_id -1, confidence 0) so per-frame
    # host timing is preserved, and excluded from every metric.
    pred = pred_all[pred_all["prediction_id"] > 0]
    metrics = coco_eval.evaluate(frames, gt, pred, ds["classes"])
    timing = pred_all.drop_duplicates("event_id")
    metrics["host_timing_ms"] = {
        "inference_mean": float(timing.host_inference_ms.mean()), "inference_median": float(timing.host_inference_ms.median()),
        "inference_p95": float(timing.host_inference_ms.quantile(0.95)),
        "postprocess_mean": float(timing.host_postprocess_ms.mean()),
        "note": "host CPU (see model_metadata.host), NOT Portenta H7",
    }
    meta = dict(spec)
    meta.update(models.tflite_complexity(mpath))
    meta.update({
        "detector_name": a.model, "model_sha256": mhash, "min_score_kept": a.min_score, "max_results": 100,
        "nms": "MediaPipe ObjectDetector default (IoU 0.5 per-class NMS as configured in the model)",
        "dataset": ds["name"], "split": a.split, "class_map": ds["classes"],
        "portenta_inference_ms": "NOT MEASURED (calibration pending)",
        "host": {"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
                 "cpu_count": os.cpu_count(), "python": platform.python_version(), "litert_threads": 1},
        "runtime": {"mediapipe": __import__("mediapipe").__version__,
                    "ai_edge_litert": __import__("importlib.metadata").metadata.version("ai-edge-litert")},
    })
    man = trace_v2.write_trace(a.out, frames, gt, pred_all, meta, metrics,
                               {"dataset": ds["name"], "split": a.split, "detector_name": a.model,
                                "model_sha256": mhash, "selection": ds.get("selection", {})})
    print(json.dumps({"out": a.out, "mAP50": metrics["mAP50"], "mAP50_95": metrics["mAP50_95"],
                      "frames": man["n_frames"], "gt": man["n_gt_boxes"], "pred": int(len(pred))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
