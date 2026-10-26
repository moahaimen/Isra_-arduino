# Final Phase-Robust Report

Date: 14 October 2026 · Frozen protocol: `PROTOCOL_PHASE_ROBUST_FROZEN.md` (written before any validation data; source hashes in `phase_robust_results/source_hashes_at_freeze.txt`). Nothing from earlier stages was modified.

## Baseline failure (kept)

The previous stage, `reference_monitor_final/`, ended **REVISE**: behavioral → ngspice transfer lost **0.119** layer macro-F1 (frozen limit 0.10; behavioral 0.658 → ngspice 0.539, CI [0.107, 0.132]). A post-hoc diagnostic attributed most of it to the sampling phase of the reference edge. This stage tests that explanation and its cure on new seeds.

## Decision

**GO.**

| criterion | behavioral | ngspice |
|---|---|---|
| A retention ≥ 0.85·N at ±20% (known, E ≤ 2%) | PASS | PASS |
| B beats old method and one-point baselines (CI > 0) | PASS | — |
| C AFE–ADC cross-confusion < 0.15 at ±20% | PASS | PASS |
| D retention ≥ 0.70·N at E = ±5% | PASS | PASS |
| E behavioral→ngspice loss ≤ 0.10 (E = 2%, ngspice grid) | PASS | — |
| G phase variation ≤ 0.05 | PASS | PASS |

N (layer macro-F1, known reference, ×1.0, pooled over phases): behavioral 0.659, ngspice 0.660. F (evidence) is satisfied by construction: every improvement quoted below carries a paired 5000-resample bootstrap CI.

**Transfer loss, primary method (PRr, E = 2%):** behavioral 0.650 → ngspice 0.649, loss **0.002** (CI [-0.003, 0.006]) against the previous stage's 0.119. With mixed behavioral + ngspice training (PRrM) the ngspice score is 0.663 (loss relative to behavioral -0.013).

**How to read this GO.** It means the pre-registered gates are met in the two simulated domains, and that the specific failure of the previous stage (a sampling-phase mismatch) is removed: with ψ spanning 0–0.999 the old Revision-1 descriptors vary by 0.081 layer macro-F1 while the phase-robust ones vary by 0.006, and the behavioral→ngspice loss falls from 0.119 to 0.002. Because the behavioral and ngspice models are now near-identical first-order models (0.1–0.3 mV apart noise-free), a transfer loss near zero is expected once the timing convention is handled; it does not show that hardware would behave the same (see limitations).

Mixed-training variant against the same ngspice-domain gates: all pass (reported only; the pre-registered primary is PRr).

## 1. What was tested

* **Phase model.** Reference/mux edges fall `ψ·T` after the previous sample (ψ ∈ {0, 0.25, 0.5, 0.75, 0.999}); ψ = 0 is the old behavioral convention, ψ = 0.999 the failed ngspice placement. Both domains implement the fractional edge exactly (behavioral two-stage discretisation; ngspice hold-then-step PWL). Noise-free, they agree to 0.1–0.3 mV RMS at every phase (development seed).
* **Phase-robust descriptors (PR).** The five fixed-sample rise fractions are replaced by whole-transient descriptors from a fit with a free edge time: fitted time constant, 10–50% and 50–90% rise-time differences, normalised transient area, fit residual (plus the retained plateau-settling errors). The fit is a deterministic grid search with closed-form span, so it cannot fail to converge; the documented fallback (|S| < 1e-4) was never triggered in 16,200 development-seed records (checked after the validation run; the validation records themselves were not counted).
* **Arms.** A0 old; R1 Revision-1; R1r R1 + phase randomisation; PR phase-robust; **PRr phase-robust + phase randomisation (primary)**; PRrM PRr + mixed behavioral + ngspice training; no-monitor control. The reference monitor (E = 0, 1, 2, 5%) and the known-reference variant are kept; all nine fault classes, tolerances, noise and 12-bit quantisation are in every test set.
* **Disclosure.** Development/debugging used seed 20261097 only (and earlier stages used 20261098/20261099). The validation seeds 20261026–28 were not seen before the freeze; no descriptor, fit setting, threshold or model was chosen from validation results.

