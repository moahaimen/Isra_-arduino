# TopoSI-Inv K0 pre-registration

Status: **FROZEN BEFORE ANY K0 RESULT.**
Project: **TopoSI-Inv — topology-generalizable inverse diagnosis of PCB/interconnect faults from sparse frequency-domain measurements.**

K0 is a kill test, not a paper experiment. Its purpose is to answer two questions before expensive work:

1. Can a topology-aware deep model localize distributed interconnect faults on **completely unseen circuit topologies** better than strong physics-based inverse methods?
2. Is graph structure itself necessary, rather than the gain coming from a generic neural network or target-specific brute-force simulation?

No threshold in this document may be changed after K0 test results are inspected.

---

## 1. Scope and exclusions

K0 uses a fast frequency-domain transmission-line/circuit simulator only.

Allowed:
- Python/NumPy/SciPy and/or scikit-rf;
- analytic RLGC / transmission-line two-port or multiport blocks;
- ideal/lumped via/stub/discontinuity models;
- synthetic measurement noise and fabrication tolerances.

Not allowed in K0:
- CST, HFSS, ADS full-wave sweeps;
- measured VNA data;
- tuning on the held-out topology family;
- changing topology families after results;
- claiming manufacturable-board or full-wave validity;
- claiming Q1 readiness from K0 alone.

If K0 passes, full-wave and hardware validation become later gates.

---

## 2. Fixed topology families

Use exactly four topology families. Each family must generate many circuit instances with variable dimensions and component values while retaining the family-level structural motif.

**F1 — CHAIN**
Multi-section transmission-line chain with 6–20 line sections and 2–5 impedance transitions.

**F2 — T-BRANCH**
Main line with one or two T branches terminated by loads/stubs; 7–22 edges total.

**F3 — MULTI-STUB / VIA-STUB**
Main path with 2–5 shunt/open/short stubs and lumped via-like parasitics at selected nodes; 7–24 edges total.

**F4 — MESHED / RECONVERGENT**
A small branched network in which two paths split and later reconverge, optionally with one shunt branch; 8–24 edges total.

K0 deliberately avoids coupled differential/multiconductor lines. Those belong to a later gate if the simpler inverse-topology hypothesis survives.

Each family is held out once:
- Fold A: train F2/F3/F4, test F1
- Fold B: train F1/F3/F4, test F2
- Fold C: train F1/F2/F4, test F3
- Fold D: train F1/F2/F3, test F4

The test family must never appear in training, model selection, normalization statistics, feature calibration, or hyperparameter tuning.

---

## 3. Circuit instance generation

For every family generate disjoint train/validation/test circuit instances from deterministic seeds.

Minimum target:
- 300 training circuit instances per training family per fold;
- 60 validation circuit instances per training family per fold;
- 120 test circuit instances in the held-out family.

If runtime is unexpectedly high, the counts may be reduced **once before any model is trained**, with the reason recorded. They may not be changed after test results are seen.

Nominal parameter ranges:
- characteristic impedance: 35–90 ohm;
- electrical length chosen so aggregate path lengths span a broad fraction of the frequency range;
- attenuation/loss: small but nonzero, randomized;
- via-like parasitics: physically plausible lumped L/C ranges;
- terminations: 35–100 ohm with occasional reactive termination.

Exact numeric distributions must be written to a machine-readable config and frozen before data generation.

---

## 4. Measurements

Frequency grid:
- 64 logarithmically spaced points from 10 MHz to 10 GHz.

Measurements:
- complex S11 and S21 for two-port families;
- for multiport representations, include every externally accessible port pair but cap the external ports at four;
- represent real and imaginary parts separately or magnitude/phase after phase unwrapping. The representation must be fixed before training.

Sparse-measurement condition:
- primary K0 uses only 16 of the 64 frequency points, selected by a deterministic log-spaced mask fixed globally;
- 64-point results may be reported as an upper-bound ablation but cannot replace the 16-point primary result.

Noise/tolerance:
- additive complex measurement noise equivalent to 35 dB SNR;
- independent small nominal manufacturing tolerances applied to non-faulted line and lumped parameters;
- the exact tolerance distribution is frozen in config.

All methods see the same noisy measurements.

---

## 5. Fault model and labels

A circuit graph has candidate fault locations on edges and eligible nodes.

K0 fault types:
1. **Z0_SHIFT** — characteristic-impedance deviation on one line edge;
2. **EXCESS_R** — additional series loss on one edge;
3. **SHUNT_LEAK** — added shunt conductance at an eligible node/edge endpoint;
4. **STUB_OR_VIA_PARASITIC** — abnormal added L/C or stub-length perturbation where that primitive exists.

Severity is continuous and sampled from pre-frozen moderate-to-hard ranges. The smallest faults must remain above the simulator's numerical noise floor but should overlap normal tolerance effects.

Regimes:
- **R0:** one fault, moderate severity;
- **R1:** one fault, hard/small severity;
- **R2:** two simultaneous faults, independently located/type sampled;
- **R3:** three simultaneous faults.

Primary K0 decision uses pooled **R1+R2+R3**. R0 is sanity only.

Targets:
- per-location fault probability;
- per-location fault type;
- continuous normalized severity for true faults.

---

## 6. Proposed model under test: TopoSI-GNN

K0 does not authorize architecture search.

Use one compact topology-aware model:
- a measurement encoder maps the 16-frequency complex S-parameter tensor into a global latent vector;
- graph nodes/edges receive nominal physical attributes (type, Z0/R/L/C/length, port-distance features);
- 3–4 message-passing layers;
- per-edge/per-node heads output fault probability, fault type, and severity.

