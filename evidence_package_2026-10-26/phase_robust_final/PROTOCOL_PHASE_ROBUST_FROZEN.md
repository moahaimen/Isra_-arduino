# Phase-robust revision — frozen protocol

Written 14 October 2026, **before any validation-seed data were generated**. Nothing earlier is modified
(`reference_monitor_final/`, `FINAL_REFERENCE_V2_REPORT.md`, `FINAL_MULTISEED_REPORT.md`, `spice_fixed/`, all earlier results and frozen protocols).

## 0. Baseline failure (kept, not hidden)
The previous stage (`reference_monitor_final/`) ended **REVISE**: behavioral → ngspice transfer lost **0.119** layer macro-F1 (frozen limit 0.10;
behavioral 0.658, ngspice 0.539, CI [0.107, 0.132]). A post-hoc development-seed diagnostic traced most of it to the sampling phase of the
reference edge relative to the ADC grid: descriptors reading the first 2-5 ms after the step (`rise_2`, `rise_5`, ...) differ between the behavioral
discrete filter (edge on the sample grid) and the ngspice edge placement (1 us before the sample). This stage tests the proposed cure under a new frozen protocol on new seeds.

## 1. Phase model
The reference edges (all AFE/ADC reference level changes and mux-control edges) occur at `t_edge = t_{i-1} + psi*T`, `0 <= psi < 1`, T = 1 ms. The first
sample on the new level has therefore settled for (1 - psi)*T. psi = 0 is the zero-order-hold convention of the earlier behavioral model; psi = 0.999 is
the edge placement of the failed stage. Behavioral model: exact two-stage discretisation of the first-order AFE at the edge interval (`ref_phase` in
`src/simulate.py`; default 0 is bit-identical to the old simulator, verified by hash). ngspice: edges placed at `t_{i-1} + psi*T + 1 us` with hold-then-step PWL (`src/spice_phase.py`).
The ADC bypass window is phase-independent by construction (edge always falls inside the preceding sample interval).
**Validation phases: psi in {0, 0.25, 0.5, 0.75, 0.999}** (the first four are the required ones; 0.999 reproduces the failed placement).

## 2. Descriptors (`src/phase_features.py`)
* **R1** = the 20 Revision-1 descriptors (`src/ref_features.py`, guard 30%, measured reference levels), including raw `rise_2/5/10/20/30`.
* **PR (phase-robust)** = R1 with all five raw rise fractions removed (they are fixed-sample descriptors; the brief names rise_2 and rise_5, the other three have the same
  weakness) and five whole-transient descriptors added, estimated on the complete second AFE plateau (60 samples + the pre-step base sample):
  `tau_norm` (fitted first-order time constant / plateau length), `rt_10_50_norm`, `rt_50_90_norm` (10-50 % and 50-90 % rise-time differences from the interpolated normalised response, capped at the window end; differences are
  shift-invariant), `area_norm` (transient area normalised by the fitted settled span), `fit_rms_norm`. The plateau-settling errors `settle_err1/2` are retained. Total 20 descriptors.
* **Fit**: `y(t) = base + S(1 - exp(-(t - t_e)/tau))` for `t >= t_e`; the edge time `t_e` is a free parameter and is not used as a descriptor; S is solved in closed form (variable projection); (tau, t_e) by a deterministic
  log-spaced grid search plus one local refinement, which has no convergence failure mode. The transient descriptors are affine-invariant (independent of ADC gain/offset and of the monitored levels).
  Documented fallback (|S| < 1e-4 only): multi-sample window area and zeros for the rise times.
* Development-seed evidence (seed 20261097, disclosed): across phase 0 -> 0.999 the R1 rise fractions shift by up to 1.39 sigma (`rise_2`), the PR descriptors by <= 0.15 sigma (`tau_norm` 0.00). No descriptor or hyper-parameter was changed afterwards.

## 3. Training, arms, monitor
* New validation dataset seeds **20261026, 20261027, 20261028**; 350 conditions x 9 faults; test 25 % (`random_state = S+1`), validation 15 % of the rest (`S+2`, unused: no early-stopped model), train = remaining 222 conditions, no overlap asserted. Two initialisation seeds (11, 22), averaged. Same MLP (`_classifier`, 96-48).
* Training amplitude x1.0, behavioral, no tolerance (as in the earlier Revision-1 arms). **Phase**: arms without `r` train at psi = 0; arms with `r` train with psi ~ U[0,1) drawn per sample (same draw for the behavioral and ngspice version of a training row).
* **Reference monitor** exactly as in `PROTOCOL_REFERENCE_MONITOR_FROZEN.md` (high-impedance buffered 12-bit channel, 16-sample averaging, 0.25 mV rms after averaging, 12-bit quantisation, gain error uniform in +-E common to the four levels, offset trimmed), E in {0, 1, 2, 5} %, matched-E training; plus `known` (measured = actual).
* **Frozen arms** (two-point path unless stated; each trained per monitor variant):
  `A0` old descriptors (raw + 38 descriptors, psi = 0 training; also passive, single-probe, AFE-only and ADC-only baselines);
  `R1` Revision-1 descriptors, psi = 0; `R1r` R1 + phase randomisation; `PR` phase-robust descriptors, psi = 0; **`PRr` phase-robust + phase randomisation (primary method)**;
  `PRrM` PRr + mixed behavioral + ngspice training (ngspice training rows: amplitude x1.0, component tolerances, extra noise, random phase, same monitor variant);
  one-point AFE-only/ADC-only versions of R1, R1r, PR and PRr use the same descriptors on their single reference window;
  **no-monitor control**: the `PRr` known-reference classifier applied with the nominal commanded levels although the amplitude changed (`assumed`).