| dataset seed | train / val / test conditions | overlap | split rs (test / val) | ngspice runs | ngspice wall s |
|---|---|---|---|---|---|
| 20261026 | 222 / 40 / 88 | 0 | 20261027 / 20261028 | 13878 | 908.1 |
| 20261027 | 222 / 40 / 88 | 0 | 20261028 / 20261029 | 13878 | 908.9 |
| 20261028 | 222 / 40 / 88 | 0 | 20261029 / 20261030 | 13878 | 905.9 |

## 2. Which ingredient helps? (E = 2%, pooled over amplitudes and phases)

| domain | arm | layer macro-F1 | layer balanced acc. | fault macro-F1 | fault balanced acc. | ψ=0 | ψ=0.25 | ψ=0.5 | ψ=0.75 | ψ=0.999 |
|---|---|---|---|---|---|---|---|---|---|---|
| behavioral | A0 | 0.281 | 0.321 | 0.227 | 0.251 | 0.279 | 0.279 | 0.281 | 0.281 | 0.282 |
| behavioral | R1 | 0.614 | 0.622 | 0.638 | 0.644 | 0.649 | 0.636 | 0.614 | 0.590 | 0.568 |
| behavioral | R1r | 0.644 | 0.647 | 0.654 | 0.656 | 0.651 | 0.650 | 0.648 | 0.641 | 0.626 |
| behavioral | PR | 0.655 | 0.661 | 0.666 | 0.668 | 0.657 | 0.656 | 0.655 | 0.655 | 0.653 |
| behavioral | PRr | 0.656 | 0.660 | 0.668 | 0.670 | 0.659 | 0.658 | 0.656 | 0.653 | 0.652 |
| behavioral | PRrM | 0.672 | 0.674 | 0.675 | 0.676 | 0.677 | 0.676 | 0.672 | 0.668 | 0.667 |
| ngspice | R1 | 0.606 | 0.616 | 0.631 | 0.638 | 0.642 | 0.625 | 0.606 | 0.584 | 0.561 |
| ngspice | R1r | 0.635 | 0.640 | 0.647 | 0.651 | 0.643 | 0.642 | 0.638 | 0.631 | 0.617 |
| ngspice | PR | 0.646 | 0.654 | 0.661 | 0.663 | 0.649 | 0.648 | 0.647 | 0.644 | 0.642 |
| ngspice | PRr | 0.649 | 0.654 | 0.662 | 0.665 | 0.654 | 0.651 | 0.649 | 0.645 | 0.643 |
| ngspice | PRrM | 0.663 | 0.666 | 0.671 | 0.673 | 0.667 | 0.665 | 0.664 | 0.659 | 0.658 |

(last five columns: layer macro-F1 at each phase.) Paired comparisons:

| domain | comparison | layer macro-F1 difference [95% CI] |
|---|---|---|
| behavioral | PR - R1 (descriptors alone) | +0.042 [+0.033, +0.051] ✓ |
| behavioral | R1r - R1 (phase randomisation alone) | +0.030 [+0.023, +0.038] ✓ |
| behavioral | PRr - R1r (descriptors, given randomisation) | +0.012 [+0.004, +0.019] ✓ |
| behavioral | PRr - PR (randomisation, given robust descriptors) | +0.000 [-0.005, +0.006] |
| behavioral | PRr - R1 (combination) | +0.042 [+0.034, +0.050] ✓ |
| behavioral | PRrM - PRr (mixed training) | +0.017 [+0.008, +0.025] ✓ |
| behavioral | PRr - A0 (vs old method) | +0.375 [+0.363, +0.387] ✓ |
| ngspice | PR - R1 (descriptors alone) | +0.041 [+0.032, +0.049] ✓ |
| ngspice | R1r - R1 (phase randomisation alone) | +0.029 [+0.022, +0.037] ✓ |
| ngspice | PRr - R1r (descriptors, given randomisation) | +0.014 [+0.006, +0.022] ✓ |
| ngspice | PRr - PR (randomisation, given robust descriptors) | +0.003 [-0.004, +0.009] |
| ngspice | PRr - R1 (combination) | +0.043 [+0.035, +0.051] ✓ |
| ngspice | PRrM - PRr (mixed training) | +0.014 [+0.005, +0.024] ✓ |

