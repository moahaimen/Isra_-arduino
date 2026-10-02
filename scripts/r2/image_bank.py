#!/usr/bin/env python3
"""Build the R2 image bank: for every real KITTI static-segment frame, the
original image and 15 deterministic image-domain attack variants, with

  * the M4 inputs (96x32 low-res gray, 17x16 fingerprint image), and
  * REAL detector predictions of the stage-1 detector (EfficientDet-Lite0
    INT8) and of the stage-2 detector (EfficientDet-Lite2 INT8) on the
    actual (perturbed) pixels.

Variants (attacker capabilities, see docs/R2_METHOD.md):
  replay perturbations of a recorded frame (variant 0 = exact copy = original)
    1 brightness x0.85   2 brightness x1.15   3 Gaussian noise sigma 6
    4 JPEG quality 40    5 shift (+3,+2) px   6 brightness x1.1 + noise 4 + JPEG 60
    7 shift (-4,0) + noise 3
  trigger-spam stimuli applied to the live frame
    8..11  global illumination flicker x0.55, x0.70, x1.35, x1.60
    12..15 bright flash patch (side 0.25 H, alpha 0.85) at 4 horizontal positions

Noise is seeded by (frame event_id, variant), so the bank is deterministic.
Every simulator run samples from this bank; detectors are never re-run per
mode. Output: <out>/bank_<split>.npz (low-res images, fingerprints) and
<out>/<split>_<model>/ detector trace V2 tables for originals and variants
(event_id = frame_event_id * 100 + variant).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import coco_eval  # noqa: E402
import datasets  # noqa: E402
import frame_features as ff  # noqa: E402
import models  # noqa: E402
import trace_v2  # noqa: E402

REPLAY_VARIANTS = {0: "exact", 1: "brightness_0.85", 2: "brightness_1.15", 3: "noise_6", 4: "jpeg_40",
                   5: "shift_+3_+2", 6: "brightness_1.1+noise_4+jpeg_60", 7: "shift_-4_0+noise_3"}
SPAM_VARIANTS = {8: "flicker_0.55", 9: "flicker_0.70", 10: "flicker_1.35", 11: "flicker_1.60",
                 12: "flash_patch_0", 13: "flash_patch_1", 14: "flash_patch_2", 15: "flash_patch_3"}
VARIANTS = {**REPLAY_VARIANTS, **SPAM_VARIANTS}
SHIFTS = {5: (3, 2), 7: (-4, 0)}


def _noise(img: np.ndarray, sigma: float, key: int) -> np.ndarray:
    rng = np.random.default_rng(key)
    return np.clip(img.astype(np.float64) + rng.normal(0, sigma, img.shape), 0, 255).astype(np.uint8)


def _bright(img, k):
    return np.clip(img.astype(np.float64) * k, 0, 255).astype(np.uint8)


def _jpeg(img, q):
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "JPEG", quality=q)
    return np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))


def _shift(img, dx, dy):
    out = np.empty_like(img)
    H, W = img.shape[:2]
    ys = np.clip(np.arange(H) - dy, 0, H - 1)
    xs = np.clip(np.arange(W) - dx, 0, W - 1)
    out[:] = img[ys][:, xs]
    return out


def _patch(img, k):
    H, W = img.shape[:2]
    s = int(0.25 * H)
    cx = int((k + 0.5) * W / 4)
    y0 = H // 2 - s // 2
    out = img.astype(np.float64)
    out[y0:y0 + s, cx - s // 2:cx + s // 2] = 0.15 * out[y0:y0 + s, cx - s // 2:cx + s // 2] + 0.85 * 255
    return out.astype(np.uint8)


def apply_variant(img: np.ndarray, v: int, key: int) -> np.ndarray:
    if v == 0:
        return img
    if v == 1:
        return _bright(img, 0.85)
    if v == 2:
        return _bright(img, 1.15)
    if v == 3:
        return _noise(img, 6, key)
    if v == 4:
        return _jpeg(img, 40)
    if v == 5:
        return _shift(img, 3, 2)
    if v == 6:
        return _jpeg(_noise(_bright(img, 1.1), 4, key), 60)
    if v == 7:
        return _noise(_shift(img, -4, 0), 3, key)
    if 8 <= v <= 11:
        return _bright(img, [0.55, 0.70, 1.35, 1.60][v - 8])
    if 12 <= v <= 15:
        return _patch(img, v - 12)
    raise ValueError(v)


def variant_gt(gt: pd.DataFrame, v: int, W: int, H: int) -> pd.DataFrame:
    g = gt.copy()
    if v in SHIFTS:
        dx, dy = SHIFTS[v]
        g["x1"] = (g.x1 + dx).clip(0, W)
        g["x2"] = (g.x2 + dx).clip(0, W)
        g["y1"] = (g.y1 + dy).clip(0, H)
        g["y2"] = (g.y2 + dy).clip(0, H)
        g = g[(g.x2 > g.x1) & (g.y2 > g.y1)]
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", default="efficientdet_lite0_int8,efficientdet_lite2_int8")
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(HERE, "..", "detector"))
    from run_real_detector import MediaPipeDetector

    ds = datasets.LOADERS["kitti_tracking"](a.data_root, a.split, "")
    frames, gt = ds["frames"], ds["gt"]
    os.makedirs(a.out, exist_ok=True)
    gt_by = dict(tuple(gt.groupby("event_id")))
    empty = gt.iloc[0:0]
    # --- M4 inputs for every (frame, variant) ---------------------------------
    keys, lows, fps = [], [], []
    vframes, vgt = [], []
    t0 = time.time()
    for fr in frames.itertuples():
        rgb = np.asarray(Image.open(os.path.join(a.data_root, fr.image_path)).convert("RGB"))
        for v in VARIANTS:
            img = apply_variant(rgb, v, fr.event_id * 100 + v)
            L, F = ff.lowres_and_fp(img)
            keys.append(fr.event_id * 100 + v)
            lows.append(L)
            fps.append(F)
            vframes.append({"event_id": fr.event_id * 100 + v, "frame_id": fr.frame_id,
                            "source_sequence": fr.source_sequence, "timestamp_ms": fr.timestamp_ms,
                            "image_path": f"{fr.image_path}#variant={v}:{VARIANTS[v]}", "width": fr.width,
                            "height": fr.height, "split": fr.split})
            g = variant_gt(gt_by.get(fr.event_id, empty), v, fr.width, fr.height).copy()
            g["event_id"] = fr.event_id * 100 + v
            vgt.append(g)
    np.savez_compressed(os.path.join(a.out, f"bank_{a.split}.npz"), keys=np.array(keys, np.int64),
                        lowres=np.stack(lows), fp=np.stack(fps))
    vframes = pd.DataFrame(vframes)
    vgt = pd.concat(vgt, ignore_index=True)
    vgt["gt_id"] = np.arange(1, len(vgt) + 1)
    print(f"M4 inputs for {len(keys)} images in {time.time() - t0:.0f} s", flush=True)
    # --- real detector predictions on every (frame, variant) --------------------
    for mname in a.models.split(","):
        mpath = models.model_path(a.model_dir, mname)
        mhash = trace_v2.sha256_file(mpath)
        assert mhash == models.MODELS[mname]["sha256"]
        det = MediaPipeDetector(mpath, 0.01)
        rows = []
        t0 = time.time()
        for k, fr in enumerate(frames.itertuples()):
            rgb = np.asarray(Image.open(os.path.join(a.data_root, fr.image_path)).convert("RGB"))
            for v in VARIANTS:
                img = apply_variant(rgb, v, fr.event_id * 100 + v)
                dets, inf_ms, post_ms = det(img)
                pid = 0
                for name, score, x1, y1, x2, y2 in dets:
                    cid = ds["coco_to_class_id"].get(name)
                    if cid is None:
                        continue
                    x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(float(fr.width), x2), min(float(fr.height), y2)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    pid += 1
                    rows.append((fr.event_id * 100 + v, pid, cid, ds["classes"][cid], score, x1, y1, x2, y2,
                                 inf_ms, post_ms, mname, mhash))
                if pid == 0:
                    rows.append((fr.event_id * 100 + v, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf_ms, post_ms,
                                 mname, mhash))
            if (k + 1) % 100 == 0:
                print(f"  {mname}: {k + 1}/{len(frames)} frames, {time.time() - t0:.0f} s", flush=True)
        pred_all = pd.DataFrame(rows, columns=trace_v2.PRED_COLS)
        pred = pred_all[pred_all.prediction_id > 0]
        orig = vframes[vframes.event_id % 100 == 0]
        metrics = {"originals": coco_eval.evaluate(orig, vgt[vgt.event_id.isin(orig.event_id)],
                                                   pred[pred.event_id.isin(orig.event_id)], ds["classes"])}
        for v, name in VARIANTS.items():
            if v == 0:
                continue
            fv = vframes[vframes.event_id % 100 == v]
            metrics[f"variant_{v}_{name}"] = coco_map_only = coco_eval.coco_map(
                fv, vgt[vgt.event_id.isin(fv.event_id)], pred[pred.event_id.isin(fv.event_id)], ds["classes"])
        meta = dict(models.MODELS[mname])
        meta.update(models.tflite_complexity(mpath))
        meta.update({"detector_name": mname, "model_sha256": mhash, "dataset": ds["name"], "split": a.split,
                     "class_map": ds["classes"], "variants": VARIANTS,
                     "portenta_inference_ms": "NOT MEASURED (calibration pending)"})
        trace_v2.write_trace(os.path.join(a.out, f"{a.split}_{mname}"), vframes, vgt, pred_all, meta, metrics,
                             {"dataset": ds["name"], "split": a.split, "detector_name": mname,
                              "selection": ds["selection"], "variants": VARIANTS})
        print(f"{mname} {a.split}: originals mAP50={metrics['originals']['mAP50']:.3f} "
              f"mAP50:95={metrics['originals']['mAP50_95']:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
