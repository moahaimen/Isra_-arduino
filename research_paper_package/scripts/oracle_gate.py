#!/usr/bin/env python3
"""E1 oracle feasibility gate (preregistered in 00_protocol/preregistration.md).

  tune  : grid-search baselines on VALIDATION outputs, write frozen_baselines.json
  gate  : evaluate frozen baselines, union ceiling and the privileged ILP oracle on a split

Inputs are the cached REAL mode outputs written by run_modes.py.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "r2"))
from build_workloads import moving_tracks  # noqa: E402
from metrics_r2 import match_tracks  # noqa: E402

MODES = ["LOW", "ROI0", "ROI1", "ROI2", "FULL"]
COST = np.array([1.0, 1.0, 1.0, 1.0, 3.0])  # Lite0 invocations (0.974 GMAC each)
DET_THR = 0.45
FULL_I = 4
SEED = 20261026


class Split:
    def __init__(self, d: str, deadline: int = 10):
        self.frames = pd.read_csv(os.path.join(d, "frames.csv")).sort_values("event_id").reset_index(drop=True)
        self.m4 = pd.read_csv(os.path.join(d, "m4.csv")).set_index("event_id").loc[self.frames.event_id].reset_index()
        gt = pd.read_csv(os.path.join(d, "gt.csv"))
        pr = pd.read_csv(os.path.join(d, "preds.csv"))
        pr = pr[pr.confidence >= DET_THR]
        tr = moving_tracks(gt)
        self.tracks = tr[tr.moving].reset_index(drop=True)
        self.N = len(self.tracks)
        eid = self.frames.event_id.to_numpy()
        self.eid = eid
        self.idx = {e: i for i, e in enumerate(eid)}
        self.seg = self.frames.source_sequence.to_numpy()
        self.seg_names = sorted(set(self.seg))
        kidx = {(int(t.seq), int(t.track_id)): k for k, t in enumerate(self.tracks.itertuples())}
        T = len(eid)
        self.H = np.zeros((len(MODES), T, self.N), dtype=bool)  # mode a at frame i hits moving track k
        self.Hall = {}  # (mode, i) -> set of all matched GT track keys (for the per-frame quality oracle)
        gb = {k: g for k, g in gt.groupby("event_id")}
        pb = {(e, m): g for (e, m), g in pr.groupby(["event_id", "mode"])}
        for i, e in enumerate(eid):
            g = gb.get(e)
            for a, m in enumerate(MODES):
                p = pb.get((e, m))
                if g is None or p is None:
                    self.Hall[(a, i)] = frozenset()
                    continue
                hit = match_tracks(g, p)
                self.Hall[(a, i)] = hit
                for tid in hit:
                    k = kidx.get((int(e // 100000), int(tid)))
                    if k is not None:
                        self.H[a, i, k] = True
        self.W = np.zeros((T, self.N), dtype=bool)  # frame i inside track k's timely window
        self.track_seg = []
        for k, t in enumerate(self.tracks.itertuples()):
            for e in range(int(t.first), int(t.first) + deadline + 1):
                if e in self.idx:
                    self.W[self.idx[e], k] = True
            self.track_seg.append(self.seg[self.idx[int(t.first)]])
        self.track_seg = np.array(self.track_seg)
        self.HW = self.H & self.W[None]
        # segment start flags and in-segment frame index
        self.start = np.r_[True, self.seg[1:] != self.seg[:-1]]
        pos = np.zeros(T, dtype=int)
        for i in range(1, T):
            pos[i] = 0 if self.start[i] else pos[i - 1] + 1
        self.pos = pos

    def evaluate(self, modes: np.ndarray, overhead: float = 0.0):
        """modes: per-frame mode index, -1 = SKIP."""
        run = modes >= 0
        timely = np.zeros(self.N, dtype=bool)
        for a in range(len(MODES)):
            sel = modes == a
            if sel.any():
                timely |= self.HW[a, sel].any(axis=0)
        cost = np.where(run, COST[np.clip(modes, 0, None)] + overhead, 0.0)
        return timely, cost


# ---------------------------------------------------------------- policies (causal: M4 features of frames <= t only)
def trig(score, start, thr, cool):
    out = np.zeros(len(score), dtype=bool)
    last = -10 ** 9
    for i in range(len(score)):
        if start[i]:
            out[i], last = True, i  # boot frame: every triggered policy runs at segment start
            continue
        if score[i] > thr and i - last > cool:
            out[i], last = True, i
    return out


def policy(S: Split, fam: str, p: dict) -> np.ndarray:
    T = len(S.eid)
    m = -np.ones(T, dtype=int)
    if fam == "always_full":
        m[:] = FULL_I
    elif fam == "fixed_period":
        m[S.pos % p["P"] == 0] = FULL_I
    elif fam in ("motion_full", "mog2_full", "adaptive_res", "roi_motion"):
        sc = S.m4.mog2_fg.to_numpy() if fam == "mog2_full" else S.m4.m_raw.to_numpy()
        t = trig(sc, S.start, p["thr"], p["cool"])
        if fam in ("motion_full", "mog2_full"):
            m[t] = FULL_I
        elif fam == "adaptive_res":
            m[t] = np.where(sc[t] >= p["thr_hi"], FULL_I, 0)
            m[S.start] = FULL_I
        else:
            tiles = S.m4[["m_tile0", "m_tile1", "m_tile2"]].to_numpy()
            m[t] = 1 + tiles[t].argmax(axis=1)
            m[S.start] = FULL_I
    return m


def grid(S: Split, fam: str):
    qs = np.quantile
    if fam == "always_full":
        return [{}]
    if fam == "fixed_period":
        return [{"P": P} for P in range(1, 31)]
    sc = S.m4.mog2_fg.to_numpy() if fam == "mog2_full" else S.m4.m_raw.to_numpy()
    thr = sorted(set(np.round(qs(sc, np.linspace(0.5, 0.995, 50)), 6)))
    cools = [0, 2, 5, 10, 20]
    if fam == "adaptive_res":
        his = sorted(set(np.round(qs(sc, np.linspace(0.5, 0.995, 10)), 6)))
        return [{"thr": a, "thr_hi": b, "cool": c} for a, b, c in itertools.product(thr, his, cools) if b >= a]
    return [{"thr": a, "cool": c} for a, c in itertools.product(thr, cools)]


FAMILIES = ["always_full", "fixed_period", "motion_full", "mog2_full", "adaptive_res", "roi_motion"]
GATE_FAMILIES = ["always_full", "fixed_period", "motion_full", "mog2_full"]  # baselines named for the gate in the prompt


def run_policy(S, fam, p, overhead=0.0):
    tl, c = S.evaluate(policy(S, fam, p), overhead)
    return tl, c


# ---------------------------------------------------------------- oracle
def oracle(S: Split, R: float, modes=(0, 1, 2, 3, 4), overhead: float = 0.0):
    """Exact min-cost mode assignment with >= ceil(R*N) timely tracks (privileged: uses GT and future)."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    need = int(np.ceil(R * S.N - 1e-9))
    cand = [(i, a) for a in modes for i in np.where(S.HW[a].any(axis=1))[0]]
    nx, ny = len(cand), S.N
    c = np.r_[[COST[a] + overhead for _, a in cand], np.zeros(ny)]
    frames_used = sorted(set(i for i, _ in cand))
    fpos = {i: r for r, i in enumerate(frames_used)}
    A = lil_matrix((len(frames_used) + ny + 1, nx + ny))
    lo, hi = [], []
    for j, (i, a) in enumerate(cand):
        A[fpos[i], j] = 1
    lo += [0] * len(frames_used)
    hi += [1] * len(frames_used)
    base = len(frames_used)
    for j, (i, a) in enumerate(cand):
        for k in np.where(S.HW[a, i])[0]:
            A[base + k, j] = -1
    for k in range(ny):
        A[base + k, nx + k] = 1
    lo += [-np.inf] * ny
    hi += [0] * ny
    A[base + ny, nx:] = 1
    lo.append(need)
    hi.append(np.inf)
    res = milp(c, constraints=LinearConstraint(A.tocsr(), lo, hi), integrality=np.ones(nx + ny),
               bounds=Bounds(0, 1), options={"time_limit": 600})
    if res.x is None:
        return None
    x = np.round(res.x).astype(int)
    m = -np.ones(len(S.eid), dtype=int)
    for j, (i, a) in enumerate(cand):
        if x[j]:
            m[i] = a
    tl, cost = S.evaluate(m, overhead)
    return {"status": int(res.status), "mip_gap": float(getattr(res, "mip_gap", 0.0) or 0.0), "modes": m,
            "timely": tl, "cost": cost}


