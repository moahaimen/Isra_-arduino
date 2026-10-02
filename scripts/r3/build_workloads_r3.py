#!/usr/bin/env python3
"""R3 simulator inputs from REAL frames (extends scripts/r2/build_workloads.py).

Per (split, segment, scenario, intensity, seed):
  wl.jsonl   observations at 10 Hz with the R2 M4 features, the MOG2 input,
             and the R3 24x8 block thumbnail (thumb192), computed from the
             DISPLAYED pixels;
  det.csv    REAL tiled stage-1 (EfficientDet-Lite0 INT8, 3 tiles) and
             stage-2 (EfficientDet-Lite2 INT8, 3 tiles) outputs on the same
             displayed image, plus the 12x4 M4-cell mask of the boxes >= the
             detection threshold (what the M7 result tells the M4);
  side.csv   evaluation-only: displayed (frame, variant), attack labels.
Scenarios and overlay processes are those of R2 (same code path).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "r2"))
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import build_workloads as bw2  # noqa: E402
import data_r3  # noqa: E402
import frame_features as ff  # noqa: E402

STAGE1, STAGE2 = "lite0_tiled", "lite2_tiled"
SCENARIOS = bw2.SCENARIOS
FRAME_W, FRAME_H = 1242.0, 375.0


def thumb192(L: np.ndarray) -> np.ndarray:
    """4x4 block means of the 96x32 frame (integer mean, M4 arithmetic)."""
    return (L.astype(np.uint32).reshape(8, 4, 24, 4).sum(axis=(1, 3)) // 16).astype(np.uint8).reshape(-1)


def box_cells(x1, y1, x2, y2, W=FRAME_W, H=FRAME_H) -> int:
    cw, ch = W / 12.0, H / 4.0
    m = 0
    for cy in range(4):
        for cx in range(12):
            if x1 < (cx + 1) * cw and x2 > cx * cw and y1 < (cy + 1) * ch and y2 > cy * ch:
                m |= 1 << (cy * 12 + cx)
    return m


class Bank:
    def __init__(self, split: str, det_thr: float):
        b = np.load(os.path.join(data_r3.DATA, "bank", f"bank_{split}.npz"))
        self.idx = {int(k): i for i, k in enumerate(b["keys"])}
        self.low, self.fp = b["lowres"], b["fp"]
        self.stage = {}
        for m in (STAGE1, STAGE2):
            p = pd.read_csv(os.path.join(data_r3.DATA, "bank", f"{split}_{m}", "predictions.csv"))
            p = p[p.prediction_id > 0]
            out = {}
            for k, g in p.groupby("event_id"):
                i = int(g.confidence.values.argmax())
                hi = g[g.confidence >= det_thr]
                cells = 0
                for r in hi.itertuples():
                    cells |= box_cells(r.x1, r.y1, r.x2, r.y2)
                out[int(k)] = (float(g.confidence.values[i]), int(g.class_id.values[i]), len(hi), cells)
            self.stage[m] = out

    def get(self, m, key):
        return self.stage[m].get(key, (0.0, 0, 0, 0))


def seg_rng(seed, seg, scenario, intensity, what):
    h = hashlib.sha256(f"{seed}|{seg}|{scenario}|{intensity:.4f}|{what}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def display_plan(g, scenario, intensity, seed):
    """R2 overlay processes (bw2.display_plan) with R3 segment keys."""
    sk = data_r3.seq_key(g)
    g2 = {"sequence": f"{sk:04d}", "first_frame": g["first_frame"], "last_frame": g["last_frame"]}
    plan = bw2.display_plan(g2, scenario, intensity, seed)
    return plan


def presence(gt: pd.DataFrame, moving: set):
    out = {}
    g = gt[gt.ignore == 0]
    for eid, grp in g.groupby("event_id"):
        mv = grp[[(int(eid) // 100000, int(t), int(c)) in moving for t, c in zip(grp.track_id, grp.class_id)]]
        out[int(eid)] = {"any": int(grp.class_id.iloc[0]), "moving": int(mv.class_id.iloc[0]) if len(mv) else 0}
    return out


def build(bank: Bank, pres, g, scenario, intensity, seed, out, det_thr):
    import cv2
    plan = display_plan(g, scenario, intensity, seed)
    os.makedirs(out, exist_ok=True)
    st = ff.FeatureState()
    mog = cv2.createBackgroundSubtractorMOG2(history=bw2.MOG2_HISTORY, varThreshold=bw2.MOG2_VAR_THRESHOLD,
                                             detectShadows=False)
    lines, det_rows, side_rows = [], [], []
    cls = {0: "none", 1: "person", 2: "vehicle"}
    for i, p in enumerate(plan):
        key = p["src"] * 100 + p["variant"]
        low = bank.low[bank.idx[key]]
        f = ff.step(st, low, bank.fp[bank.idx[key]])
        mog2_fg = float((mog.apply(low) > 0).mean())
        attack = p["attack"]
        live_content = attack != "replay"
        sp = pres.get(p["src"], {"any": 0, "moving": 0})
        lp = pres.get(p["live"], {"any": 0, "moving": 0})
        th = thumb192(low)
        obj = {"event_id": i + 1, "timestamp_ms": round(i * bw2.FRAME_MS, 3), "duration_ms": bw2.FRAME_MS,
               "scenario": scenario, "episode_id": p["session"] if attack != "none" else -1,
               "episode_type": "attack" if attack != "none" else ("object" if lp["moving"] else "background"),
               "is_legitimate": attack == "none", "object_present": bool(lp["moving"]) if live_content else False,
               "object_class": cls[lp["moving"]] if live_content else "none",
               "motion_score": round(f["motion_score"], 4), "visual_score": round(f["visual_score"], 4),
               "temporal_change_score": round(f["temporal_change_score"], 4),
               "sensor_consistency_score": round(f["sensor_consistency_score"], 4),
               "noise_score": round(f["noise_score"], 4), "content_signature": f"{f['sig64']:016x}",
               "attack_type": attack, "replay_id": -1, "burst_id": -1,
               "ground_truth_action": "block" if attack != "none" else ("detect" if lp["moving"] else "ignore"),
               "frame_has_object": bool(sp["any"]), "frame_object_class": cls[sp["any"]],
               "edge_change_score": round(f["edge_change_score"], 4), "r2_motion": round(f["r2_motion"], 4),
               "r2_temporal": round(f["r2_temporal"], 4), "r2_visual": round(f["r2_visual"], 4),
               "r2_consistency": round(f["r2_consistency"], 4), "mog2_fg": round(mog2_fg, 5),
               "motion_cells": f"{f['motion_cells']:016x}", "fp256": "".join(f"{w:016x}" for w in f["fp"]),
               "fg768": "".join(f"{w:016x}" for w in f["fg"]), "fg_count": f["fg_count"],
               "thumb192": th.tobytes().hex()}
        lines.append(json.dumps(obj, separators=(",", ":")))
        c1, k1, n1, m1 = bank.get(STAGE1, key)
        c2, k2, n2, m2 = bank.get(STAGE2, key)
        det_rows.append((i + 1, k1, f"{c1:.5f}", n1, f"{m1:016x}", f"{c2:.5f}", k2, n2, f"{m2:016x}"))
        side_rows.append((i + 1, p["live"], p["src"], p["variant"], key, attack, p["session"]))
    wl = os.path.join(out, "wl.jsonl")
    with open(wl, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    meta = {"generator_version": "r3-realframes-1.0", "scenario": scenario, "seed": seed,
            "seconds": len(plan) * bw2.FRAME_MS / 1000.0, "attack_intensity": intensity,
            "segment": data_r3.seg_name(g), "seq_key": data_r3.seq_key(g), "first_frame": g["first_frame"],
            "split": g["split"], "num_events": len(plan), "stage1": STAGE1, "stage2": STAGE2, "det_thr": det_thr}
    json.dump(meta, open(wl + ".meta.json", "w"), indent=1)
    pd.DataFrame(det_rows, columns=["event_id", "predicted_class", "confidence", "num_boxes", "s1_cells",
                                    "second_pass_confidence", "second_pass_predicted_class", "second_pass_num_boxes",
                                    "s2_cells"]).to_csv(os.path.join(out, "det.csv"), index=False)
    pd.DataFrame(side_rows, columns=["event_id", "live_frame", "src_frame", "variant", "bank_key", "attack_type",
                                     "session"]).to_csv(os.path.join(out, "side.csv"), index=False)
    return meta
