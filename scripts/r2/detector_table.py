#!/usr/bin/env python3
"""Real-detector complexity and accuracy table (results/r2/DETECTORS.md and
.csv) from the stored detector traces. Portenta H7 latency is NOT MEASURED
for every model; host latency is the cloud host CPU."""
from __future__ import annotations

import glob
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.environ.get("R2_DATA", "/home/claude/data_r2")


def main() -> int:
    rows = []
    for d in sorted(glob.glob(os.path.join(ROOT, "data", "detector_traces", "real", "voc2007_test_*"))):
        meta = json.load(open(os.path.join(d, "model_metadata.json")))
        met = json.load(open(os.path.join(d, "metrics.json")))
        man = json.load(open(os.path.join(d, "trace_manifest.json")))
        op = {o["score_threshold"]: o for o in met.get("operating_points", [])}
        rows.append({"model": meta.get("architecture", meta["detector_name"]), "detector": meta["detector_name"],
                     "role": meta.get("role"), "precision": meta.get("precision"),
                     "input": "x".join(str(x) for x in meta.get("input", [])),
                     "parameters": meta.get("parameters"), "model_bytes": meta.get("model_bytes"),
                     "MACs": meta.get("macs"), "dataset": "PASCAL VOC 2007 test", "images": man["n_frames"],
                     "gt_boxes": man["n_gt_boxes"], "gt_boxes_non_ignored": man.get("n_gt_boxes_non_ignored"),
                     "pred_boxes": met.get("n_detections", man["n_predicted_boxes"]), "mAP50": met["mAP50"], "mAP50_95": met["mAP50_95"],
                     "P@0.5": op.get(0.5, {}).get("precision"), "R@0.5": op.get(0.5, {}).get("recall"),
                     "F1@0.5": op.get(0.5, {}).get("F1"),
                     "host_ms_median": met.get("host_timing_ms", {}).get("inference_median"),
                     "portenta_ms": "NOT MEASURED"})
    for m in ("efficientdet_lite0_int8", "efficientdet_lite2_int8"):
        for split in ("validation", "test"):
            d = os.path.join(DATA, "bank", f"{split}_{m}")
            if not os.path.exists(d):
                continue
            meta = json.load(open(os.path.join(d, "model_metadata.json")))
            met = json.load(open(os.path.join(d, "metrics.json")))["originals"]
            fr = pd.read_csv(os.path.join(d, "frames.csv"))
            gt = pd.read_csv(os.path.join(d, "ground_truth.csv"))
            pr = pd.read_csv(os.path.join(d, "predictions.csv"))
            o = fr[fr.event_id % 100 == 0]
            op = {x["score_threshold"]: x for x in met.get("operating_points", [])}
            rows.append({"model": meta["architecture"], "detector": m, "role": meta.get("role"),
                         "precision": meta["precision"].split(" ")[0], "input": "x".join(str(x) for x in meta["input"]),
                         "parameters": meta["parameters"], "model_bytes": meta["model_bytes"], "MACs": meta["macs"],
                         "dataset": f"KITTI tracking static segments ({split}, original frames)",
                         "images": len(o), "gt_boxes": int(gt.event_id.isin(o.event_id).sum()),
                         "gt_boxes_non_ignored": int((gt.event_id.isin(o.event_id) & (gt["ignore"] == 0)).sum()),
                         "pred_boxes": int(((pr.prediction_id > 0) & pr.event_id.isin(o.event_id)).sum()),
                         "mAP50": met["mAP50"], "mAP50_95": met["mAP50_95"],
                         "P@0.5": op.get(0.5, {}).get("precision"), "R@0.5": op.get(0.5, {}).get("recall"),
                         "F1@0.5": op.get(0.5, {}).get("F1"),
                         "host_ms_median": met.get("host_timing_ms", {}).get("inference_median"),
                         "portenta_ms": "NOT MEASURED"})
    df = pd.DataFrame(rows)
    out = os.path.join(ROOT, "results", "r2")
    os.makedirs(out, exist_ok=True)
    df.to_csv(os.path.join(out, "detectors.csv"), index=False)
    lines = ["| model | role | precision | input | params | bytes | MACs | dataset | images | GT boxes | pred boxes | mAP50 | mAP50:95 | host ms (median, 1 thread) | Portenta ms |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        macs = f"{r.MACs / 1e9:.2f} G" if isinstance(r.MACs, (int, float)) and r.MACs == r.MACs else "n/a"
        host = f"{r.host_ms_median:.1f}" if isinstance(r.host_ms_median, float) and r.host_ms_median == r.host_ms_median else "n/a"
        lines.append(f"| {r.model} | {r.role} | {r.precision} | {r.input} | {r.parameters / 1e6:.3f} M | "
                     f"{r.model_bytes / 1e6:.2f} MB | {macs} | {r.dataset} | {r.images} | {r.gt_boxes} | "
                     f"{r.pred_boxes} | {r.mAP50:.3f} | {r.mAP50_95:.3f} | {host} | {r.portenta_ms} |")
    with open(os.path.join(out, "detectors_table.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