def ceiling(S: Split):
    return S.HW.any(axis=(0, 1))


def per_frame_quality_oracle(S: Split, qmin: float):
    m = -np.ones(len(S.eid), dtype=int)
    for i in range(len(S.eid)):
        F = S.Hall[(FULL_I, i)]
        if not F:
            continue
        best = FULL_I
        for a in (0, 1, 2, 3):
            if len(S.Hall[(a, i)] & F) >= qmin * len(F):
                best = a
                break
        m[i] = best
    return m


# ---------------------------------------------------------------- statistics
def seg_boot(S, timely_by, cost_by, n=10000, seed=SEED):
    """Segment-clustered bootstrap. timely_by/cost_by: dict name -> per-track bool / per-frame cost arrays."""
    rng = np.random.default_rng(seed)
    segs = S.seg_names
    tk = {s: np.where(S.track_seg == s)[0] for s in segs}
    fr = {s: np.where(S.seg == s)[0] for s in segs}
    out = {k: [] for k in timely_by}
    ratio = []
    for _ in range(n):
        pick = rng.choice(len(segs), len(segs), replace=True)
        ti = np.concatenate([tk[segs[j]] for j in pick])
        fi = np.concatenate([fr[segs[j]] for j in pick])
        if len(ti) == 0:
            continue
        for k in timely_by:
            out[k].append(timely_by[k][ti].mean())
        if "oracle" in cost_by and "best" in cost_by:
            b = cost_by["best"][fi].sum()
            if b > 0:
                ratio.append(cost_by["oracle"][fi].sum() / b)
    ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in out.items()}
    if ratio:
        ci["cost_ratio_oracle_over_best"] = [float(np.percentile(ratio, 2.5)), float(np.percentile(ratio, 97.5))]
    return ci