Parameter count target: <= 2 million.

Only one small predeclared hyperparameter set and at most two random seeds are allowed in K0. No tuning on the held-out family.

---

## 7. Required baselines

All baselines receive the nominal target netlist/topology and exactly the same measurements unless explicitly topology-blind.

### B1 — TDR / impulse heuristic
IFFT or equivalent reflectometry transform with peak picking and path-distance mapping. For branched networks, use the nominal graph path lengths to map peaks to candidate locations.

### B2 — Linearized sparse physics inverse
Compute the nominal sensitivity/Jacobian of the selected measurements with respect to candidate fault parameters, then solve a sparse inverse problem using L1/elastic-net regularization. Regularization is selected only on training-family validation circuits.

### B3 — Nonlinear target-specific inverse fit
Strong classical baseline. Optimize a sparse set of fault parameters against measured S-parameters using multi-start nonlinear least squares.

Target-specific forward-simulation budget must be reported. Evaluate at:
- 32 simulations;
- 128 simulations;
- 512 simulations.

No hidden extra simulations for choosing starts or thresholds.

### B4 — Topology-blind / adjacency-free DL
Use the same measurement encoder and the same nominal local candidate attributes as TopoSI-GNN, but **remove graph adjacency/message passing**. Implement as shared per-candidate MLP/DeepSets conditioning on the global measurement latent.

This baseline tests whether topology reasoning is actually necessary.

### B5 — nominal-only ranking sanity baseline
Rank candidates by a simple nominal sensitivity norm without fitting.

The strongest baseline at the relevant budget is used for the decision. Do not choose a weaker baseline because it is convenient.

---

## 8. Fair cost accounting

For every method report:
- number of target-specific forward simulations;
- wall time on the same host;
- peak memory;
- offline training/data-generation simulations separately;
- per-new-target inference/optimization cost.

Pretraining cost is not free.

For any amortization claim, compute the number of new unseen target circuits required to break even versus B3.

---

## 9. Metrics

Primary multi-fault metric:
- **sample-level set-F1** for exact fault locations, averaged across samples.

Also report:
- exact-set accuracy;
- top-k location recall where k equals the true number of faults;
- mean graph-distance localization error for unmatched predictions;
- fault-type macro-F1 on correctly localized faults;
- normalized severity MAE on correctly localized/type-correct faults;
- per-family/fold results;
- bootstrap 95% confidence intervals clustered by circuit instance.

Do not use edge-wise accuracy because class imbalance makes it misleading.

---

## 10. Frozen K0 decision rule

The project receives **STRONG GO** only if all mandatory conditions below hold.

### Mandatory condition M1 — graph necessity
On pooled held-out-family R1+R2+R3:

TopoSI-GNN must beat B4 adjacency-free DL in set-F1 by:
- >= 10 percentage points;
- with 95% CI lower bound >= 5 points;
- and positive gain in at least 3 of 4 held-out-family folds.

If M1 fails: **STOP**.

### Route A — accuracy advantage
At the same target-specific simulation budget, TopoSI-GNN must beat the strongest of B1/B2/B3 by:
- >= 20 percentage points pooled set-F1;
- 95% CI lower bound >= 10 points;
- positive gain in at least 3 of 4 folds;
- no fold worse by more than 5 points.

If M1 + Route A pass: **STRONG GO**.

### Route B — target-simulation efficiency
If Route A fails, Route B may pass only if:
- TopoSI-GNN is within 5 percentage points of the strongest B3 result achieved with <=512 target simulations;
- TopoSI-GNN uses at least 20x fewer target-specific simulations than the matched-accuracy classical method;
- amortized break-even, including offline simulation + training cost, is <=100 new unseen target circuits;
- M1 still passes.

If M1 + Route B pass: **GO, efficiency framing**.

Otherwise:
- 5–20 point classical advantage gap or uncertain CIs: **BORDERLINE**, one cheap diagnostic allowed only if pre-specified from a clear failure mode;
- failure of M1 and both routes: **STOP**.

No rescue tuning is allowed after STOP.

---

## 11. Sanity checks before decision data

Must pass before K0 test evaluation:
1. network solver reproduces a set of analytically solvable transmission-line examples;
2. graph -> network -> graph metadata round-trip preserves all candidate fault locations;
3. no circuit hash overlap between train/validation/test;
4. no held-out-family samples contribute to normalization;
5. injecting a large single fault produces a detectable measurement change above noise;
6. B2 sensitivity inverse beats random ranking on easy R0 cases.

If any sanity check fails, fix the implementation and document it before proceeding. Sanity fixes may not alter the frozen decision thresholds.

---

## 12. Reproducibility artifacts

Required:
- frozen config JSON/YAML with all distributions and seeds;
- generator source;
- model/baseline source;
- raw per-instance predictions;
- cost-accounting table;
- K0 report;
- exact git commit;
- deviation log.

Do not commit huge generated datasets if reproducible from seeds.

---

## 13. K0 interpretation

K0 passing means only:
- unseen-topology inverse localization appears feasible;
- topology-aware DL is materially useful;
- classical direct inversion is not an obvious superior explanation.

It does **not** establish:
- full-wave validity;
- PCB measurement validity;
- robustness to calibration/de-embedding error;
- publication novelty;
- Q1 acceptance.

Those become later gates only after K0 passes.
