#!/usr/bin/env python3
"""Replay attack success by transformation (variant) for cooldown-only, cooldown+R3 gate, cooldown+gradient-tolerant gate (KITTI validation)."""
import os, sys, json, shutil, subprocess, tempfile
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
thr = 0.45; root = os.path.join(lib31.D31, f"workloads_validation_{thr:.2f}")
B = {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0}
CFG = {"cooldown_only": ("event", B), "cooldown+r3_replay": ("event_ugs_gate", {**B, "ug_budget": False}),
       "cooldown+grad_replay": ("event_ugs_gate", {**B, "ug_budget": False, "ug_grad_c": 0.5})}
NAMES = {0: "exact", 1: "bright x0.85", 2: "bright x1.15", 3: "noise s6", 4: "jpeg q40", 5: "shift 3,2 px", 6: "bright+noise+jpeg", 7: "shift -4 px + noise",
         20: "shift 10 px", 21: "shift 24,8 px", 22: "shift 48 px", 23: "crop 95%", 24: "crop 90%", 25: "shift24+crop95+gain+noise"}
rows = []
for seg in lib31.segments("validation", ("kitti",)):
    for sc in ("replay_exact", "replay_perturbed", "replay_shift"):
        for sd in (1001, 1002, 1003):
            wl = lib31.wl_dir(root, seg, sc, 1.0, sd)
            side = pd.read_csv(os.path.join(wl, "side.csv"))
            for name, (mode, p) in CFG.items():
                out = tempfile.mkdtemp(prefix="sv_")
                a = [lib31.SIM, "--config", os.path.join(lib31.ROOT, "config", "default_config.json"), "--mode", mode, "--workload", os.path.join(wl, "wl.jsonl"),
                     "--detector-backend", "trace_replay", "--detector-trace", os.path.join(wl, "det.csv"), "--trace-timing", "simulated",
                     "--detection-threshold", str(thr), "--log-level", "none", "--out-dir", out]
                for k, v in p.items():
                    a += [f"--{k.replace('_', '-')}", ("true" if v is True else "false" if v is False else str(v))]
                subprocess.run(a, cwd=lib31.ROOT, check=True, capture_output=True)
                o = pd.read_csv(os.path.join(out, "observations.csv"), keep_default_na=False)
                o["started"] = o.started.astype(int); m = o.merge(side, on="event_id")
                m = m[m.attack_type_x == "replay"] if "attack_type_x" in m else m[m.attack_type == "replay"]
                for v, g in m.groupby("variant"):
                    rows.append({"config": name, "variant": int(v), "frames": len(g), "started": int(g.started.sum())})
                shutil.rmtree(out)
d = pd.DataFrame(rows).groupby(["config", "variant"])[["frames", "started"]].sum().reset_index()
d["success"] = d.started / d.frames; d["transformation"] = d.variant.map(NAMES)
d.to_csv(sys.argv[1], index=False)
pv = d.pivot(index=["variant", "transformation"], columns="config", values="success").round(3)
pf = d.groupby("variant").frames.sum().rename("frames"); print(pv.join(pf, on="variant").to_string())