**Reading.**

* *Phase-robust descriptors alone* (PR vs R1, both trained at ψ = 0): improves layer macro-F1 by 0.042 (CI [+0.033, +0.051]) in the behavioral domain and improves layer macro-F1 by 0.041 (CI [+0.032, +0.049]) on ngspice.
* *Phase randomisation alone* (R1r vs R1): improves layer macro-F1 by 0.030 (CI [+0.023, +0.038]) behavioral; improves layer macro-F1 by 0.029 (CI [+0.022, +0.037]) ngspice.
* *Descriptors given randomisation* (PRr vs R1r): improves layer macro-F1 by 0.012 (CI [+0.004, +0.019]) behavioral; improves layer macro-F1 by 0.014 (CI [+0.006, +0.022]) ngspice. *Randomisation given robust descriptors* (PRr vs PR): has no resolvable effect (+0.000, CI [-0.005, +0.006]) behavioral; has no resolvable effect (+0.003, CI [-0.004, +0.009]) ngspice.
* *Combination* (PRr vs R1): improves layer macro-F1 by 0.042 (CI [+0.034, +0.050]) behavioral; improves layer macro-F1 by 0.043 (CI [+0.035, +0.051]) ngspice.
* *Mixed-domain training* (PRrM vs PRr): improves layer macro-F1 by 0.017 (CI [+0.008, +0.025]) behavioral; improves layer macro-F1 by 0.014 (CI [+0.005, +0.024]) ngspice.

Overall layer macro-F1 is not the same thing as phase robustness; the more telling quantity is the spread across phases:

| domain | arm | layer macro-F1 range over the 5 phases (max − min) | ≤ 0.05 (gate G threshold) |
|---|---|---|---|
| behavioral | A0 | 0.003 | yes |
| behavioral | R1 | 0.081 | no |
| behavioral | R1r | 0.025 | yes |
| behavioral | PR | 0.004 | yes |
| behavioral | PRr | 0.006 | yes |
| behavioral | PRrM | 0.010 | yes |
| ngspice | R1 | 0.081 | no |
| ngspice | R1r | 0.026 | yes |
| ngspice | PR | 0.007 | yes |
| ngspice | PRr | 0.010 | yes |
| ngspice | PRrM | 0.009 | yes |

(Gate G itself is applied to PRr for the known and E = 2% variants; the other arms are shown for attribution.) A0 is flat across phase only because it is already far below the others once the reference amplitude is shifted (§3).

Figures: `phase_robust_figures/fig1_phase_sensitivity.png`, `fig3_attribution.png`.

## 3. A — retention, C — confusion, D — monitor error

| domain | condition | ×0.8 | ×1.2 | A |
|---|---|---|---|---|
| behavioral | known reference | 0.615 (0.93) | 0.643 (0.98) | PASS |
| behavioral | monitor E=0% | 0.610 (0.93) | 0.642 (0.98) | PASS |
| behavioral | monitor E=±1% | 0.608 (0.92) | 0.644 (0.98) | PASS |
| behavioral | monitor E=±2% | 0.614 (0.93) | 0.663 (1.01) | PASS |
| ngspice | known reference | 0.616 (0.93) | 0.642 (0.97) | PASS |
| ngspice | monitor E=0% | 0.606 (0.92) | 0.644 (0.98) | PASS |
| ngspice | monitor E=±1% | 0.604 (0.92) | 0.644 (0.98) | PASS |
| ngspice | monitor E=±2% | 0.611 (0.93) | 0.664 (1.01) | PASS |