def summarize(S, name, tl, cost):
    T = len(S.eid)
    return {"policy": name, "R_timely": float(tl.mean()), "timely_tracks": int(tl.sum()), "tracks": S.N,
            "cost_units": float(cost.sum()), "cost_per_frame": float(cost.sum() / T),
            "rel_cost_vs_always_full": float(cost.sum() / (3.0 * T)), "frames": T,
            "detector_invocations_frames": int((cost > 0).sum())}


def select(S, fam):
    best = None
    for p in grid(S, fam):
        tl, c = run_policy(S, fam, p)
        r, cs = tl.mean(), c.sum()
        key = (0, cs) if r >= 0.90 else (1, -r, cs)
        if best is None or key < best[0]:
            best = (key, p, float(r), float(cs / len(S.eid)))
    return {"params": best[1], "val_R_timely": best[2], "val_cost_per_frame": best[3],
            "met_0.90_on_validation": best[0][0] == 0}


def to_py(o):
    if isinstance(o, dict):
        return {k: to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tune", "gate"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--frozen", default=os.path.join(HERE, "..", "03_oracle_gate", "frozen_baselines.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "03_oracle_gate"))
    ap.add_argument("--tag", default="test")
    a = ap.parse_args()
    S = Split(a.data)
    if a.cmd == "tune":
        fz = {"rule": "min validation cost s.t. validation R_timely >= 0.90, else max R_timely (ties: lower cost)",
              "det_thr": DET_THR, "deadline_frames": 10, "costs": dict(zip(MODES, COST.tolist())),
              "validation_tracks": S.N, "validation_frames": len(S.eid),
              "validation_union_ceiling": float(ceiling(S).mean()),
              "families": {f: select(S, f) for f in FAMILIES}}
        json.dump(to_py(fz), open(a.frozen, "w"), indent=1)
        h = hashlib.sha256(open(a.frozen, "rb").read()).hexdigest()
        open(a.frozen + ".sha256", "w").write(h + "\n")
        print(json.dumps(to_py(fz), indent=1))
        return 0
    fz = json.load(open(a.frozen))
    rows, tl_by, cost_by, modes_by = [], {}, {}, {}
    ceil = ceiling(S)
    rows.append({"policy": "union_ceiling (all modes every frame)", "R_timely": float(ceil.mean()),
                 "timely_tracks": int(ceil.sum()), "tracks": S.N})
    for f in FAMILIES:
        p = fz["families"][f]["params"]
        m = policy(S, f, p)
        tl, c = S.evaluate(m)
        r = summarize(S, f, tl, c)
        r["params"] = json.dumps(p)
        r["in_gate_set"] = f in GATE_FAMILIES
        rows.append(r)
        tl_by[f], cost_by[f], modes_by[f] = tl, c, m
    feas = [r for r in rows if r.get("in_gate_set") and r["R_timely"] >= 0.90]
    best = min(feas, key=lambda r: r["cost_units"]) if feas else None
    ref = best if best else next(r for r in rows if r["policy"] == "always_full")
    R_target = max(0.90, ref["R_timely"]) if best else 0.90
    gate = {"tag": a.tag, "tracks": S.N, "frames": len(S.eid), "segments": len(S.seg_names),
            "union_ceiling": float(ceil.mean()), "best_feasible_baseline": best["policy"] if best else None,
            "reference_baseline": ref["policy"], "reference_cost_units": ref["cost_units"],
            "reference_R_timely": ref["R_timely"], "R_target": R_target}
    if ceil.mean() + 1e-12 < 0.90:
        gate.update({"P2_oracle_reaches_0.90": False, "P1": None, "S1": None, "decision": "STOP",
                     "reason": "union ceiling < 0.90: R_timely >= 0.90 is unattainable by any policy or oracle with these detector modes"})
        R_eval = [float(ceil.sum() / S.N)]
    else:
        R_eval = [R_target]
    # oracle at R_target (or at the ceiling if the target is unattainable), plus a cost-recall curve
    curve = []
    for R in sorted(set([0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, float(ceil.mean())] + R_eval)):
        if R > ceil.mean() + 1e-12:
            continue
        for name, ms in (("oracle_4mode", (0, 1, 2, 3, 4)), ("oracle_skip_full", (FULL_I,))):
            for ov in (0.0, 0.25):
                o = oracle(S, R, ms, ov)
                if o is None:
                    continue
                s = summarize(S, f"{name}@R>={R:.3f}{'+ovh0.25' if ov else ''}", o["timely"], o["cost"])
                s.update({"R_constraint": R, "overhead": ov, "mode_set": name,
                          "mode_counts": json.dumps({("SKIP" if k < 0 else MODES[k]): int((o["modes"] == k).sum())
                                                     for k in range(-1, 5)})})
                curve.append(s)
                if R == R_eval[0] and ov == 0.0:
                    tl_by[name], cost_by[name], modes_by[name] = o["timely"], o["cost"], o["modes"]
    if "decision" not in gate:
        o4, o2 = [c for c in curve if c["R_constraint"] == R_target and c["overhead"] == 0.0]
        gate["oracle_cost_units"] = o4["cost_units"]
        gate["oracle_R_timely"] = o4["R_timely"]
        gate["oracle_skip_full_cost_units"] = o2["cost_units"]
        gate["P1_ratio_oracle_over_reference"] = o4["cost_units"] / ref["cost_units"]
        gate["P1_pass"] = gate["P1_ratio_oracle_over_reference"] <= 0.60
        gate["P2_oracle_reaches_0.90"] = o4["R_timely"] >= 0.90
        gate["S1_ratio_4mode_over_skipfull"] = o4["cost_units"] / o2["cost_units"]
        gate["S1_pass"] = gate["S1_ratio_4mode_over_skipfull"] <= 0.80
        ov = [c for c in curve if c["R_constraint"] == R_target and c["overhead"] == 0.25]
        if len(ov) == 2:
            gate["sens_overhead0.25_S1_ratio"] = ov[0]["cost_units"] / ov[1]["cost_units"]
        gate["baseline_reached_0.90"] = best is not None
        gate["decision"] = "GO" if (gate["P1_pass"] and gate["P2_oracle_reaches_0.90"] and gate["S1_pass"]) else "STOP"
    # per-frame quality oracle (descriptive)
    pfq = []
    for q in (0.8, 0.9, 1.0):
        m = per_frame_quality_oracle(S, q)
        tl, c = S.evaluate(m)
        s = summarize(S, f"per_frame_quality_oracle_Qmin{q}", tl, c)
        s["mode_counts"] = json.dumps({("SKIP" if k < 0 else MODES[k]): int((m == k).sum()) for k in range(-1, 5)})
        pfq.append(s)
    # sensitivity to the deadline (descriptive): ceiling at D = 5 and 20
    for D in (5, 20):
        S2 = Split(a.data, deadline=D)
        gate[f"union_ceiling_D{D}"] = float(ceiling(S2).mean())
        gate[f"always_full_R_D{D}"] = float(S2.evaluate(policy(S2, "always_full", {}))[0].mean())
    # bootstrap
    tb = {k: v for k, v in tl_by.items()}
    cb = {}
    if "oracle_4mode" in cost_by:
        cb = {"oracle": cost_by["oracle_4mode"], "best": cost_by[ref["policy"]]}
    gate["segment_bootstrap_95ci"] = seg_boot(S, tb, cb)
    gate["per_segment"] = []
    for s in S.seg_names:
        tk = S.track_seg == s
        fi = S.seg == s
        d = {"segment": s, "frames": int(fi.sum()), "tracks": int(tk.sum()), "ceiling": float(ceil[tk].mean()) if tk.any() else None}
        for k in tl_by:
            d[f"R_{k}"] = float(tl_by[k][tk].mean()) if tk.any() else None
            d[f"cost_{k}"] = float(cost_by[k][fi].sum())
        gate["per_segment"].append(d)
    os.makedirs(a.out, exist_ok=True)
    pd.DataFrame(rows + curve + pfq).to_csv(os.path.join(a.out, f"oracle_results_{a.tag}.csv"), index=False)
    pd.DataFrame(gate["per_segment"]).to_csv(os.path.join(a.out, f"per_segment_{a.tag}.csv"), index=False)
    json.dump(to_py(gate), open(os.path.join(a.out, f"gate_{a.tag}.json"), "w"), indent=1)
    pt = S.tracks.copy()
    for k in tl_by:
        pt[f"timely_{k}"] = tl_by[k]
    pt["ceiling"] = ceil
    pt.to_csv(os.path.join(a.out, f"per_track_{a.tag}.csv"), index=False)
    print(json.dumps(to_py({k: v for k, v in gate.items() if k != "per_segment"}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
