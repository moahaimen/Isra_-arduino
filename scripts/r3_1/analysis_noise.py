#!/usr/bin/env python3
"""O2: characterise WHY noisy scenes fail. For each M4 feature used by the
schedulers, per dataset: distribution (5/25/50/75/95 %) over frames that are
{background, object} x {clean, noisy}, and the separability of object vs background
(ROC AUC, rank-based) within each condition. 'object' = a moving GT/reference track is
present in the live frame (ground_truth_action == detect); 'background' otherwise.
Uses validation workloads only (seed given). Writes results/r3_1/noise/*.csv + figure."""
import argparse, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
from scipy.stats import rankdata

FEATS = ["motion_score", "visual_score", "temporal_change_score", "sensor_consistency_score", "noise_score",
         "edge_change_score", "r2_motion", "r2_visual", "r2_temporal", "r2_consistency", "mog2_fg", "fg_count"]


def auc(pos, neg):
    if len(pos) < 5 or len(neg) < 5: return np.nan
    r = rankdata(np.concatenate([pos, neg]))
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--split", default="validation")
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--thr", type=float, default=0.45)
    ap.add_argument("--out", default=os.path.join(lib31.ROOT, "results", "r3_1", "noise"))
    a = ap.parse_args()
    lib31.lock(a.split)
    root = os.path.join(lib31.D3 if a.dataset == "kitti" else lib31.D31, f"workloads_{a.split}_{a.thr:.2f}")  # KITTI feature tables are identical in the R3 workloads
    rows = []
    for seg in lib31.segments(a.split, (a.dataset,)):
        for sc in ("clean", "noisy"):
            wl = lib31.wl_dir(root, seg, sc, 1.0, a.seed)
            if not os.path.exists(os.path.join(wl, "wl.jsonl")): continue
            for l in open(os.path.join(wl, "wl.jsonl")):
                o = json.loads(l)
                o["fg_count"] = float(o["fg_count"])
                rows.append({"group": seg["group"], "cond": sc, "cls": "object" if o["ground_truth_action"] == "detect" else "background",
                             **{f: o[f] for f in FEATS}})
    d = pd.DataFrame(rows)
    os.makedirs(a.out, exist_ok=True)
    q = d.melt(id_vars=["group", "cond", "cls"], value_vars=FEATS, var_name="feature")
    dist = q.groupby(["cond", "cls", "feature"]).value.describe(percentiles=[.05, .25, .5, .75, .95]).reset_index()
    dist.to_csv(os.path.join(a.out, f"dist_{a.dataset}.csv"), index=False)
    sep = []
    for cond in ("clean", "noisy"):
        for f in FEATS:
            x = d[d.cond == cond]
            sep.append({"cond": cond, "feature": f, "auc_object_vs_background": auc(x[x.cls == "object"][f].values, x[x.cls == "background"][f].values),
                        "n_obj": int((x.cls == "object").sum()), "n_bg": int((x.cls == "background").sum())})
    pd.DataFrame(sep).to_csv(os.path.join(a.out, f"separability_{a.dataset}.csv"), index=False)
    pv = pd.DataFrame(sep).pivot(index="feature", columns="cond", values="auc_object_vs_background")
    print(a.dataset, "frames", len(d), d.groupby(["cond", "cls"]).size().to_dict())
    print(pv.round(3).to_string())
    med = dist.pivot_table(index="feature", columns=["cond", "cls"], values="50%")
    print(med.round(3).to_string())


if __name__ == "__main__":
    main()
