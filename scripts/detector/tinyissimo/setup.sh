#!/usr/bin/env bash
# TinyissimoYOLO (MCU-target detector) environment.
#
# The upstream code (ETH-PBL, an Ultralytics 8.1.29 fork carrying AGPL-3.0
# headers) is NOT copied into this repository. It is cloned at a pinned
# commit outside the repo and imported from there by the adapter scripts in
# this directory, which are owned by this repository.
set -euo pipefail
EXT=${EXT:-/home/claude/ext}
UPSTREAM=https://github.com/ETH-PBL/TinyissimoYOLO.git
COMMIT=19bea4bd1ea1e2c29a6ee6b14bd7494ce8c6ba25
mkdir -p "$EXT"
if [ ! -d "$EXT/TinyissimoYOLO" ]; then git clone -q "$UPSTREAM" "$EXT/TinyissimoYOLO"; fi
git -C "$EXT/TinyissimoYOLO" checkout -q "$COMMIT"
test "$(git -C "$EXT/TinyissimoYOLO" rev-parse HEAD)" = "$COMMIT"
if [ ! -d "$EXT/tiy" ]; then python3 -m venv "$EXT/tiy"; fi
# shellcheck disable=SC1091
. "$EXT/tiy/bin/activate"
# PyPI torch (download.pytorch.org is not reachable from the cloud container;
# the PyPI wheel runs on CPU when no GPU is present).
pip install -q "torch==2.5.1" "torchvision==0.20.1"
pip install -q "numpy<2" "opencv-python-headless<4.11" matplotlib pyyaml requests scipy tqdm pandas seaborn \
    psutil py-cpuinfo pillow "onnx==1.16.2" "onnxruntime==1.19.2" thop pycocotools
echo "TinyissimoYOLO at $COMMIT in $EXT/TinyissimoYOLO, venv $EXT/tiy"
