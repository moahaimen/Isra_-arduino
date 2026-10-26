# Preregistration: oracle feasibility gate (E1)

Frozen 2026-10-26, committed to git before any held-out (test) frame is downloaded, read or run through a detector.
Only the oracle gate (E1) is preregistered here. Controller work (E2–E9) is not authorised unless this gate returns GO.

## 1. Question

Can a per-frame choice among a_t ∈ {SKIP, LOW, ROI, FULL}, selected by a privileged oracle using real
mode-specific detector outputs, preserve timely first detection (R_timely ≥ 0.90) at ≤ 0.60 × the M7 cost
of the strongest validation-tuned baseline on held-out sequences?

## 2. Data and splits (reused, frozen earlier, never changed here)

`data/splits/r3_splits.json` (SHA-256 in `data/splits/r3_splits.sha256`, committed in R3 before any R3 result).

| role here | R3 split | content |
|---|---|---|
| debugging only | development | KITTI tracking static segments 0001, 0002, 0020 |
| baseline tuning | validation | KITTI tracking static segments 0006, 0012, 0015, 0016, 0017, 0019 ×2 (1,039 frames, 61 moving tracks) |
| held-out evaluation | test (locked since R3, never opened) | KITTI raw 2011_09_26 drives 0017, 0019, 0029, 0051, 0057, 0084, static runs (723 frames) |

Sequences/drives are disjoint between validation and test (exact-OXTS mapping, `results/r3/gate_a/tracking_to_raw.csv`).
GT conventions are those of `scripts/r3/data_r3.py`. Moving track: R2 definition (`build_workloads.moving_tracks`,
≥ 2 non-ignored frames and ≥ 15 px centre displacement). Onset = first non-ignored frame of the track in the segment.

## 3. Detector modes (all real inference, one model)

Model: EfficientDet-Lite0 INT8 (MediaPipe, SHA-256 pinned in `scripts/detector/models.py`), score threshold 0.45
(R3/D1 value), IoU ≥ 0.5 one-to-one class-aware matching (`metrics_r2.match_tracks`).

| mode | input | Lite0 invocations | cost units |
|---|---|---|---|
| SKIP | none | 0 | 0 |
| LOW | whole 1242×375 frame squashed to 320×320 (reduced effective resolution) | 1 | 1 |
| ROI_k, k ∈ {0,1,2} | one of the three near-square tiles (1/3 width + 10 % overlap) at tile resolution | 1 | 1 |
| FULL | all three tiles, class-wise NMS (IoU 0.5) | 3 | 3 |

Every mode output is produced by running the model on that mode's pixels. ROI_k outputs are the raw tile-k
outputs; FULL is the NMS merge of the three tiles (identical to R3 stage 1). No accuracy is inferred from a cost model.
Primary cost: Lite0 invocations (∝ MACs: 0.974 GMAC per invocation from the TFLite graph). Mode-switching overhead:
none in the primary cost (same weights and arena for all modes); a sensitivity cost adds a fixed 0.25-unit overhead per
non-SKIP frame (wake / pre-processing), stated as a modelled assumption.

## 4. Metric

Track k is *timely detected* by a policy if, in some frame t with onset_k ≤ t ≤ onset_k + D (D = 10 frames = 1 s),
the policy ran mode a_t and a_t's outputs match track k. R_timely = timely tracks / moving tracks, pooled over the split.
C = Σ_t cost(a_t), reported per frame and relative to Always-FULL (= 3 units/frame). Detection results are applied at the
invoked frame for every policy and for the oracle (no simulated M7 queueing, identical for all; see deviations.md).

## 5. Oracle (privileged upper bound, never a deployable result)

Integer program per split: binary x_{t,a} (≤ 1 mode per frame), y_k (track k timely):
minimise Σ cost(a) x_{t,a} s.t. y_k ≤ Σ_{t ∈ W_k, a hits k at t} x_{t,a}, Σ_k y_k ≥ ⌈R·N⌉. Solved exactly (HiGHS via scipy `milp`).
It uses future GT and the same cached detector outcomes and costs as every policy. Reported separately as a privileged bound.
A restricted oracle with modes {SKIP, FULL} only is solved the same way (for criterion S1).

## 6. Baselines (same outcomes, same costs, tuned on validation only)

* B1 Always-FULL.
* B2 Fixed-period FULL, period P ∈ {1,…,30}.
* B3 Motion-triggered FULL: frame-difference foreground fraction of the 96×32 grayscale M4 image (R2 BASIC front end `m_raw`) > θ, then cooldown c frames.
* B4 Strongest existing adaptive scheduler: MOG2-event (OpenCV MOG2 foreground fraction > θ, cooldown c), the family that was best under leave-one-group-out in R3.1 Gate B (the R3/R3.1 utility-gated scheduler was dominated there and is not re-run).
* B5 Adaptive resolution: trigger as B3; LOW if score < θ_hi else FULL.
* B6 ROI-based: trigger as B3; ROI on the tile with the largest motion fraction.

