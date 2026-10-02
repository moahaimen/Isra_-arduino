#!/usr/bin/env python3
"""Ablation matrix: the full secure system with one component removed at a time.

All variants of a (scenario, seed) replay the SAME workload. Variants:
    full_secure, no_security, no_cooldown, no_early_exit, no_adaptive_trigger,
    no_replay_protection, no_rate_limit, no_burst_detection,
    no_consistency_check, always_on (energy reference)

Example:
    python3 scripts/run_ablations.py --scenarios normal trigger_spam replay mixed --seeds 1:10 --seconds 3600
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

VARIANTS = {
    "full_secure": ("secure", []),
    "no_security": ("secure", ["--disable-security"]),
    "no_cooldown": ("secure", ["--disable-cooldown"]),
    "no_early_exit": ("secure", ["--disable-early-exit"]),
    "no_adaptive_trigger": ("secure", ["--disable-adaptive-trigger"]),
    "no_replay_protection": ("secure", ["--disable-replay-protection"]),
    "no_rate_limit": ("secure", ["--disable-rate-limit"]),
    "no_burst_detection": ("secure", ["--disable-burst-detection"]),
    "no_consistency_check": ("secure", ["--disable-consistency-check"]),
    "always_on": ("always_on", []),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenarios", nargs="+", default=["normal", "busy", "trigger_spam", "replay", "mixed"])
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS))
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
    cid = a.campaign_id or f"ablation_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    specs = []
    for sc in a.scenarios:
        for seed in seeds:
            for v in a.variants:
                mode, flags = VARIANTS[v]
                specs.append({"run_id": f"{sc}__s{seed:02d}__{v}", "scenario": sc, "seed": seed,
                              "seconds": a.seconds, "mode": mode, "label": v, "group": "ablation",
                              "workload_args": {}, "sim_args": flags})
    print(f"ablation campaign {cid}: {len(specs)} runs")
    cdir = campaign.run_campaign(specs, a.campaign_root, cid, binary=a.binary, config=a.config, jobs=a.jobs,
                                 log_level=a.log_level,
                                 meta={"kind": "ablation", "variants": {v: VARIANTS[v] for v in a.variants},
                                       "scenarios": a.scenarios, "seeds": seeds, "seconds": a.seconds})
    aggregate.aggregate_ablation(cdir)
    plots.plot_ablation(cdir)
    print(f"done: {cdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
