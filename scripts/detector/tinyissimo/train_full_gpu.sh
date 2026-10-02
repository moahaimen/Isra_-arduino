#!/usr/bin/env bash
# FULL TinyissimoYOLO training (upstream methodology) - requires a CUDA GPU.
#
# Not executed in the R3 cloud container (CPU only, no GPU). The R2 model
# (30 CPU epochs) is under-trained; this script is the complete, ready command
# for the full schedule, verified on a CPU smoke run (1 epoch, R2) with the
# same code path (scripts/detector/tinyissimo/train.py).
#
# Upstream: https://github.com/ETH-PBL/TinyissimoYOLO @ 19bea4bd1ea1e2c29a6ee6b14bd7494ce8c6ba25
# Upstream recipe (a_train_export.py): tinyissimo-v8 (scale b), 256x256, SGD,
# epochs 1000, batch 512, Ultralytics default augmentation and LR schedule
# (lr0 0.01, lrf 0.01 linear, momentum 0.937, weight decay 5e-4, warmup 3
# epochs, mosaic 1.0 closed for the last 10 epochs, HSV/flip/scale/translate
# defaults).
#
# Checkpoint selection: the trainer's validation set is VOC 2007 *val*
# (official val half of trainval), NOT VOC 2007 test; we train on VOC 2007
# train + VOC 2012 trainval when available, otherwise VOC07 train only, and
# keep both best.pt (val mAP50:95) and last.pt; the reported model is
# best.pt selected on val. VOC 2007 test is evaluated once afterwards with
# scripts/detector/tinyissimo/evaluate.py.
#
# Usage: bash train_full_gpu.sh [EPOCHS=1000] [BATCH=512] [SEED=0]
set -euo pipefail
EPOCHS=${1:-1000}
BATCH=${2:-512}
SEED=${3:-0}
HERE="$(cd "$(dirname "$0")" && pwd)"
EXT=${EXT:-/home/claude/ext}
DATA=${DATA:-/home/claude/data_r2}
bash "$HERE/setup.sh"
# shellcheck disable=SC1091
. "$EXT/tiy/bin/activate"
python - <<PY
import torch, sys
if not torch.cuda.is_available():
    sys.exit("CUDA GPU required for the full TinyissimoYOLO schedule (refusing a knowingly inadequate CPU run)")
print("GPU:", torch.cuda.get_device_name(0))
PY
# VOC07: train split for training, val split for checkpoint selection (never test)
python "$HERE/prepare_voc_yolo.py" --voc-root "$DATA/voc" --out "$DATA/voc_yolo_full" --select-split
cd "$EXT/TinyissimoYOLO"
python - <<PY
import json, os, time, hashlib, subprocess, torch
from ultralytics import YOLO
m = YOLO("ultralytics/cfg/models/tinyissimo/tinyissimo-v8.yaml")
t0 = time.time()
m.train(data="$DATA/voc_yolo_full/voc2007_select.yaml", project="$DATA/tinyissimo_runs", name="full_${EPOCHS}ep_s${SEED}",
        optimizer="SGD", imgsz=256, epochs=$EPOCHS, batch=$BATCH, device=0, seed=$SEED, deterministic=True,
        val=True, exist_ok=True)
run = "$DATA/tinyissimo_runs/full_${EPOCHS}ep_s${SEED}"
rec = {"upstream_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
       "epochs": $EPOCHS, "batch": $BATCH, "seed": $SEED, "imgsz": 256, "optimizer": "SGD",
       "gpu": torch.cuda.get_device_name(0), "train_wall_s": time.time() - t0,
       "checkpoint_rule": "best.pt by Ultralytics fitness (0.1 mAP50 + 0.9 mAP50:95) on VOC07 val",
       "best_sha256": hashlib.sha256(open(run + "/weights/best.pt", "rb").read()).hexdigest(),
       "last_sha256": hashlib.sha256(open(run + "/weights/last.pt", "rb").read()).hexdigest()}
json.dump(rec, open(run + "/train_record_full.json", "w"), indent=1)
print(rec)
PY
