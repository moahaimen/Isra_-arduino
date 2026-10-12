# LOCAL EXECUTION PROMPT — TopoEMI-ZS K0, minimal-token mode

Work only in the **current local repository**.

The user has already merged earlier GitHub work into the local codebase. Do not pull, checkout, reset, rebase, or overwrite unrelated local changes.

The new TopoEMI-ZS files may exist only on the fetched ref `origin/research/topoemi-zs-k0`. If they are absent from the working tree, read/export only these files from that local ref using `git show`; do not checkout the branch:

- `docs/topoemi/TOPOEMI_NOVELTY_SCREEN.md`
- `docs/topoemi/TOPOEMI_K0_PREREGISTRATION.md`

Treat the current local working tree as source of truth for code and data.

## IMPORTANT: MINIMAL TOKEN MODE

Do not narrate routine work in chat.

Do not send periodic prose updates.

Keep all detailed logs locally.

Maintain only:
`results/topoemi_k0/STATUS.txt`

Maximum 6 short lines:
```
PHASE:
DONE:
CURRENT:
BLOCKER:
CPU/SPEND:
NEXT:
```

Only talk to me if:
1. a real blocker needs my decision;
2. the frozen protocol cannot be executed as written;
3. paid compute would exceed $10;
4. K0-A reaches an immediate STOP;
5. K0-B is complete.

Do not call another LLM or paid API.

## OBJECTIVE

Execute **TopoEMI-ZS K0 only** according to the frozen preregistration.

The research question is whether a layout-conditioned model can localize multiple EMI sources on completely unseen PCB/layout families from sparse phaseless near-field measurements and materially outperform:
- a layout-blind DL control;
- strong target-specific phaseless inverse methods.

This is a kill test. A scientifically valid STOP is preferable to rescue tuning.

## STEP 0 — PROTOCOL INTEGRITY

Before coding:
- create `results/topoemi_k0/PROTOCOL_SNAPSHOT.txt`;
- record SHA256 of the preregistration and novelty-screen files;
- create/freeze `results/topoemi_k0/config_frozen.json`;
- record root seed and package versions;
- create `results/topoemi_k0/DEVIATIONS.md`.

If any implementation detail is ambiguous, choose the most conservative physically reasonable interpretation **before viewing held-out results**, document it in:
`results/topoemi_k0/PROTOCOL_INTERPRETATIONS.md`.

Do not silently reinterpret thresholds.

## STEP 1 — FORWARD MODEL

Implement a physically meaningful equivalent-source near-field model.

Primary candidate sources:
- Mx/My aligned with routed source/current-path segments;
- Pz only at eligible pad/component nodes if needed.

Primary observations:
- phaseless |Hx|, |Hy|, |Hz|;
- 3 fixed frequencies;
- one scan plane;
- frozen sparse positions.

Use analytic/free-space dyadic/equivalent-dipole Green functions. Do not use arbitrary image kernels.

Unit-test:
- single dipole against closed-form reference;
- linear superposition;
- coordinate/orientation conventions.

## STEP 2 — FOUR LAYOUT FAMILIES

Implement exactly:
- L1 ROUTED-CHAIN
- L2 CLOCK-TREE
- L3 POWER-LOOP
- L4 MIXED-BOARD

24–96 eligible source candidates per board.

Use 4 leave-one-family-out folds exactly as preregistered.

Automatically hash board layouts and assert no train/val/test overlap.

## STEP 3 — SANITY GATES

Run all preregistered sanity checks before held-out decision evaluation.

Especially:
- C1/C2 must recover noiseless dense single-source cases with set-F1 >=0.90 on validation-only calibration data;
- strong R0 perturbation >=5 sigma in >=95% cases.

If a sanity test fails because of a coding error, fix it and document the fix before proceeding.

If the physics formulation itself cannot satisfy sanity, STOP and report.

## STEP 4 — K0-A FAIL-FAST

Run K0-A first. Do not launch full K0-B yet.

K0-A:
- 80 train boards per training family/fold;
- 20 validation boards per training family;
- 40 held-out test boards;
- one model seed;
- R0 + R1 only.

Implement:
- TopoEMI-ZS;
- D0 layout-blind DL;
- C1 Tikhonov/L2 phaseless inverse;
- C2 Adam+L2 phaseless inverse;
- C3 sparse Bayesian/compressive inverse;
- C5 hotspot sanity baseline.

Primary sparse scan = 48/576 positions.

K0-A immediate STOP if any:
- TopoEMI-ZS held-out R0 set-F1 <0.70;
- TopoEMI-ZS - D0 < +5 pp on pooled R0+R1;
- C2 or C3 beats TopoEMI-ZS by >20 pp on pooled R0+R1 at <=1024 forward evaluations.

If K0-A triggers STOP:
- do NOT tune;
- do NOT run K0-B;
- write report and decision;
- message me with the final short summary.

If K0-A survives, continue automatically to K0-B.

## STEP 5 — TOPOEMI-ZS MODEL

Exactly one architecture, <=2.5M parameters:
- sparse measurement token encoder: x,y,frequency,field component,magnitude;
- layout candidate encoder with coordinates, candidate/source type and routed-geometry/connectivity attributes;
- cross-attention or message passing between measurement representation and candidate representation;
- per-candidate source probability;
- orientation/type head;
- strength head.

