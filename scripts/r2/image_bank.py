#!/usr/bin/env python3
"""Build the R2 image bank: for every real KITTI static-segment frame, the
original image and 19 deterministic image-domain variants, with

  * the M4 inputs (96x32 low-res gray, 17x16 fingerprint image), and
  * REAL detector predictions of the stage-1 detector (EfficientDet-Lite0
    INT8) and of the stage-2 detector (EfficientDet-Lite2 INT8) on the
    actual (perturbed) pixels.

Variants (see docs/R2_METHOD.md):
  replay perturbations of a recorded frame (variant 0 = exact copy = original)
    1 brightness x0.85   2 brightness x1.15   3 Gaussian noise sigma 6
    4 JPEG quality 40    5 shift (+3,+2) px   6 brightness x1.1 + noise 4 + JPEG 60
    7 shift (-4,0) + noise 3
  trigger-spam stimuli applied to the live frame
    8..11  global illumination flicker x0.55, x0.70, x1.35, x1.60
    12..15 bright flash patch (side 0.25 H, alpha 0.85) at 4 horizontal positions
  noisy-camera condition applied to the live frame (benign, not an attack)
    16..19 low light x0.6 with per-frame auto-exposure gain g ~ U(0.85, 1.15),
           Gaussian sensor noise sigma 10 and row (line) noise sigma 4

Random draws are seeded by (frame event_id, variant), so the bank is
deterministic. Every simulator run samples from this bank; detectors are
never re-run per mode. Output: <out>/bank_<split>.npz (low-res images,
fingerprints) and <out>/<split>_<model>/ detector trace V2 tables for
originals and variants (event_id = frame_event_id * 100 + variant).

Detector inference is sharded over frames (--shard k --nshards n writes
<out>/<split>_<model>.part<k>.csv); --merge assembles the trace and metrics.
"""
from __future__ import annotations

import argparse
import io
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
NOISY_VARIANTS = {16: "lowlight_ae_noise_a", 17: "lowlight_ae_noise_b", 18: "lowlight_ae_noise_c",
                  19: "lowlight_ae_noise_d"}
VARIANTS = {**REPLAY_VARIANTS, **SPAM_VARIANTS, **NOISY_VARIANTS}
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


def _noisy_camera(img, key):
    rng = np.random.default_rng(key)
    g = 0.6 * rng.uniform(0.85, 1.15)
    H, W = img.shape[:2]
    x = img.astype(np.float64) * g + rng.normal(0, 10, img.shape) + rng.normal(0, 4, (H, 1, 1))
    return np.clip(x, 0, 255).astype(np.uint8)


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
    if 16 <= v <= 19:
        return _noisy_camera(img, key)
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


def load_split(data_root: str, split: str):
    ds = datasets.LOADERS["kitti_tracking"](data_root, split, "")
    return ds, ds["frames"], ds["gt"]


def variant_tables(frames: pd.DataFrame, gt: pd.DataFrame):
    gt_by = dict(tuple(gt.groupby("event_id")))
    empty = gt.iloc[0:0]
    vframes, vgt = [], []
    for fr in frames.itertuples():
        for v in VARIANTS:
            vframes.append({"event_id": fr.event_id * 100 + v, "frame_id": fr.frame_id,
                            "source_sequence": fr.source_sequence, "timestamp_ms": fr.timestamp_ms,
                            "image_path": f"{fr.image_path}#variant={v}:{VARIANTS[v]}", "width": fr.width,
                            "height": fr.height, "split": fr.split})
            g = variant_gt(gt_by.get(fr.event_id, empty), v, fr.width, fr.height).copy()
            g["event_id"] = fr.event_id * 100 + v
            vgt.append(g)
    vframes = pd.DataFrame(vframes)
    vgt = pd.concat(vgt, ignore_index=True)
    vgt["gt_id"] = np.arange(1, len(vgt) + 1)
    return vframes, vgt


def build_m4(a, frames):
    keys, lows, fps = [], [], []
    t0 = time.time()
    for fr in frames.itertuples():
        rgb = np.asarray(Image.open(os.path.join(a.data_root, fr.image_path)).convert("RGB"))
        for v in VARIANTS:
            img = apply_variant(rgb, v, fr.event_id * 100 + v)
            L, F = ff.lowres_and_fp(img)
            keys.append(fr.event_id * 100 + v)
            lows.append(L)
            fps.append(F)
    np.savez_compressed(os.path.join(a.out, f"bank_{a.split}.npz"), keys=np.array(keys, np.int64),
                        lowres=np.stack(lows), fp=np.stack(fps))
    print(f"M4 inputs for {len(keys)} images in {time.time() - t0:.0f} s", flush=True)