Grids: θ over the 50 validation quantiles 0.50…0.995 of the score, c ∈ {0, 2, 5, 10, 20}, θ_hi over the same quantiles.
Selection rule (each family, validation only): the minimum-cost configuration with validation R_timely ≥ 0.90; if none,
the configuration with maximum R_timely (ties → lower cost). Selected configurations are frozen in
`03_oracle_gate/frozen_baselines.json` (hash recorded) before the test split is opened.

## 7. Frozen GO / STOP criteria (test split)

Let R_ceil = R_timely of the per-frame union over all modes (every mode on every frame); this caps every policy and the oracle.
Let the *best feasible baseline* be the family with the lowest test cost among baselines with test R_timely ≥ 0.90.

* **P1 (user criterion):** C_oracle(R ≥ max(0.90, R_best)) ≤ 0.60 · C_best.
* **P2 (user criterion):** the oracle reaches R_timely ≥ 0.90 (requires R_ceil ≥ 0.90).
* If no baseline reaches 0.90 on test, this is reported explicitly and P1 is evaluated against Always-FULL at R = 0.90 if R_ceil ≥ 0.90; otherwise **STOP** (the target is unattainable with the available detector).
* **S1 (added by this run, see deviations.md):** the four-mode contribution requires C_oracle ≤ 0.80 · C_oracle{SKIP,FULL} at the same R. If S1 fails, LOW/ROI add < 20 % beyond pure temporal skipping: the result is **NO-GO for the mode-selection claim** (the remaining temporal-skipping question is the one already closed in R3.1/D1).
* **GO** only if P1, P2 and S1 all pass. Any failure → **STOP**, no controller training.
* Deployability (Section 8) is reported alongside; a GO on host-reference detector modes would still need an MCU-deployable detector before any hardware-feasible claim.

## 8. Deployability check (reported, not part of P1/P2)

Peak activation memory (tensor-liveness bound from the TFLite graph), weight size and MACs per mode vs STM32H747 (1 MB SRAM total,
2 MB flash; Portenta H7 adds 8 MB SDRAM, 16 MB QSPI). Host CPU latency is labelled host-only; no Cortex-M7 latency is measured.

## 9. Statistics (descriptive at the gate)

Sequence-clustered bootstrap (resample segments, 10,000 replicates, seed 20261026) for R_timely of each policy and the oracle/baseline cost ratio.
With 6–7 segments the intervals are wide; this is stated, not hidden. Secondary descriptive analyses: D ∈ {5, 20} frames, the
0.25-unit overhead cost, and the per-frame quality oracle (cheapest mode whose matched set ⊇ Q_min of FULL's matched set, Q_min ∈ {0.8, 0.9, 1.0}).

---

# Addendum A (frozen 2026-10-26, after validation-only gate results, before any test result was computed)

Validation-only gate (diagnostic, not the decision): P1, P2, S1 pass; oracle cost is 2.2 % of fixed-period FULL (P = 2).
A clairvoyant oracle needs about one correctly placed invocation per track, so a pass mainly says the detector *can* see the
tracks; it says nothing about whether an M4 controller can know *when and where*. 29 of 61 validation tracks start at a segment's
first frame (left-censored by the segment cut).

Because the user's prompt says to proceed to controller work on GO but also to stop when a mandatory gate fails and not to
continue merely to produce figures, a second cheap gate is fixed now:

**E2 gate (causal controller).** Controllers (Section 7 of the prompt: rule-based = frozen B3/B5, logistic regression,
decision tree depth ≤ 4, gradient-boosted trees, MLP (16), and the proposed minimum-sufficient-inference predictor, MSIP)
are trained on validation + development segments only, with leave-one-segment-out (LOSO) selection of the decision threshold,
then frozen and evaluated once on test. Inputs are causal only: M4 features of frames ≤ t, frames since the last invocation,
detections returned by earlier invocations. Training labels (GT, training only): "running mode a at t would timely-detect a
moving track".
* **GO to E3–E9** only if the best validation-selected controller reaches, on test, R_timely ≥ 0.90 (or ≥ the best feasible
  baseline's R if higher) at cost ≤ 0.60 × that baseline's test cost.
* Otherwise **STOP** after E2: report the negative result; do not build the full figure/table package.
* Secondary (descriptive): the same comparison restricted to tracks whose onset is after the segment's first frame.
