# DualGuard-FI G0 — critical SDC detectability preregistration

Status: **FROZEN BEFORE G0 RESULTS**
Purpose: cheap kill test only.

G0 uses the existing frozen detector and existing real-frame data. It does not train or replace the detector, does not claim physical-fault equivalence, and does not authorize publication claims.

## 1. Core hypothesis

Critical silent object-detection corruptions contain complementary signatures across:
1. execution/timing/control-flow observables;
2. compact internal-activation witnesses;
3. output semantic/temporal consistency.

A fused monitor should detect substantially more critical SDCs than any one witness family alone at the same low false-positive rate.

## 2. Detector and data

Use the best already-existing, runnable object detector in the repository with frozen weights. Do not retrain it.

Preferred data order:
1. existing real KITTI/ZTF? object-detection validation frames already used in R2/R3;
2. if multiple detector checkpoints exist, choose one **before fault results** based only on existing clean validation quality and deployability.

Record:
- detector/checkpoint hash;
- dataset/frame manifest hash;
- preprocessing hash.

Minimum G0 set:
- 300 distinct real validation frames if already available;
- otherwise use every existing real validation frame up to that count.

No synthetic images for the primary result.

## 3. Golden outputs

For every frame, run one clean inference and store:
- final detections;
- selected internal witness values;
- phase timing / completion markers.

Golden inference is the reference for detecting software-emulated SDC.

If ground-truth labels are available, use them for safety severity classification as described below.

## 4. Frozen software fault-emulation campaign

G0 is a **screening proxy**, not physical-fault validation.

Use four fault families:

### F1 — transient activation corruption
At one of the preselected monitored or adjacent layers:
- single-element sign flip;
- exponent-scale corruption / large finite perturbation;
- contiguous small block corruption.

### F2 — detector-head corruption
Inject into pre-NMS objectness/class/box tensors:
- one value corruption;
- one candidate suppression;
- one candidate amplification;
- small contiguous block corruption.

### F3 — control/completion corruption
Software-emulate:
- skipped detector substep where implementation permits;
- stale intermediate/output reuse;
- premature completion / truncated candidate processing.

Do not introduce undefined behavior or crash-only cases into the primary SDC pool.

### F4 — weight/read corruption
Transiently alter one weight/read value during inference or use an equivalent reversible hook. Restore immediately after each run.

Do not permanently modify the checkpoint.

## 5. Fault locations and counts

Freeze locations before evaluation:
- 3 internal layers distributed early / middle / late;
- detector head;
- one control/completion point if safely hookable.

Target campaign:
- >= 5,000 total faulted inferences;
- >= 1,000 critical SDCs if achievable without changing the fault distribution.

Random seed is frozen.

If <500 critical SDCs are produced, G0 is **INCONCLUSIVE/STOP** rather than changing the injection distribution after seeing results.

## 6. Critical SDC definition

Primary critical-SDC label is determined from the faulted output versus clean output, and where possible checked against ground truth.

A faulted inference is **critical SDC** if it completes without a software crash/error flag and causes at least one of:

1. **Missed important object**:
   - a clean detection with confidence >=0.50 and matched GT when GT exists disappears, or its faulted best match has IoU <0.30.

2. **Wrong class**:
   - matched clean object changes class with faulted confidence >=0.50.

3. **Severe box corruption**:
   - same-class match drops from clean IoU >=0.50 to faulted IoU <0.30.

4. **High-confidence ghost**:
   - new unmatched faulted detection appears with confidence >=0.70.

5. **Mass suppression / explosion**:
   - >=50% of clean confident detections disappear, or number of confident detections increases by >=2x with at least two new unmatched detections.

Thresholds above are frozen before G0.

Crashes, exceptions and explicit hardware/software error flags are **detected faults**, not silent data corruptions, and are reported separately.

Benign corruptions that change neither safety-relevant detection semantics nor the above criteria remain negative cases.

## 7. Witness families

### W1 — execution witness
Use low-cost observables available without reproducing the detector:
- total inference time / cycle count;
- selected phase times where already instrumentable;
- completion sequence / heartbeat;
- candidate count entering/exiting NMS if available.

