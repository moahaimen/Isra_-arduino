# Q1-readiness audit of R2 (written as a hostile Reviewer 2)

Scope: branch `research/q1-real-detector-r2`. Numbers are taken from
`results/r2/RESULTS_R2.md`, `results/r2/test/*.csv`,
`results/r2/detectors_table.md` and `results/r2/DETECTORS.md`, all generated
by scripts in `scripts/r2/`. Verdict per question: PASS, PARTIAL or FAIL.

**Overall verdict: NOT READY for a strong Q1 submission.** R2 removed the
synthetic-detector and synthetic-feature weaknesses of R1 and produced a
clean, pre-registered evaluation, but that evaluation shows that the
proposed robust watcher and the diversity-aware gate do NOT deliver the
detection improvements they were designed for on the real test data. The
system-level evidence is also limited by a weak host-reference detector on
KITTI (always-on reaches only 0.28 moving-track recall) and by a small test
set (712 frames, 41 moving tracks).

## 1. Are detector outputs real? PASS

Every prediction comes from executing a real pretrained network:
EfficientDet-Lite0 INT8/FP32, SSD-MobileNetV2 FP32, EfficientDet-Lite2 INT8
(MediaPipe, SHA-256-pinned), and a TinyissimoYOLO model trained in this
container (see `results/r2/DETECTORS.md`). The simulator replays these
predictions (`trace_replay`); the synthetic distribution is used only by the
archived R1 study. Weakness: the host-reference detectors are COCO-trained
and not MCU-class (2.7-5.5 M parameters, 0.74-3.4 GMACs).

## 2. Are bounding boxes real? PASS

Ground truth: VOC 2007 and KITTI tracking annotations, unmodified (ignore
regions follow the official protocols). Predicted boxes are the detectors'
own boxes; trace V2 keeps every box above score 0.01 with its score and
class (`data/detector_traces/real/*`, image-bank traces).

## 3. Is mAP standard? PASS

pycocotools COCOeval (mAP@0.5, mAP@0.5:0.95, per-class AP), plus one-to-one
P/R/F1. Regression tests with hand-computed values (`tests/test_r2.py`:
perfect detections -> 1.0, half recall -> 51/101 under 101-point
interpolation, IoU-0.6 box -> exact mAP@0.5:0.95). VOC 2007 test: Lite0 INT8
0.708 / 0.459, Lite0 FP32 0.714 / 0.472, SSD-MobileNetV2 0.665 / 0.428.
Caveat: COCO-to-VOC class mapping (cross-dataset, no fine-tuning), and the
VOC mAP uses COCO's 101-point interpolation, not the VOC07 11-point metric.

## 4. Are watcher features derived from real frames? PASS

Computed from the displayed 96x32 frame and a 17x16 thumbnail
(`scripts/r2/frame_features.py`); C++ port `simulation/watcher/frame_features.h`
is bit-identical (double) and float-identical within 2e-8 on real frames
(`tests/test_r2.py::FrameFeatureTests`). No label or detector output is read.
About 1.45 x 10^5 simple operations per frame; 76.8 KB state in the float
firmware variant (host check).

## 5. Are the main results still dominated by synthetic assumptions? PARTIAL

Detection quality, features and overlays are now real-image-based. Still
synthetic: all timing (M7 inference 140 ms, second pass 110 ms, RPC, wake-up),
all power values (energy is modeled), the attack arrival processes and the
replay/spam threat model. The M7 timing model represents an MCU-class
detector, while the predictions come from larger host-reference detectors:
detection quality and latency therefore come from different models. The
duty-cycle and energy conclusions (C10, C11) are consequences of these
assumptions plus the real trigger decisions.

## 6. Was test-set tuning avoided? PASS (with disclosed amendment)

Splits frozen by segment before any result (commit 022a026). All parameters
tuned on validation with one declared objective and procedure
(`scripts/r2/tune_r2.py`, refuses other splits). The frozen file's SHA-256
was committed (`714870b`) before the test campaign, and the campaign refuses
to run on a mismatch. Disclosed deviations: (a) amendment 1 changed the
replay rule and its tuning grid after validation diagnosis, before freezing
and before any test run; (b) the test-split detector mAP (not used for any
choice) was printed by the image-bank job before the campaign. No
parameter was changed after the test campaign; the ablations (S3) are
labelled exploratory.

## 7. Is security blind to attack labels? PASS

The gate receives only observable frame data
(`RobustFrame`, `SecurityFrame`). Test: flipping every GT/attack label in a
workload leaves all watcher/gate/detector decisions byte-identical
(`tests/test_r2.py::test_decisions_blind_to_labels`).

## 8. Do legitimate bursts work? FAIL

