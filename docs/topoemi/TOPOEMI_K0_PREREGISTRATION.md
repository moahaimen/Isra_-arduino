# TopoEMI-ZS K0 preregistration

Status: **FROZEN BEFORE K0 DECISION RESULTS**
Target venue if all later gates succeed: **MDPI Sensors**
Working title: **Layout-Conditioned Zero-Shot Phaseless EMI Source Localization from Sparse Near-Field Measurements**

This K0 is a kill test. It is not a paper experiment and cannot establish publishability by itself.

## 1. Core hypothesis

A layout-conditioned model can exploit target-board geometry/connectivity to localize multiple EMI sources from sparse phaseless near-field measurements on an **unseen board/layout**, materially outperforming both:
1. a topology/layout-blind DL control; and
2. strong target-specific phaseless inverse methods at comparable measurement/simulation budgets.

If either statement is false, stop the project.

## 2. K0 forward model

Use an equivalent-source electromagnetic model, not a generic Gaussian image generator.

Candidate sources:
- tangential magnetic dipoles Mx/My aligned with routed current-path segments;
- optional normal electric dipoles Pz only at eligible pad/component nodes.

Field measurements:
- primary: |Hx|, |Hy| and |Hz| magnitudes;
- no phase in the primary K0 condition;
- one fixed scan plane per sample;
- three fixed frequencies to reduce single-frequency ambiguity without creating a dense spectral scan.

The forward operator must be derived from physically meaningful free-space/equivalent-dipole Green functions. Numerical implementation must be unit-tested against closed-form single-dipole cases.

Do not add a neural surrogate to the forward model in K0.

## 3. Layout families

Use exactly four structurally distinct PCB-like layout families:

**L1 — ROUTED-CHAIN**
One or more long routed traces with bends, pads and 1–3 branches.

**L2 — CLOCK-TREE**
A source/root region with branching distribution paths and multiple loads.

**L3 — POWER-LOOP**
Compact high-current loop motifs with input/output loops, switching-node region and nearby return path.

**L4 — MIXED-BOARD**
Two or three functional clusters connected by routed paths, with reconvergent or cross-board connectivity.

Each generated board contains 24–96 eligible source candidates.

Four leave-one-family-out folds:
- A: hold out L1
- B: hold out L2
- C: hold out L3
- D: hold out L4

Held-out family data must not influence training, normalization, calibration, hyperparameter choice or threshold selection.

## 4. Dataset sizes

Fail-fast K0-A:
- train: 80 board instances per training family per fold;
- validation: 20 per training family;
- held-out test: 40 boards;
- one model seed;
- use R0 and R1 only.

K0-A exists only to detect catastrophic failure quickly.

Full K0-B, run only if K0-A does not trigger STOP:
- train: 300 board instances per training family per fold;
- validation: 60 per training family;
- held-out test: 120 boards;
- two seeds;
- R0–R3, with primary decision on R1+R2+R3.

If runtime estimates exceed approximately 2 local CPU-hours or require paid compute, stop and report before scaling.

## 5. Scan geometry and sparsity

Nominal dense grid: 24 x 24 = 576 possible scan positions.

Primary sparse condition:
- 48 positions = 8.33% of the dense grid;
- deterministic globally frozen sampling pattern with good spatial coverage;
- identical number of samples for all methods.

Secondary conditions if K0-B runs:
- 24 positions = 4.17%;
- 96 positions = 16.67%;
- 576 positions is an oracle/full-scan reference only and cannot replace the sparse primary result.

Scan height is normalized to board size but fixed within a nominal range chosen before data generation.

## 6. Practical nuisance variables

These are part of the frozen generative model, not post-result rescue perturbations.

For each test sample independently:
- scan-height error: uniform ±10% around nominal;
- global probe-gain error: ±1.5 dB;
- XY scan registration offset: up to ±0.5 nominal grid spacing;
- per-sample additive measurement noise: nominal 30 dB SNR;
- mild board-size / source-amplitude variation.

K0-B robustness slice:
- 25 dB SNR;
- height error up to ±15%;
- XY offset up to ±0.75 grid step.

All methods are told the nominal geometry but not the realized nuisance values unless a baseline explicitly estimates them, in which case all forward evaluations used for nuisance estimation count toward its budget.

