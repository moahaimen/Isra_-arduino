#!/usr/bin/env bash
# FULL TinyissimoYOLO training (R3.1 audited recipe). Two stages, requires a CUDA GPU.
#
#   Stage 1  VOC pretraining  : VOC07 train + VOC12 trainval (11,540 images), checkpoint selection on
#                               VOC07 val (2,510 images), VOC07 TEST never used for any choice.
#   Stage 2  KITTI-tile adaptation: person/car on 3 near-square tiles per KITTI-tracking frame
#                               (scripts/r3/prepare_kitti_tiles.py: train sequences only, selection on the
#                               detector-validation sequences 0013/0018; no R3 validation or test frame).
#   Export   ONNX (FP32) -> ONNX Runtime static PTQ INT8 (evaluate.py); the TFLite-Micro / X-CUBE-AI
#                               conversion for the Portenta is NOT implemented here.
#
# Upstream: https://github.com/ETH-PBL/TinyissimoYOLO @ 19bea4bd1ea1e2c29a6ee6b14bd7494ce8c6ba25
# Audit of the upstream recipe (docs/R3_1_GPU_AUDIT.md): a_train_export.py trains tinyissimo-v8 (scale 'b',
# 839,392 parameters at nc=20) at 256x256 with SGD, epochs=1000, batch=512 on "coco.yaml" (the shipped model
# config says nc: 20; Ultralytics replaces nc by the dataset's), all other hyper-parameters Ultralytics 8.1.29
# defaults: lr0 0.01, lrf 0.01 (linear), momentum 0.937, weight decay 5e-4, warmup 3 epochs, mosaic 1.0 with
# close_mosaic 10, HSV 0.015/0.7/0.4, translate 0.1, scale 0.5, fliplr 0.5, AMP on, seed 0, deterministic.
# We keep every one of those, change only the dataset (VOC07+12 here, KITTI tiles in stage 2) and add a
# held-out validation set for checkpoint selection.
#
# Usage:  bash train_full_gpu.sh [EPOCHS1=1000] [BATCH1=512] [EPOCHS2=200] [BATCH2=128] [SEED=0]
# Smoke:  SMOKE=1 bash train_full_gpu.sh     (CPU, 1 epoch, 1 % of the data, writes only to *_smoke dirs;
#                                              verifies the code path, produces NO result)
set -euo pipefail
E1=${1:-1000}; B1=${2:-512}; E2=${3:-200}; B2=${4:-128}; SEED=${5:-0}
SMOKE=${SMOKE:-0}
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
EXT=${EXT:-/home/claude/ext}
DATA=${DATA:-/home/claude/data_r2}
R3=${R3:-/home/claude/data_r3}
bash "$HERE/setup.sh" >/dev/null
# shellcheck disable=SC1091
. "$EXT/tiy/bin/activate"
if [ "$SMOKE" = "1" ]; then DEV=cpu; E1=1; E2=1; B1=16; B2=16; FRAC=0.01; TAG=_smoke; else DEV=0; FRAC=1.0; TAG=""; fi
python - <<PY
import sys, torch
if "$SMOKE" != "1" and not torch.cuda.is_available():
    sys.exit("CUDA GPU required for the full TinyissimoYOLO schedule (refusing a knowingly inadequate CPU run); use SMOKE=1 to test the code path")
PY
python "$HERE/prepare_voc_yolo.py" --voc-root "$DATA/voc" --out "$DATA/voc_yolo_full" --select-split --with-2012
cd "$EXT/TinyissimoYOLO"
python - <<PY
import hashlib, json, os, platform, subprocess, time
import torch
from ultralytics import YOLO

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
env = {"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none (SMOKE/CPU)",
       "cuda": torch.version.cuda, "torch": torch.__version__, "python": platform.python_version(),
       "upstream_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()}
runs = "$DATA/tinyissimo_runs"
# ---- stage 1: VOC pretraining
t0 = time.time()
m = YOLO("ultralytics/cfg/models/tinyissimo/tinyissimo-v8.yaml")
n_params = sum(p.numel() for p in m.model.parameters())
m.train(data="$DATA/voc_yolo_full/voc2007_select.yaml", project=runs, name="s1_voc_${E1}ep_s${SEED}$TAG",
        optimizer="SGD", imgsz=256, epochs=$E1, batch=$B1, device="$DEV", seed=$SEED, deterministic=True,
        val=True, exist_ok=True, fraction=$FRAC, plots=False)
r1 = runs + "/s1_voc_${E1}ep_s${SEED}$TAG"
rec = {"env": env, "stage1": {"epochs": $E1, "batch": $B1, "seed": $SEED, "imgsz": 256, "optimizer": "SGD",
       "data": "VOC07 train + VOC12 trainval; select on VOC07 val", "parameters": n_params,
       "wall_s": time.time() - t0, "best_sha256": sha(r1 + "/weights/best.pt"), "last_sha256": sha(r1 + "/weights/last.pt"),
       "selection": "best.pt by Ultralytics fitness (0.1 mAP50 + 0.9 mAP50-95) on VOC07 val",
       "curve": "results.csv in the run directory"}}
# ---- stage 2: KITTI tile adaptation (person/car), initialised from the stage-1 best checkpoint
t0 = time.time()
m2 = YOLO("ultralytics/cfg/models/tinyissimo/tinyissimo-v8.yaml").load(r1 + "/weights/best.pt")
m2.train(data="$R3/kitti_tiles/kitti_tiles.yaml", project=runs, name="s2_kitti_${E2}ep_s${SEED}$TAG",
         optimizer="SGD", imgsz=256, epochs=$E2, batch=$B2, device="$DEV", seed=$SEED, deterministic=True,
         val=True, exist_ok=True, fraction=$FRAC, plots=False)
r2 = runs + "/s2_kitti_${E2}ep_s${SEED}$TAG"
rec["stage2"] = {"epochs": $E2, "batch": $B2, "seed": $SEED, "data": "KITTI tracking det_train tiles; select on det_val tiles (0013, 0018)",
                 "wall_s": time.time() - t0, "best_sha256": sha(r2 + "/weights/best.pt"), "last_sha256": sha(r2 + "/weights/last.pt")}
json.dump(rec, open(r2 + "/train_record_r31.json", "w"), indent=1)
print(json.dumps(rec, indent=1))
PY
