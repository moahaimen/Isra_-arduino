#!/usr/bin/env python3
"""R3 image bank: for every frame of an R3 split and each of the 20 R2
variants (exact/perturbed replay 0-7, spam 8-15, noisy camera 16-19, see
scripts/r2/image_bank.py), the M4 inputs (96x32, 17x16) and REAL detector
predictions of the tiled stage-1 (EfficientDet-Lite0 INT8, 3 tiles) and
tiled stage-2 (EfficientDet-Lite2 INT8, 3 tiles) detectors on the actual
(perturbed) pixels. Keys: event_id * 100 + variant.

  --step m4 | detect (--shard k --nshards n) | merge
Test split only with --allow-test (after config/r3_frozen.json is committed).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "r2"))
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import coco_eval  # noqa: E402
import data_r3  # noqa: E402
import frame_features as ff  # noqa: E402
import trace_v2  # noqa: E402
from image_bank import VARIANTS, apply_variant, variant_gt  # noqa: E402
from run_detector_r3 import MP  # noqa: E402

MODELS = {"lite0_tiled": ("efficientdet_lite0_int8", 3), "lite2_tiled": ("efficientdet_lite2_int8", 3)}
BANK = os.path.join(data_r3.DATA, "bank")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--step", required=True, choices=["m4", "detect", "merge"])
    ap.add_argument("--models", default="lite0_tiled,lite2_tiled")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--allow-test", action="store_true")
    a = ap.parse_args()
    if a.split == "test" and not a.allow_test:
        raise SystemExit("test split is locked until config/r3_frozen.json is committed")
    os.makedirs(BANK, exist_ok=True)
    ds = data_r3.load(a.split)
    frames, gt = ds["frames"], ds["gt"]
    if a.step == "m4":
        keys, lows, fps = [], [], []
        for fr in frames.itertuples():
            rgb = np.asarray(Image.open(fr.abs_path).convert("RGB"))
            for v in VARIANTS:
                L, F = ff.lowres_and_fp(apply_variant(rgb, v, fr.event_id * 100 + v))
                keys.append(fr.event_id * 100 + v)
                lows.append(L)
                fps.append(F)
        np.savez_compressed(os.path.join(BANK, f"bank_{a.split}.npz"), keys=np.array(keys, np.int64),
                            lowres=np.stack(lows), fp=np.stack(fps))
        print("m4", len(keys))
        return 0
    for mname in a.models.split(","):
        if a.step == "detect":
            det = MP(*MODELS[mname])
            rows = []
            sub = frames.iloc[a.shard::a.nshards]
            t0 = time.time()
            for k, fr in enumerate(sub.itertuples()):
                rgb = np.asarray(Image.open(fr.abs_path).convert("RGB"))
                for v in VARIANTS:
                    dets, inf, post = det(apply_variant(rgb, v, fr.event_id * 100 + v), timing=(v == 0))
                    pid = 0
                    for cid, s, x1, y1, x2, y2 in dets:
                        x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(float(fr.width), x2), min(float(fr.height), y2)
                        if x2 <= x1 or y2 <= y1:
                            continue
                        pid += 1
                        rows.append((fr.event_id * 100 + v, pid, cid, data_r3.CLASSES[cid], s, x1, y1, x2, y2, inf,
                                     post, mname, det.hash))
                    if pid == 0:
                        rows.append((fr.event_id * 100 + v, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf, post, mname,
                                     det.hash))
                if (k + 1) % 50 == 0:
                    print(f"{mname} {a.split} shard {a.shard}: {k + 1}/{len(sub)} {time.time() - t0:.0f}s", flush=True)
            pd.DataFrame(rows, columns=trace_v2.PRED_COLS).to_csv(
                os.path.join(BANK, f"{a.split}_{mname}.part{a.shard}.csv"), index=False, float_format="%.5f")
        else:
            parts = [os.path.join(BANK, f"{a.split}_{mname}.part{k}.csv") for k in range(a.nshards)]
            pred_all = pd.concat([pd.read_csv(p) for p in parts]).sort_values(["event_id", "prediction_id"])
            vfr, vgt = [], []
            gt_by = {k: g for k, g in gt.groupby("event_id")}
            for fr in frames.itertuples():
                for v in VARIANTS:
                    vfr.append({"event_id": fr.event_id * 100 + v, "frame_id": fr.frame_id,
                                "source_sequence": fr.source_sequence, "timestamp_ms": fr.timestamp_ms,
                                "image_path": f"{fr.image_path}#variant={v}", "width": fr.width, "height": fr.height,
                                "split": a.split})
                    g = variant_gt(gt_by.get(fr.event_id, gt.iloc[0:0]), v, fr.width, fr.height).copy()
                    g["event_id"] = fr.event_id * 100 + v
                    vgt.append(g)
            vfr = pd.DataFrame(vfr)
            vgt = pd.concat(vgt, ignore_index=True)
            vgt["gt_id"] = np.arange(1, len(vgt) + 1)
            assert set(pred_all.event_id) == set(vfr.event_id)
            pred = pred_all[pred_all.prediction_id > 0]
            orig = vfr[vfr.event_id % 100 == 0]
            metrics = {"originals": coco_eval.evaluate(orig, vgt[vgt.event_id.isin(orig.event_id)],
                                                       pred[pred.event_id.isin(orig.event_id)], ds["classes"])}
            det = MP(*MODELS[mname])
            meta = dict(det.meta)
            meta.update({"detector_name": mname, "tiles": MODELS[mname][1], "split": a.split, "variants": VARIANTS,
                         "portenta_inference_ms": "NOT MEASURED"})
            out = os.path.join(BANK, f"{a.split}_{mname}")
            trace_v2.write_trace(out, vfr, vgt, pred_all, meta, metrics, {"split": a.split, "detector": mname})
            vgt.to_csv(os.path.join(out, "ground_truth_tracks.csv"), index=False)
            for p in parts:
                os.remove(p)
            print(mname, a.split, "originals mAP50", metrics["originals"]["mAP50"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
