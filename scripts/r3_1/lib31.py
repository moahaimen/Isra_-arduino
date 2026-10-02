"""R3.1 shared layer: segment registry (KITTI tracking groups + MEVA camera
groups), real-frame workload builder, per-run metrics, and campaign running.

Datasets
  kitti  frames 1242x375, 3 tiles/stage, stage-2 (Lite2 tiles) available, GT = KITTI labels.
  meva   frames 1280x720 (resized), 2 tiles/stage, stage 1 only, GT = REFERENCE tracks
         (scripts/r3_1/meva_reference.py): detector-referenced, NOT annotation.

event_id = seq_key * 100000 + frame; bank key = event_id * 100 + variant.
The test splits are locked: build/run helpers refuse them unless allow_test.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(ROOT, ".."))
for d in ("scripts/r3", "scripts/r2", "scripts/detector", "scripts/r3_1"):
    sys.path.insert(0, os.path.join(ROOT, d))
import build_workloads as bw2  # noqa: E402  (R2 overlay processes, moving_tracks)
import data_r3  # noqa: E402
import frame_features as ff  # noqa: E402
from metrics_r2 import BURST_WINDOW_MS, LIVE_VARIANTS, RATIOS, TIMELY_MS, match_tracks, sdiv  # noqa: E402

D3 = data_r3.DATA                                       # /home/claude/data_r3
D31 = os.environ.get("R31_DATA", "/home/claude/data_r3_1")
SIM = os.path.join(ROOT, "build", "edge_sim")
FRAME_MS = 100.0
DATASETS = {"kitti": {"W": 1242.0, "H": 375.0, "tiles": 3, "stage2": True},
            "meva": {"W": 1280.0, "H": 720.0, "tiles": 2, "stage2": False}}
KIT_GROUP = lambda seq: f"kitti_{seq}"  # noqa: E731


def meva_manifest() -> Dict:
    return json.load(open(os.path.join(ROOT, "data", "splits", "r3_1_meva_splits.json")))


def segments(split: str, datasets=("kitti", "meva")) -> List[Dict]:
    out = []
    if "kitti" in datasets:
        for g in data_r3.segments(split):
            if g["source"] != "kitti_tracking":
                continue  # R3 test (raw drives) stays locked
            out.append({"dataset": "kitti", "split": split, "group": KIT_GROUP(g["sequence"]), "name": data_r3.seg_name(g),
                        "seq_key": data_r3.seq_key(g), "first": g["first_frame"], "n": g["n_frames"], **DATASETS["kitti"]})
    if "meva" in datasets:
        m = meva_manifest()
        allg = sorted(s["group"] for s in m["segments"])
        for s in m["segments"]:
            if s["split"] == split:
                out.append({"dataset": "meva", "split": split, "group": s["group"], "name": "meva_" + s["group"],
                            "seq_key": 2001 + allg.index(s["group"]), "first": 0, "n": (s["end_s"] - s["start_s"]) * s["fps"],
                            **DATASETS["meva"]})
    return out


def groups(split, datasets=("kitti", "meva")):
    return sorted({s["group"] for s in segments(split, datasets)})


def lock(split, allow_test=False):
    if split == "test" and not allow_test:
        raise SystemExit("test splits are locked until config/r3_1_frozen.json is committed")


# ------------------------------------------------------------------ ground truth
_gt_cache: Dict = {}


def gt_for(split: str, dataset: str) -> pd.DataFrame:
    k = (split, dataset)
    if k not in _gt_cache:
        if dataset == "kitti":
            _gt_cache[k] = data_r3.load(split, with_images=False)["gt"]
        else:
            parts = []
            for s in segments(split, ("meva",)):
                g = pd.read_csv(os.path.join(D31, "meva", s["group"], "reference_gt.csv"))
                parts.append(g)
            _gt_cache[k] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return _gt_cache[k]


# ------------------------------------------------------------------ bank access
def bank_paths(seg):
    if seg["dataset"] == "kitti":
        return (os.path.join(D3, "bank", f"bank_{seg['split']}.npz"),
                {"s1": os.path.join(D3, "bank", f"{seg['split']}_lite0_tiled", "predictions.csv"),
                 "s2": os.path.join(D3, "bank", f"{seg['split']}_lite2_tiled", "predictions.csv")})
    return (os.path.join(D31, "bank", f"meva_{seg['group']}.npz"),
            {"s1": os.path.join(D31, "bank", f"meva_{seg['group']}_lite0_tiled2", "predictions.csv")})


def box_cells(x1, y1, x2, y2, W, H) -> int:
    cw, ch = W / 12.0, H / 4.0
    m = 0
    for cy in range(4):
        for cx in range(12):
            if x1 < (cx + 1) * cw and x2 > cx * cw and y1 < (cy + 1) * ch and y2 > cy * ch:
                m |= 1 << (cy * 12 + cx)
    return m


class Bank:
    """M4 inputs and real detector outputs of one DATASET split (all its groups)."""

    def __init__(self, dataset: str, split: str, det_thr: float):
        self.dataset, self.det_thr = dataset, det_thr
        self.low, self.fp, self.idx, self.stage = [], [], {}, {"s1": {}, "s2": {}}
        W, H = DATASETS[dataset]["W"], DATASETS[dataset]["H"]
        seen = set()
        for seg in segments(split, (dataset,)):
            npz, preds = bank_paths(seg)
            if npz in seen:
                continue
            seen.add(npz)
            b = np.load(npz)
            off = len(self.low)
            self.low.extend(list(b["lowres"]))
            self.fp.extend(list(b["fp"]))
            for i, k in enumerate(b["keys"]):
                self.idx[int(k)] = off + i
            for st, path in preds.items():
                if not os.path.exists(path):
                    continue
                p = pd.read_csv(path)
                p = p[p.prediction_id > 0]
                for key, g in p.groupby("event_id"):
                    i = int(g.confidence.values.argmax())
                    hi = g[g.confidence >= det_thr]
                    cells = 0
                    for r in hi.itertuples():
                        cells |= box_cells(r.x1, r.y1, r.x2, r.y2, W, H)
                    self.stage[st][int(key)] = (float(g.confidence.values[i]), int(g.class_id.values[i]), len(hi), cells)

    def get(self, st, key):
        return self.stage[st].get(key, (0.0, 0, 0, 0))


def thumb192(L: np.ndarray) -> np.ndarray:
    return (L.astype(np.uint32).reshape(8, 4, 24, 4).sum(axis=(1, 3)) // 16).astype(np.uint8).reshape(-1)


def presence_for(gt: pd.DataFrame):
    tr = bw2.moving_tracks(gt)
    mv = {(int(r.seq), int(r.track_id), int(r.class_id)) for r in tr[tr.moving].itertuples()}
    return bw2.gt_presence(gt, mv)


def wl_dir(root, seg, scenario, intensity, seed):
    return os.path.join(root, seg["name"], scenario, f"i{intensity:g}", f"s{seed}")


def build_workload(bank: Bank, pres, seg, scenario, intensity, seed, out, det_thr):
    import cv2
    g2 = {"sequence": f"{seg['seq_key']:04d}", "first_frame": seg["first"], "last_frame": seg["first"] + seg["n"] - 1}
    plan = bw2.display_plan(g2, scenario, intensity, seed)
    os.makedirs(out, exist_ok=True)
    st = ff.FeatureState()
    mog = cv2.createBackgroundSubtractorMOG2(history=bw2.MOG2_HISTORY, varThreshold=bw2.MOG2_VAR_THRESHOLD, detectShadows=False)
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
        obj = {"event_id": i + 1, "timestamp_ms": round(i * FRAME_MS, 3), "duration_ms": FRAME_MS, "scenario": scenario,
               "episode_id": p["session"] if attack != "none" else -1,
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
               "thumb192": thumb192(low).tobytes().hex()}
        lines.append(json.dumps(obj, separators=(",", ":")))
        c1, k1, n1, m1 = bank.get("s1", key)
        row = [i + 1, k1, f"{c1:.5f}", n1, f"{m1:016x}", seg["tiles"], seg["tiles"]]
        if seg["stage2"]:
            c2, k2, n2, m2 = bank.get("s2", key)
            row += [f"{c2:.5f}", k2, n2, f"{m2:016x}"]
        det_rows.append(row)
        side_rows.append((i + 1, p["live"], p["src"], p["variant"], key, attack, p["session"]))
    wl = os.path.join(out, "wl.jsonl")
    open(wl, "w").write("\n".join(lines) + "\n")
    json.dump({"generator_version": "r3_1-realframes-1.0", "scenario": scenario, "seed": seed,
               "seconds": len(plan) * FRAME_MS / 1000.0, "attack_intensity": intensity, "segment": seg["name"],
               "group": seg["group"], "dataset": seg["dataset"], "seq_key": seg["seq_key"], "first_frame": seg["first"],
               "split": seg["split"], "num_events": len(plan), "det_thr": det_thr, "tiles": seg["tiles"]},
              open(wl + ".meta.json", "w"), indent=1)
    cols = ["event_id", "predicted_class", "confidence", "num_boxes", "s1_cells", "s1_tiles", "s2_tiles"]
    if seg["stage2"]:
        cols += ["second_pass_confidence", "second_pass_predicted_class", "second_pass_num_boxes", "s2_cells"]
    pd.DataFrame(det_rows, columns=cols).to_csv(os.path.join(out, "det.csv"), index=False)
    pd.DataFrame(side_rows, columns=["event_id", "live_frame", "src_frame", "variant", "bank_key", "attack_type", "session"]
                 ).to_csv(os.path.join(out, "side.csv"), index=False)


_banks, _press = {}, {}


def _build_job(a):
    segd, items, root, thr = a
    k = (segd["dataset"], segd["split"], thr)
    if k not in _banks:
        _banks[k] = Bank(segd["dataset"], segd["split"], thr)
        _press[k] = presence_for(gt_for(segd["split"], segd["dataset"]))
    for sc, it, sd in items:
        d = wl_dir(root, segd, sc, it, sd)
        if not os.path.exists(os.path.join(d, "side.csv")):
            build_workload(_banks[k], _press[k], segd, sc, it, sd, d, thr)
    return len(items)


def build_all(split, root, scen, ints, seeds, thr, workers=4, datasets=("kitti", "meva"), allow_test=False):
    lock(split, allow_test)
    jobs = []
    for sd_ in segments(split, datasets):
        items = [(sc, it, s) for sc in scen for it in ints for s in seeds]
        for k in range(0, len(items), 30):
            jobs.append((sd_, items[k:k + 30], root, thr))
    with ProcessPoolExecutor(workers) as ex:
        return sum(ex.map(_build_job, jobs))


# ------------------------------------------------------------------ metrics
class Context:
    def __init__(self, split, dataset, det_thr):
        gt = gt_for(split, dataset)
        tr = bw2.moving_tracks(gt)
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
        self.hits = {"s1": {}, "s2": {}}
        seen = set()
        for seg in segments(split, (dataset,)):
            _, preds = bank_paths(seg)
            for st, path in preds.items():
                if path in seen or not os.path.exists(path):
                    continue
                seen.add(path)
                p = pd.read_csv(path)
                p = p[(p.prediction_id > 0) & (p.confidence >= det_thr)]
                for key, grp in p.groupby("event_id"):
                    if key % 100 in LIVE_VARIANTS:
                        self.hits[st][int(key)] = match_tracks(gt_by.get(key // 100, empty), grp)
        self.det_thr = det_thr

    def segment_tracks(self, sk, first, last):
        t = self.tracks[self.tracks.seq == sk]
        lo, hi = sk * 100000 + first, sk * 100000 + last
        t = t[(t["first"] >= lo) & (t["first"] <= hi)].copy()
        t["onset_ms"] = (t["first"] - lo) * FRAME_MS
        on = np.sort(t.onset_ms.values)
        t["burst"] = [((np.abs(on - x) <= BURST_WINDOW_MS).sum() >= 2) for x in t.onset_ms.values]
        return t


_ctx: Dict = {}


def ctx(split, dataset, thr):
    k = (split, dataset, thr)
    if k not in _ctx:
        cache = os.path.join(D31, "cache", f"ctx_{split}_{dataset}_{thr:.3f}.pkl")
        if os.path.exists(cache):
            c = object.__new__(Context)
            c.__dict__.update(pickle.load(open(cache, "rb")))
        else:
            c = Context(split, dataset, thr)
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            pickle.dump(c.__dict__, open(cache, "wb"))
        _ctx[k] = c
    return _ctx[k]


def run_metrics(run_dir, wl, c: Context) -> Dict:
    summ = json.load(open(os.path.join(run_dir, "summary.json")))
    meta = json.load(open(os.path.join(wl, "wl.jsonl.meta.json")))
    obs = pd.read_csv(os.path.join(run_dir, "observations.csv"), keep_default_na=False)
    side = pd.read_csv(os.path.join(wl, "side.csv"))
    states = pd.read_csv(os.path.join(run_dir, "states.csv"))
    df = obs.merge(side, on="event_id", suffixes=("", "_side"))
    for col in ("processed", "started", "second_pass", "triggered", "raw_positive", "sec_evaluated", "sec_accept"):
        df[col] = df[col].astype(int).astype(bool)
    sk, first, n_frames = int(meta["seq_key"]), int(meta["first_frame"]), int(meta["num_events"])
    tracks = c.segment_tracks(sk, first, first + n_frames - 1)
    always_on = summ["mode"] == "always_on"
    det_time, frame_hits, last_det = {}, 0, {}
    useful = {"first": 0, "refresh": 0, "redundant": 0, "empty": 0}
    proc = df[df.processed & (df.attack_type_side != "replay")].sort_values("result_m7_ms")
    for r in proc.itertuples():
        hit = c.hits["s2" if r.second_pass else "s1"].get(int(r.bank_key), frozenset())
        inst = c.instances.get(int(r.src_frame), frozenset())
        t_res = r.result_delivered_ms if r.result_delivered_ms >= 0 else r.result_m7_ms
        if t_res < 0:
            continue
        frame_hits += len(hit & inst)
        hh = set(hit) & set(inst)
        if not hh:
            useful["empty"] += 1
        elif any(t not in last_det for t in hh):
            useful["first"] += 1                                  # first detection of a track
        elif any(t_res - last_det[t] >= 2000.0 for t in hh):
            useful["refresh"] += 1                                # useful refresh (track not seen for >= 2 s)
        else:
            useful["redundant"] += 1                              # redundant redetection
        for t in hh:
            last_det[t] = t_res
        for tid in hit:
            if tid not in det_time or t_res < det_time[tid]:
                det_time[tid] = t_res
    live = df[df.attack_type_side != "replay"]
    frame_instances = sum(len(c.instances.get(int(f), ())) for f in live.src_frame)
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
    spam, rep = df.attack_type_side == "trigger_spam", df.attack_type_side == "replay"
    rex, rpe = rep & (df.variant == 0), rep & (df.variant != 0)
    rsh = rep & df.variant.isin([5, 7])
    sec = df[df.sec_evaluated]
    l_ev = sec[sec.attack_type_side == "none"]
    l_obj = l_ev[l_ev.ground_truth_action == "detect"]
    sess = df[atk].groupby("session")["started"].any() if atk.any() else pd.Series(dtype=bool)
    m = {"mode": summ["mode"], "scenario": meta["scenario"], "intensity": float(meta["attack_intensity"]),
         "seed": int(meta["seed"]), "segment": meta["segment"], "group": meta["group"], "dataset": meta["dataset"],
         "frames": n_frames, "seconds": float(summ["seconds"]), "moving_tracks": len(tracks), "tracks_detected": det_any,
         "tracks_timely": det_timely, "burst_tracks": b_n, "burst_detected": b_det, "burst_timely": b_tim,
         "track_latency_sum_ms": float(np.sum(lat)) if lat else 0.0, "track_latency_n": len(lat),
         "frame_hits": frame_hits, "frame_instances": frame_instances,
         "wake_first": useful["first"], "wake_refresh": useful["refresh"], "wake_redundant": useful["redundant"],
         "wake_empty": useful["empty"],
         "attack_frames": int(atk.sum()), "attack_started": int((atk & df.started).sum()),
         "spam_frames": int(spam.sum()), "spam_started": int((spam & df.started).sum()),
         "replay_frames": int(rep.sum()), "replay_started": int((rep & df.started).sum()),
         "replay_exact_frames": int(rex.sum()), "replay_exact_started": int((rex & df.started).sum()),
         "replay_pert_frames": int(rpe.sum()), "replay_pert_started": int((rpe & df.started).sum()),
         "replay_shift_frames": int(rsh.sum()), "replay_shift_started": int((rsh & df.started).sum()),
         "attack_sessions": int(len(sess)), "attack_sessions_reached": int(sess.sum()) if len(sess) else 0,
         "legit_gate_evaluated": int(len(l_ev)), "legit_gate_blocked": int((~l_ev.sec_accept).sum()),
         "legit_obj_gate_evaluated": int(len(l_obj)), "legit_obj_gate_blocked": int((~l_obj.sec_accept).sum()),
         "attack_gate_evaluated": int((sec.attack_type_side != "none").sum()),
         "attack_gate_blocked": int(((sec.attack_type_side != "none") & ~sec.sec_accept).sum()),
         "triggers": int(df.triggered.sum()) if not always_on else np.nan, "processed": int(df.processed.sum()),
         "m7_active_ms": float(summ["m7_active_ms"]), "wakes": int(summ["wakes"]), "energy_mJ": float(states.energy_mJ.sum()),
         "energy_m7_mJ": float(states[states.core == "M7"].energy_mJ.sum()), "rpc_queue_full": int(summ["rpc_queue_full"])}
    # malicious wake energy: M7 energy attributable to attack frames (active time of attack-started frames x inference+post power)
    started_atk = df[atk & df.started]
    act = (started_atk.s1_ms + started_atk.s2_ms.clip(lower=0) + started_atk.post_ms).sum()
    m["malicious_active_ms"] = float(act)
    dl = df[(df.result_delivered_ms >= 0) & (df.decision_ms >= 0) & ~atk]
    lat2 = (dl.result_delivered_ms - dl.decision_ms).values
    m["trigger_latency_sum_ms"] = float(lat2.sum())
    m["trigger_latency_n"] = int(len(lat2))
    m["trigger_latency_p95_ms"] = float(np.percentile(lat2, 95)) if len(lat2) else float("nan")
    for reason in ("RATE_LIMIT", "REPLAY", "CONSISTENCY_FAILURE", "CONTENT_RATE", "BUCKET", "FLOOD"):
        m[f"block_{reason.lower()}"] = int((sec.sec_reason == reason).sum())
    return m


RATIOS = dict(RATIOS)
RATIOS.update({"frame_recall": ("frame_hits", "frame_instances"),
               "replay_shift_success": ("replay_shift_started", "replay_shift_frames"),
               "useful_wake_efficiency": ("wake_first", "processed"),
               "refresh_wake_share": ("wake_refresh", "processed"),
               "redundant_wake_share": ("wake_redundant", "processed"),
               "empty_wake_share": ("wake_empty", "processed")})


def pool(df: pd.DataFrame, keys) -> pd.DataFrame:
    num = [c for c in df.select_dtypes("number").columns if c not in keys and c not in ("intensity", "seed")]
    g = df.groupby(keys, dropna=False)[num].sum(min_count=1).reset_index()
    g["seconds_ms"] = g["seconds"] * 1000.0
    for k, (a, b) in RATIOS.items():
        g[k] = [sdiv(x, y) for x, y in zip(g[a], g[b])]
    g["energy_per_min_mJ"] = g["energy_mJ"] / (g["seconds"] / 60.0)
    g["energy_per_new_track_mJ"] = [sdiv(e, n) for e, n in zip(g["energy_mJ"], g["tracks_detected"])]
    g["malicious_wake_time_share"] = [sdiv(a, b) for a, b in zip(g["malicious_active_ms"], g["m7_active_ms"])]
    return g


# ------------------------------------------------------------------ runner
def sim_args(mode, params):
    out = []
    for src in (params.get("common", {}), params.get(mode, {})):
        for k, v in src.items():
            if isinstance(v, bool):
                v = "true" if v else "false"
            out += [f"--{k.replace('_', '-')}", str(v)]
    return out


def run_one(wl, mode, params, split, dataset, thr, label=None, sim_mode=None):
    tmp = tempfile.mkdtemp(prefix="r31_")
    try:
        cmd = [SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", sim_mode or mode,
               "--workload", os.path.join(wl, "wl.jsonl"), "--detector-backend", "trace_replay",
               "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
               "--detection-threshold", str(thr), "--log-level", "none", "--out-dir", tmp] + sim_args(mode, params)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"edge_sim failed: {' '.join(cmd)}\n{r.stderr}")
        m = run_metrics(tmp, wl, ctx(split, dataset, thr))
        m["mode"] = label or mode
        return m
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run_job(a):
    wl, specs, split, dataset, thr = a
    return [run_one(wl, name, p, split, dataset, thr, label=name, sim_mode=sm) for name, sm, p in specs]


def run_campaign(split, root, specs, scen, ints, seeds, thr, workers=4, executor=None, datasets=("kitti", "meva"),
                 allow_test=False):
    """specs: list of (label, sim_mode, params)."""
    lock(split, allow_test)
    jobs = [(wl_dir(root, s, sc, it, sd), [(n, sm, {"common": p.get("common", {}), n: p.get(n, p.get("params", {}))}) for n, sm, p in specs],
             split, s["dataset"], thr)
            for s in segments(split, datasets) for sc in scen for it in ints for sd in seeds]
    rows = []
    if executor is not None:
        for res in executor.map(_run_job, jobs, chunksize=4):
            rows += res
    else:
        with ProcessPoolExecutor(workers) as ex:
            for res in ex.map(_run_job, jobs, chunksize=4):
                rows += res
    return pd.DataFrame(rows)
