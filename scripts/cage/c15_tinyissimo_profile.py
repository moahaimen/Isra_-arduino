#!/usr/bin/env python3
"""C1.5: measured Tinyissimo host forward + NMS timing, NOT Portenta energy.

Run inside the pinned TinyissimoYOLO Ultralytics environment. Only use
development/validation images; never supply locked-test images.
Example:
 python scripts/cage/c15_tinyissimo_profile.py --checkpoint /path/best.pt \
   --images /path/to/allowed/validation/images --output /tmp/c15.csv
"""
import argparse
import csv
import hashlib
import json
import statistics
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO
from ultralytics.utils import ops

def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)

def timed(fn, device):
    synchronize(device)
    start = time.perf_counter_ns()
    value = fn()
    synchronize(device)
    return value, (time.perf_counter_ns() - start) / 1e6

def tensor_image(path, device, size):
    # Controlled fixed-shape RGB input. No hidden resizing or file I/O in timings.
    im = Image.open(path).convert("RGB").resize((size, size))
    a = np.asarray(im).copy()
    return torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).to(device).float() / 255.0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.7)
    p.add_argument("--max-det", type=int, default=300)
    p.add_argument("--max-nms", type=int, default=30000)
    a = p.parse_args()
    if not a.checkpoint.is_file():
        p.error("Checkpoint not found")
    paths = sorted(x for x in a.images.rglob("*") if x.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not paths:
        p.error("No images found")
    if a.repeats < 1:
        p.error("--repeats must be >=1")
    device = torch.device(a.device)
    detector = YOLO(str(a.checkpoint))
    model = detector.model.to(device).eval()
    # Ultralytics NMS supports pre-NMS selection via conf threshold. Model output
    # shapes vary across upstream revisions; fail rather than silently fabricate.
    rows = []
    with torch.inference_mode():
        for path in paths:
            x = tensor_image(path, device, a.size)
            for _ in range(a.warmup):
                pred = model(x)
                raw = pred[0] if isinstance(pred, (tuple, list)) else pred
                if not isinstance(raw, torch.Tensor) or raw.ndim != 3:
                    raise RuntimeError(f"Unexpected raw detector output shape/type: {type(raw)}")
                ops.non_max_suppression(raw, a.conf, a.iou, max_det=a.max_det,
                                        max_nms=a.max_nms)
            for repeat in range(a.repeats):
                pred, forward_ms = timed(lambda: model(x), device)
                raw = pred[0] if isinstance(pred, (tuple, list)) else pred
                if not isinstance(raw, torch.Tensor) or raw.ndim != 3:
                    raise RuntimeError(f"Unexpected raw output: {type(raw)}")
                # Ultralytics raw predictions usually [B,4+nc,N]; check format
                # explicitly. This is a confidence-filter candidate proxy, not
                # the exact internal NMS comparison count.
                nc = int(getattr(model, "nc", len(getattr(model, "names", {}))))
                if raw.shape[1] != nc + 4:
                    raise RuntimeError(f"Unexpected raw shape {tuple(raw.shape)} for nc={nc}; inspect version")
                candidates = int((raw[0, 4:, :].amax(dim=0) > a.conf).sum().item())
                boxes, nms_ms = timed(
                    lambda: ops.non_max_suppression(raw, a.conf, a.iou,
                        max_det=a.max_det, max_nms=a.max_nms), device)
                rows.append({
                    "image": str(path), "repeat": repeat,
                    "raw_candidates_above_conf": candidates,
                    "final_boxes": len(boxes[0]), "forward_ms": forward_ms,
                    "nms_ms": nms_ms, "total_ms": forward_ms + nms_ms
                })
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["image"], []).append(row)
    medians = [statistics.median(v["total_ms"] for v in rs) for rs in grouped.values()]
    summary = {
        "status": "MEASURED_HOST_ONLY",
        "checkpoint_sha256": hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        "device": str(device), "images": len(grouped), "repeats": a.repeats,
        "size": a.size, "conf": a.conf, "iou": a.iou,
        "median_image_total_ms": statistics.median(medians),
        "max_over_median_image_total": max(medians) / statistics.median(medians),
        "limitations": [
            "No adversarial inputs generated; natural-image variation only",
            "No measured energy or Portenta timing",
            "Pre-NMS candidate proxy excludes exact NMS internal comparison counts",
            "Forward and NMS measured separately; preprocessing excluded",
            "Model compatibility with installed Ultralytics must be smoke-tested"
        ]
    }
    summary_path = a.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