| domain | condition | ×0.8 | ×1.2 |
|---|---|---|---|
| behavioral | known reference | AFE 0.91 / ADC 0.83 / cross 0.026 | AFE 0.90 / ADC 0.80 / cross 0.089 |
| behavioral | monitor E=0% | AFE 0.88 / ADC 0.84 / cross 0.035 | AFE 0.86 / ADC 0.80 / cross 0.085 |
| behavioral | monitor E=±1% | AFE 0.91 / ADC 0.83 / cross 0.032 | AFE 0.88 / ADC 0.79 / cross 0.087 |
| behavioral | monitor E=±2% | AFE 0.89 / ADC 0.83 / cross 0.035 | AFE 0.88 / ADC 0.80 / cross 0.079 |
| behavioral | monitor E=±5% | AFE 0.89 / ADC 0.78 / cross 0.033 | AFE 0.88 / ADC 0.78 / cross 0.083 |
| ngspice | known reference | AFE 0.91 / ADC 0.83 / cross 0.028 | AFE 0.90 / ADC 0.80 / cross 0.088 |
| ngspice | monitor E=0% | AFE 0.88 / ADC 0.84 / cross 0.036 | AFE 0.86 / ADC 0.80 / cross 0.083 |
| ngspice | monitor E=±1% | AFE 0.90 / ADC 0.84 / cross 0.033 | AFE 0.87 / ADC 0.79 / cross 0.086 |
| ngspice | monitor E=±2% | AFE 0.88 / ADC 0.83 / cross 0.036 | AFE 0.88 / ADC 0.80 / cross 0.078 |
| ngspice | monitor E=±5% | AFE 0.89 / ADC 0.77 / cross 0.034 | AFE 0.88 / ADC 0.78 / cross 0.081 |

Largest cross-confusion: 0.089 (bh|known|a120); limit 0.15.

| domain | scope | layer macro-F1 at E = 5% | fraction of N | ≥ 0.70 |
|---|---|---|---|---|
| behavioral | a80 | 0.611 | 0.928 | PASS |
| behavioral | a120 | 0.649 | 0.985 | PASS |
| behavioral | pooled | 0.648 | 0.985 | PASS |
| ngspice | a80 | 0.610 | 0.924 | PASS |
| ngspice | a120 | 0.646 | 0.979 | PASS |
| ngspice | pooled | 0.640 | 0.969 | PASS |

**No-monitor control** (the same PRr known-reference classifier given the nominal levels although the amplitude changed), layer macro-F1 pooled over phases:

| amplitude | with known reference | no monitor (assumed nominal) |
|---|---|---|
| x0.8 | 0.615 | 0.310 |
| x0.9 | 0.646 | 0.423 |
| x1.0 | 0.659 | 0.659 |
| x1.1 | 0.667 | 0.389 |
| x1.2 | 0.643 | 0.237 |

Figures: `fig2_amplitude_curves.png`, `fig4_cross_confusion.png`.

## 4. B — superiority at ±20% (behavioral, pooled over phases; two-point PRr minus baseline, layer macro-F1)

