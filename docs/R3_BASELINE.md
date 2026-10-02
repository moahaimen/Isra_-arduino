# R3 baseline: the frozen R2 state (verified 2026-10-02 before any R3 change)

R3 starts from branch `research/q1-real-detector-r2` at commit `15b0a16`.
Branch `research/q1-contribution-r3` was created from exactly that commit.
Nothing of R1 (`claude/research-grade-simulation-r1m7cp`, `2d809b0`) or R2 is
modified by R3; R3 adds files under `scripts/r3/`, `results/r3/`, `docs/R3_*`
and new simulator components.

## Verification performed

| check | result |
|---|---|
| HEAD | `15b0a16`, clean working tree |
| test suite (`tests/run_tests.sh`) | C++ unit tests 205 passed, firmware host checks (R1, R2) PASS, 43 Python tests OK |
| frozen R2 parameters | SHA-256 `84e8712f653201dd88a23cf4e6e11da88f687d7b595953e5937d001e57e0dc9e` = committed `results/r2/frozen_params.sha256` |
| detector traces | every committed table of `data/detector_traces/real/*` matches its `trace_manifest.json` SHA-256 (predictions.csv of three VOC traces is git-ignored by design) |
| R2 result files | SHA-256 of every file in `results/r2/test/`, `RESULTS_R2.md`, `frozen_params.json`, pre-registration: `results/r3/r2_baseline_sha256.txt` |

## R2 baseline results (test split, KITTI static segments, 30 realizations)

| quantity | value |
|---|---|
| detectors on VOC 2007 test (mAP50 / mAP50:95) | EfficientDet-Lite0 INT8 0.708 / 0.459; Lite0 FP32 0.714 / 0.472; SSD-MobileNetV2 0.665 / 0.428; Lite2 INT8 0.766 / 0.533; TinyissimoYOLO v8-b 30 ep FP32 0.258 / 0.118, INT8 0.257 / 0.118 |
| detectors on KITTI test originals | Lite0 INT8 0.231 / 0.068; Lite2 INT8 0.240 / 0.078; TinyissimoYOLO FP32 0.121 / 0.031 |
| always-on ceiling (clean) | moving-track recall 0.278, timely (<= 1 s) 0.069 |
| confirmed hypotheses | C7 (FRR 0.270 vs 0.648 under spam x8), C9 (spam non-inferiority), C10 (duty 0.061 vs 1.0), C11 (energy) |
| not confirmed | C1-C3 significantly reversed (robust watcher worse than legacy EWMA in noisy: track recall 0.049 vs 0.198); C4-C6, C8 |

## R2 negative findings carried into R3 (diagnosis)

1. Detector ceiling too low: COCO detectors on 1242x375 KITTI frames squashed
   to a square input; always-on detects 11 of 41 moving test tracks.
2. TinyissimoYOLO under-trained (30 CPU epochs vs 1000 GPU epochs upstream).
3. Robust-watcher thresholds tuned on 2 validation segments did not transfer.
4. Legitimate-burst recall poor (robust_event 0.086 vs fixed threshold 0.229).
5. Replay check: exact/photometric replays 86-100 % caught, shifted 20-25 %.
6. Replay check caused most of robust_secure's FRR (0.26 -> 0.014 without it).
7. Token buckets / emergency budget never engaged at the tested rates.
8. No Portenta H7 timing or power measurement exists.

## Consequence for R3's test data

The R2 test segments were evaluated once in R2, and R3's design is informed by
the R2 failure analysis. They are therefore NOT an untouched test set for R3.
R3 builds its final test split from KITTI raw drives that are not part of the
KITTI tracking benchmark (see `docs/R3_GATE_A.md`).
