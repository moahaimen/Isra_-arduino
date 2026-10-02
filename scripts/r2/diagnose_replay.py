#!/usr/bin/env python3
"""Validation-only diagnosis behind amendment 1 of the pre-registration:
distance of each moving frame (r2_motion >= 0.2) to the closest frame
observed >= 2 s earlier, for live frames and for every replay variant,
under three fingerprints (foreground-mask Jaccard, dHash-256 Hamming,
gain-normalised block code)."""
import glob
import json
import sys

import numpy as np
import pandas as pd

DATA = "/home/claude/data_r2"
if len(sys.argv) > 1 and sys.argv[1] == "test":
    raise SystemExit("validation only")
pc = lambda x: bin(x).count("1")  # noqa: E731


def words(h):
    return [int(h[16 * k:16 * k + 16], 16) for k in range(len(h) // 16)]


res = []
for wl in sorted(glob.glob(f"{DATA}/workloads_validation/*/replay_*/i1/s100[1-5]")):
    rows = [json.loads(l) for l in open(wl + "/wl.jsonl")]
    side = pd.read_csv(wl + "/side.csv")
    fg = [words(r["fg768"]) for r in rows]
    fp = [words(r["fp256"]) for r in rows]
    for i, r in enumerate(rows):
        if r["r2_motion"] < 0.2:
            continue
        cand = [j for j in range(i) if (i - j) * 100 >= 2000]
        if not cand:
            continue
        jac = max((sum(pc(a & b) for a, b in zip(fg[i], fg[j])) / max(1, sum(pc(a | b) for a, b in zip(fg[i], fg[j]))))
                  for j in cand)
        ham = min(sum(pc(a ^ b) for a, b in zip(fp[i], fp[j])) for j in cand)
        res.append({"attack": side.attack_type[i], "variant": side.variant[i], "fg_jaccard_max": jac,
                    "dhash_min": ham})
d = pd.DataFrame(res)
print(d.groupby(["attack", "variant"]).describe(percentiles=[0.05, 0.5, 0.95]).round(2).to_string())