| condition | amplitude | two-point A0 | passive | single probe | AFE-only A0 | ADC-only A0 | AFE-only PRr | ADC-only PRr |
|---|---|---|---|---|---|---|---|---|
| known reference | ×0.8 | +0.475 [+0.461, +0.489] ✓ | +0.356 [+0.341, +0.371] ✓ | +0.266 [+0.250, +0.282] ✓ | +0.295 [+0.280, +0.311] ✓ | +0.495 [+0.482, +0.508] ✓ | +0.142 [+0.128, +0.155] ✓ | +0.160 [+0.144, +0.175] ✓ |
| known reference | ×1.2 | +0.521 [+0.507, +0.535] ✓ | +0.384 [+0.368, +0.400] ✓ | +0.246 [+0.230, +0.261] ✓ | +0.348 [+0.329, +0.366] ✓ | +0.521 [+0.507, +0.534] ✓ | +0.126 [+0.112, +0.140] ✓ | +0.190 [+0.176, +0.206] ✓ |
| monitor E=0% | ×0.8 | +0.470 [+0.456, +0.483] ✓ | +0.351 [+0.337, +0.366] ✓ | +0.261 [+0.246, +0.276] ✓ | +0.290 [+0.276, +0.305] ✓ | +0.490 [+0.478, +0.502] ✓ | +0.134 [+0.122, +0.145] ✓ | +0.154 [+0.140, +0.168] ✓ |
| monitor E=0% | ×1.2 | +0.521 [+0.508, +0.533] ✓ | +0.383 [+0.369, +0.399] ✓ | +0.246 [+0.231, +0.260] ✓ | +0.347 [+0.329, +0.365] ✓ | +0.521 [+0.508, +0.533] ✓ | +0.127 [+0.114, +0.141] ✓ | +0.185 [+0.171, +0.199] ✓ |
| monitor E=±1% | ×0.8 | +0.468 [+0.455, +0.480] ✓ | +0.349 [+0.335, +0.364] ✓ | +0.259 [+0.244, +0.274] ✓ | +0.288 [+0.274, +0.303] ✓ | +0.488 [+0.477, +0.499] ✓ | +0.135 [+0.123, +0.147] ✓ | +0.154 [+0.140, +0.168] ✓ |
| monitor E=±1% | ×1.2 | +0.523 [+0.510, +0.535] ✓ | +0.385 [+0.371, +0.401] ✓ | +0.247 [+0.233, +0.262] ✓ | +0.349 [+0.331, +0.368] ✓ | +0.522 [+0.510, +0.534] ✓ | +0.133 [+0.120, +0.147] ✓ | +0.190 [+0.175, +0.205] ✓ |
| monitor E=±2% | ×0.8 | +0.474 [+0.459, +0.488] ✓ | +0.356 [+0.340, +0.371] ✓ | +0.265 [+0.250, +0.281] ✓ | +0.294 [+0.279, +0.310] ✓ | +0.494 [+0.481, +0.507] ✓ | +0.144 [+0.131, +0.157] ✓ | +0.153 [+0.138, +0.167] ✓ |
| monitor E=±2% | ×1.2 | +0.541 [+0.527, +0.555] ✓ | +0.404 [+0.389, +0.420] ✓ | +0.266 [+0.251, +0.282] ✓ | +0.368 [+0.348, +0.388] ✓ | +0.541 [+0.528, +0.554] ✓ | +0.156 [+0.141, +0.170] ✓ | +0.203 [+0.187, +0.219] ✓ |
| monitor E=±5% | ×0.8 | +0.471 [+0.455, +0.488] ✓ | +0.353 [+0.336, +0.370] ✓ | +0.263 [+0.246, +0.279] ✓ | +0.292 [+0.275, +0.309] ✓ | +0.492 [+0.477, +0.506] ✓ | +0.144 [+0.130, +0.159] ✓ | +0.164 [+0.148, +0.180] ✓ |
| monitor E=±5% | ×1.2 | +0.528 [+0.512, +0.543] ✓ | +0.390 [+0.374, +0.407] ✓ | +0.252 [+0.236, +0.269] ✓ | +0.354 [+0.334, +0.373] ✓ | +0.527 [+0.513, +0.541] ✓ | +0.138 [+0.122, +0.154] ✓ | +0.199 [+0.182, +0.216] ✓ |

Smallest CI lower bound over all 70 comparisons: +0.112.

## 5. E — domain transfer and G — phase variation

| variant | BB (behavioral) | BS (PRr on ngspice) | loss BB−BS [CI] | ≤ 0.10 | MS (PRrM on ngspice) | MS−BS [CI] |
|---|---|---|---|---|---|---|
| known reference | 0.639 | 0.639 | -0.001 [-0.005, 0.004] | PASS | 0.677 | +0.038 [+0.029, +0.047] |
| monitor E=0% | 0.636 | 0.635 | 0.001 [-0.003, 0.004] | PASS | 0.675 | +0.040 [+0.031, +0.050] |
| monitor E=±1% | 0.637 | 0.634 | 0.002 [-0.001, 0.006] | PASS | 0.670 | +0.036 [+0.027, +0.045] |
| monitor E=±2% | 0.650 | 0.649 | 0.002 [-0.003, 0.006] | PASS | 0.663 | +0.014 [+0.005, +0.024] |
| monitor E=±5% | 0.640 | 0.640 | 0.001 [-0.003, 0.005] | PASS | 0.655 | +0.015 [+0.006, +0.024] |