## 7. Fault/source regimes

Sources are sparse relative to eligible candidate locations.

R0 — one strong source, easy sanity regime.
R1 — one moderate/weak source.
R2 — two simultaneous sources with unequal amplitudes.
R3 — three simultaneous sources, including at least one close-spaced pair where graph distance <=2 or Euclidean separation is small.

Source type/orientation and complex coefficient are sampled from frozen distributions.

Primary K0-B decision pools R1+R2+R3.
R0 cannot produce GO.

## 8. Proposed model under test

Name: **TopoEMI-ZS**

Allowed architecture:
- sparse measurement encoder for positions + frequency + |H| components;
- target-layout encoder over candidate source graph/geometry;
- cross-attention or message passing between measurement latent and candidate nodes/edges;
- per-candidate source probability;
- per-candidate source orientation/type;
- source-strength regression.

Constraints:
- <= 2.5 million trainable parameters;
- exactly one frozen architecture;
- at most two model seeds;
- no architecture search after held-out results;
- no target-board fine-tuning.

The model may use positional encoding and physical coordinates.

## 9. Required DL ablation

**D0 — Layout-blind DL**

Same sparse measurement encoder and approximately matched parameter count, but no trace graph, connectivity, component eligibility or routed geometry beyond the board bounding box and scan coordinates.

This is mandatory.

A second optional control may provide candidate XY coordinates but no adjacency/connectivity. It is diagnostic only; D0 remains the primary graph/layout-necessity baseline.

## 10. Required classical baselines

### C1 — Tikhonov / L2 phaseless inverse
A fair iterative phaseless source reconstruction baseline.

### C2 — Adam + L2 phaseless reconstruction
Implement the conceptual method class represented by Sensors 2026 (Ma et al., DOI 10.3390/s26030939): optimize source coefficients against phaseless measurements with L2 regularization.

Do not claim exact reproduction unless implementation details actually match the paper.

### C3 — Sparse Bayesian / compressive source localization
A strong sparse probabilistic inverse inspired by the TEMC 2025 Bayesian compressive-sensing work (DOI 10.1109/TEMC.2024.3482849).

### C4 — Adaptive global optimization
Differential-evolution / L-SHADE-like phaseless source reconstruction, reflecting TEMC 2025 DOI 10.1109/TEMC.2025.3605016.

For K0-A, C1–C3 are sufficient. If K0-A survives, C4 is mandatory for K0-B.

### C5 — naive hotspot heuristic
Back-project / nearest-peak or field-hotspot ranking. Sanity baseline only.

## 11. Equal-budget accounting

For every classical inverse:
- count every forward-model evaluation;
- count nuisance-parameter probes;
- count restart initialization evaluations;
- report wall time;
- report the best result at fixed budgets.

Budgets:
- 256 forward evaluations;
- 1,024 forward evaluations;
- 4,096 forward evaluations.

TopoEMI-ZS receives no target-specific optimization or retraining. One nominal forward construction for geometry metadata may be counted as 1 target forward evaluation.

Do not use wall-clock break-even as the primary scientific decision because the analytic K0 forward model is intentionally cheap. Primary efficiency metric is **target-specific forward-evaluation count**. Wall time is secondary.

Offline training/data generation cost must still be reported and used in a separate amortization calculation.

## 12. Primary metrics

Primary source-localization metric:
- sample-level **set-F1** over exact candidate source locations.

Also report:
- exact-set accuracy;
- top-k source recall, k = true number of sources;
- mean Euclidean localization error for unmatched sources;
- graph-distance error where graph exists;
- source-strength normalized MAE for correctly localized sources;
- source type/orientation macro-F1;
- false-positive count per board;
- per-fold metrics;
- per-regime metrics;
- clustered bootstrap 95% CI over board instances.

Do not use per-candidate accuracy as a headline metric.

## 13. K0-A fail-fast rule

After the sanity checks and before any K0-B scale-up, evaluate one-seed K0-A.

