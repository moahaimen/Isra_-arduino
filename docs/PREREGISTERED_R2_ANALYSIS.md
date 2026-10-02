# Pre-registered analysis plan: R2 real-detector-trace study

Status: **written and committed before any validation tuning result and
before any test-split simulation result was computed.** Only the
development split (3 short segments, 2 moving tracks) has been run, as a
pipeline smoke test. Any later change to this document is made in a separate
commit with the reason stated, and all analyses specified here are reported
whatever their outcome.

## 1. Data, units and splits

* Frames: KITTI tracking (training), camera image_02, static-camera segments
  (OXTS speed < 0.2 m/s for >= 30 frames). Split frozen in
  `data/splits/r2_kitti_splits.json` (commit 022a026) by whole segment:
  development 150 frames (0001, 0002, 0020), validation 327 frames (0006,
  0017), test 712 frames (0012, 0015, 0016, 0019 x 2).
* Every displayed frame is one observation (10 Hz). The M4 features are
  computed from the displayed pixels (`scripts/r2/frame_features.py`).
* Detector outputs are REAL: stage 1 = EfficientDet-Lite0 INT8, stage 2 =
  EfficientDet-Lite2 INT8 (MediaPipe, COCO-trained, SHA-256 pinned), run once
  on every (frame, variant) of the image bank (`scripts/r2/image_bank.py`)
  and replayed identically by every mode. M7 timing and all power values are
  SIMULATED (calibration pending).
* Scenarios (`scripts/r2/build_workloads.py`): clean, noisy, spam (intensity
  0, 0.5, 1, 2, 4, 8, 16), replay_exact, replay_perturbed, mixed (intensity 1).
* Replication unit for confirmatory tests: one **realization** = one overlay
  seed with all 5 test segments pooled (counts summed over segments, then
  ratios formed). Test seeds 1..30 (30 realizations, matched across modes:
  every mode runs on identical workload files). Validation seeds
  1001..1010. Clean has no overlay randomness (only simulated timing
  varies with the seed), so clean results are descriptive only.

## 2. Methods compared (all on the same workloads)

| name | watcher | security | early exit |
|---|---|---|---|
| always_on | none (M7 runs continuously) | none | yes |
| motion_only | frame-difference motion >= threshold, global cooldown | none | no |
| mog2_event | MOG2 foreground fraction >= threshold, global cooldown (literature baseline, Zivkovic 2004/2006) | none | no |
| fixed_threshold | R1 score, fixed threshold, global cooldown | none | no |
| event | R1 score, legacy EWMA-adaptive threshold ("legacy_adaptive"), global cooldown | none | yes |
| secure | as event | legacy R1 gate | yes |
| robust_event | R2 robust watcher (gain-compensated front end, median/MAD threshold bounded to [theta_min, theta_max], hysteresis, persistence, per-content cooldown) | none | yes |
| robust_secure | as robust_event | R2 gate (consistency, foreground-mask + dHash replay check, per-content and global token buckets, emergency budget for novel content) | yes |

## 3. Metrics (definitions in `scripts/r2/metrics_r2.py`)

* **Moving track**: KITTI track (Car or Pedestrian, non-ignored boxes)
  spanning >= 2 frames whose box centre moves >= 15 px between its first and
  last non-ignored frame.
* **Track detected**: some frame processed by the M7 that shows LIVE content
  (not a replayed frame) yields, from the stage that ran last, a box with
  confidence >= detection threshold matching the track's GT box (same class,
  IoU >= 0.5, one-to-one, greedy by confidence).
* **track_recall** = detected moving tracks / moving tracks.
  **timely_recall** = tracks detected within 1.0 s of onset (first
  non-ignored frame) / moving tracks.
  **burst tracks** = moving tracks whose onset is within 2.0 s of another
  moving track's onset in the same segment; **burst_timely_recall** analogous.
* **attack success** = attack frames whose request reached the M7 (detector
  started) / attack frames; separately for spam frames, exact-replay frames
  and perturbed-replay frames.
* **FRR** = legitimate requests blocked by the gate / legitimate requests
  evaluated by the gate.
* **duty_cycle** = M7 awake time / simulated time; **energy** = modeled
  energy (uncalibrated power model x simulated state times), mJ.
* Latency: track latency (onset to first detection) and trigger-to-result.

## 4. Tuning (validation split only)

* Shared detector-level parameters (`scripts/r2/tune_common.py`): detection
  threshold = argmax mean box F1 of stage 1 and stage 2 on validation
  original frames over {0.30..0.70}; early-exit (hi, lo) = argmax
  F1(cascade) - 0.1 x stage-2 fraction.
* Method parameters (`scripts/r2/tune_r2.py`): identical procedure for every
  method. Objective
  `J = mean_C timely_recall - 0.5 * mean_C duty_cycle - 0.5 * mean_{C in attack conditions} attack_success`
  over conditions C = clean, noisy, spam x1, spam x8, replay_exact,
  replay_perturbed, mixed x1 (validation seeds 1001..1010, clean 1001..1003).
  Coordinate descent, 2 passes, over the declared grid of each method,
  starting from the R1 defaults; secure variants start from the tuned
  watcher of their non-secure counterpart and tune only gate parameters.
