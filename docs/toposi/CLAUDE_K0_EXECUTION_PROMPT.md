# Claude execution prompt — TopoSI-Inv K0 only

Repository: `moahaimen/Isra_-arduino`

Branch: `research/toposi-inv-k0`

Your task is to execute **K0 only** for the new TopoSI-Inv project.

First read and obey:
`docs/toposi/TOPOSI_K0_PREREGISTRATION.md`

That file is frozen before results. Do not modify any K0 decision threshold after seeing results.

## Objective

Test whether a topology-aware graph model can localize and characterize faults on **completely unseen PCB/interconnect topology families** from sparse S-parameter measurements, and whether it materially beats:
- strong physics-based sparse inversion;
- target-specific nonlinear inverse fitting;
- and an adjacency-free deep-learning control.

This is a kill test. We prefer a fast, defensible STOP over weeks of rescue tuning.

## Work sequence

### 1. Environment and reproducibility

Create a self-contained project folder, preferably:
`toposi_inv/`

Use Python with NumPy/SciPy and scikit-rf if useful.

Freeze:
- package versions;
- deterministic seeds;
- generator config;
- exact topology/fault distributions.

Write a machine-readable config before generating the decision data.

Do not use CST, HFSS, ADS, or paid cloud compute in K0.

### 2. Implement the fast network simulator

Implement the four topology families exactly as pre-registered:
- CHAIN
- T-BRANCH
- MULTI-STUB / VIA-STUB
- MESHED / RECONVERGENT

Use physically meaningful transmission-line/lumped network blocks.

Run the six sanity checks in the pre-registration before any held-out-family evaluation.

If the simulator disagrees with analytically solvable examples, stop and fix the simulator first.

### 3. Generate family-disjoint data

Use 4 leave-one-family-out folds.

No held-out-family circuit may influence:
- training;
- validation;
- normalization;
- hyperparameters;
- thresholds.

Store circuit hashes and automatically assert disjointness.

Primary measurements use the frozen 16-point sparse frequency mask.

### 4. Implement exactly one compact TopoSI-GNN

Do not architecture-search.

Use:
- one measurement encoder;
- nominal physical graph features;
- 3–4 message-passing layers;
- per-location heads for probability/type/severity;
- <=2M parameters;
- at most two random seeds.

### 5. Implement all required baselines

Mandatory:
- B1 TDR/impulse localization;
- B2 linearized sparse Jacobian inverse;
- B3 target-specific nonlinear least-squares inverse with 32, 128, and 512 forward-simulation budgets;
- B4 adjacency-free deep-learning control with the same measurement encoder/local candidate attributes;
- B5 nominal sensitivity ranking.

B3 must be treated as a strong baseline. Do not cripple it.

All hidden optimization simulations must count toward its budget.

### 6. Evaluate the frozen K0 metrics

Primary decision data:
- held-out-family R1+R2+R3;
- sample-level set-F1;
- clustered bootstrap 95% CI by circuit instance.

Also report:
- exact-set accuracy;
- top-k location recall;
- graph-distance localization error;
- fault-type macro-F1;
- normalized severity MAE;
- per-fold results;
- simulation and wall-time cost.

### 7. Apply the frozen decision rule literally

M1 graph necessity:
TopoSI-GNN vs B4 must be >= +10 pp set-F1, CI lower bound >= +5 pp, positive in >=3/4 folds.

Route A:
TopoSI-GNN vs strongest classical baseline at same target simulation budget must be >= +20 pp, CI lower bound >= +10 pp, positive in >=3/4 folds, and no fold worse by >5 pp.

Route B if A fails:
within 5 pp of strongest B3 <=512-sim result, >=20x fewer target simulations, amortized break-even <=100 unseen targets, and M1 must still pass.

Return exactly one:
- `STRONG GO`
- `GO — efficiency framing`
- `BORDERLINE`
- `STOP`

Do not change these rules.

## Anti-rescue rules

After test results are visible:
- do not add layers;
- do not change loss weights;
- do not change fault severity distributions;
- do not change topology families;
- do not change frequency points;
- do not weaken B3;
- do not substitute a different metric;
- do not add a new model to save the result.

A genuine implementation bug may be fixed, but:
1. document it in `DEVIATIONS.md`;
2. explain why it is an implementation correction and not result-driven tuning;
3. rerun only the affected stage.

## Cost constraint

Keep this K0 cheap.

Do not use paid GPU/cloud services unless absolutely unavoidable.
CPU execution is preferred.
Do not launch expensive large-scale sweeps.

If estimated additional compute spend would exceed approximately **$10**, stop and report why before proceeding.

## Progress reporting

Every ~30 minutes while actively working, report no more than 6 short lines:
- Phase
- Completed
- Result so far
- Problem/blocker
- Spend/compute status
- Next

Do not rerun anything merely to produce a progress update.

## Required final artifacts

Commit and push:
- frozen config;
- simulator/generator;
- models/baselines;
- analysis scripts;
- small result CSV/JSON files;
- `results/toposi_k0/K0_REPORT.md`;
- `results/toposi_k0/K0_DECISION.txt`;
- `DEVIATIONS.md`.

Do not commit large generated datasets.

Final response must state:
1. exact git commit;
2. sanity-check status;
3. M1 result;
4. Route A result;
5. Route B result;
6. strongest classical baseline;
7. strongest adjacency-free DL baseline;
8. exact final decision;
9. whether any threshold or model was changed after seeing test results.

**START K0 NOW. Stop after K0. Do not start a K1 or full-wave stage.**
