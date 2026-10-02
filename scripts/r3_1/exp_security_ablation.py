#!/usr/bin/env python3
"""R3.1 security-design ablation (KITTI validation only): is each mechanism independently useful?
cooldown = the watcher's global 2 s cooldown; rate = global token bucket (cap 10, 1/s); replay = stale-frame gate (gradient tolerant c=0.5);
budget variants only matter with a bucket.  Configurations:
  none            no cooldown, no security
  cooldown_only   cooldown 2 s
  rate_only       no cooldown + bucket
  replay_only     no cooldown + replay gate
  cooldown+rate   cooldown + bucket
  cooldown+replay cooldown + replay gate (no bucket)
  full            cooldown + replay gate + bucket (+ novelty reserve, inert with this watcher)
  full_r3gate     as full but R3 gate (grad_c = 0)"""
import os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31, pandas as pd
thr = 0.45; C = {"detection_threshold": thr}
B = {"trigger_threshold": 0.25, "adaptive_gain": 1.0}
def S(l, m, cd, p): return (l, m, {"common": C, "params": {**B, "cooldown_ms": cd, **p}})
NOB = {"ug_budget": False}; NOREP = {"ug_replay": False}
specs = [S("none", "event", 0, {}),
         S("cooldown_only", "event", 2000, {}),
         S("rate_only", "event_ugs_gate", 0, NOREP),
         S("replay_only", "event_ugs_gate", 0, {**NOB, "ug_grad_c": 0.5}),
         S("cooldown+rate", "event_ugs_gate", 2000, NOREP),
         S("cooldown+replay", "event_ugs_gate", 2000, {**NOB, "ug_grad_c": 0.5}),
         S("full", "event_ugs_gate", 2000, {"ug_grad_c": 0.5}),
         S("full_r3gate", "event_ugs_gate", 2000, {}),
         ("always_on", "always_on", {"common": C, "params": {}})]
root = os.path.join(lib31.D31, f"workloads_validation_{thr:.2f}"); fr = []
with ProcessPoolExecutor(2) as ex:
    for sc, ints in [("clean", [1.0]), ("noisy", [1.0]), ("spam", [1.0, 8.0, 16.0]), ("replay_exact", [1.0]), ("replay_perturbed", [1.0]),
                     ("mixed", [1.0]), ("replay_shift", [1.0])]:
        fr.append(lib31.run_campaign("validation", root, specs, [sc], ints, [1001, 1002, 1003], thr, executor=ex, datasets=("kitti",)))
pd.concat(fr).to_csv(sys.argv[1], index=False); print("done")
