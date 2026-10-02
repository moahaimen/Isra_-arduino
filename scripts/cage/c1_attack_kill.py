#!/usr/bin/env python3
"""CAGE C1 attack kill test (KITTI validation traces, simulation, modeled energy; NO locked data).
Attackers only SELECT and ORDER natural frames from the segment's own frame/variant bank (no adversarial perturbation crafting).
 benign         the real scene
 wake_only      alternate brightness-flicker variants (8-15) of the CHEAPEST frame (maximise watcher change, minimise M7 cost)
 inference_only one repeated high-cost frame (maximise M7 cost, no scene change)
 naive          interleave wake_only frames and the repeated high-cost frame (independent combination)
 joint          alternate among M mutually dissimilar high-cost frames (every change both wakes and is expensive)
Victim: legacy event trigger (threshold 0.25, adaptive gain 1.0) with cooldown 2 s (and 0.5 s)."""
import json, os, shutil, subprocess, sys, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r3_1"))
import lib31
thr = 0.45; M = 4
bank = lib31.Bank("kitti", "validation", thr)
pres = lib31.presence_for(lib31.gt_for("validation", "kitti"))

def proxy(key):  # relative M7 cost of a frame under the cascade (selection only; the simulator measures the real cost)
    c1, _, n1, _ = bank.get("s1", key)
    c = 1.0 + 0.03 * n1
    if 0.15 < c1 < 0.80:
        c2, _, n2, _ = bank.get("s2", key)
        c += 2.2 + 0.03 * n2
    return c

def plan_for(strategy, seg, rng):
    sk, first, n = seg["seq_key"], seg["first"], seg["n"]
    live = [sk * 100000 + f for f in range(first, first + n)]
    mk = lambda i, src, v, atk: {"live": live[i], "src": src, "variant": v, "attack": atk, "session": 1 if atk != "none" else -1}
    if strategy == "benign":
        return [mk(i, live[i], 0, "none") for i in range(n)]
    cost = {f: proxy(f * 100) for f in live}
    order = sorted(live, key=lambda f: -cost[f]); cheap = min(live, key=lambda f: cost[f])
    top = order[0]
    def th(f): return lib31.thumb192(bank.low[bank.idx[f * 100]]).astype(float)
    chosen = [top]
    for f in order[1:]:                       # greedy: next costly frame that differs most from those chosen
        if len(chosen) >= M: break
        if cost[f] >= 0.8 * cost[top] and all(np.abs(th(f) - th(g)).mean() > 12 for g in chosen): chosen.append(f)
    while len(chosen) < M: chosen.append(order[len(chosen)])
    P = []
    for i in range(n):
        if strategy == "wake_only": P.append(mk(i, cheap, 8 + i % 8, "trigger_spam"))
        elif strategy == "inference_only": P.append(mk(i, top, 0, "trigger_spam"))
        elif strategy == "naive": P.append(mk(i, cheap, 8 + (i // 2) % 8, "trigger_spam") if i % 2 == 0 else mk(i, top, 0, "trigger_spam"))
        elif strategy == "joint": P.append(mk(i, chosen[i % M], 0, "trigger_spam"))
    return P

STRATS = ["benign", "wake_only", "inference_only", "naive", "joint"]
VICTIMS = {"cooldown2s": {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0},
           "cooldown0.5s": {"trigger_threshold": 0.25, "cooldown_ms": 500, "adaptive_gain": 1.0}}
rows = []; root = tempfile.mkdtemp(prefix="c1_")
for seg in lib31.segments("validation", ("kitti",)):
    for st in STRATS:
        wl = os.path.join(root, seg["name"], st)
        lib31.build_workload(bank, pres, seg, "spam", 1.0, 1001, wl, thr, plan=plan_for(st, seg, None))
        for vn, vp in VICTIMS.items():
            out = tempfile.mkdtemp(prefix="c1o_")
            a = [lib31.SIM, "--config", os.path.join(lib31.ROOT, "config", "default_config.json"), "--mode", "event", "--workload", os.path.join(wl, "wl.jsonl"),
                 "--detector-backend", "trace_replay", "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
                 "--detection-threshold", str(thr), "--log-level", "none", "--out-dir", out]
            for k, v in vp.items(): a += [f"--{k.replace('_', '-')}", str(v)]
            subprocess.run(a, cwd=lib31.ROOT, check=True, capture_output=True)
            sm = json.load(open(os.path.join(out, "summary.json")))
            o = pd.read_csv(os.path.join(out, "observations.csv"), keep_default_na=False)
            pr = o[o.processed.astype(int) == 1]
            rows.append({"group": seg["group"], "strategy": st, "victim": vn, "seconds": sm["seconds"], "frames": sm["observations"], "triggers": sm["triggers"],
                         "rpc_sent": sm["rpc_sent"], "processed": len(pr), "second_pass": int(pr.second_pass.astype(int).sum()),
                         "busy_ms_total": float((pr.s1_ms + pr.s2_ms + pr.post_ms).sum()) if len(pr) else 0.0,
                         "m7_active_ms": sm["m7_active_ms"], "energy_mJ": sm["energy_mJ"],
                         "latency_ms": float(pr.result_m7_ms.sub(pr.rpc_send_ms).mean()) if len(pr) else 0.0})
            shutil.rmtree(out)
shutil.rmtree(root)
d = pd.DataFrame(rows); d.to_csv(sys.argv[1], index=False)
g = d.groupby(["victim", "strategy"])[["seconds", "frames", "rpc_sent", "processed", "second_pass", "busy_ms_total", "m7_active_ms", "energy_mJ"]].sum().reset_index()
g["wake_req_per_s"] = g.rpc_sent / g.seconds; g["busy_ms_per_req"] = g.busy_ms_total / g.processed.clip(lower=1); g["stage2_rate"] = g.second_pass / g.processed.clip(lower=1)
g["duty"] = g.m7_active_ms / (g.seconds * 1000); g["energy_J_per_min"] = g.energy_mJ / g.seconds * 60 / 1000
ben = g[g.strategy == "benign"].set_index("victim").energy_mJ
g["CEAF"] = [r.energy_mJ / ben[r.victim] for r in g.itertuples()]
out = []
for v, x in g.groupby("victim"):
    comp = x[x.strategy.isin(["wake_only", "inference_only", "naive"])].CEAF.max(); j = x[x.strategy == "joint"].CEAF.iloc[0]
    g.loc[x.index, "cross_stage_gain_vs_best_baseline"] = j / comp
g.to_csv(sys.argv[2], index=False)
pd.set_option("display.width", 200)
print(g[["victim", "strategy", "wake_req_per_s", "busy_ms_per_req", "stage2_rate", "duty", "energy_J_per_min", "CEAF", "cross_stage_gain_vs_best_baseline"]].round(3).to_string())
