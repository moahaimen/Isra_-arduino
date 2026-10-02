#!/usr/bin/env python3
"""Build R2 simulator inputs from REAL frames.

For one (split, segment, scenario, intensity, seed) this writes

  wl.jsonl (+ .meta.json)  one observation per displayed camera frame (10 Hz),
                           with M4 features computed by frame_features.step on
                           the DISPLAYED pixels (attack/noise variants included)
  det.csv                  trace_replay detector table: stage 1 = real
                           EfficientDet-Lite0 INT8 output, stage 2 = real
                           EfficientDet-Lite2 INT8 output, on the same
                           displayed image (from the image bank)
  side.csv                 evaluation-only side table: which real frame and
                           which variant was displayed, attack labels

Every operating mode replays exactly these three files, so all methods see
identical frames, ground truth, detector predictions and attack overlay.

Scenarios (overlays on the real frame sequence; all draws keyed by seed):
  clean             original frames
  noisy             every frame shown through a noisy-camera variant 16..19
                    (low light, auto-exposure gain jitter, sensor + row noise)
  spam              trigger-spam events, Poisson rate SPAM_RATE * intensity per
                    second, each lasting 1..3 frames, variant 8..15 (global
                    flicker or bright flash patch) applied to the live frame
  replay_exact      replay sessions, Poisson rate REPLAY_RATE * intensity per
                    second: a clip of 5..15 recorded frames of the same camera,
                    recorded >= 3 s earlier, shown unmodified instead of the
                    live frames
  replay_perturbed  as replay_exact, with one perturbation 1..7 per session
                    (brightness, noise, JPEG, shift, combinations)
  mixed             spam at 0.5 x intensity + replay sessions at 0.5 x
                    intensity (exact or perturbed with probability 1/2)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import frame_features as ff  # noqa: E402

FRAME_MS = 100.0
SPAM_RATE = 0.2       # spam events per second at intensity 1
REPLAY_RATE = 0.1     # replay sessions per second at intensity 1
REPLAY_MIN_AGE_MS = 3000.0
MOG2_HISTORY, MOG2_VAR_THRESHOLD = 500, 16.0
SCENARIOS = ["clean", "noisy", "spam", "replay_exact", "replay_perturbed", "mixed"]
STAGE1 = "efficientdet_lite0_int8"
STAGE2 = "efficientdet_lite2_int8"
KITTI_TO_SIM_CLASS = {1: 1, 2: 2}  # person -> CLS_PERSON, car -> CLS_VEHICLE


def seg_rng(seed: int, seg: str, scenario: str, intensity: float, what: str) -> np.random.Generator:
    h = hashlib.sha256(f"{seed}|{seg}|{scenario}|{intensity:.4f}|{what}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


class Bank:
    """M4 inputs and real detector predictions for every (frame, variant)."""

    def __init__(self, bank_dir: str, split: str):
        b = np.load(os.path.join(bank_dir, f"bank_{split}.npz"))
        self.idx = {int(k): i for i, k in enumerate(b["keys"])}
        self.low, self.fp = b["lowres"], b["fp"]
        self.pred = {}
        for m in (STAGE1, STAGE2):
            p = pd.read_csv(os.path.join(bank_dir, f"{split}_{m}", "predictions.csv"))
            p = p[p.prediction_id > 0]
            self.pred[m] = {k: g for k, g in p.groupby("event_id")}

    def stage(self, model: str, key: int, det_thr: float):
        g = self.pred[model].get(key)
        if g is None or len(g) == 0:
            return 0.0, 0, 0
        i = int(g.confidence.values.argmax())
        return (float(g.confidence.values[i]), KITTI_TO_SIM_CLASS[int(g.class_id.values[i])],
                int((g.confidence.values >= det_thr).sum()))


def segments(split: str) -> List[Dict]:
    sp = json.load(open(os.path.join(HERE, "..", "..", "data", "splits", "r2_kitti_splits.json")))
    return [g for g in sp["segments"] if g["split"] == split]


def seg_name(g: Dict) -> str:
    return f"{g['sequence']}_{g['first_frame']:04d}"


def display_plan(g: Dict, scenario: str, intensity: float, seed: int) -> List[Dict]:
    """Which (source frame, variant) is displayed at each live time step."""
    s = int(g["sequence"])
    live = [s * 100000 + f for f in range(g["first_frame"], g["last_frame"] + 1)]
    n = len(live)
    plan = [{"live": live[i], "src": live[i], "variant": 0, "attack": "none", "session": -1} for i in range(n)]
    name = seg_name(g)
    if scenario == "noisy":
        r = seg_rng(seed, name, scenario, intensity, "noise")
        for p in plan:
            p["variant"] = 16 + int(r.integers(0, 4))
    spam_k = intensity if scenario == "spam" else (0.5 * intensity if scenario == "mixed" else 0.0)
    rep_k = intensity if scenario in ("replay_exact", "replay_perturbed") else (0.5 * intensity if scenario == "mixed" else 0.0)
    sess = 0
    if spam_k > 0:
        r = seg_rng(seed, name, scenario, intensity, "spam")
        t = 0.0
        while True:
            t += r.exponential(1.0 / (SPAM_RATE * spam_k)) * 1000.0
            i0 = int(t // FRAME_MS)
            if i0 >= n:
                break
            dur = int(r.integers(1, 4))
            v = int(r.integers(8, 16))
            sess += 1
            for i in range(i0, min(n, i0 + dur)):
                if plan[i]["attack"] == "none":
                    plan[i].update(variant=v, attack="trigger_spam", session=sess)
    if rep_k > 0:
        r = seg_rng(seed, name, scenario, intensity, "replay")
        t = 0.0
        while True:
            t += r.exponential(1.0 / (REPLAY_RATE * rep_k)) * 1000.0
            i0 = int(t // FRAME_MS)
            if i0 >= n:
                break
            L = int(r.integers(5, 16))
            # source clip must have ended >= REPLAY_MIN_AGE_MS before i0
            max_start = i0 - int(REPLAY_MIN_AGE_MS // FRAME_MS) - L
            if scenario == "replay_exact":
                v = 0
            elif scenario == "replay_perturbed":
                v = int(r.integers(1, 8))
            else:
                v = 0 if r.random() < 0.5 else int(r.integers(1, 8))
            if max_start < 0:
                continue  # nothing old enough recorded yet
            j0 = int(r.integers(0, max_start + 1))
            sess += 1
            for k in range(L):
                i = i0 + k
                if i >= n:
                    break
                plan[i].update(src=live[j0 + k], variant=v, attack="replay", session=sess)
    return plan


def gt_presence(gt: pd.DataFrame, moving: set) -> Dict[int, Dict]:
    out = {}
    g = gt[gt.ignore == 0]
    for eid, grp in g.groupby("event_id"):
        mv = grp[[(int(eid) // 100000, int(t), int(c)) in moving for t, c in zip(grp.track_id, grp.class_id)]]
        out[int(eid)] = {"any": int(grp.class_id.iloc[0]), "moving": int(mv.class_id.iloc[0]) if len(mv) else 0}
    return out


def build(bank: Bank, gt_pres: Dict[int, Dict], g: Dict, scenario: str, intensity: float, seed: int, out: str,
          det_thr: float) -> Dict:
    import cv2
    plan = display_plan(g, scenario, intensity, seed)
    os.makedirs(out, exist_ok=True)
    st = ff.FeatureState()
    # Literature baseline input: MOG2 (Zivkovic 2004; Zivkovic & van der
    # Heijden 2006) on the same 96x32 frames, OpenCV defaults, no shadows.
    mog = cv2.createBackgroundSubtractorMOG2(history=MOG2_HISTORY, varThreshold=MOG2_VAR_THRESHOLD,
                                             detectShadows=False)
    lines, det_rows, side_rows = [], [], []
    for i, p in enumerate(plan):
        key = p["src"] * 100 + p["variant"]
        low = bank.low[bank.idx[key]]
        f = ff.step(st, low, bank.fp[bank.idx[key]])
        mog2_fg = float((mog.apply(low) > 0).mean())
        eid = i + 1
        attack = p["attack"]
        live_content = attack != "replay"
        pres = gt_presence_lookup(gt_pres, p["src"])
        live_pres = gt_presence_lookup(gt_pres, p["live"])
        obj = {
            "event_id": eid, "timestamp_ms": round(i * FRAME_MS, 3), "duration_ms": FRAME_MS,
            "scenario": scenario, "episode_id": p["session"] if attack != "none" else -1,
            "episode_type": "attack" if attack != "none" else ("object" if live_pres["moving"] else "background"),
            "is_legitimate": attack == "none",
            "object_present": bool(live_pres["moving"]) if live_content else False,
            "object_class": cls_name(live_pres["moving"]) if live_content else "none",
            "motion_score": round(f["motion_score"], 4), "visual_score": round(f["visual_score"], 4),
            "temporal_change_score": round(f["temporal_change_score"], 4),
            "sensor_consistency_score": round(f["sensor_consistency_score"], 4),
            "noise_score": round(f["noise_score"], 4), "content_signature": f"{f['sig64']:016x}",
            "attack_type": attack, "replay_id": -1, "burst_id": -1,
            "ground_truth_action": "block" if attack != "none" else ("detect" if live_pres["moving"] else "ignore"),
            "frame_has_object": bool(pres["any"]), "frame_object_class": cls_name(pres["any"]),
            "edge_change_score": round(f["edge_change_score"], 4), "r2_motion": round(f["r2_motion"], 4),
            "r2_temporal": round(f["r2_temporal"], 4), "r2_visual": round(f["r2_visual"], 4),
            "r2_consistency": round(f["r2_consistency"], 4), "mog2_fg": round(mog2_fg, 5),
            "motion_cells": f"{f['motion_cells']:016x}",
            "fp256": "".join(f"{w:016x}" for w in f["fp"]), "fg768": "".join(f"{w:016x}" for w in f["fg"]),
            "fg_count": f["fg_count"],
        }
        lines.append(json.dumps(obj, separators=(",", ":")))
        c1, k1, n1 = bank.stage(STAGE1, key, det_thr)
        c2, k2, n2 = bank.stage(STAGE2, key, det_thr)
        det_rows.append((eid, k1, f"{c1:.5f}", n1, f"{c2:.5f}", k2, n2))
        side_rows.append((eid, p["live"], p["src"], p["variant"], key, attack, p["session"]))
    wl = os.path.join(out, "wl.jsonl")
    with open(wl, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    seconds = len(plan) * FRAME_MS / 1000.0
    meta = {"generator_version": "r2-realframes-1.0", "scenario": scenario, "seed": seed, "seconds": seconds,
            "attack_intensity": intensity, "segment": seg_name(g), "split": g["split"], "num_events": len(plan),
            "frame_ms": FRAME_MS, "spam_rate_per_s": SPAM_RATE, "replay_rate_per_s": REPLAY_RATE,
            "replay_min_age_ms": REPLAY_MIN_AGE_MS, "stage1": STAGE1, "stage2": STAGE2,
            "mog2": {"history": MOG2_HISTORY, "var_threshold": MOG2_VAR_THRESHOLD, "detect_shadows": False}}
    with open(wl + ".meta.json", "w") as fh:
        json.dump(meta, fh, indent=1)
    pd.DataFrame(det_rows, columns=["event_id", "predicted_class", "confidence", "num_boxes",
                                    "second_pass_confidence", "second_pass_predicted_class",
                                    "second_pass_num_boxes"]).to_csv(os.path.join(out, "det.csv"), index=False)
    pd.DataFrame(side_rows, columns=["event_id", "live_frame", "src_frame", "variant", "bank_key", "attack_type",
                                     "session"]).to_csv(os.path.join(out, "side.csv"), index=False)
    return meta


def gt_presence_lookup(pres: Dict[int, Dict], frame: int) -> Dict:
    return pres.get(frame, {"any": 0, "moving": 0})


def cls_name(c: int) -> str:
    return {0: "none", 1: "person", 2: "vehicle"}[KITTI_TO_SIM_CLASS.get(c, 0)]


def moving_tracks(gt: pd.DataFrame, min_disp_px: float = 15.0) -> pd.DataFrame:
    """Pre-registered definition (docs/PREREGISTERED_R2_ANALYSIS.md): a track
    is a MOVING track when its non-ignored boxes span >= 2 frames and the box
    centre moves >= 15 px between its first and last non-ignored frame."""
    g = gt[gt.ignore == 0].copy()
    g["cx"] = (g.x1 + g.x2) / 2
    g["cy"] = (g.y1 + g.y2) / 2
    g["seq"] = g.event_id // 100000
    g = g.sort_values("event_id")
    tr = g.groupby(["seq", "track_id", "class_id"]).agg(
        n=("event_id", "size"), first=("event_id", "min"), last=("event_id", "max"),
        cx0=("cx", "first"), cx1=("cx", "last"), cy0=("cy", "first"), cy1=("cy", "last")).reset_index()
    tr["disp"] = np.hypot(tr.cx1 - tr.cx0, tr.cy1 - tr.cy0)
    tr["moving"] = (tr.n >= 2) & (tr.disp >= min_disp_px)
    return tr


def main() -> int:
    import kitti
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--intensities", default="1")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--bank", default="/home/claude/data_r2/bank")
    ap.add_argument("--data-root", default="/home/claude/data_r2/kitti")
    ap.add_argument("--out", required=True)
    ap.add_argument("--det-thr", type=float, default=0.5)
    a = ap.parse_args()
    bank = Bank(a.bank, a.split)
    gt = kitti.load(a.data_root, a.split)["gt"]
    tr = moving_tracks(gt)
    mv = {(int(r.seq), int(r.track_id), int(r.class_id)) for r in tr[tr.moving].itertuples()}
    pres = gt_presence(gt, mv)
    seeds = [int(x) for x in a.seeds.split(",")] if "," in a.seeds or "-" not in a.seeds else \
        list(range(int(a.seeds.split("-")[0]), int(a.seeds.split("-")[1]) + 1))
    n = 0
    for g in segments(a.split):
        for sc in a.scenarios.split(","):
            for it in [float(x) for x in a.intensities.split(",")]:
                for sd in seeds:
                    build(bank, pres, g, sc, it, sd, os.path.join(a.out, f"{seg_name(g)}/{sc}/i{it:g}/s{sd}"), a.det_thr)
                    n += 1
    print(f"built {n} workloads in {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
