# TopoEMI-ZS R1 — nuisance-robustness kill gate

Status: **FROZEN BEFORE R1 RESULTS**
Relation to K0: K0 remains **STOP**. R1 is a new prospective hypothesis test, not a reinterpretation or rescue of K0.

## Research question

Does a frozen layout-conditioned TopoEMI-ZS model retain a **material localization advantage** over a strong nuisance-aware classical sparse Bayesian inverse when sparse phaseless near-field measurements contain realistic scan and calibration errors on completely unseen PCB/layout instances?

## Non-negotiable rules

- Do not retrain TopoEMI-ZS.
- Do not fine-tune on R1 boards.
- Do not change architecture, loss, thresholds, scan pattern, source regimes, or K0 training data.
- Use fresh board instances and fresh seeds not used in K0.
- Freeze every R1 nuisance grid and baseline setting before viewing any R1 held-out result.
- C3 must be allowed to estimate nuisance parameters fairly; every extra forward evaluation counts.
- K0 decision remains STOP regardless of R1.

## Frozen models

Use the exact final K0-B weights for:
- TopoEMI-ZS, both seeds;
- D0, both seeds.

Primary TopoEMI result is the mean/ensemble defined before R1 evaluation. If K0 used seed averaging, preserve it. Otherwise report seeds separately and their mean; do not choose the better seed post hoc.

## Fresh R1 board set

Four held-out layout families:
- L1 ROUTED-CHAIN
- L2 CLOCK-TREE
- L3 POWER-LOOP
- L4 MIXED-BOARD

Generate **80 fresh boards per family** using a new root seed not used anywhere in K0.

No board hash may overlap K0 train/validation/test.

Primary source regimes:
- R1 one weak/moderate source
- R2 two unequal simultaneous sources
- R3 three simultaneous sources with at least one close-spaced pair

Pool R1+R2+R3 for the primary decision.

Primary scan condition:
- 48/576 scan points
- same frozen 48-point sampling pattern used in K0
- phaseless |Hx|, |Hy|, |Hz|
- same three frequencies as K0

## Frozen nuisance grid

Evaluate the following independently and in combined slices.

### A. SNR
- 30 dB
- 25 dB
- 20 dB
- 15 dB

### B. scan-height error
Uniform around nominal:
- ±10%
- ±15%
- ±20%
- ±25%

### C. XY registration error
Uniform:
- ±0.5 grid step
- ±0.75 grid step
- ±1.0 grid step
- ±1.5 grid steps

### D. probe gain error
Uniform:
- ±1.5 dB
- ±2.0 dB
- ±3.0 dB

### E. combined practical slices
E1 — moderate:
- 25 dB SNR
- ±15% height
- ±0.75 grid-step XY
- ±2 dB gain

E2 — severe:
- 20 dB SNR
- ±20% height
- ±1.0 grid-step XY
- ±3 dB gain

E3 — extreme characterization only:
- 15 dB SNR
- ±25% height
- ±1.5 grid-step XY
- ±3 dB gain

Primary R1 decision uses **E1 + E2 pooled**, not E3.

## Classical baseline

Primary comparator: **C3-R**, nuisance-aware sparse Bayesian/compressive source localization.

C3-R must:
- receive the nominal layout;
- receive the same 48 phaseless measurements;
- jointly or hierarchically estimate source support/strength plus nuisance variables;
- have access to the exact frozen nuisance ranges but not realized nuisance values;
- count every forward-model evaluation, including nuisance proposals, restarts and calibration probes.

Evaluate C3-R at:
- 1,024 evaluations
- 4,096 evaluations

Use the strongest C3-R result as the primary classical comparator.

Also report:
- original K0 C3 without nuisance estimation;
- D0 frozen model.

Do not weaken C3-R to help TopoEMI.

## Metrics

Primary:
- sample-level exact-location set-F1.

Secondary:
- exact-set accuracy;
- top-k recall (k=true source count);
- Euclidean localization error;
- graph-distance error;
- false positives per board;
- source-strength normalized MAE;
- orientation/type macro-F1.

Statistics:
- clustered bootstrap 95% CI over board instances;
- per-family results;
- per-regime results;
- per-nuisance-slice results.

## Frozen R1 decision rule

### Mandatory R1-A — robust advantage
On pooled fresh-board E1+E2, R1+R2+R3:

TopoEMI-ZS minus strongest C3-R must be:
- **>= +8 percentage points set-F1**;
- **95% CI lower bound >= +4 points**;
- positive in at least **3/4 layout families**;
- no family worse by more than 3 points.

### Mandatory R1-B — not merely a catastrophic-classical failure
TopoEMI-ZS must retain:
- pooled set-F1 **>=0.60** on E1;
- pooled set-F1 **>=0.50** on E2.

### Mandatory R1-C — layout conditioning remains useful
TopoEMI-ZS minus frozen D0 on pooled E1+E2 must be:
- **>= +10 percentage points**;
- 95% CI lower bound >= +5 points.

### Decision
- If R1-A + R1-B + R1-C all pass: **R1 STRONG PASS**.
- Otherwise: **R1 STOP** and close TopoEMI-ZS as the primary paper direction.

No borderline rescue.

## Interpretation if R1 STRONG PASS

A pass supports a new paper framing:
**robust sparse phaseless PCB near-field EMI source localization under unknown scan/calibration errors on unseen layouts**.

It does not yet authorize submission. Next required gates would be:
- stronger literature audit focused on nuisance-aware EMI inverse localization;
- high-fidelity/full-wave validation;
- physical PCB + near-field probe experiment if feasible;
- measurement/calibration protocol.

## Required outputs

- results/topoemi_r1/config_frozen.json
- results/topoemi_r1/PROTOCOL_SNAPSHOT.txt
- results/topoemi_r1/DEVIATIONS.md
- results/topoemi_r1/R1_REPORT.md
- results/topoemi_r1/R1_DECISION.txt
- per-sample/family/slice CSV or JSON
- forward-evaluation accounting
- hash-overlap proof versus K0
