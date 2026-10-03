#!/usr/bin/env python3
"""D1 K1: validation-only clairvoyant feasibility bound for timely first discovery.

This is NOT a scheduler and NOT a paper result. It answers one question:
under the current corrected 3-tile simulated detector cost, is >=90% timely
moving-track recall even feasible at M7 duty <=25%?

It uses future GT/detector hits deliberately:
- LP relaxation => optimistic upper bound on maximum timely track coverage.
- Greedy set cover => attainable clairvoyant lower bound.

Locked test is refused unconditionally.
"""
from __future__ import annotations
import argparse, json, os, sys
from dataclasses import dataclass
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "r3_1"))
import lib31  # noqa: E402
from scipy.optimize import linprog  # noqa: E402

FRAME_MS = 100.0
TIMELY_MS = 1000.0

@dataclass
class Candidate:
    frame: int
    time_ms: float
    cost_ms: float
    hits: frozenset[int]
    stage2: bool

def cost_for(bank, key, cfg, optimistic=False):
    c1, _, n1, _ = bank.get("s1", key)
    ambiguous = cfg["early_exit_low_threshold"] < c1 < cfg["early_exit_threshold"]
    if optimistic:
        # Deliberately generous: pay only the mandatory 3-tile stage-1 cost,
        # but later allow the best of S1/S2 hits. This is an upper-headroom aid.
        return 3 * cfg["inference_ms"] + cfg["m7_wakeup_ms"], ambiguous
    n = n1
    cost = 3 * cfg["inference_ms"] + cfg["m7_wakeup_ms"]
    if ambiguous:
        _, _, n2, _ = bank.get("s2", key)
        cost += 3 * cfg["second_pass_cost_ms"]
        n = n2
    cost += cfg["postprocess_base_ms"] + cfg["postprocess_per_box_ms"] * n
    return float(cost), ambiguous

def build_candidates(seg, bank, ctx, cfg, optimistic=False):
    tracks = ctx.segment_tracks(seg["seq_key"], seg["first"], seg["first"] + seg["n"] - 1)
    onset = {int(r.track_id): float(r.onset_ms) for r in tracks.itertuples()}
    track_ids = set(onset)
    cand = []
    for frame in range(seg["first"], seg["first"] + seg["n"]):
        eid = seg["seq_key"] * 100000 + frame
        key = eid * 100
        cost, stage2 = cost_for(bank, key, cfg, optimistic=optimistic)
        t = (frame - seg["first"]) * FRAME_MS
        if optimistic:
            hits = set(ctx.hits["s1"].get(key, frozenset())) | set(ctx.hits["s2"].get(key, frozenset()))
        else:
            st = "s2" if stage2 else "s1"
            hits = set(ctx.hits[st].get(key, frozenset()))
        # Result is only useful for K1 if delivered <=1s after this track's onset.
        result_t = t + cost
        timely = frozenset(tid for tid in hits if tid in track_ids and 0 <= result_t - onset[tid] <= TIMELY_MS)
        if timely:
            cand.append(Candidate(frame, t, cost, timely, stage2))
    return tracks, cand

def lp_upper(track_ids, candidates, budget_ms):
    tids = sorted(track_ids)
    if not tids:
        return 1.0, 0.0
    if not candidates:
        return 0.0, 0.0
    ti = {t:i for i,t in enumerate(tids)}
    nf, nt = len(candidates), len(tids)
    # Variables [x_f in 0..1, y_t in 0..1]; maximize sum(y).
    c = np.r_[np.zeros(nf), -np.ones(nt)]
    Aub, bub = [], []
    # y_t <= sum_{f hits t} x_f
    for t in tids:
        row = np.zeros(nf + nt)
        for j, ca in enumerate(candidates):
            if t in ca.hits:
                row[j] = -1.0
        row[nf + ti[t]] = 1.0
        Aub.append(row); bub.append(0.0)
    row = np.zeros(nf + nt)
    row[:nf] = [ca.cost_ms for ca in candidates]
    Aub.append(row); bub.append(float(budget_ms))
    r = linprog(c, A_ub=np.array(Aub), b_ub=np.array(bub),
                bounds=[(0,1)]*(nf+nt), method="highs")
    if not r.success:
        raise RuntimeError("linprog failed: " + r.message)
    covered = -float(r.fun)
    spent = float(np.dot(r.x[:nf], [ca.cost_ms for ca in candidates]))
    return covered / nt, spent

