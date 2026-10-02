#!/usr/bin/env bash
# End-to-end reproduction of the R2 study (CPU only; several hours).
set -euo pipefail
cd "$(dirname "$0")/../.."
apt-get install -y -q libegl1 libgles2 >/dev/null 2>&1 || echo "install libegl1 libgles2 for MediaPipe"
pip install -q numpy pandas scipy matplotlib pycocotools==2.0.11 ai-edge-litert==2.2.0 mediapipe==1.0.1 \
    opencv-python-headless pillow
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release >/dev/null && cmake --build build -j"$(nproc)" >/dev/null
bash scripts/r2/fetch_data.sh
DATA=${DATA:-/home/claude/data_r2}
# real detectors on VOC 2007 test
for m in efficientdet_lite0_int8 efficientdet_lite0_fp32 ssd_mobilenet_v2_fp32 efficientdet_lite2_int8; do
  out=$DATA/voc_traces/voc2007_test_$m
  [ -f "$out/metrics.json" ] || python3 scripts/detector/run_real_detector.py --dataset voc2007 --split test \
      --model $m --model-dir "$DATA/models" --data-root "$DATA/voc" --out "$out"
done
# image bank (M4 inputs + real Lite0/Lite2 predictions on every frame variant)
for s in development validation test; do python3 scripts/r2/image_bank.py --split $s --step m4; done
for m in efficientdet_lite0_int8 efficientdet_lite2_int8; do for s in development validation test; do
  for k in 0 1 2 3; do python3 scripts/r2/image_bank.py --split $s --step detect --models $m --shard $k --nshards 4 & done; wait
  python3 scripts/r2/image_bank.py --split $s --step merge --models $m --nshards 4
done; done
# validation-only tuning, freeze (the committed frozen_params.json is used as is if present)
if [ ! -f results/r2/frozen_params.json ]; then
  python3 scripts/r2/tune_common.py
  python3 scripts/r2/tune_r2.py
  python3 scripts/r2/freeze_params.py
  echo "commit results/r2/frozen_params.* before running the test campaign"; exit 0
fi
python3 scripts/r2/run_test_campaign.py
python3 scripts/r2/run_ablation_r2.py
python3 scripts/r2/replay_variants_r2.py
python3 scripts/r2/analyze_r2.py --campaign "$DATA/test_campaign" --out results/r2/test
python3 scripts/r2/detector_table.py
python3 scripts/r2/make_report_r2.py
# MCU-target detector (separate venv, upstream pinned, not copied)
bash scripts/detector/tinyissimo/setup.sh
echo "TinyissimoYOLO: see scripts/detector/tinyissimo/{prepare_voc_yolo,train,evaluate}.py"
