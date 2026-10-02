#!/usr/bin/env python3
"""MEVA image bank for R3.1: for every extracted frame of a group and each of the 20
variants of scripts/r2/image_bank.py (exact/perturbed replay 0-7, spam 8-15, noisy
camera 16-19): the M4 inputs (96x32 and 17x16 gray) and the real stage-1 detector
output (EfficientDet-Lite0 INT8 on 2 near-square tiles) on the perturbed pixels.
Keys: event_id * 100 + variant, event_id = seq_key * 100000 + frame_index.
Steps: m4 | detect (--shard/--nshards) | merge. Test groups refuse to run."""
import argparse, json, os, sys, time
import cv2, numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib31  # noqa: E402
from image_bank import VARIANTS, apply_variant  # noqa: E402
from run_detector_r3 import MP  # noqa: E402
import frame_features as ff  # noqa: E402
import trace_v2  # noqa: E402

BANK = os.path.join(lib31.D31, "bank")


def frames_of(seg):
    d = os.path.join(lib31.D31, "meva", seg["group"])
    return sorted(f for f in os.listdir(d) if f.endswith(".jpg"))


def load_rgb(seg, f):
    return cv2.cvtColor(cv2.imread(os.path.join(lib31.D31, "meva", seg["group"], f)), cv2.COLOR_BGR2RGB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True)
    ap.add_argument("--step", required=True, choices=["m4", "detect", "merge"])
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    seg = next(s for s in lib31.segments("development") + lib31.segments("validation") if s["group"] == a.group)
    os.makedirs(BANK, exist_ok=True)
    files = frames_of(seg)
    sk = seg["seq_key"]
    if a.step == "m4":
        keys, lows, fps = [], [], []
        for i, f in enumerate(files):
            rgb = load_rgb(seg, f)
            for v in VARIANTS:
                L, F = ff.lowres_and_fp(apply_variant(rgb, v, (sk * 100000 + i) * 100 + v))
                keys.append((sk * 100000 + i) * 100 + v); lows.append(L); fps.append(F)
        np.savez_compressed(os.path.join(BANK, f"meva_{a.group}.npz"), keys=np.array(keys, np.int64), lowres=np.stack(lows), fp=np.stack(fps))
        print("m4", a.group, len(keys)); return
    name = "lite0_tiled2"
    if a.step == "detect":
        det = MP("efficientdet_lite0_int8", 2)
        rows, t0 = [], time.time()
        for i in range(a.shard, len(files), a.nshards):
            rgb = load_rgb(seg, files[i])
            for v in VARIANTS:
                key = (sk * 100000 + i) * 100 + v
                dets, inf, post = det(apply_variant(rgb, v, key), timing=(v == 0))
                pid = 0
                for cid, s, x1, y1, x2, y2 in dets:
                    x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(1280.0, x2), min(720.0, y2)
                    if x2 <= x1 or y2 <= y1: continue
                    pid += 1; rows.append((key, pid, cid, {1: "person", 2: "car"}[cid], s, x1, y1, x2, y2, inf, post, name, det.hash))
                if pid == 0: rows.append((key, 0, -1, "none", 0.0, 0.0, 0.0, 1.0, 1.0, inf, post, name, det.hash))
            if (i // a.nshards) % 50 == 0: print(a.group, a.shard, i, f"{time.time()-t0:.0f}s", flush=True)
        pd.DataFrame(rows, columns=trace_v2.PRED_COLS).to_csv(os.path.join(BANK, f"meva_{a.group}_{name}.part{a.shard}.csv"), index=False, float_format="%.5f")
    else:
        parts = [os.path.join(BANK, f"meva_{a.group}_{name}.part{k}.csv") for k in range(a.nshards)]
        p = pd.concat([pd.read_csv(x) for x in parts]).sort_values(["event_id", "prediction_id"])
        assert len(set(p.event_id)) == len(files) * len(VARIANTS), (len(set(p.event_id)), len(files) * len(VARIANTS))
        out = os.path.join(BANK, f"meva_{a.group}_{name}"); os.makedirs(out, exist_ok=True)
        p.to_csv(os.path.join(out, "predictions.csv"), index=False)
        json.dump({"detector": name, "tiles": 2, "n_events": int(len(set(p.event_id))), "model_sha256": str(p.model_hash.iloc[0])},
                  open(os.path.join(out, "meta.json"), "w"))
        for x in parts: os.remove(x)
        print("merged", a.group)


if __name__ == "__main__":
    main()
