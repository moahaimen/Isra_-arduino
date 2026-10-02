# Paper contribution package (R3, provisional)

Status: the full paper is NOT justified yet (Gates A-C not satisfied, no confirmatory test). This file states what
can be defended on the present evidence and what cannot. All R3 numbers below are validation-split, tuned, descriptive.

## Problem statement

An always-on camera node with a low-power core (M4) and a high-power detector core (M7) must decide per frame
whether to wake the M7, under (i) real scene dynamics and sensor noise, (ii) attacks that waste wakes (trigger spam,
denial of sleep) or present stale content (replay), and (iii) a requirement not to drop legitimate detections.

## Research gap

Prior art on event-triggered / wake-up vision typically reports energy and a single trigger accuracy on synthetic or
still-image workloads, and security work blocks attacks without reporting what it costs legitimate detections.
(No systematic literature review was performed in this project; verify before use.) R1-R3 show that both
matter: R2's gate blocked replays by rejecting 62-65 % of legitimate requests.

## Method (docs/R3_ALGORITHM.md)

Gain-compensated M4 features -> bounded noise-normalised evidence accumulator (hysteresis) -> per-component content
regions with novelty -> closed-loop utility rule (confirm / retry / back-off from the M7's own returned detections) ->
temporal-context replay session test -> global wake budget with reserved novelty budget. Header-only C++, 92 KB (history 64).

```
for each frame t:  f <- features(L_t)                          # M4, no labels
  e_t <- clip((S_t - b)/s - z0, 0, e_max);  A <- rho A + e_t;  active <- hysteresis(A)
  for each connected component of the motion mask: region <- match_or_create(.)        # novelty
  wake <- active and (some region novel or (some region due and outstanding < K))        # utility/load
  if wake and gate.accept(t, thumbnail, novel):  send(); mark regions checked
on result(cells): region.confirmed <- cells intersect region                              # closed loop
gate: replay <- stale (n_old <= k) and discontinuous (n_prev >= j) [session state]; else token buckets
```

## Defensible contributions (on current evidence)

1. A real-frame benchmark methodology (matched traces, tiled detection, overlays, validation-only tuning,
   pre-registered confirmatory test in R2) and the diagnosis that a 33 % -> 98 % track-recall gap came from input geometry, not model capacity.
2. A closed-loop wake scheduler that is the best of 6 methods on clean validation video at ~25 % duty
   (UR_timely 0.91, track 0.99), with a wake-efficiency audit explaining where wakes go.
3. An availability-preserving replay test: FRR 0.7-2.9 % vs 62-65 % (R2) with 96 % exact-replay blocking.

## Negative results to report

* The legacy EWMA rule retains more on noisy validation video (0.90 vs 0.78 at similar duty).
* R2's robust watcher and gate did not transfer; R2 confirmatory hypotheses C1-C3 were reversed.
* Trigger spam is not suppressed by the R3 gate; novelty priority is exploitable by diverse spam.
* Shifted replay is not handled; the global budget raises FRR to 10.7 % at spam x8.
* The MCU-class detector trained here is far from usable (about 3.7 h of CPU training in total); no on-board numbers exist.
* The validation data cannot reward avoiding useless wakes (object-dense scenes).

## Limitations

KITTI standstill segments only (61 validation tracks); tuned on the validation groups reported; modeled M7 timing
and energy; host detectors; single implementation (no independent Python reference of scheduler/gate); no literature
search; no hardware.

## Generated artefacts

Figures: `results/r3/figures/fig_pareto_duty_utility_validation.png`, `fig_secure_utility_validation.png`.
Tables: `results/r3/gate_a/detectors_validation.csv`, `results/r3/gate_b_summary.csv`, `results/r3/gate_c_summary.csv`,
`results/r3/tuning/*` (grids, Pareto fronts, iterations). Architecture figure, algorithm flow figure, ablation and final
main/security tables are NOT produced because the final campaign and component ablations were not run.
