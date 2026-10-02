#!/usr/bin/env python3
"""One-at-a-time parameter sweeps around the default configuration.

For each swept parameter every other parameter stays at its default
(config/default_config.json). Simulator parameters are passed as CLI
overrides; workload parameters (attack_intensity, arrival_scale) produce a
new shared workload per value, replayed by every mode at that value.
Energy-model parameters are swept without re-simulation by
aggregate.energy_model_sensitivity (modeled energy is linear in power).

Example:
    python3 scripts/run_sensitivity.py --seeds 1:10 --seconds 3600
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "eval_energy"))
import aggregate  # noqa: E402
import campaign  # noqa: E402
import plots  # noqa: E402

# name -> (kind, values, scenarios, modes[, fixed extra simulator args])
SWEEPS = {
    "trigger_threshold": ("sim", [0.45, 0.50, 0.55, 0.60, 0.65], ["normal", "noisy", "mixed"],
                          ["fixed_threshold", "event", "secure"]),
    "cooldown_ms": ("sim", [0, 500, 1500, 3000, 6000], ["normal", "trigger_spam"], ["event", "secure"]),
    "early_exit_threshold": ("sim", [0.6, 0.7, 0.8, 0.9, 0.95], ["normal", "busy"], ["event", "secure"]),
    "arrival_scale": ("workload", [0.5, 1.0, 2.0, 4.0], ["normal"], ["always_on", "event", "secure"]),
    "attack_intensity": ("workload", [0.0, 0.5, 1.0, 2.0, 4.0, 8.0], ["trigger_spam", "replay", "mixed"],
                         ["fixed_threshold", "event", "secure"]),
    "rpc_latency_ms": ("sim", [0.1, 0.5, 2.0, 5.0, 10.0], ["busy"], ["event", "secure"]),
    "rpc_jitter_ms": ("sim", [0.0, 0.2, 1.0, 5.0], ["busy"], ["event", "secure"]),
    "rpc_loss": ("sim", [0.0, 0.01, 0.05, 0.1], ["normal", "busy"], ["event", "secure"]),
    # Stress context: with the default 1.5 s cooldown the M7 is always idle
    # before the next trigger, so the queue is only exercised without cooldown.
    "rpc_queue_capacity": ("sim", [1, 2, 4, 8], ["burst", "busy"], ["event", "secure"], ["--cooldown-ms", "0"]),
    "inference_ms": ("sim", [70, 140, 280, 560], ["normal", "busy"], ["always_on", "event", "secure"]),
    "consistency_threshold": ("sim", [0.3, 0.4, 0.5, 0.6, 0.7], ["trigger_spam", "mixed"], ["secure"]),
    "rate_limit": ("sim", [5, 10, 20, 40], ["busy", "trigger_spam"], ["secure"]),
    "burst_threshold": ("sim", [5, 10, 20, 40], ["burst", "trigger_spam"], ["secure"]),
    "replay_window_ms": ("sim", [60000, 300000, 600000, 1800000], ["replay"], ["secure"]),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--params", nargs="+", default=list(SWEEPS))
    ap.add_argument("--seeds", default="1:10")
    ap.add_argument("--seconds", type=float, default=3600.0)
    ap.add_argument("--campaign-id", default=None)
    ap.add_argument("--campaign-root", default=os.path.join(campaign.REPO, "results", "campaigns"))
    ap.add_argument("--config", default=campaign.DEFAULT_CONFIG)
    ap.add_argument("--binary", default=campaign.DEFAULT_BIN)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--log-level", default="decisions", choices=["full", "decisions", "none"])
    a = ap.parse_args()
    seeds = campaign.parse_seeds(a.seeds)
    cid = a.campaign_id or f"sensitivity_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    specs = []
    for p in a.params:
        kind, values, scenarios, modes = SWEEPS[p][:4]
        extra = list(SWEEPS[p][4]) if len(SWEEPS[p]) > 4 else []
        for v in values:
            for sc in scenarios:
                for seed in seeds:
                    for mode in modes:
                        flag = f"--{p.replace('_', '-')}"
                        specs.append({
                            "run_id": f"{p}={v}__{sc}__s{seed:02d}__{mode}", "scenario": sc, "seed": seed,
                            "seconds": a.seconds, "mode": mode, "label": mode, "group": "sensitivity",
                            "sweep_param": p, "sweep_value": v,
                            "workload_args": {p: v} if kind == "workload" else {},
                            "sim_args": ([flag, str(v)] if kind == "sim" else []) + extra,
                        })
    print(f"sensitivity campaign {cid}: {len(specs)} runs")
    cdir = campaign.run_campaign(specs, a.campaign_root, cid, binary=a.binary, config=a.config, jobs=a.jobs,
                                 log_level=a.log_level,
                                 meta={"kind": "sensitivity", "sweeps": {p: SWEEPS[p] for p in a.params},
                                       "seeds": seeds, "seconds": a.seconds})
    aggregate.aggregate_sensitivity(cdir)
    plots.plot_sensitivity(cdir)
    print(f"done: {cdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
