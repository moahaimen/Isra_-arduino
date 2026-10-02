#!/usr/bin/env python3
"""Main simulation campaign: every scenario x mode x seed on shared workloads.

Example (default research campaign, 480 runs):
    python3 scripts/run_experiments.py \
      --scenarios quiet normal busy burst noisy trigger_spam replay mixed \
      --modes always_on motion_only fixed_threshold event event_no_early_exit secure \
      --seeds 1:10 --seconds 3600

Steps: generate and preserve each workload once -> run every mode on the SAME
workload -> capture raw JSONL/CSV -> per-run metrics + validation ->
aggregate CSV + paired statistics + tables -> figures. Campaign metadata
(git commit, binary hash, environment, configuration copies) is stored in
<campaign>/config/. An existing campaign directory is never overwritten.
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenarios", nargs="+", default=campaign.ALL_SCENARIOS)
    ap.add_argument("--modes", nargs="+", default=campaign.ALL_MODES)
    ap.add_argument("--seeds", default="1:10")
    ap.add_argument("--seconds", type=float, default=3600.0)
    ap.add_argument("--campaign-id", default=None)
    ap.add_argument("--campaign-root", default=os.path.join(campaign.REPO, "results", "campaigns"))
    ap.add_argument("--config", default=campaign.DEFAULT_CONFIG)
    ap.add_argument("--binary", default=campaign.DEFAULT_BIN)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--log-level", default="full", choices=["full", "decisions", "none"])
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()

    seeds = campaign.parse_seeds(a.seeds)
    cid = a.campaign_id or f"main_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    specs = []
    for sc in a.scenarios:
        for seed in seeds:
            for mode in a.modes:
                specs.append({"run_id": f"{sc}__s{seed:02d}__{mode}", "scenario": sc, "seed": seed,
                              "seconds": a.seconds, "mode": mode, "label": mode, "group": "main",
                              "workload_args": {}, "sim_args": []})
    print(f"campaign {cid}: {len(a.scenarios)} scenarios x {len(a.modes)} modes x {len(seeds)} seeds "
          f"= {len(specs)} runs of {a.seconds:g} s")
    cdir = campaign.run_campaign(specs, a.campaign_root, cid, binary=a.binary, config=a.config, jobs=a.jobs,
                                 log_level=a.log_level,
                                 meta={"kind": "main", "scenarios": a.scenarios, "modes": a.modes,
                                       "seeds": seeds, "seconds": a.seconds})
    aggregate.aggregate_main(cdir)
    aggregate.energy_model_sensitivity(cdir)
    if not a.no_figures:
        plots.plot_main(cdir)
    print(f"done: {cdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