* The selected parameters are written to `results/r2/frozen_params.json`;
  its SHA-256 is committed (`results/r2/frozen_params.sha256`) BEFORE the test
  campaign is run. The test campaign refuses to run if the hash differs.
  `scripts/r2/tune_r2.py` refuses any split other than validation.

## 5. Confirmatory hypotheses (one family C1-C8, C10, C11, Holm-Bonferroni, alpha = 0.05; C9 non-inferiority)

Test: two-sided Wilcoxon signed-rank on the 30 matched realization pairs
(zero differences discarded; < 6 non-zero pairs = not testable = not
confirmed). Effect size: matched-pairs rank-biserial correlation; also mean
paired difference with 95 % t-interval. A hypothesis is CONFIRMED only if
the Holm-adjusted p < 0.05, the effect has the stated direction, AND the
practical-size criterion holds.

| id | scenario | metric | comparison | confirmed if |
|---|---|---|---|---|
| C1 | noisy | timely_recall | robust_event vs event | robust higher by >= 0.10 |
| C2 | noisy | track_recall | robust_event vs event | robust higher by >= 0.10 |
| C3 | noisy | burst_timely_recall | robust_event vs event | robust higher by >= 0.10 |
| C4 | mixed x1 | burst_timely_recall | robust_secure vs secure | robust higher by >= 0.10 |
| C5 | replay_exact | replay_exact_success | robust_secure vs secure | robust lower by >= 0.10 |
| C6 | replay_perturbed | replay_pert_success | robust_secure vs secure | robust lower by >= 0.10 |
| C7 | spam x8 | frr | robust_secure vs secure | robust lower by >= 0.10 |
| C8 | spam x8 | timely_recall | robust_secure vs secure | robust higher by >= 0.10 |
| C9 | spam x8 | spam_success | robust_secure vs secure | NON-INFERIORITY: upper bound of the 95 % t-interval of the mean paired difference (robust - legacy) <= +0.05 (not part of the Holm family; Wilcoxon reported for information) |
| C10 | noisy | duty_cycle | robust_event vs always_on | robust mean <= 0.5 x always_on mean, significant |
| C11 | noisy | energy_mJ | robust_event vs always_on | robust mean <= 0.6 x always_on mean, significant |

Primary metrics are those listed in the table; no other metric or
comparison is confirmatory.

## 6. Secondary / exploratory analyses (reported in full, Holm within each family)

* S1: every method against robust_secure on timely_recall, track_recall,
  duty_cycle, energy and attack success, per scenario.
* S2: spam intensity sweep 0, 0.5, 1, 2, 4, 8, 16 x for all methods: attack
  success, timely recall, FRR, duty cycle, modeled energy, latency (means and
  95 % CIs).
* S3: component ablations of robust_event / robust_secure on the test split,
  run after the main campaign with the frozen parameters: basic front end,
  persist_k = 1, global cooldown, fixed threshold (no robust normalisation),
  no replay check, no content buckets, no emergency budget.
* S4: replay detection per perturbation variant; replay memory/compute cost.
* S5: detector-level results: pycocotools mAP50 / mAP50:95 of every detector
  on PASCAL VOC 2007 test and on the KITTI test original frames.
* Clean scenario: descriptive (per segment) only.
* R1 (synthetic detector) vs R2 (real traces): side-by-side table, never
  pooled.

## 7. Reporting rules

* All 11 confirmatory outcomes are reported, including failures.
* No run is excluded; failed runs would be reported with their error.
* Host detector latencies are labelled HOST; no Portenta timing or power
  value is reported as measured.

## Amendment 1 (2026-10-02, before freezing parameters and before any test-split run)

Validation tuning showed that the replay check of the R2 gate, as first
written (foreground-mask Jaccard >= j_thr AND dHash Hamming <= h_max), let
~14 % of exact-replay frames through: the foreground mask is computed
against the current, drifting background estimate, so an exact replay
reaches only Jaccard ~0.55 with its original (validation diagnosis:
`scripts/r2/diagnose_replay.py`). The dHash of the frame itself separates
replays from live moving frames (validation: live median 20 bits, 5th
percentile 5; exact replays 0; photometric/JPEG/noise replays <= 5; shifted
replays 9-20).

Change: the foreground-mask condition is optional (j_thr <= 0 disables it)
and the robust_secure tuning grid becomes rg_fg_jaccard_thr in {0, 0.5, 0.6,
0.7, 0.8}, rg_dhash_max in {2, 4, 6, 8, 12, 16, 32}, rg_fg_min in {0, 12};
all other grids, the objective, the confirmatory hypotheses and the
success criteria are unchanged. Only robust_secure is re-tuned. The
validation result that motivated the change (the legacy EWMA rule is not
worse than the robust watcher on the validation noisy condition) is NOT
acted upon: the watcher design and its grid are unchanged.