The per-content cooldown triggers each object separately (unit tests), but
on the test split robust_event's burst recall is 0.086 (clean) vs 0.229
fixed_threshold and 0.257 MOG2; robust_secure's burst timely recall is 0.000
in the mixed scenario, as is legacy secure's (C4 not confirmed). The binding
constraint is not the cooldown: robust_event's validation-tuned thresholds
(theta_max 0.7, z_on 5) are conservative and miss objects on the test
scenes.

## 9. Does noisy operation work? FAIL

Pre-registered C1-C3 (noisy, robust_event vs legacy EWMA event) are
significant in the OPPOSITE direction: timely recall 0.001 vs 0.043, track
recall 0.049 vs 0.198, burst timely recall 0.001 vs 0.050 (Holm p < 1e-5).
The R1 failure mode of the legacy rule (recall 0.486 vs 0.799) does not
reproduce on real frames, and the robust watcher is worse. The gain
compensation itself works (flicker test; noisy-scenario duty 0.061 vs 0.330
for legacy event), but it buys duty, not recall.

## 10. Are perturbed replays handled? PARTIAL

Gate-level detection (S4): exact replays 97.9 % blocked as REPLAY;
brightness/noise/JPEG/combined 86-100 %; small shifts only 20-25 %. But
end-to-end replay attack success is not better than the legacy gate (C5,
C6 not confirmed: 0.002 vs 0.001 exact, 0.026 vs 0.035 perturbed), because
the legacy gate blocks almost everything, including 58-80 % of legitimate
requests. The dHash rule causes most of robust_secure's own FRR (0.26 ->
0.014 without the replay check, S3): static-camera scenes stay within 6
dHash bits of older frames.

## 11. Does security preserve useful detection under high attack load? PARTIAL

FRR under spam x8 is 0.270 vs 0.648 for the legacy gate (C7 confirmed), and
spam success stays within the non-inferiority margin (C9: 0.072 vs 0.034,
upper CI 0.047 <= 0.05). But useful detection is near zero for both gates
(timely recall 0.007 vs 0.002, C8 not confirmed), and robust_secure's
track recall (0.094) is far below the ungated baselines (0.20-0.29 at spam x8).
The token buckets and the emergency budget never bind at the tested rates
(S3: removing them changes nothing except the content bucket's FRR at x8).

## 12. Are all methods evaluated on identical frames/traces? PASS

One workload directory (wl.jsonl, det.csv, side.csv) per (segment, scenario,
intensity, seed) is replayed by all 8 modes; detector outputs keyed by
event; test `test_identical_detector_trace_across_modes`.

## 13. Are statistics pre-registered? PASS

`docs/PREREGISTERED_R2_ANALYSIS.md` committed (3595d61) before validation
tuning and before any test run; one amendment, dated and justified, before
freezing. 30 matched realizations, Wilcoxon signed-rank, rank-biserial,
Holm, practical-size criteria; all 11 outcomes reported (4 confirmed:
C7, C9, C10, C11; 7 not confirmed, 3 of them significantly reversed).

## 14. Are physical vs modeled quantities unmistakably separated? PASS

Host latencies are labelled HOST in every table; Portenta latency is "NOT
MEASURED" everywhere; `config/power_model.json` stays `calibrated: false`;
`trace_timing=simulated` makes the simulator ignore host timing.

## 15. What remains before submission?

1. **Detector domain gap.** COCO-trained detectors on squashed 1242x375
   KITTI frames (mAP50:95 0.07-0.08 on the test frames) leave too little
   detectable signal (11 of 41 moving tracks for always_on). Needed: a
   detector fine-tuned for the camera geometry (tiling or 2:1 input), or a
   surveillance-style dataset (MOT17 / VIRAT with detection GT); the cloud
   network policy blocks motchallenge.net.
2. **Data volume.** 2 validation segments did not represent the 5 test
   segments: the validation-tuned robust thresholds did not transfer.
   Needed: tens of sequences, cross-validation by sequence.
3. **Redesign of the robust watcher's operating point**: report full
   recall-duty trade-off curves (not one objective-chosen point) and compare
   methods at equal duty.
4. **Replay check:** a scene-specific fingerprint that is not fooled by
   static backgrounds (e.g. compare only within the active motion region),
   evaluated with FRR as a constraint.
5. **MCU-target detector:** TinyissimoYOLO (839k parameters, 0.185 GMACs) was
   trained here for 30 epochs on CPU (upstream: 1000 epochs, GPU) and reaches
   only VOC07-test mAP50 0.258 (INT8 1.09 MB: 0.257), versus 0.708 for the
   host-reference EfficientDet-Lite0. A fully trained model (GPU), its
   TFLite-Micro/X-CUBE-AI export and its on-board latency are required
   (`docs/HARDWARE_MINIMAL_R2.md`).
6. **Hardware calibration** of power and timing, end-to-end energy of one
   fixed trace.
7. A published wake-up baseline beyond MOG2 (e.g. a learned low-power trigger)
   under the same workloads.
