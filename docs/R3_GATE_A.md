# Gate A: detector and data quality (validation split only)

**Verdict: PASS for host-reference detectors; FAIL for the MCU-target detector.**
The R3 test split (723 frames of KITTI raw drives 17, 19, 29, 51, 57, 84) was NOT touched:
`scripts/r3/run_detector_r3.py` and `image_bank_r3.py` refuse `--split test` without
`--allow-test`, and no test frame has been read by any R3 script.

## Data

| split | source | frames | moving tracks |
|---|---|---|---|
| development | KITTI tracking static segments 0001, 0002, 0020 | 150 | 2 |
| validation | KITTI tracking static segments 0006, 0012, 0015, 0016, 0017, 0019 x 2 (the R2 test segments are R3 validation: their R2 results are known, so they cannot be R3 test) | 1,039 | 61 |
| test | KITTI RAW drives 2011_09_26_drive_{0017, 0019, 0029, 0051, 0057, 0084}, static runs (OXTS speed < 0.2 m/s, >= 30 frames); tracking-benchmark sources excluded by exact OXTS match (`results/r3/gate_a/tracking_to_raw.csv`); boxes projected from the raw 3D tracklets | 723 | not yet computed (locked) |

Manifest `data/splits/r3_splits.json` (SHA-256 in `r3_splits.sha256`, committed at `7228e82`
before any R3 detector result). Licence: KITTI, CC BY-NC-SA 3.0, images not redistributed.
MOT17, VisDrone-VID, UA-DETRAC, VIRAT/MEVA video and Hugging Face are blocked or unavailable
from this container (checked 2026-10-02); KITTI remains the only temporal source, so the
sequence-diversity limitation of R2 persists (see Q1_READINESS_R3.md).

## Detector results on validation (frame-level, 1,039 original frames, pycocotools)

| detector | role | params | GMACs/frame | mAP50 | mAP50:95 | AP50 person / car | AP S / M / L | R@0.45 | frame-level track ceiling | timely ceiling (<= 1 s) |
|---|---|---|---|---|---|---|---|---|---|---|
| EfficientDet-Lite0 INT8, whole frame squashed to 320x320 (R2 setting) | host ref | 3.32 M | 0.97 | 0.244 | 0.087 | 0.010 / 0.477 | 0.016 / 0.063 / 0.294 | 0.071 | **0.328** | 0.197 |
| EfficientDet-Lite0 INT8, 3 tiles (R3 stage 1) | host ref | 3.32 M | 2.92 | 0.688 | 0.308 | 0.754 / 0.621 | 0.328 / 0.310 / 0.421 | 0.660 | **0.984** | 0.918 |
| EfficientDet-Lite2 INT8, 3 tiles (R3 stage 2) | host ref | 5.52 M | 10.1 | 0.760 | 0.344 | 0.814 / 0.706 | 0.444 / 0.333 / 0.434 | 0.758 | **1.000** | 0.902 |
| YOLOv8n COCO @1248x384 | host ref | 3.16 M | 5.18 | 0.785 | 0.359 | 0.813 / 0.757 | 0.522 / 0.334 / 0.494 | 0.749 | 1.000 | 0.918 |
| YOLOv8s COCO @1248x384 | host ref | 11.2 M | 16.9 | 0.811 | 0.375 | 0.816 / 0.806 | 0.523 / 0.351 / 0.497 | 0.784 | 1.000 | 0.967 |
| TinyissimoYOLO v8-b, VOC checkpoint (30 CPU epochs), 3 tiles | MCU target | 0.84 M | 0.56 | 0.481 | 0.167 | 0.571 / 0.391 | 0.113 / 0.156 / 0.314 | 0.258 | 0.869 | 0.574 |
| TinyissimoYOLO v8-b fine-tuned on KITTI tiles (+20 CPU epochs), 3 tiles | MCU target | 0.83 M | 0.56 | 0.407 | 0.174 | 0.127 / 0.687 | 0.179 / 0.170 / 0.313 | 0.175 | 0.410 | 0.271 |

Source: `results/r3/gate_a/detectors_validation.csv` (`scripts/r3/gate_a_report.py`); traces in
`/home/claude/data_r3/gate_a` (not in git; regenerate with `run_detector_r3.py`).
mAP is computed against the validation GT with Van / Cyclist / Person_sitting / small / occluded
boxes as ignore regions. Host numbers are not Portenta numbers.

## Key finding (confirms the R2 diagnosis)

The R2 "detector ceiling" problem was an input-geometry problem: squashing a 1242x375 frame into
a 320x320 input leaves 33 % track recall (0.33) even if the detector sees every frame; processing
three near-square tiles of the SAME model recovers 98 % (Lite0) / 100 % (Lite2). Detector
domain adaptation was not needed for the host-reference detectors.

## Always-on ceiling (R_ceiling), simulated M7 that processes frames sequentially

Validation, 3 clean and 3 noisy realizations per segment (`always_on` mode, tiled cascade,
threshold 0.45): timely track recall **0.847 (clean) / 0.716 (noisy)**; track recall 0.995 / 0.967
(182 and 177 of 183). It is below the frame-level ceiling because the simulated M7 needs ~140 ms
per frame (a modeled value). Utility retention = R_method / R_always_on is defined on these.

## MCU-target detector: FAIL

TinyissimoYOLO trained here (CPU, 30 + 20 epochs) cannot serve as the always-on detector
(timely ceiling 0.57 / 0.27). `scripts/detector/tinyissimo/train_full_gpu.sh` is the complete
upstream-recipe command (1000 epochs, batch 512, VOC07 train + val for selection, test untouched),
syntax-checked and with its data conversion tested; it refuses to run without a CUDA GPU. NOT RUN
(no GPU in this container). All R3 scheduling results therefore use the host-reference cascade
(EfficientDet-Lite0 tiles, Lite2 tiles as second pass) as the M7 detector's predictions, with
M7 timing simulated.

## Shared detector parameters (validation)

Detection threshold 0.45 (argmax of mean F1 of both stages over 0.20-0.70), early exit
hi 0.5 / lo 0.3 (`results/r3/tuning/common.json`): the cascade sends only 1.5 % of frames to
stage 2 (stage-1 F1 0.733 vs stage-2 0.755).
