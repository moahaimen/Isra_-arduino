# E1 oracle feasibility gate and E2 causal-controller check

Protocol: `00_protocol/preregistration.md` (commit 941f4f3, before any test frame was read) and Addendum A (commit aa0cbd7, before
any test result). Frozen baselines: commit 9efe7ed (`frozen_baselines.json`, SHA-256 e6dbcb1e…). Frozen controllers: commit 2bb62f1.
All numbers below come from `oracle_results.csv`, `gate_test.json`, `gate_validation.json`, `per_segment_*.csv`, `per_track_*.csv`,
`new_onset_tracks_secondary.csv`, `../04_experiments/controller_results/*`, `../07_statistics/e2_test_comparison.json`.
Cost unit = one EfficientDet-Lite0 invocation (0.974 GMAC); Always-FULL = 3 units/frame. Host timings are not Cortex-M7 timings;
no energy is claimed.

## Data actually used

| split | role | segments | frames | moving tracks | notes |
|---|---|---|---|---|---|
| validation | tuning / controller training | 7 KITTI tracking static segments | 1,039 | 61 (42 person, 19 car) | 29 tracks start at a segment's first frame |
| test | held-out, opened once | 6 KITTI raw static runs | 723 | 32 (all car) | one segment has no moving track; 6 tracks start at frame 0 |

Real mode outputs were regenerated for every frame and mode; validation reproduces R3 Gate A exactly (FULL timely ceiling 0.918,
LOW 0.197).

## Held-out results (test)

| policy (frozen on validation) | R_timely | cost / frame | vs Always-FULL |
|---|---|---|---|
| union ceiling (all modes, every frame) | 1.000 (32/32) | — | — |
| B1 Always-FULL | 1.000 | 3.00 | 1.00 |
| B2 Fixed-period FULL (P = 2) | 1.000 | 1.50 | 0.50 |
| B3 Motion-triggered FULL | 0.906 | 0.96 | 0.32 |
| **B4 MOG2-event FULL (best feasible baseline)** | **0.906 (29/32)** | **0.80** | **0.27** |
| B5 Adaptive resolution (selected config never chose LOW) | 0.906 | 0.96 | 0.32 |
| B6 ROI on most-moving tile | 0.469 | 0.19 | 0.06 |
| **Oracle, 4 modes (privileged)** | 0.906 | **0.028** | 0.009 |
| Oracle, {SKIP, FULL} only (privileged) | 0.906 | 0.079 | 0.026 |
| Per-frame quality oracle, Q_min = 0.9 (privileged, every frame) | 1.000 | 1.81 | 0.60 |

### E1 gate (preregistered criteria)

* P1: C_oracle / C_best = 20 / 579 = **0.035** (segment bootstrap 95 % CI 0.014–0.042) ≤ 0.60 → pass.
* P2: oracle R_timely 0.906 ≥ 0.90 → pass. The baseline did reach 0.90 on test (it did not on validation: 0.82).
* S1: 4-mode / {SKIP, FULL} oracle cost = 20 / 57 = **0.35** ≤ 0.80 → pass (0.40 with 0.25-unit switching overhead).
* **E1 formally GO.** Validation gives the same picture (oracle 2.2 % of fixed-period P = 2; S1 0.39).

Why this pass is weak evidence: the clairvoyant oracle needs only ~one correctly placed single-tile invocation per track
(test: 20 invocations for 29 tracks, over 723 frames). Any detector that sees the objects at all yields this; it measures the
detector's reach, not whether an M4 can know *when and where* to look. This was anticipated in Addendum A.

### E2 gate (causal controllers, preregistered in Addendum A)

Six controller families, trained on validation with leave-one-segment-out selection, then frozen:

| controller (test) | R_timely | cost / frame | note |
|---|---|---|---|
| FULL-trigger, logistic regression | 1.000 | 3.00 | fires every frame |
| FULL-trigger, decision tree (depth 4) | 1.000 | 3.00 | fires every frame |
| **FULL-trigger, gradient-boosted trees** (validation-selected) | 1.000 | 3.00 | 3.75 × MOG2 cost (95 % CI 2.9–5.9) |
| FULL-trigger, MLP (16) | 1.000 | 2.90 | |
| MSIP (proposed cost-aware mode rule), logistic regression | 0.813 | 1.02 | |
| MSIP, decision tree | 0.844 | 0.80 | same cost as MOG2, lower recall |
| MSIP, gradient-boosted trees | 0.844 | 1.33 | |
| MSIP, MLP | 0.969 | 1.65 | 2.1 × MOG2 cost |

Required to pass: R_timely ≥ 0.906 at ≤ 0.48 units/frame. **No controller comes close → E2 STOP.**

The reason is measured, not assumed: out-of-fold AUROC of the M4 features (frame-difference fraction, per-tile motion, MOG2
foreground, short rolling means) for "an invocation now would timely-detect a moving track" is **0.49–0.53**, i.e. chance.
To reach 0.90 recall the learned controllers must therefore run almost every frame. Hand-tuned motion/MOG2 triggering is already
the strongest causal policy found in R3.1 and again here.

### Secondary (descriptive)

* Tracks with onset after the segment start (validation 32, test 26): MOG2 0.656 / 0.885, fixed-period P = 2 0.844 / 1.000,
  oracle 0.812 / 0.885 (pooled constraint), validation ceiling 0.844. On validation even Always-FULL reaches only 0.844 on these.
* Deadline D = 5 / 20 frames: validation ceiling 0.869 / 0.934; test 1.0 / 1.0.
* LOW is nearly useless on KITTI geometry (every-frame timely ceiling 0.197 on validation): squashing a 1242×375 frame to 320×320
  loses small objects. The oracle's savings come from ROI tiles, which a causal policy must localise (B6: R 0.47).

## Decision

**STOP.** The privileged oracle shows that the detector modes contain large headroom, but the cheap M4 signals cannot predict
it, so there is no evidence that a deployable minimum-sufficient-inference controller beats simple motion/MOG2 triggering.
Controller development beyond this check, E3–E9, figures and manuscript sections were not produced, per the prompt
("STOP immediately…", "Never continue merely to produce attractive figures").