| domain | arm | variant | ψ=0 | ψ=0.25 | ψ=0.5 | ψ=0.75 | ψ=0.999 | range (max−min) | ≤ 0.05 |
|---|---|---|---|---|---|---|---|---|---|
| behavioral | PRr | known reference | 0.648 | 0.646 | 0.646 | 0.645 | 0.643 | 0.005 | PASS |
| behavioral | PRr | monitor E=±2% | 0.659 | 0.658 | 0.656 | 0.653 | 0.652 | 0.006 | PASS |
| behavioral | PRrM | known reference | 0.690 | 0.687 | 0.686 | 0.683 | 0.679 | 0.011 | PASS |
| behavioral | PRrM | monitor E=±2% | 0.677 | 0.676 | 0.672 | 0.668 | 0.667 | 0.010 | PASS |
| behavioral | R1 | known reference | 0.638 | 0.625 | 0.603 | 0.580 | 0.556 | 0.082 | **FAIL** |
| behavioral | R1 | monitor E=±2% | 0.649 | 0.636 | 0.614 | 0.590 | 0.568 | 0.081 | **FAIL** |
| behavioral | A0 | known reference | 0.279 | 0.279 | 0.281 | 0.281 | 0.282 | 0.003 | PASS |
| behavioral | A0 | monitor E=±2% | 0.279 | 0.279 | 0.281 | 0.281 | 0.282 | 0.003 | PASS |
| ngspice | PRr | known reference | 0.645 | 0.640 | 0.641 | 0.637 | 0.634 | 0.011 | PASS |
| ngspice | PRr | monitor E=±2% | 0.654 | 0.651 | 0.649 | 0.645 | 0.644 | 0.010 | PASS |
| ngspice | PRrM | known reference | 0.683 | 0.682 | 0.677 | 0.674 | 0.670 | 0.013 | PASS |
| ngspice | PRrM | monitor E=±2% | 0.667 | 0.665 | 0.664 | 0.659 | 0.658 | 0.009 | PASS |
| ngspice | R1 | known reference | 0.634 | 0.618 | 0.597 | 0.572 | 0.550 | 0.085 | **FAIL** |
| ngspice | R1 | monitor E=±2% | 0.642 | 0.625 | 0.606 | 0.584 | 0.561 | 0.081 | **FAIL** |

`A0` and `R1` are shown for comparison only; the gate applies to `PRr`.

## 6. Per-class recall, separation and cost

Layer recall (pooled, E = 2%; last row: PRr known-reference classifier without a monitor at ×0.8/×1.2):

| domain | arm | scope | healthy | sensor | afe | adc |
|---|---|---|---|---|---|---|
| bh | A0 | pooled E=2% | 0.01 | 0.15 | 0.24 | 0.88 |
| bh | R1 | pooled E=2% | 0.1 | 0.7 | 0.87 | 0.82 |
| bh | R1r | pooled E=2% | 0.15 | 0.8 | 0.87 | 0.76 |
| bh | PR | pooled E=2% | 0.13 | 0.78 | 0.93 | 0.8 |
| bh | PRr | pooled E=2% | 0.14 | 0.78 | 0.91 | 0.81 |
| bh | PRrM | pooled E=2% | 0.24 | 0.74 | 0.94 | 0.78 |
| bh | PRr known (no monitor, assumed levels) | unmonitored x0.8/x1.2 | 0.0 | 0.04 | 0.4 | 0.88 |
| sp | R1 | pooled E=2% | 0.09 | 0.69 | 0.86 | 0.81 |
| sp | R1r | pooled E=2% | 0.14 | 0.8 | 0.87 | 0.76 |
| sp | PR | pooled E=2% | 0.12 | 0.77 | 0.92 | 0.8 |
| sp | PRr | pooled E=2% | 0.13 | 0.77 | 0.9 | 0.81 |
| sp | PRrM | pooled E=2% | 0.22 | 0.74 | 0.93 | 0.78 |

