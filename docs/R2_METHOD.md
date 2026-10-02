# R2 method: real detector traces, real-frame watcher, robust trigger and diversity-aware security

R1 (branch `claude/research-grade-simulation-r1m7cp`, HEAD 2d809b0) is kept
unchanged as the archived synthetic-detector baseline. R2 replaces the two
synthetic elements that dominated R1 (detector quality, watcher features)
with quantities computed from real annotated images, and replaces the two
R1 components that failed (EWMA-adaptive threshold, global cooldown/burst
gate).

## 1. What is real and what is simulated

| quantity | R2 source |
|---|---|
| images / video frames | REAL: PASCAL VOC 2007 test (4,952 images); KITTI tracking static-camera segments (1,189 frames at 10 Hz) |
| ground-truth boxes | REAL annotations (VOC "difficult" and KITTI DontCare / Van / Person_sitting / Cyclist / hard boxes are ignore regions) |
| detector predictions (boxes, classes, scores) | REAL: pretrained detectors executed on every image / every displayed (frame, variant) |
| detector accuracy (mAP) | REAL: pycocotools COCOeval |
| host detector latency | MEASURED on the cloud host CPU; never used as Portenta timing |
| watcher features | REAL: computed from the displayed low-resolution pixels |
| attack and noise overlays | image-domain perturbations of real frames (deterministic, seeded); their timing is a simulated threat model |
| M4/M7 timing, RPC, wake-up | SIMULATED (calibration pending) |
| power / energy | MODELED from uncalibrated power assumptions |

## 2. Detectors

* **MCU-target detector: TinyissimoYOLO** (ETH-PBL,
  https://github.com/ETH-PBL/TinyissimoYOLO, commit
  `19bea4bd1ea1e2c29a6ee6b14bd7494ce8c6ba25`), variant `tinyissimo-v8`
  scale `b` (839,392 parameters), 256x256 input, 20 VOC classes. No
  pretrained checkpoint is published upstream, so none is used. The upstream
  code (an Ultralytics 8.1.29 fork with AGPL-3.0 headers) is cloned at the
  pinned commit outside this repository (`scripts/detector/tinyissimo/setup.sh`);
  this repository only contains adapter scripts (VOC conversion, training,
  evaluation/export). A CPU-only training run was executed in the cloud
  container: 30 epochs, batch 64, VOC 2007 trainval, 2.0 h on 4 CPU cores
  (upstream: 1000 epochs, batch 512, GPU). VOC 2007 test: FP32 mAP50 0.258 /
  mAP50:95 0.118; INT8 (ONNX Runtime static PTQ of every Conv, 1.09 MB)
  0.257 / 0.118; 0.185 GMACs. It is reported as an UNDER-TRAINED MCU-target
  reference, not as TinyissimoYOLO's attainable accuracy
  (`results/r2/DETECTORS.md`).
* **Host-reference detectors** (real pretrained weights, real predictions):
  MediaPipe EfficientDet-Lite0 INT8 / FP32, SSD-MobileNetV2 FP32,
  EfficientDet-Lite2 INT8 (Apache-2.0, COCO-trained, SHA-256 pinned in
  `scripts/detector/models.py`). They are NOT MCU-class (2.7 - 5.5 M
  parameters) and are labelled host reference everywhere. In the R2
  simulation, stage 1 = EfficientDet-Lite0 INT8 and stage 2 (second pass of
  the early-exit cascade) = EfficientDet-Lite2 INT8.

## 3. Detector trace V2 and evaluation

`scripts/detector/trace_v2.py`: normalized `frames.csv`, `ground_truth.csv`,
`predictions.csv` (multiple boxes per frame), `model_metadata.json`,
`metrics.json`, `trace_manifest.json` (SHA-256 of every table).
`scripts/detector/coco_eval.py`: pycocotools mAP@0.5 and mAP@0.5:0.95,
per-class AP, and operating-point precision/recall/F1 with one-to-one greedy
matching. Regression tests with hand-computed values: `tests/test_r2.py`.

## 4. Real temporal data and overlays

KITTI tracking training sequences, camera image_02, segments where the ego
vehicle is stationary (OXTS speed < 0.2 m/s for >= 30 frames), split by whole
segment before any result (`data/splits/r2_kitti_splits.json`). Each displayed
frame is one observation at 10 Hz. Overlays (`scripts/r2/build_workloads.py`):

* noisy: low light x0.6, per-frame auto-exposure gain U(0.85, 1.15),
  Gaussian sensor noise sigma 10 and row noise sigma 4 (variants 16-19);
* spam: Poisson events (0.2/s x intensity), 1-3 frames each, global
  illumination flicker (x0.55 - x1.60) or a bright flash patch;