Do not architecture-search.

No target-board fine-tuning.

For K0-B: max two seeds.

D0 must have approximately matched parameter count and the same measurement encoder but no routed graph/connectivity or target-layout structure.

## STEP 6 — CLASSICAL BASELINES

C1: iterative Tikhonov/L2 phaseless inverse.

C2: Adam + L2 phaseless inverse inspired by Sensors 2026 DOI 10.3390/s26030939. Do not claim exact reproduction unless exact.

C3: sparse Bayesian/compressive phaseless localization inspired by IEEE TEMC DOI 10.1109/TEMC.2024.3482849.

C4 for K0-B: differential-evolution/L-SHADE-like phaseless inverse inspired by IEEE TEMC DOI 10.1109/TEMC.2025.3605016.

C5: hotspot/backprojection sanity baseline.

All classical methods receive the same nominal target layout and sparse measurements.

Count every forward evaluation including:
- initial probes;
- restarts;
- nuisance estimation;
- objective checks used for optimization.

Report at budgets 256 / 1024 / 4096.

Do not cripple baselines.

## STEP 7 — NUISANCE ROBUSTNESS

Use the frozen nuisance model:
- ±10% scan-height error;
- ±1.5 dB gain;
- up to ±0.5 grid-step XY offset;
- 30 dB nominal SNR.

K0-B robustness slice:
- 25 dB SNR;
- ±15% height;
- ±0.75 grid-step XY.

Methods may estimate nuisance variables, but every added forward evaluation counts.

## STEP 8 — K0-B

Only if K0-A survives.

Use:
- 300 train boards per training family/fold;
- 60 validation;
- 120 held-out test boards;
- two model seeds;
- R0/R1/R2/R3.

Primary decision = pooled held-out R1+R2+R3.

Metrics:
- sample-level exact-location set-F1;
- exact-set accuracy;
- top-k recall;
- localization error;
- graph-distance error;
- type/orientation macro-F1;
- strength normalized MAE;
- false positives;
- clustered bootstrap 95% CI over board instances.

## FROZEN FINAL DECISION

M1:
TopoEMI-ZS - D0 >= +10 pp set-F1;
95% CI lower bound >= +5 pp;
positive in >=3/4 folds.
Failure => STOP.

Route A:
against strongest C1-C4 baseline with <=1024 target forward evaluations:
- >= +15 pp pooled set-F1;
- CI lower bound >= +8 pp;
- positive in >=3/4 folds;
- no fold worse by >5 pp.
M1 + A => STRONG GO.

Route B if A fails:
- within 5 pp of strongest C1-C4 at <=4096 evaluations;
- >=20x fewer target forward evaluations;
- sparse-measurement advantage as preregistered;
- M1 passes;
- simulation-count amortized break-even <=500 unseen boards.
M1 + B => GO — measurement/compute efficiency framing.

Otherwise => STOP.

## ANTI-RESCUE

After held-out results are visible, do not:
- modify architecture;
- change hyperparameters/loss weights;
- change source difficulty;
- change nuisance ranges;
- change layouts;
- change sparse scan positions;
- weaken a classical baseline;
- switch metrics;
- add phase;
- substitute dense scan;
- retrain to improve the result.

Read-only diagnostics are allowed after a fail. They cannot alter the decision.

## COMPUTE / TOKEN CONTROL

Use local CPU first.
Cache generated boards/fields.
Resume interrupted work; do not regenerate deterministic completed data.
Keep training logs on disk.
Use detached execution for long jobs.
Do not spend paid compute >$10.

For speed:
- vectorize the Green-function forward model;
- batch generated field calculations;
- cache geometry-to-Green matrices;
- parallelize classical evaluations conservatively;
- avoid per-sample Python loops where possible.

Do not reduce scientific baselines just to finish faster.

## REQUIRED OUTPUTS

Create:
- `results/topoemi_k0/K0_REPORT.md`
- `results/topoemi_k0/K0_DECISION.txt`
- `results/topoemi_k0/STATUS.txt`
- `results/topoemi_k0/config_frozen.json`
- `results/topoemi_k0/PROTOCOL_SNAPSHOT.txt`
- `results/topoemi_k0/PROTOCOL_INTERPRETATIONS.md`
- `results/topoemi_k0/DEVIATIONS.md`
- concise CSV/JSON metrics and cost accounting
- reproducible scripts/source

Do not push or commit unless I explicitly ask.

## FINAL MESSAGE — KEEP SHORT

When done, answer only:

```
TOPOEMI K0 COMPLETE

K0-A: PASS/STOP
Sanity: PASS/FAIL
M1: PASS/FAIL — TopoEMI vs D0 difference + CI
Route A: PASS/FAIL — strongest classical method, scores, margin + CI
Route B: PASS/FAIL — forward-evaluation ratio, sparse-scan comparison, break-even
Best TopoEMI set-F1:
Best classical set-F1:
Decision: STRONG GO / GO-efficiency / STOP
Post-result changes: NONE / list
Results: results/topoemi_k0/K0_REPORT.md
```

Start now. Do not spend tokens narrating the work.
