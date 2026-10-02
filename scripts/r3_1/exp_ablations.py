#!/usr/bin/env python3
"""R3.1 validation-only ablations of the security stack on KITTI validation (event watcher, Gate-B point): full gate, minus replay,
minus novelty budget (no effect with the event watcher: inert), plain rate limit only, no security. Spam x8, replay_exact, replay_perturbed, mixed, clean, noisy."""
import os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31, pandas as pd
out = sys.argv[1]; thr = 0.45
W = {"trigger_threshold": 0.25, "cooldown_ms": 2000, "adaptive_gain": 1.0}; C = {"detection_threshold": thr}
def S(l, m, p): return (l, m, {"common": C, "params": {**W, **p}})
specs = [S("full_gate", "event_ugs_gate", {"ug_shift_tol": 1, "ug_shift_try": 192}),
         S("minus_shift_tol", "event_ugs_gate", {}),
         S("minus_replay_verification", "event_ugs_gate", {"ug_replay": False}),
         S("minus_budget", "event_ugs_gate", {"ug_budget": False}),
         S("minus_novelty_budget", "event_ugs_gate", {"ug_novelty_capacity": 0.0}),
         S("plain_rate_only", "event_plain_limit", {}),
         S("no_security", "event", {}),
         ("always_on", "always_on", {"common": C, "params": {}})]
root = os.path.join(lib31.D31, f"workloads_validation_{thr:.2f}"); fr = []
with ProcessPoolExecutor(2) as ex:
    for sc, ints in [("clean", [1.0]), ("noisy", [1.0]), ("spam", [8.0]), ("replay_exact", [1.0]), ("replay_perturbed", [1.0]), ("mixed", [1.0])]:
        fr.append(lib31.run_campaign("validation", root, specs, [sc], ints, [1001, 1002, 1003], thr, executor=ex, datasets=("kitti",)))
pd.concat(fr).to_csv(out, index=False); print("done")
