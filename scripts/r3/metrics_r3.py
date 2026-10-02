"""R3 per-run metrics (same definitions as scripts/r2/metrics_r2.py, R3 data
and detectors), plus frame-level recall.

* moving track, track recall, timely recall (<= 1.0 s), burst tracks: as R2;
* frame recall = (live frame, moving-track box) instances whose frame was
  processed by the M7 and whose box was matched / all such instances in the
  segment (a strict per-frame measure; always-on cannot reach 1.0 because the
  M7 is slower than the camera);
* utility retention and secure utility retention are formed in the analysis
  from paired runs (ratios of pooled recalls), not per run.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from typing import Dict, FrozenSet

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "r2"))
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import data_r3  # noqa: E402
from build_workloads import moving_tracks  # noqa: E402
from build_workloads_r3 import STAGE1, STAGE2  # noqa: E402
from metrics_r2 import BURST_WINDOW_MS, LIVE_VARIANTS, RATIOS, TIMELY_MS, match_tracks, sdiv  # noqa: E402

RATIOS = dict(RATIOS)
RATIOS["frame_recall"] = ("frame_hits", "frame_instances")


class Context:
    def __init__(self, split: str, det_thr: float):
        cache = os.path.join(data_r3.DATA, "cache", f"ctx_{split}_{det_thr:.3f}.pkl")
        if os.path.exists(cache):
            self.__dict__.update(pickle.load(open(cache, "rb")))
            return
        gt = data_r3.load(split, with_images=False)["gt"]
        tr = moving_tracks(gt)
        self.tracks = tr[tr.moving].copy()
        mv = {(int(r.seq), int(r.track_id)) for r in self.tracks.itertuples()}
        g = gt[gt.ignore == 0]
        self.instances = {}
        for eid, grp in g.groupby("event_id"):
            ids = [int(t) for t in grp.track_id if (int(eid) // 100000, int(t)) in mv]
            if ids:
                self.instances[int(eid)] = frozenset(ids)
        gt_by = {k: v for k, v in gt.groupby("event_id")}
        empty = gt.iloc[0:0]
        self.hits = {}
        for m in (STAGE1, STAGE2):
            p = pd.read_csv(os.path.join(data_r3.DATA, "bank", f"{split}_{m}", "predictions.csv"))
            p = p[(p.prediction_id > 0) & (p.confidence >= det_thr)]
            h = {}
            for key, grp in p.groupby("event_id"):
                if key % 100 in LIVE_VARIANTS:
                    h[int(key)] = match_tracks(gt_by.get(key // 100, empty), grp)
            self.hits[m] = h
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        pickle.dump({"tracks": self.tracks, "hits": self.hits, "instances": self.instances}, open(cache, "wb"))

    def segment_tracks(self, sk: int, first: int, last: int) -> pd.DataFrame:
        t = self.tracks[self.tracks.seq == sk]
        lo, hi = sk * 100000 + first, sk * 100000 + last
        t = t[(t["first"] >= lo) & (t["first"] <= hi)].copy()
        t["onset_ms"] = (t["first"] - lo) * data_r3.FRAME_MS
        on = np.sort(t.onset_ms.values)
        t["burst"] = [((np.abs(on - x) <= BURST_WINDOW_MS).sum() >= 2) for x in t.onset_ms.values]
        return t


def run_metrics(run_dir: str, wl_dir: str, ctx: Context) -> Dict:
    summ = json.load(open(os.path.join(run_dir, "summary.json")))
    meta = json.load(open(os.path.join(wl_dir, "wl.jsonl.meta.json")))
    obs = pd.read_csv(os.path.join(run_dir, "observations.csv"), keep_default_na=False)
    side = pd.read_csv(os.path.join(wl_dir, "side.csv"))
    states = pd.read_csv(os.path.join(run_dir, "states.csv"))
    df = obs.merge(side, on="event_id", suffixes=("", "_side"))
    for c in ("processed", "started", "second_pass", "triggered", "raw_positive", "sec_evaluated", "sec_accept"):
        df[c] = df[c].astype(int).astype(bool)
    sk, first, n_frames = int(meta["seq_key"]), int(meta["first_frame"]), int(meta["num_events"])
    tracks = ctx.segment_tracks(sk, first, first + n_frames - 1)
    always_on = summ["mode"] == "always_on"
    det_time: Dict[int, float] = {}
    frame_hits = 0
    proc = df[df.processed & (df.attack_type_side != "replay")]
    for r in proc.itertuples():
        hit = ctx.hits[STAGE2 if r.second_pass else STAGE1].get(int(r.bank_key), frozenset())
        t_res = r.result_delivered_ms if r.result_delivered_ms >= 0 else r.result_m7_ms
        if t_res < 0:
            continue
        frame_hits += len(hit & ctx.instances.get(int(r.src_frame), frozenset()))
        for tid in hit:
            if tid not in det_time or t_res < det_time[tid]:
                det_time[tid] = t_res
    live = df[df.attack_type_side != "replay"]
    frame_instances = sum(len(ctx.instances.get(int(f), ())) for f in live.src_frame)
    lat, det_any, det_timely, b_n, b_det, b_tim = [], 0, 0, 0, 0, 0
    for t in tracks.itertuples():
        d = det_time.get(int(t.track_id))
        ok = d is not None
        tl = ok and (d - t.onset_ms) <= TIMELY_MS
        det_any += ok
        det_timely += tl
        if ok:
            lat.append(d - t.onset_ms)
        if t.burst:
            b_n += 1
            b_det += ok
            b_tim += tl
    atk = df.attack_type_side != "none"
    spam = df.attack_type_side == "trigger_spam"
    rep = df.attack_type_side == "replay"
    rex, rpe = rep & (df.variant == 0), rep & (df.variant != 0)
    rsh = rep & df.variant.isin([5, 7])
    sec = df[df.sec_evaluated]
    l_ev = sec[sec.attack_type_side == "none"]
    l_obj = l_ev[l_ev.ground_truth_action == "detect"]
    sess = df[atk].groupby("session")["started"].any() if atk.any() else pd.Series(dtype=bool)
    m = {"mode": summ["mode"], "scenario": meta["scenario"], "intensity": float(meta["attack_intensity"]),
         "seed": int(meta["seed"]), "segment": meta["segment"], "frames": n_frames, "seconds": float(summ["seconds"]),
         "moving_tracks": len(tracks), "tracks_detected": det_any, "tracks_timely": det_timely,
         "burst_tracks": b_n, "burst_detected": b_det, "burst_timely": b_tim,
         "track_latency_sum_ms": float(np.sum(lat)) if lat else 0.0, "track_latency_n": len(lat),
         "track_latency_p95_ms": float(np.percentile(lat, 95)) if lat else float("nan"),
         "frame_hits": frame_hits, "frame_instances": frame_instances,
         "attack_frames": int(atk.sum()), "attack_started": int((atk & df.started).sum()),
         "spam_frames": int(spam.sum()), "spam_started": int((spam & df.started).sum()),
         "replay_frames": int(rep.sum()), "replay_started": int((rep & df.started).sum()),
         "replay_exact_frames": int(rex.sum()), "replay_exact_started": int((rex & df.started).sum()),
         "replay_pert_frames": int(rpe.sum()), "replay_pert_started": int((rpe & df.started).sum()),
         "replay_shift_frames": int(rsh.sum()), "replay_shift_started": int((rsh & df.started).sum()),
         "attack_sessions": int(len(sess)), "attack_sessions_reached": int(sess.sum()) if len(sess) else 0,
         "spoofed_detections": int((rep & df.processed & (df.final_conf >= ctx_thr(ctx))).sum()),
         "legit_gate_evaluated": int(len(l_ev)), "legit_gate_blocked": int((~l_ev.sec_accept).sum()),
         "legit_obj_gate_evaluated": int(len(l_obj)), "legit_obj_gate_blocked": int((~l_obj.sec_accept).sum()),
         "attack_gate_evaluated": int((sec.attack_type_side != "none").sum()),
         "attack_gate_blocked": int(((sec.attack_type_side != "none") & ~sec.sec_accept).sum()),
         "triggers": int(df.triggered.sum()) if not always_on else np.nan,
         "processed": int(df.processed.sum()), "second_passes": int((df.processed & df.second_pass).sum()),
         "m7_active_ms": float(summ["m7_active_ms"]), "wakes": int(summ["wakes"]),
         "energy_mJ": float(states.energy_mJ.sum()),
         "energy_m7_mJ": float(states[states.core == "M7"].energy_mJ.sum()),
         "rpc_queue_full": int(summ["rpc_queue_full"])}
    dl = df[(df.result_delivered_ms >= 0) & (df.decision_ms >= 0) & ~atk]
    lat2 = (dl.result_delivered_ms - dl.decision_ms).values
    m["trigger_latency_sum_ms"] = float(lat2.sum())
    m["trigger_latency_n"] = int(len(lat2))
    m["trigger_latency_p95_ms"] = float(np.percentile(lat2, 95)) if len(lat2) else float("nan")
    for reason in ("RATE_LIMIT", "REPLAY", "DUPLICATE", "BURST", "CONSISTENCY_FAILURE", "CONTENT_RATE"):
        m[f"block_{reason.lower()}"] = int((sec.sec_reason == reason).sum())
    return m


def ctx_thr(ctx) -> float:
    return getattr(ctx, "det_thr", 0.3)


RATIOS["replay_shift_success"] = ("replay_shift_started", "replay_shift_frames")


def pool(df: pd.DataFrame, keys) -> pd.DataFrame:
    num = [c for c in df.select_dtypes("number").columns if c not in keys and c not in ("intensity", "seed")
           and not c.endswith("_p95_ms")]
    g = df.groupby(keys, dropna=False)[num].sum(min_count=1).reset_index()
    g["seconds_ms"] = g["seconds"] * 1000.0
    for k, (a, b) in RATIOS.items():
        g[k] = [sdiv(x, y) for x, y in zip(g[a], g[b])]
    g["energy_per_min_mJ"] = g["energy_mJ"] / (g["seconds"] / 60.0)
    g["energy_per_detected_track_mJ"] = [sdiv(e, n) for e, n in zip(g["energy_mJ"], g["tracks_detected"])]
    g["n_segments"] = df.groupby(keys, dropna=False).size().values
    return g