* replay: Poisson sessions (0.1/s x intensity), a 5-15-frame clip of the
  same camera recorded >= 3 s earlier replaces the live frames, exact or with
  one perturbation (brightness x0.85 / x1.15, noise sigma 6, JPEG q40,
  shift (+3,+2) px, brightness+noise+JPEG, shift+noise);
* mixed: spam and replay at half intensity.

The real detectors were run once on every (frame, variant) image
(`scripts/r2/image_bank.py`, 20 variants x 1,189 frames x 2 detectors).
Every operating mode replays the same workload JSONL, the same detector
table and the same overlay.

## 5. M4 watcher features from real frames

`scripts/r2/frame_features.py` (reference) and
`simulation/watcher/frame_features.h` (C++ port, bit-identical outputs on the
test frames in double and in the firmware float variant). Inputs: a 96x32
gray frame and a 17x16 thumbnail (camera binning). Two front ends:

* basic: frame-difference fraction, background-deviation fraction (EMA
  background, alpha 0.02), cell activity, scale-invariant edge-map Jaccard
  change, Immerkaer noise, intensity/edge consistency;
* gain-compensated (R2): global gain g = median over 48 cells of
  mean(B)/mean(L), clipped to [0.5, 2], applied before differencing; plus a
  12x4 motion-cell bitmask and a 48x16 foreground mask.

Fingerprints: 256-bit dHash of the 17x16 thumbnail; 64-bit dHash of a 9x8
downsample (the legacy gate's content signature). Operation count:
`frame_features.op_count_per_frame()` (about 1.45 x 10^5 simple operations per
frame, i.e. well under 1 ms at 240 MHz). No label or detector output is read
(checked by `tests/test_r2.py`).

## 6. Robust watcher (replaces legacy_adaptive)

`simulation/watcher/robust_watcher.h`:

```
S_t      = 0.30 m + 0.35 v + 0.20 tau + 0.15 c            (gain-compensated features)
med, MAD of the last 64 background scores (recorded while idle and S < theta_on)
sigma    = max(1.4826 MAD, sigma_floor)
theta_on = clamp(med + z_on sigma, theta_min, theta_max)
theta_off= clamp(med + z_off sigma, 0, theta_on)
IDLE -> ACTIVE after persist_k consecutive frames with S >= theta_on
ACTIVE -> IDLE after release_k consecutive frames with S < theta_off
```

The upper bound theta_max is the key difference from the legacy rule
(`theta + gain * max(0, ewma(noise) - ref)`), which raised the threshold
without bound when noise rose and lost real events (R1 noisy recall 0.486
vs 0.799 fixed). While ACTIVE, triggers are issued per content: the motion
cell mask is matched (>= overlap_thr of its cells inside a 1-cell dilation)
against up to 8 recently triggered regions; a new region triggers at once,
a known region re-triggers after content_cooldown_ms. Different objects in
a burst therefore trigger individually instead of being swallowed by one
global cooldown.

## 7. Diversity-aware security gate (replaces the legacy gate in robust_secure)

`simulation/security/robust_gate.h`, checks in order:

1. consistency: compensated motion and edge change must agree
   (r2_consistency >= c_min);
2. replay: block if some frame observed between `min_age` and `window` ago
   has foreground-mask Jaccard >= j_thr AND dHash-256 Hamming <= h_max.
   A whole-frame hash alone cannot separate replays from live static-camera
   frames (on the development split live frames lie 4-7 bits from old
   frames, perturbed replays 1-15 bits); the gain-compensated foreground mask
   carries the object configuration, which a replay reproduces;
3. per-content token bucket (8 slots keyed by motion-cell overlap, capacity
   b_c, refill r_c < global refill, so one content cannot hold the budget);
4. global token bucket (capacity B_g, refill R_g), with an emergency budget
   (capacity E, slow refill) that only novel content with watcher z >=
   z_emergency may use when the global bucket is empty.

Tokens are consumed only by accepted requests. The gate sees no label.
Memory: 20.9 KB with a 128-entry history (host check), 82 KB with 512.

## 8. Literature baseline

`mog2_event`: OpenCV MOG2 background subtraction (Zivkovic, ICPR 2004;
Zivkovic & van der Heijden, PRL 2006) on the same 96x32 frames (history
500, varThreshold 16, no shadow detection); trigger when the foreground
fraction >= threshold, global cooldown. Implemented and run under the same
workloads and tuning procedure as every other method.

## 9. Statistics

Pre-registered in `docs/PREREGISTERED_R2_ANALYSIS.md` (committed before
tuning and before any test run): 30 matched overlay realizations on the test
split, paired Wilcoxon signed-rank, rank-biserial effect size, Holm
correction, practical-size criteria.