def run_shard(a, ds, frames, mname):
    from run_real_detector import MediaPipeDetector

    mpath = models.model_path(a.model_dir, mname)
    mhash = trace_v2.sha256_file(mpath)
    assert mhash == models.MODELS[mname]["sha256"]
    det = MediaPipeDetector(mpath, 0.01)
    rows = []
    t0 = time.time()
    sub = frames.iloc[a.shard::a.nshards]
    for k, fr in enumerate(sub.itertuples()):
        rgb = np.asarray(Image.open(os.path.join(a.data_root, fr.image_path)).convert("RGB"))
        for v in VARIANTS:
            img = apply_variant(rgb, v, fr.event_id * 100 + v)
            dets, inf_ms, post_ms = det(img, timing=(v == 0))
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
        if (k + 1) % 50 == 0:
            print(f"  {mname} shard {a.shard}/{a.nshards}: {k + 1}/{len(sub)} frames, {time.time() - t0:.0f} s",
                  flush=True)
    pd.DataFrame(rows, columns=trace_v2.PRED_COLS).to_csv(
        os.path.join(a.out, f"{a.split}_{mname}.part{a.shard}.csv"), index=False, float_format="%.5f")


def merge(a, ds, frames, gt, mname):
    parts = [os.path.join(a.out, f"{a.split}_{mname}.part{k}.csv") for k in range(a.nshards)]
    pred_all = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    pred_all = pred_all.sort_values(["event_id", "prediction_id"]).reset_index(drop=True)
    vframes, vgt = variant_tables(frames, gt)
    assert set(pred_all.event_id) == set(vframes.event_id), "missing (frame, variant) predictions"
    pred = pred_all[pred_all.prediction_id > 0]
    orig = vframes[vframes.event_id % 100 == 0]
    metrics = {"originals": coco_eval.evaluate(orig, vgt[vgt.event_id.isin(orig.event_id)],
                                               pred[pred.event_id.isin(orig.event_id)], ds["classes"])}
    t = pred_all[pred_all.event_id % 100 == 0].drop_duplicates("event_id")
    metrics["originals"]["host_timing_ms"] = {
        "inference_mean": float(t.host_inference_ms.mean()), "inference_median": float(t.host_inference_ms.median()),
        "inference_p95": float(t.host_inference_ms.quantile(0.95)), "note": "host CPU, NOT Portenta H7"}
    for v, name in VARIANTS.items():
        if v == 0:
            continue
        fv = vframes[vframes.event_id % 100 == v]
        metrics[f"variant_{v}_{name}"] = coco_eval.coco_map(
            fv, vgt[vgt.event_id.isin(fv.event_id)], pred[pred.event_id.isin(fv.event_id)], ds["classes"])
    mpath = models.model_path(a.model_dir, mname)
    meta = dict(models.MODELS[mname])
    meta.update(models.tflite_complexity(mpath))
    meta.update({"detector_name": mname, "model_sha256": models.MODELS[mname]["sha256"], "dataset": ds["name"],
                 "split": a.split, "class_map": ds["classes"], "variants": VARIANTS,
                 "host_timing_note": "host_inference_ms measured for variant 0 only (NaN for variants)",
                 "portenta_inference_ms": "NOT MEASURED (calibration pending)"})
    trace_v2.write_trace(os.path.join(a.out, f"{a.split}_{mname}"), vframes, vgt, pred_all, meta, metrics,
                         {"dataset": ds["name"], "split": a.split, "detector_name": mname,
                          "selection": ds["selection"], "variants": VARIANTS})
    for p in parts:
        os.remove(p)
    print(f"{mname} {a.split}: originals mAP50={metrics['originals']['mAP50']:.3f} "
          f"mAP50:95={metrics['originals']['mAP50_95']:.3f}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--data-root", default="/home/claude/data_r2/kitti")
    ap.add_argument("--model-dir", default="/home/claude/data_r2/models")
    ap.add_argument("--out", default="/home/claude/data_r2/bank")
    ap.add_argument("--models", default="efficientdet_lite0_int8,efficientdet_lite2_int8")
    ap.add_argument("--step", choices=["m4", "detect", "merge"], required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ds, frames, gt = load_split(a.data_root, a.split)
    if a.step == "m4":
        build_m4(a, frames)
    for mname in a.models.split(","):
        if a.step == "detect":
            run_shard(a, ds, frames, mname)
        elif a.step == "merge":
            merge(a, ds, frames, gt, mname)
    return 0


if __name__ == "__main__":
    sys.exit(main())