Fine-fault recall (pooled, E = 2%):

| domain | arm | healthy | sensor_bias | sensor_gain | sensor_noise | afe_offset | afe_bandwidth | adc_offset | adc_gain | adc_clipping |
|---|---|---|---|---|---|---|---|---|---|---|
| bh | A0 | 0.01 | 0.05 | 0.06 | 0.09 | 0.13 | 0.51 | 0.54 | 0.8 | 0.06 |
| bh | R1 | 0.23 | 0.23 | 0.31 | 0.99 | 0.76 | 0.94 | 0.99 | 0.95 | 0.4 |
| bh | R1r | 0.33 | 0.32 | 0.26 | 0.98 | 0.82 | 0.93 | 1.0 | 0.96 | 0.31 |
| bh | PR | 0.28 | 0.28 | 0.32 | 0.98 | 0.86 | 0.96 | 1.0 | 0.92 | 0.43 |
| bh | PRr | 0.29 | 0.26 | 0.31 | 0.98 | 0.86 | 0.95 | 1.0 | 0.92 | 0.45 |
| bh | PRrM | 0.36 | 0.26 | 0.34 | 0.98 | 0.92 | 0.94 | 1.0 | 0.93 | 0.37 |
| sp | R1 | 0.23 | 0.24 | 0.31 | 0.99 | 0.75 | 0.92 | 0.99 | 0.94 | 0.38 |
| sp | R1r | 0.31 | 0.33 | 0.26 | 0.99 | 0.81 | 0.91 | 1.0 | 0.95 | 0.3 |
| sp | PR | 0.25 | 0.28 | 0.33 | 0.98 | 0.84 | 0.94 | 0.99 | 0.9 | 0.45 |
| sp | PRr | 0.27 | 0.26 | 0.31 | 0.98 | 0.84 | 0.94 | 0.99 | 0.91 | 0.48 |
| sp | PRrM | 0.32 | 0.26 | 0.35 | 0.98 | 0.91 | 0.93 | 1.0 | 0.91 | 0.4 |

Cost: two-point MLP parameters 6868 (layer) / 7113 (fault). Descriptor extraction per sample (mean over seeds): Revision-1 0.47 ms, phase-robust 0.79 ms (single core, Python); MLP inference 0.0007 ms. ngspice: 13878 runs per seed in about 908 s on 3 workers.

## 7. Limitations

* Both domains are first-order-RC plus affine-ADC models of the same author; in the noise-free check they agree to 0.1–0.3 mV at every phase. The ngspice test therefore probes extra amplifier/rail noise, tolerances, switch on/off resistance and the circuit-level edge handling, not unmodelled hardware effects (charge injection, op-amp bandwidth/slew, reference settling, leakage). It is not an independent hardware validation.
* The phase model assumes a single, common edge phase for all reference and mux edges and a constant, known edge-to-sample timing within a record; jitter between edges, phase drift within a record and a phase that differs between AFE and ADC references were not tested.
* The monitor is simulated (common gain error, white noise, offset trimmed); matched-E training assumes the monitor's error bound is known when training.
* Three dataset seeds with 88 test conditions; CIs resample conditions, not datasets. The ngspice grid has three amplitudes and five phases per condition; one-point baselines use three behavioral amplitudes.
* Absolute performance remains modest and the weak classes (healthy; sensor bias/gain; ADC clipping) are unchanged by this revision; this is not a deployable detector. No hardware, energy or cost measurement; no journal-acceptance claim.

## 8. Recommendation

1. Adopt the phase-robust descriptors with phase-randomised training (PRr) as the proposed method; it meets every frozen gate in both domains, including the cross-domain transfer limit that the previous stage missed.
2. Report honestly that the failed stage was largely a sampling-phase artefact of how the circuit and discrete-time models were aligned, and that the phase-robust descriptors remove the dependence; state which ingredient mattered using §2.
3. Before any physical claim, validate on a SPICE model with real op-amp/switch behaviour or hardware (see limitations).

No journal-acceptance claim is made.

FINAL DECISION: GO