* **Test grids** (all with component tolerances (AFE gain +-5 %, tau +-10 %, ADC gain +-2 %, ADC offset +-10 mV, sensor baseline +-5 %), ADC noise 2.5 mV rms, 12-bit quantisation, all nine fault classes; tolerance, noise and monitor draws are shared between domains):
  behavioral: amplitudes x0.8, 0.9, 1.0, 1.1, 1.2 (one-point baselines: 0.8, 1.0, 1.2) x the 5 phases;
  ngspice (per-sample netlist of the `spice_fixed/` circuit, + 0.5 mV rms amplifier and rail noise): amplitudes x0.8, 1.0, 1.2 x the 5 phases.
  Pooling over phases (and amplitudes where stated) sums the confusion matrices.

## 4. Metrics and statistics
Layer macro-F1 (primary), fine-fault macro-F1, balanced accuracy, per-class recall, AFE recall, ADC recall, AFE-ADC cross-confusion (fraction of AFE+ADC samples assigned to the other), parameter count, per-sample descriptor and inference time.
Paired condition-level cluster bootstrap, 5000 resamples, per-seed and pooled CIs (mean of the three per-seed differences); an improvement is stated only if the pooled CI excludes zero; "consistent" = same sign in all 3 seeds.
N_d = layer macro-F1 of `PRr` with known reference at x1.0 pooled over the 5 phases in domain d (behavioral `bh`, ngspice `sp`).

## 5. Pre-registered criteria (method = `PRr`; X over known, E=0, 1, 2, 5 % with the matching monitored model)
* **A retention** (both domains): for X in {known, E0, E1, E2} at x0.8 and x1.2 pooled over phases: layer macro-F1 >= 0.85 N_d.
* **B superiority** (behavioral): for every X and x0.8, x1.2 pooled over phases: pooled CI lower bound of F1(PRr_X) - F1(b) > 0 for each baseline b in {two-point A0, passive A0, single A0, AFE-only A0, ADC-only A0, AFE-only PRr_X, ADC-only PRr_X}.
* **C confusion** (both domains): AFE-ADC cross-confusion < 0.15 for every X at x0.8 and x1.2 pooled over phases.
* **D monitor error** (both domains): at E = 5 %: F1 >= 0.70 N_d at x0.8, at x1.2, and pooled over all amplitudes and phases of the domain.
* **E transfer**: matched E = 2 %, grid {0.8, 1.0, 1.2} x 5 phases: F1_bh(PRr) - F1_sp(PRr) <= 0.10 (point estimate; CI reported; other E reported). (Behavioral-trained model tested on ngspice.)
* **F evidence**: every improvement claimed (B, attribution, mixed training) must have a pooled CI excluding zero.
* **G phase variation**: for X in {known, E2}: F1 pooled over amplitudes, per phase; max - min over the 5 phases <= 0.05, in both domains.
* **Decision**: `GO` iff A, B, C, D, E and G all hold for `PRr` (gates A_bh, A_sp, B, C_bh, C_sp, D_bh, D_sp, E, G_bh, G_sp). Otherwise `REVISE`, listing the failed gates with numbers.
  The mixed-training arm `PRrM` is evaluated against the same ngspice-domain gates (E_mixed: F1_bh(PRr) - F1_sp(PRrM) <= 0.10) and reported, but it is **not** the pre-registered primary; if only `PRrM` passed, the decision stays REVISE and the report says so.
* **Attribution** (reported, E = 2 %, pooled): PR - R1 (descriptors alone), R1r - R1 (randomisation alone), PRr - R1r, PRr - PR, PRr - R1 (combination), PRrM - PRr (mixed training), PRr - A0; plus per-phase F1 of every arm.
* No tuning of descriptors, fit settings, thresholds, monitor or models on validation/test data after this freeze. Development/debugging used seed **20261097** only (earlier stages disclosed 20261098/20261099).

## 6. Known limitation disclosed before the run
In the noise-free development check the behavioral and ngspice models agree to 0.1-0.3 mV RMS at every phase (both are first-order RC + affine ADC models), so the cross-domain test mainly probes the extra amplifier/rail noise, tolerances, switch Ron/Roff effects and the circuit-level edge handling; it is not an independent hardware validation.
