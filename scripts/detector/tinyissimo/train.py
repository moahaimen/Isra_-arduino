#!/usr/bin/env python3
"""Train TinyissimoYOLO on PASCAL VOC 2007 trainval with the upstream trainer.

Runs inside the venv created by setup.sh; imports the upstream package from
the pinned clone ($EXT/TinyissimoYOLO). Hyper-parameters follow upstream
a_train_export.py (tinyissimo-v8 at scale 'b', 256x256, SGD) except for the
epoch count and batch size, which are reduced to fit the compute that is
actually available (CPU only in the cloud container). The run records every
setting in <project>/<name>/train_record.json; the final-epoch weights
(last.pt) are used, never a checkpoint selected on test data (val=False).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

EXT = os.environ.get("EXT", "/home/claude/ext")
UP = os.path.join(EXT, "TinyissimoYOLO")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="/home/claude/data_r2/voc_yolo/voc2007.yaml")
    ap.add_argument("--variant", default="v8", choices=["v8", "v5", "v1-small"])
    ap.add_argument("--imgsz", type=int, default=256)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--project", default="/home/claude/data_r2/tinyissimo_runs")
    ap.add_argument("--name", default="voc07_v8b_256")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, UP)
    os.chdir(UP)
    import subprocess

    import torch
    from ultralytics import YOLO

    commit = subprocess.check_output(["git", "-C", UP, "rev-parse", "HEAD"], text=True).strip()
    run_dir = os.path.join(a.project, a.name)
    if a.resume:
        model = YOLO(os.path.join(run_dir, "weights", "last.pt"))
    else:
        model = YOLO(f"ultralytics/cfg/models/tinyissimo/tinyissimo-{a.variant}.yaml")
    rec = {"upstream": "https://github.com/ETH-PBL/TinyissimoYOLO", "upstream_commit": commit,
           "variant": f"tinyissimo-{a.variant}" + (" (scale b)" if a.variant in ("v8", "v5") else ""),
           "imgsz": a.imgsz, "epochs": a.epochs, "batch": a.batch, "optimizer": "SGD", "data": a.data,
           "train_split": "VOC2007 trainval (5011 images, difficult boxes excluded)", "val_during_training": False,
           "checkpoint_used": "last.pt (final epoch)", "device": "cpu", "torch": torch.__version__,
           "host": platform.platform(), "cpu_count": os.cpu_count(),
           "parameters": int(sum(p.numel() for p in model.model.parameters())),
           "upstream_recipe": "a_train_export.py: 256x256, epochs=1000, batch=512, SGD, GPU"}
    os.makedirs(run_dir, exist_ok=True)
    t0 = time.time()
    model.train(data=a.data, project=a.project, name=a.name, exist_ok=True, optimizer="SGD", imgsz=a.imgsz,
                epochs=a.epochs, batch=a.batch, workers=a.workers, device="cpu", val=False, plots=False,
                seed=0, deterministic=True, resume=a.resume, amp=False)
    rec["train_wall_s"] = time.time() - t0
    with open(os.path.join(run_dir, "train_record.json"), "w") as f:
        json.dump(rec, f, indent=2)
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
