#!/usr/bin/env python3
"""Assemble the validation-tuned parameters of every method into
results/r2/frozen_params.json and record its SHA-256 in
results/r2/frozen_params.sha256. Both files are committed before the test
campaign; scripts/r2/run_test_campaign.py refuses to run when the hash of the
file differs from the recorded one."""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TUN = os.path.join(ROOT, "results", "r2", "tuning")
MODES = ["always_on", "motion_only", "mog2_event", "fixed_threshold", "event", "secure", "robust_event",
         "robust_secure"]


def main() -> int:
    common = json.load(open(os.path.join(TUN, "common.json")))
    out = {"_tuned_on": "validation", "_procedure": "docs/PREREGISTERED_R2_ANALYSIS.md section 4",
           "common": common["sim"]}
    for m in MODES:
        t = json.load(open(os.path.join(TUN, f"{m}.json")))
        assert t["split"] == "validation"
        out[m] = {k: v for k, v in t["best_params"].items() if k not in common["sim"]}
        out[f"_objective_{m}"] = {k: t["objective"][k] for k in ("J", "timely", "duty", "attack_success", "recall")}
    path = os.path.join(ROOT, "results", "r2", "frozen_params.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    with open(os.path.join(ROOT, "results", "r2", "frozen_params.sha256"), "w") as fh:
        fh.write(f"{h}  results/r2/frozen_params.json\n")
    print(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