def greedy_lower(track_ids, candidates, budget_ms):
    uncovered = set(track_ids)
    spent = 0.0
    chosen = []
    remaining = list(candidates)
    while remaining:
        best = None; best_gain = 0.0
        for ca in remaining:
            if spent + ca.cost_ms > budget_ms:
                continue
            gain = len(ca.hits & uncovered) / ca.cost_ms
            if gain > best_gain:
                best, best_gain = ca, gain
        if best is None or best_gain <= 0:
            break
        chosen.append(best)
        spent += best.cost_ms
        uncovered -= best.hits
        remaining.remove(best)
    n = len(track_ids)
    return ((n - len(uncovered)) / n if n else 1.0), spent, chosen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation", choices=["validation"])
    ap.add_argument("--det-thr", type=float, default=0.45)
    ap.add_argument("--duty", type=float, default=0.25)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "d1", "k1_oracle.csv"))
    a = ap.parse_args()
    cfg = json.load(open(os.path.join(ROOT, "config", "default_config.json")))
    bank = lib31.Bank("kitti", "validation", a.det_thr)
    context = lib31.ctx("validation", "kitti", a.det_thr)
    rows = []
    for optimistic in (False, True):
        for seg in lib31.segments("validation", ("kitti",)):
            tracks, cand = build_candidates(seg, bank, context, cfg, optimistic)
            tids = set(int(x) for x in tracks.track_id)
            duration_ms = seg["n"] * FRAME_MS
            budget = a.duty * duration_ms
            up, up_spent = lp_upper(tids, cand, budget)
            lo, lo_spent, chosen = greedy_lower(tids, cand, budget)
            rows.append({
                "cost_model": "optimistic_stage1_cost_best_stage_hits" if optimistic else "corrected_cascade_simulated",
                "segment": seg["name"], "group": seg["group"], "frames": seg["n"],
                "tracks": len(tids), "candidates": len(cand), "duty_budget": a.duty,
                "budget_ms": budget, "lp_upper_timely_recall": up,
                "lp_fractional_spent_ms": up_spent, "greedy_timely_recall": lo,
                "greedy_spent_ms": lo_spent, "greedy_invocations": len(chosen)
            })
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_csv(a.out, index=False)
    summary = {}
    for cm, g in df.groupby("cost_model"):
        w = g.tracks.clip(lower=1)
        summary[cm] = {
            "segments": len(g),
            "tracks": int(g.tracks.sum()),
            "weighted_lp_upper_timely_recall": float(np.average(g.lp_upper_timely_recall, weights=w)),
            "weighted_greedy_timely_recall": float(np.average(g.greedy_timely_recall, weights=w)),
            "min_segment_lp_upper": float(g.lp_upper_timely_recall.min()),
            "max_segment_lp_upper": float(g.lp_upper_timely_recall.max())
        }
    decision = summary["optimistic_stage1_cost_best_stage_hits"]["weighted_lp_upper_timely_recall"]
    report = {
        "status": "KILL" if decision < 0.90 else "PROCEED_TO_K2",
        "rule": "Kill only if optimistic LP upper bound < 0.90 at duty <=0.25",
        "det_thr": a.det_thr, "duty": a.duty, "summary": summary,
        "caveat": "Costs are simulator assumptions, not Portenta measurements; LP is intentionally clairvoyant/fractional."
    }
    j = os.path.splitext(a.out)[0] + ".json"
    open(j, "w").write(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