Immediate **STOP** if either:
1. TopoEMI-ZS R0 set-F1 < 0.70 on held-out families; or
2. TopoEMI-ZS does not beat D0 layout-blind DL by at least +5 percentage points on pooled R0+R1; or
3. C2 or C3 beats TopoEMI-ZS by >20 points on pooled R0+R1 at <=1024 evaluations.

K0-A does not authorize GO. It only authorizes running K0-B.

## 14. Frozen K0-B decision rule

### M1 — layout conditioning is necessary
On pooled held-out-family R1+R2+R3:

TopoEMI-ZS - D0 must be:
- >= +10 percentage points set-F1;
- 95% CI lower bound >= +5 points;
- positive in at least 3 of 4 folds.

If M1 fails: **STOP**.

### Route A — strong accuracy advantage
At the same sparse measurements and <=1,024 target forward evaluations for the classical method, TopoEMI-ZS must beat the strongest of C1–C4 by:
- >= +15 percentage points pooled set-F1;
- 95% CI lower bound >= +8 points;
- positive gain in >=3/4 folds;
- no fold worse by >5 points.

If M1 + Route A pass: **STRONG GO**.

### Route B — sparse-measurement / inverse-cost advantage
If Route A fails, Route B can pass only if all hold:
- TopoEMI-ZS is within 5 points of the strongest C1–C4 result even when that classical method receives up to 4,096 forward evaluations;
- TopoEMI-ZS uses at least 20x fewer target-specific forward evaluations;
- at 48 scan points, TopoEMI-ZS beats the strongest classical method restricted to 48 scan points by >=8 points OR matches its accuracy while using <= half as many scan points in the 24-point condition;
- M1 passes;
- simulation-count amortized break-even, including offline generation, is <=500 unseen target boards.

If M1 + Route B pass: **GO — measurement/compute efficiency framing**.

Otherwise: **STOP**.

No "borderline rescue" architecture tuning is allowed. A diagnostic may explain failure but cannot change K0.

## 15. Sanity gates

Before any held-out decision data:

1. Single dipole closed-form field test passes numerical tolerance.
2. Superposition test: multiple-source field equals sum of isolated-source fields within numerical tolerance.
3. Source-index/graph-layout round trip is exact.
4. No board hash overlap train/val/test.
5. Held-out family absent from normalization/training.
6. Strong R0 source produces a measurement perturbation at least 5 sigma above noise in >=95% of cases.
7. C1/C2 on noiseless dense R0 recover a single source with set-F1 >=0.90 on a small validation-only calibration set.
8. Randomized labels collapse DL performance toward chance / no-skill behavior on a tiny diagnostic subset.

If 1–7 fail, fix implementation before training/evaluation and document it. #8 is diagnostic and must not use held-out test data.

## 16. Anti-rescue rules

After any held-out K0 result is visible, do not:
- change architecture;
- change loss weights;
- change source sparsity/severity;
- change nuisance ranges;
- change layout families;
- change scan positions;
- change thresholds;
- drop a strong baseline;
- change the primary metric;
- add phase information;
- replace 48-point primary results with dense-scan results.

A genuine code defect may be fixed only with a written deviation explaining:
- the defect;
- why it is implementation-only;
- which outputs are affected;
- exactly what is rerun.

## 17. Required K0 outputs

- frozen config JSON/YAML and hash;
- environment/package versions;
- seeds;
- source/layout generator;
- forward model tests;
- TopoEMI-ZS and D0 code;
- C1–C5 baselines;
- per-sample raw prediction summary;
- per-fold/regime CSV;
- bootstrap CIs;
- forward-evaluation and wall-time accounting;
- DEVIATIONS.md;
- K0_REPORT.md;
- K0_DECISION.txt.

Do not commit large cached datasets.

## 18. What a K0 PASS means

A pass means the computational hypothesis is worth continuing.

It does **not** mean the paper is ready.

Before submission to Sensors, later gates must include:
- deeper novelty audit against 2025–2026 EMI source-reconstruction papers;
- full-wave or equivalent high-fidelity EM validation;
- at least one physical PCB / measured near-field experiment if feasible;
- probe calibration / measurement procedure;
- robustness to real scan misregistration and probe uncertainty;
- ablations and statistical analysis;
- comparison with the strongest feasible source-reconstruction baselines.

Synthetic K0-only results are insufficient for the final paper.
