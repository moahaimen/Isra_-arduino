#!/usr/bin/env python3
"""Gate A table (validation split only): every candidate detector's real
mAP50 / mAP50:95 / per-class / size-bucket AP, operating-point recall at the
shared detection threshold, and the FRAME-LEVEL always-on ceiling (moving-track
recall and timely recall when the detector sees every frame). The SIMULATED
always-on ceiling (M7 slower than the camera) comes from the Gate-B runs."""
import glob, json, os, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "detector")); sys.path.insert(0, os.path.join(HERE, "..", "r2"))
import data_r3, coco_eval
from run_detector_r3 import track_ceiling
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
THR = json.load(open(os.path.join(ROOT, "results", "r3", "tuning", "common.json")))["detection_threshold"]
gt_tracks = data_r3.load("validation", with_images=False)["gt"]
rows = []
def add(name, role, frames, gt, pred, meta):
    m = coco_eval.evaluate(frames, gt, pred, data_r3.CLASSES, score_thresholds=[THR])
    ceil, _ = track_ceiling(frames, gt_tracks, pred, THR)
    rows.append({"detector": name, "role": role, "params_M": meta.get("parameters", float("nan")) / 1e6,
                 "GMACs": meta.get("macs", float("nan")) / 1e9 * (meta.get("tiles", 1) if "tiy" not in name else 1),
                 "mAP50": m["mAP50"], "mAP50_95": m["mAP50_95"], "AP50_person": m["per_class"]["person"]["AP50"],
                 "AP50_car": m["per_class"]["car"]["AP50"], "AP_small": m["AP_small"], "AP_medium": m["AP_medium"],
                 "AP_large": m["AP_large"], f"P@{THR}": m["operating_points"][0]["precision"],
                 f"R@{THR}": m["operating_points"][0]["recall"], "moving_tracks": ceil["moving_tracks"],
                 "track_recall_ceiling": ceil["track_recall"], "timely_recall_ceiling": ceil["timely_track_recall"]})
for d in sorted(glob.glob(os.path.join(data_r3.DATA, "gate_a", "val_*"))):
    fr, gt, pr = (pd.read_csv(os.path.join(d, x)) for x in ("frames.csv", "ground_truth.csv", "predictions.csv"))
    meta = json.load(open(os.path.join(d, "model_metadata.json")))
    nm = os.path.basename(d)[4:]
    role = "mcu_target" if "tiy" in nm else "host_reference"
    if nm.endswith("_tiled") and "tiy" not in nm: meta["tiles"] = 3
    add(nm, role, fr, gt, pr[pr.prediction_id > 0], meta)
for m in ("lite2_tiled",):
    d = os.path.join(data_r3.DATA, "bank", f"validation_{m}")
    fr, gt, pr = (pd.read_csv(os.path.join(d, x)) for x in ("frames.csv", "ground_truth.csv", "predictions.csv"))
    o = fr[fr.event_id % 100 == 0].copy(); o["event_id"] //= 100
    g = gt[gt.event_id % 100 == 0].copy(); g["event_id"] //= 100
    p = pr[(pr.prediction_id > 0) & (pr.event_id % 100 == 0)].copy(); p["event_id"] //= 100
    add(m, "host_reference (stage 2)", o, g, p, json.load(open(os.path.join(d, "model_metadata.json"))) | {"tiles": 3})
t = pd.DataFrame(rows)
os.makedirs(os.path.join(ROOT, "results", "r3", "gate_a"), exist_ok=True)
t.to_csv(os.path.join(ROOT, "results", "r3", "gate_a", "detectors_validation.csv"), index=False)
print(t.round(3).to_string())
