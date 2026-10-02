#!/usr/bin/env python3
"""Evaluate a trained TinyissimoYOLO checkpoint on PASCAL VOC 2007 test and
write a detector trace V2 (FP32 PyTorch, and INT8 after ONNX export and
ONNX Runtime static post-training quantization).

Runs in the venv of setup.sh (imports the pinned upstream clone). Detections
are produced by the upstream predictor (conf >= 0.001, NMS IoU 0.5, max 100
boxes per image, letterboxed 256x256 input) and scored with the same
pycocotools evaluator as every other detector (scripts/detector/coco_eval.py).

  python scripts/detector/tinyissimo/evaluate.py --weights <run>/weights/last.pt \
      --out data/detector_traces/real/voc2007_test_tinyissimo_v8b_256_fp32
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
sys.path.insert(0, os.path.join(HERE, ".."))
EXT = os.environ.get("EXT", "/home/claude/ext")
UP = os.path.join(EXT, "TinyissimoYOLO")
sys.path.insert(0, UP)

import coco_eval  # noqa: E402
import datasets  # noqa: E402
import trace_v2  # noqa: E402

CONF, IOU, MAXDET, IMGSZ = 0.001, 0.5, 100, 256


def letterbox(img: np.ndarray, size: int):
    import cv2
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    im = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top, left = (size - nh) // 2, (size - nw) // 2
    out = np.full((size, size, 3), 114, np.uint8)
    out[top:top + nh, left:left + nw] = im
    return out, r, left, top


def nms_decode(raw: np.ndarray, r, left, top, W, H):
    """raw: (4 + nc, A) YOLOv8 head output (xywh in input pixels, class scores)."""
    import torch
    import torchvision
    x = torch.from_numpy(raw.T.copy())
    boxes, scores = x[:, :4], x[:, 4:]
    conf, cls = scores.max(1)
    keep = conf > CONF
    boxes, conf, cls = boxes[keep], conf[keep], cls[keep]
    xyxy = torch.cat([boxes[:, :2] - boxes[:, 2:] / 2, boxes[:, :2] + boxes[:, 2:] / 2], 1)
    k = torchvision.ops.batched_nms(xyxy, conf, cls, IOU)[:MAXDET]
    out = []
    for i in k.tolist():
        x1, y1, x2, y2 = xyxy[i].tolist()
        x1, x2 = (x1 - left) / r, (x2 - left) / r
        y1, y2 = (y1 - top) / r, (y2 - top) / r
        out.append((int(cls[i]) + 1, float(conf[i]), max(0.0, x1), max(0.0, y1), min(W, x2), min(H, y2)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--data-root", default="/home/claude/data_r2/voc")
    ap.add_argument("--out", required=True)
    ap.add_argument("--precision", choices=["fp32", "int8"], default="fp32")
    ap.add_argument("--calib", type=int, default=200, help="trainval images for INT8 calibration")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    import cv2
    import torch
    from ultralytics import YOLO

    torch.set_num_threads(1)
    if os.path.exists(a.out) and os.listdir(a.out):
        print("refusing to overwrite", a.out, file=sys.stderr)
        return 2
    yolo = YOLO(a.weights)
    net = yolo.model.float().eval()
    n_params = int(sum(p.numel() for p in net.parameters()))
    os.makedirs(a.out, exist_ok=True)
    onnx_path = os.path.join(os.path.dirname(a.weights), "tinyissimo_v8b_256.onnx")
    if not os.path.exists(onnx_path):
        torch.onnx.export(net, torch.zeros(1, 3, IMGSZ, IMGSZ), onnx_path, opset_version=13,
                          input_names=["images"], output_names=["output0"])
    ds = datasets.load_voc2007(a.data_root, "test")
    frames, gt = ds["frames"], ds["gt"]
    if a.limit:
        frames = frames.head(a.limit)
        gt = gt[gt.event_id.isin(frames.event_id)]
    import onnxruntime as ort
    model_file = onnx_path
    if a.precision == "int8":
        from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
        tv = datasets.load_voc2007(a.data_root, "train")["frames"].head(a.calib)

        class Reader(CalibrationDataReader):
            def __init__(self):
                self.it = iter(tv.itertuples())

            def get_next(self):
                fr = next(self.it, None)
                if fr is None:
                    return None
                img = cv2.cvtColor(cv2.imread(os.path.join(a.data_root, fr.image_path)), cv2.COLOR_BGR2RGB)
                x, *_ = letterbox(img, IMGSZ)
                return {"images": (x.transpose(2, 0, 1)[None].astype(np.float32) / 255.0)}

        model_file = onnx_path.replace(".onnx", "_int8.onnx")
        if not os.path.exists(model_file):
            quantize_static(onnx_path, model_file, Reader(), quant_format=QuantFormat.QDQ,
                            activation_type=QuantType.QInt8, weight_type=QuantType.QInt8, per_channel=True)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    sess = ort.InferenceSession(model_file, so, providers=["CPUExecutionProvider"])
    mhash = trace_v2.sha256_file(model_file)
    rows = []
    t0 = time.time()
    for k, fr in enumerate(frames.itertuples()):
        img = cv2.cvtColor(cv2.imread(os.path.join(a.data_root, fr.image_path)), cv2.COLOR_BGR2RGB)
        x, r, left, top = letterbox(img, IMGSZ)
        inp = x.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        t1 = time.perf_counter()
        raw = sess.run(None, {"images": inp})[0][0]
        inf = (time.perf_counter() - t1) * 1000
        t2 = time.perf_counter()
        dets = nms_decode(raw, r, left, top, float(fr.width), float(fr.height))
        post = (time.perf_counter() - t2) * 1000
        pid = 0
        for cid, sc, x1, y1, x2, y2 in dets:
            if x2 <= x1 or y2 <= y1:
                continue
            pid += 1
            rows.append((fr.event_id, pid, cid, ds["classes"][cid], sc, x1, y1, x2, y2, inf, post,
                         f"tinyissimo_v8b_256_{a.precision}", mhash))
        if pid == 0:
            rows.append((fr.event_id, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf, post,
                         f"tinyissimo_v8b_256_{a.precision}", mhash))
        if (k + 1) % 500 == 0:
            print(f"  {k + 1}/{len(frames)} {time.time() - t0:.0f} s", flush=True)
    pred_all = pd.DataFrame(rows, columns=trace_v2.PRED_COLS)
    pred = pred_all[pred_all.prediction_id > 0]
    metrics = coco_eval.evaluate(frames, gt, pred, ds["classes"])
    tm = pred_all.drop_duplicates("event_id")
    metrics["host_timing_ms"] = {"inference_mean": float(tm.host_inference_ms.mean()),
                                 "inference_median": float(tm.host_inference_ms.median()),
                                 "inference_p95": float(tm.host_inference_ms.quantile(0.95)),
                                 "postprocess_mean": float(tm.host_postprocess_ms.mean()),
                                 "note": "host CPU, ONNX Runtime 1 thread, NOT Portenta H7"}
    rec = json.load(open(os.path.join(os.path.dirname(os.path.dirname(a.weights)), "train_record.json")))
    try:
        from thop import profile
        macs, _ = profile(net, inputs=(torch.zeros(1, 3, IMGSZ, IMGSZ),), verbose=False)
    except Exception:
        macs = float("nan")
    meta = {"detector_name": f"tinyissimo_v8b_256_{a.precision}", "architecture": "TinyissimoYOLO v8 (scale b)",
            "role": "mcu_target", "upstream": rec["upstream"], "upstream_commit": rec["upstream_commit"],
            "parameters": n_params, "macs": float(macs), "model_bytes": os.path.getsize(model_file),
            "model_file": os.path.basename(model_file), "model_sha256": mhash, "precision": a.precision.upper(),
            "input": [IMGSZ, IMGSZ], "training": rec, "training_set": "PASCAL VOC 2007 trainval",
            "confidence_threshold_kept": CONF, "nms_iou": IOU, "max_detections": MAXDET,
            "int8": ("ONNX Runtime static PTQ, QDQ, per-channel weights, "
                     f"{a.calib} VOC07 train calibration images") if a.precision == "int8" else None,
            "dataset": ds["name"], "split": "test", "class_map": ds["classes"],
            "portenta_inference_ms": "NOT MEASURED (calibration pending)",
            "host": {"platform": platform.platform(), "cpu_count": os.cpu_count(), "threads": 1}}
    trace_v2.write_trace(a.out, frames, gt, pred_all, meta, metrics,
                         {"dataset": ds["name"], "split": "test", "detector_name": meta["detector_name"],
                          "model_sha256": mhash})
    print(json.dumps({"mAP50": metrics["mAP50"], "mAP50_95": metrics["mAP50_95"], "params": n_params,
                      "bytes": meta["model_bytes"], "macs": macs}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