Do not use the final critical-SDC label itself as a feature.

### W2 — internal activation witness
Implement a SafeComp-style compact monitor baseline:
- per-selected-layer low-order quantiles / extrema / compact distribution summary;
- at most a few dozen scalars total.

No full activation copy.

### W3 — semantic witness
Use only final detection outputs and prior clean temporal context where sequential frames exist:
- detection count;
- confidence distribution;
- class-count changes;
- box-motion/IoU continuity;
- appearance/disappearance consistency.

If sequential context is not available for a frame, use only same-frame output statistics and report that limitation.

### WF — fused guardian
Fuse W1 + W2 + W3 using a deliberately small model:
- logistic regression, shallow tree/boosted classifier, or a fixed score fusion;
- no deep monitor network.

Model selection is performed only on a training split of faulted/clean monitor examples.

## 8. Splitting and leakage control

Split by **clean frame identity**, not by fault injection instance:
- 60% monitor-train;
- 20% monitor-validation;
- 20% held-out monitor-test.

All faults derived from the same clean frame stay in the same split.

Thresholds are selected only on validation to achieve FPR <=1%.

Held-out test is opened once.

## 9. Required baselines

Evaluate:
- B0 timing/execution only = W1;
- B1 activation monitor only = W2;
- B2 semantic only = W3;
- B3 best pairwise fusion;
- BF full fusion W1+W2+W3.

Also report an idealized static weight-CRC baseline for F4 only, clearly labeled as not applicable to transient compute/activation faults.

## 10. Metrics

Primary:
- recall/TPR on **critical SDCs** at FPR <=1% on clean + benign held-out inferences.

Secondary:
- precision;
- AUROC / AUPRC;
- recall by fault family F1–F4;
- recall by criticality type;
- false alarms per 1,000 clean inferences;
- estimated witness extraction overhead;
- data bytes per inference exported to M4;
- monitor decision latency estimate.

Use bootstrap 95% CI clustered by clean frame.

## 11. Frozen G0 decision rule

G0 **PASS** only if all conditions hold on the held-out test set:

### G0-A — critical SDC coverage
Full fusion BF:
- TPR >= 95% at FPR <=1%;
- 95% CI lower bound for TPR >=92%.

### G0-B — complementarity
BF must beat the best single witness among W1/W2/W3 by:
- >=8 percentage points TPR at the same <=1% FPR;
- 95% CI lower bound of the improvement >=4 pp.

If best single witness is within 3 pp of BF, automatic **STOP** for novelty even if G0-A passes.

### G0-C — breadth
BF must reach:
- >=90% TPR on each represented critical fault family with >=100 critical samples.

### G0-D — overhead feasibility
Estimated embedded overhead before cross-core communication:
- <=10% detector runtime;
- compact witness payload <=2 kB per inference.

If overhead cannot be estimated credibly from host instrumentation, mark G0-D provisional; it must be measured on hardware before any paper claim.

### Decision
- All G0-A/B/C pass and G0-D passes/provisional: **G0 PASS -> authorize hardware feasibility gate**.
- Anything else: **G0 STOP**.

No rescue tuning after held-out test results.

## 12. What G0 PASS does NOT prove

It does not prove:
- physical glitch behavior matches software emulation;
- M4 remains trustworthy during a real clock/voltage glitch;
- Portenta H7 overhead/energy is acceptable;
- novelty is publication-ready.

The next gate after PASS is a hardware feasibility/physical-fault gate.

## 13. Required outputs

Create:
- results/dualguard_g0/config_frozen.json
- results/dualguard_g0/PROTOCOL_SNAPSHOT.txt
- results/dualguard_g0/DEVIATIONS.md
- results/dualguard_g0/G0_REPORT.md
- results/dualguard_g0/G0_DECISION.txt
- per-fault prediction CSV/JSON
- monitor split manifest
- checkpoint/data/preprocessing hashes
- witness-overhead estimate

Do not push large datasets or model files.
