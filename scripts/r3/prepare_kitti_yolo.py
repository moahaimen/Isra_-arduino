#!/usr/bin/env python3
"""KITTI-tracking detector fine-tuning set in YOLO format (R3 domain
adaptation). Sequences and exclusions come from data/splits/r3_splits.json:

  train: det_train sequences, every 2nd frame, EXCLUDING any frame inside an
         R3 development/validation segment;
  val:   det_val sequences (0013, 0018), every 2nd frame (checkpoint selection).

No frame of an R3 validation segment and no KITTI raw test drive is used.
Labels: 0 person (Pedestrian, Person_sitting), 1 car (Car, Van). Cyclist,
Truck, Tram, Misc and DontCare are not labelled (evaluation treats Van /
Cyclist / Person_sitting / DontCare as ignore regions).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
sys.path.insert(0, HERE)
import kitti  # noqa: E402
import data_r3  # noqa: E402

OUT = os.path.join(data_r3.DATA, "kitti_yolo")
CLS = {"Pedestrian": 0, "Person_sitting": 0, "Car": 1, "Van": 1}
N_FRAMES = {"0000": 154, "0001": 447, "0002": 233, "0003": 144, "0004": 314, "0005": 297, "0007": 800,
            "0008": 390, "0009": 803, "0010": 294, "0011": 373, "0013": 340, "0014": 106, "0018": 339, "0020": 837}


def main() -> int:
    sp = data_r3.splits()
    excluded = {(g["sequence"], f) for g in sp["segments"] if g["source"] == "kitti_tracking"
                for f in range(g["first_frame"], g["last_frame"] + 1)}
    root = os.path.join(data_r3.DATA_R2, "kitti")
    counts = {}
    for part, seqs in (("train", sp["detector_train_sequences"]), ("val", sp["detector_val_sequences"])):
        want = [(s, f) for s in seqs for f in range(0, N_FRAMES[s], 2) if (s, f) not in excluded]
        kitti.download_frames(root, want, workers=16)
        os.makedirs(os.path.join(OUT, "images", part), exist_ok=True)
        os.makedirs(os.path.join(OUT, "labels", part), exist_ok=True)
        nb = 0
        labs = {s: kitti.read_labels(root, s) for s in seqs}
        for s, f in want:
            name = f"{s}_{f:06d}"
            src = os.path.join(root, "training", "image_02", s, f"{f:06d}.png")
            dst = os.path.join(OUT, "images", part, name + ".png")
            if not os.path.lexists(dst):
                os.symlink(src, dst)
            l = labs[s]
            l = l[(l.frame == f) & l.type.isin(CLS)]
            W, H = 1242.0, 375.0
            lines = []
            for r in l.itertuples():
                x1, y1, x2, y2 = max(0, r.x1), max(0, r.y1), min(W, r.x2), min(H, r.y2)
                if x2 <= x1 or y2 <= y1:
                    continue
                lines.append(f"{CLS[r.type]} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} "
                             f"{(y2 - y1) / H:.6f}")
            nb += len(lines)
            with open(os.path.join(OUT, "labels", part, name + ".txt"), "w") as fh:
                fh.write("\n".join(lines) + ("\n" if lines else ""))
        counts[part] = {"images": len(want), "boxes": nb, "sequences": seqs}
    with open(os.path.join(OUT, "kitti.yaml"), "w") as fh:
        fh.write(f"path: {OUT}\ntrain: images/train\nval: images/val\nnames:\n  0: person\n  1: car\n")
    json.dump(counts, open(os.path.join(OUT, "counts.json"), "w"), indent=1)
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
