#!/usr/bin/env python3
"""Why does the R3 scheduler need ~0.66 M7 duty under the corrected tiled cost?  (diagnosis only; NO tuning)
Separates trigger frequency from per-activation detector cost on KITTI validation (clean + noisy, seeds 1001-1003), for
 - R3 scheduler at its R3 validation-selected parameters,
 - legacy event trigger at its Gate-B point (threshold 0.25, cooldown 2 s),
each with the real 3-tile cost and with a counterfactual single-tile cost (det.csv tile columns set to 1; trigger timing may
change slightly because result latency feeds back).  Reports per method/condition:
 wake-request rate, M7 wake count, tiles per activation, stage-2 activation rate, active-time contribution of each component,
 useful (first-detection) wakes per wake."""
import json, os, shutil, subprocess, sys, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
thr = 0.45
base = json.load(open(os.path.join(lib31.ROOT, "results/r3/tuning/gateB_ugs_event.json")))["selected"]
CFG = {"r3_scheduler": ("ugs_event", base),
       "event_trigger": ("event", {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0}),
       "always_on": ("always_on", {})}
root = os.path.join(lib31.D31, f"workloads_validation_{thr:.2f}")
rows = []
for seg in lib31.segments("validation", ("kitti",)):
    for sc in ("clean", "noisy"):
        for sd in (1001, 1002, 1003):
            wl = lib31.wl_dir(root, seg, sc, 1.0, sd)
            for tiles in (3, 1):
                tmpw = tempfile.mkdtemp(prefix="dg_")
                shutil.copy(os.path.join(wl, "wl.jsonl"), tmpw); shutil.copy(os.path.join(wl, "wl.jsonl.meta.json"), tmpw)
                shutil.copy(os.path.join(wl, "side.csv"), tmpw)
                det = pd.read_csv(os.path.join(wl, "det.csv"))
                if tiles == 1:
                    det["s1_tiles"] = 1; det["s2_tiles"] = 1
                det.to_csv(os.path.join(tmpw, "det.csv"), index=False)
                for name, (mode, p) in CFG.items():
                    out = tempfile.mkdtemp(prefix="dgo_")
                    args = [lib31.SIM, "--config", os.path.join(lib31.ROOT, "config", "default_config.json"), "--mode", mode, "--workload",
                            os.path.join(tmpw, "wl.jsonl"), "--detector-backend", "trace_replay", "--detector-trace", os.path.join(tmpw, "det.csv"),
                            "--trace-timing", "simulated", "--detection-threshold", str(thr), "--log-level", "none", "--out-dir", out]
                    for k, v in p.items(): args += [f"--{k.replace('_', '-')}", str(v)]
                    subprocess.run(args, cwd=lib31.ROOT, check=True, capture_output=True)
                    summ = json.load(open(os.path.join(out, "summary.json")))
                    obs = pd.read_csv(os.path.join(out, "observations.csv"), keep_default_na=False)
                    st = pd.read_csv(os.path.join(out, "states.csv"))
                    m7 = st[st.core == "M7"].set_index("state").time_ms
                    pr = obs[obs.processed.astype(int) == 1]
                    m = lib31.run_metrics(out, wl, lib31.ctx("validation", "kitti", thr)) if tiles == 3 else None
                    secs = summ["seconds"]
                    r = {"method": name, "tiles": tiles, "condition": sc, "seed": sd, "group": seg["group"], "seconds": secs,
                         "triggers": summ["triggers"], "rpc_requests": summ["rpc_sent"], "m7_wakes": summ["wakes"],
                         "processed": len(pr), "second_pass": int(pr.second_pass.astype(int).sum()) if len(pr) else 0,
                         "tile_evals": int(len(pr) * tiles + (pr.second_pass.astype(int).sum() * tiles if len(pr) else 0)),
                         "m7_active_ms": summ["m7_active_ms"], "energy_mJ": summ["energy_mJ"],
                         "t_stage1_ms": float(pr.s1_ms.sum()) if len(pr) else 0.0, "t_stage2_ms": float(pr.s2_ms.sum()) if len(pr) else 0.0,
                         "t_post_ms": float(pr.post_ms.sum()) if len(pr) else 0.0}
                    for s in ("M7_WAKEUP", "M7_INFERENCE", "M7_SECOND_PASS", "M7_POSTPROCESS", "M7_IDLE_AWAKE"):
                        r["state_" + s] = float(m7.get(s, 0.0))
                    if m: r.update({k: m[k] for k in ("wake_first", "wake_refresh", "wake_redundant", "wake_empty", "tracks_detected", "tracks_timely")})
                    rows.append(r)
                    shutil.rmtree(out)
                shutil.rmtree(tmpw)
df = pd.DataFrame(rows); df.to_csv(sys.argv[1], index=False); print("rows", len(df))
