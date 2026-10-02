#!/usr/bin/env python3
"""Domain adaptation of the MCU-target detector: fine-tune TinyissimoYOLO
(pinned upstream fork) from the R2 VOC checkpoint (30 CPU epochs) on KITTI
tracking tiles (scripts/r3/prepare_kitti_tiles.py; train sequences only,
no R3 validation/test frame), 2 classes (person, car), 256x256.

Checkpoint selection: best.pt by the trainer's fitness (0.1 mAP50 + 0.9
mAP50:95) on the detector-validation sequences 0013/0018 (never R3
validation or test segments). Runs in the venv of setup.sh, CPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time

EXT = os.environ.get("EXT", "/home/claude/ext")
UP = os.path.join(EXT, "TinyissimoYOLO")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", default="/home/claude/data_r2/tinyissimo_runs/voc07_v8b_256_e30/weights/last.pt")
    ap.add_argument("--data", default="/home/claude/data_r3/kitti_tiles/kitti_tiles.yaml")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--project", default="/home/claude/data_r3/tinyissimo_kitti")
    ap.add_argument("--name", default="tiles_e20")
    a = ap.parse_args()
    sys.path.insert(0, UP)
    os.chdir(UP)
    import subprocess

    import torch
    from ultralytics import YOLO

    m = YOLO("ultralytics/cfg/models/tinyissimo/tinyissimo-v8.yaml").load(a.init)
    t0 = time.time()
    m.train(data=a.data, project=a.project, name=a.name, exist_ok=True, optimizer="SGD", imgsz=256, epochs=a.epochs,
            batch=a.batch, workers=2, device="cpu", val=True, plots=False, seed=0, deterministic=True, amp=False)
    run = os.path.join(a.project, a.name)
    rec = {"upstream": "https://github.com/ETH-PBL/TinyissimoYOLO",
           "upstream_commit": subprocess.check_output(["git", "-C", UP, "rev-parse", "HEAD"], text=True).strip(),
           "variant": "tinyissimo-v8 (scale b), 2 classes", "init": a.init,
           "init_sha256": hashlib.sha256(open(a.init, "rb").read()).hexdigest(), "data": a.data,
           "train": "KITTI tracking det_train sequences, every 2nd frame, 3 tiles/frame, no R3 val/test frames",
           "checkpoint_selection": "best.pt by fitness on det_val sequences 0013, 0018 (tiles)",
           "epochs": a.epochs, "batch": a.batch, "imgsz": 256, "optimizer": "SGD", "device": "cpu",
           "torch": torch.__version__, "host": platform.platform(), "train_wall_s": time.time() - t0,
           "best_sha256": hashlib.sha256(open(os.path.join(run, "weights", "best.pt"), "rb").read()).hexdigest()}
    json.dump(rec, open(os.path.join(run, "finetune_record.json"), "w"), indent=1)
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
