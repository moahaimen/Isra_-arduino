#!/usr/bin/env python3
"""R2 metrics for one simulator run on a real-frame workload.

Everything is derived from the simulator outputs (observations.csv,
summary.json, states.csv, wake_intervals.csv), the workload's evaluation-only
side table (side.csv: which real frame/variant was displayed, attack labels)
and the REAL detector predictions of the image bank. Pre-registered
definitions (docs/PREREGISTERED_R2_ANALYSIS.md):

* Moving track: KITTI track whose non-ignored boxes span >= 2 frames and
  whose box centre moves >= 15 px between first and last non-ignored frame.
* A processed frame DETECTS a track when the real detector output of the
  stage the M7 actually ran last (stage 1 = EfficientDet-Lite0 on early exit,
  else stage 2 = EfficientDet-Lite2), restricted to boxes with confidence >=
  the detection threshold, matches the track's non-ignored GT box in that
  frame one-to-one (same class, IoU >= 0.5, greedy by confidence). Only
  frames that show LIVE content count: a replayed (old) frame never detects a
  live track.
* Track recall = detected moving tracks / moving tracks.
  Timely recall = tracks detected within 1.0 s of their onset (first
  non-ignored frame). Burst tracks = moving tracks whose onset lies within
  2.0 s of another moving track's onset in the same segment.
* Attack success = attack frames whose request reached the M7 detector
  (detection started) / attack frames.
* FRR = legitimate (non-attack) requests blocked by the gate / legitimate
  requests evaluated by the gate.
* Energy is MODELED (uncalibrated power assumptions x simulated state times).
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from typing import Dict, FrozenSet, Tuple

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
from build_workloads import STAGE1, STAGE2, FRAME_MS, moving_tracks  # noqa: E402
from coco_eval import iou_xyxy  # noqa: E402

NAN = float("nan")
TIMELY_MS = 1000.0
BURST_WINDOW_MS = 2000.0
LIVE_VARIANTS = set(range(8, 20)) | {0}


def sdiv(a, b):
    return float(a) / float(b) if b else NAN


def match_tracks(gt: pd.DataFrame, pred: pd.DataFrame, iou_thr: float = 0.5) -> FrozenSet[int]:
    """Track ids of non-ignored GT boxes matched one-to-one by predictions."""
    gt = gt[gt["ignore"] == 0]
    if len(gt) == 0 or len(pred) == 0:
        return frozenset()
    used, hit = set(), set()
    for p in pred.sort_values("confidence", ascending=False).itertuples():
        best, bi = iou_thr, None
        for gi, g in enumerate(gt.itertuples()):
            if gi in used or g.class_id != p.class_id:
                continue
            o = iou_xyxy((p.x1, p.y1, p.x2, p.y2), (g.x1, g.y1, g.x2, g.y2))
            if o >= best:
                best, bi = o, gi
        if bi is not None:
            used.add(bi)
            hit.add(int(gt.iloc[bi]["track_id"]))
    return frozenset(hit)


class SplitContext:
    """GT tracks and per-(frame, variant, stage) matched track sets for one split."""

    def __init__(self, split: str, bank_dir: str, data_root: str, det_thr: float, cache_dir: str):
        import kitti
        self.split, self.det_thr = split, det_thr
        cache = os.path.join(cache_dir, f"ctx_{split}_thr{det_thr:.3f}.pkl")
        if os.path.exists(cache):
            with open(cache, "rb") as fh:
                self.__dict__.update(pickle.load(fh))
            return
        gt = kitti.load(data_root, split)["gt"]
        tr = moving_tracks(gt)
        self.tracks = tr[tr.moving].copy()
        gt_by = {k: g for k, g in gt.groupby("event_id")}
        empty = gt.iloc[0:0]
        self.hits: Dict[str, Dict[int, FrozenSet[int]]] = {}
        for m in (STAGE1, STAGE2):
            p = pd.read_csv(os.path.join(bank_dir, f"{split}_{m}", "predictions.csv"))
            p = p[(p.prediction_id > 0) & (p.confidence >= det_thr)]
            by = {k: g for k, g in p.groupby("event_id")}
            h = {}
            for key, g in by.items():
                v = key % 100
                if v not in LIVE_VARIANTS:
                    continue  # replay variants never credit live tracks
                h[int(key)] = match_tracks(gt_by.get(key // 100, empty), g)
            self.hits[m] = h
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache, "wb") as fh:
            pickle.dump({"split": split, "det_thr": det_thr, "tracks": self.tracks, "hits": self.hits}, fh)

    def segment_tracks(self, seq: int, first: int, last: int) -> pd.DataFrame:
        t = self.tracks[self.tracks.seq == seq]
        lo, hi = seq * 100000 + first, seq * 100000 + last
        t = t[(t["first"] >= lo) & (t["first"] <= hi)].copy()
        t["onset_ms"] = (t["first"] - lo) * FRAME_MS
        on = np.sort(t.onset_ms.values)
        t["burst"] = [((np.abs(on - x) <= BURST_WINDOW_MS).sum() >= 2) for x in t.onset_ms.values]
        return t


def run_metrics(run_dir: str, wl_dir: str, ctx: SplitContext) -> Dict:
    summ = json.load(open(os.path.join(run_dir, "summary.json")))
    meta = json.load(open(os.path.join(wl_dir, "wl.jsonl.meta.json")))
    obs = pd.read_csv(os.path.join(run_dir, "observations.csv"), keep_default_na=False)
    side = pd.read_csv(os.path.join(wl_dir, "side.csv"))
    states = pd.read_csv(os.path.join(run_dir, "states.csv"))
    assert len(obs) == len(side) and (obs.event_id.values == side.event_id.values).all()
    df = obs.merge(side, on="event_id", suffixes=("", "_side"))
    for c in ("processed", "started", "second_pass", "triggered", "raw_positive", "sec_evaluated", "sec_accept"):
        df[c] = df[c].astype(int).astype(bool)
    seq, first = (int(x) for x in meta["segment"].split("_"))
    n_frames = int(meta["num_events"])
    tracks = ctx.segment_tracks(seq, first, first + n_frames - 1)
    always_on = summ["mode"] == "always_on"
    # --- track detection -----------------------------------------------------
    det_time: Dict[int, float] = {}
    proc = df[df.processed & (df.attack_type_side != "replay")]
    for r in proc.itertuples():
        model = STAGE2 if r.second_pass else STAGE1
        hit = ctx.hits[model].get(int(r.bank_key), frozenset())
        t_res = r.result_delivered_ms if r.result_delivered_ms >= 0 else r.result_m7_ms
        if t_res < 0:
            continue
        for tid in hit:
            if tid not in det_time or t_res < det_time[tid]:
                det_time[tid] = t_res
    lat = []
    det_any = det_timely = burst_n = burst_det = burst_timely = 0
    for t in tracks.itertuples():
        d = det_time.get(int(t.track_id))
        ok = d is not None
        timely = ok and (d - t.onset_ms) <= TIMELY_MS
        det_any += ok
        det_timely += timely
        if ok:
            lat.append(d - t.onset_ms)
        if t.burst:
            burst_n += 1
            burst_det += ok
            burst_timely += timely
    n_tr = len(tracks)
    # --- attacks / security -------------------------------------------------------
    atk = df.attack_type_side != "none"
    legit = ~atk
    spam = df.attack_type_side == "trigger_spam"
    rep = df.attack_type_side == "replay"
    rep_exact = rep & (df.variant == 0)
    rep_pert = rep & (df.variant != 0)
    sec = df[df.sec_evaluated]
    l_ev = sec[sec.attack_type_side == "none"]
    l_blk = int((~l_ev.sec_accept).sum())
    # legit requests whose displayed frame contains a moving-track object
    l_obj = l_ev[l_ev.ground_truth_action == "detect"]
    sess = df[atk].groupby("session")["started"].any() if atk.any() else pd.Series(dtype=bool)
    det_flag = df.final_conf >= ctx.det_thr
    m = {
        "mode": summ["mode"], "scenario": meta["scenario"], "intensity": float(meta["attack_intensity"]),
        "seed": int(meta["seed"]), "segment": meta["segment"], "frames": n_frames,
        "seconds": float(summ["seconds"]),
        "moving_tracks": n_tr, "tracks_detected": det_any, "tracks_timely": det_timely,
        "burst_tracks": burst_n, "burst_detected": burst_det, "burst_timely": burst_timely,
        "track_latency_sum_ms": float(np.sum(lat)) if lat else 0.0, "track_latency_n": len(lat),
        "attack_frames": int(atk.sum()), "attack_started": int((atk & df.started).sum()),
        "spam_frames": int(spam.sum()), "spam_started": int((spam & df.started).sum()),
        "replay_frames": int(rep.sum()), "replay_started": int((rep & df.started).sum()),
        "replay_exact_frames": int(rep_exact.sum()), "replay_exact_started": int((rep_exact & df.started).sum()),
        "replay_pert_frames": int(rep_pert.sum()), "replay_pert_started": int((rep_pert & df.started).sum()),
        "attack_sessions": int(len(sess)), "attack_sessions_reached": int(sess.sum()) if len(sess) else 0,
        "spoofed_detections": int((rep & df.processed & det_flag).sum()),
        "legit_gate_evaluated": int(len(l_ev)), "legit_gate_blocked": l_blk,
        "legit_obj_gate_evaluated": int(len(l_obj)), "legit_obj_gate_blocked": int((~l_obj.sec_accept).sum()),
        "attack_gate_evaluated": int((sec.attack_type_side != "none").sum()),
        "attack_gate_blocked": int(((sec.attack_type_side != "none") & ~sec.sec_accept).sum()),
        "triggers": int(df.triggered.sum()) if not always_on else NAN,
        "legit_triggers_no_object": int((df.triggered & legit & (df.ground_truth_action != "detect")).sum())
        if not always_on else NAN,
        "processed": int(df.processed.sum()), "second_passes": int((df.processed & df.second_pass).sum()),
        "m7_active_ms": float(summ["m7_active_ms"]), "wakes": int(summ["wakes"]),
        "energy_mJ": float(states.energy_mJ.sum()), "energy_m7_mJ": float(states[states.core == "M7"].energy_mJ.sum()),
        "rpc_queue_full": int(summ["rpc_queue_full"]),
    }
    delivered = df[(df.result_delivered_ms >= 0) & (df.decision_ms >= 0) & legit]
    m["trigger_latency_sum_ms"] = float((delivered.result_delivered_ms - delivered.decision_ms).sum())
    m["trigger_latency_n"] = int(len(delivered))
    for reason in ("RATE_LIMIT", "REPLAY", "DUPLICATE", "BURST", "CONSISTENCY_FAILURE", "CONTENT_RATE"):
        m[f"block_{reason.lower()}"] = int((sec.sec_reason == reason).sum())
    return m


# Ratios computed after pooling counts over the segments of one realization.
RATIOS = {
    "track_recall": ("tracks_detected", "moving_tracks"),
    "timely_recall": ("tracks_timely", "moving_tracks"),
    "burst_recall": ("burst_detected", "burst_tracks"),
    "burst_timely_recall": ("burst_timely", "burst_tracks"),
    "mean_track_latency_ms": ("track_latency_sum_ms", "track_latency_n"),
    "attack_success": ("attack_started", "attack_frames"),
    "spam_success": ("spam_started", "spam_frames"),
    "replay_success": ("replay_started", "replay_frames"),
    "replay_exact_success": ("replay_exact_started", "replay_exact_frames"),
    "replay_pert_success": ("replay_pert_started", "replay_pert_frames"),
    "session_success": ("attack_sessions_reached", "attack_sessions"),
    "frr": ("legit_gate_blocked", "legit_gate_evaluated"),
    "frr_object": ("legit_obj_gate_blocked", "legit_obj_gate_evaluated"),
    "gate_attack_detection": ("attack_gate_blocked", "attack_gate_evaluated"),
    "duty_cycle": ("m7_active_ms", "seconds_ms"),
    "mean_trigger_latency_ms": ("trigger_latency_sum_ms", "trigger_latency_n"),
}


def pool(df: pd.DataFrame, keys) -> pd.DataFrame:
    """Sum counts over segments, then form ratios."""
    num = [c for c in df.select_dtypes("number").columns if c not in keys and c not in ("intensity", "seed")]
    g = df.groupby(keys, dropna=False)[num].sum(min_count=1).reset_index()
    g["seconds_ms"] = g["seconds"] * 1000.0
    for k, (a, b) in RATIOS.items():
        g[k] = [sdiv(x, y) for x, y in zip(g[a], g[b])]
    g["energy_per_min_mJ"] = g["energy_mJ"] / (g["seconds"] / 60.0)
    g["n_segments"] = df.groupby(keys, dropna=False).size().values
    return g
