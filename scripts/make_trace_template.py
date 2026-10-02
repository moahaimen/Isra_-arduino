#!/usr/bin/env python3
"""Write a detector-trace template for a workload (one row per event).

Ground-truth columns are filled from the workload; prediction columns are
left EMPTY and must be filled by running a real detector on the frames.

Usage: python3 scripts/make_trace_template.py <workload.jsonl> <out.csv>
"""
import csv
import json
import sys

COLS = ["event_id", "ground_truth_class", "predicted_class", "confidence", "inference_ms", "postprocess_ms",
        "num_boxes", "correct", "second_pass_confidence", "second_pass_predicted_class", "second_pass_ms",
        "gt_x", "gt_y", "gt_w", "gt_h", "pred_x", "pred_y", "pred_w", "pred_h"]

if len(sys.argv) != 3:
    sys.exit(__doc__)
with open(sys.argv[1]) as fin, open(sys.argv[2], "w", newline="") as fout:
    w = csv.DictWriter(fout, fieldnames=COLS)
    w.writeheader()
    for line in fin:
        e = json.loads(line)
        w.writerow({"event_id": e["event_id"], "ground_truth_class": e.get("frame_object_class", e["object_class"])})
