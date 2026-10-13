# LOCAL EXECUTION PROMPT — DualGuard-FI G0, minimal-token mode

Work only in the current local repository.

The local tree already contains the user's merged research code and detector artifacts. Do NOT pull, checkout, reset, rebase, or overwrite unrelated local changes.

If the DualGuard docs are not present locally, read them from the already-fetched remote ref without checking anything out:

- `origin/research/dualguard-fi-g0:docs/dualguard/DUALGUARD_FI_NOVELTY_AUDIT.md`
- `origin/research/dualguard-fi-g0:docs/dualguard/DUALGUARD_FI_G0_PREREGISTRATION.md`

Treat the current local working tree as source of truth for code, data, checkpoints and cached detector outputs.

## MINIMAL TOKEN MODE

Do not narrate routine work.
Do not send periodic prose updates.
Keep detailed logs locally.

Maintain only:
`results/dualguard_g0/STATUS.txt`

Maximum 6 short lines:
```
PHASE:
DONE:
CURRENT:
BLOCKER:
CPU/SPEND:
NEXT:
```

Only message me if:
1. the frozen protocol cannot be executed as written;
2. a real implementation blocker requires my decision;
3. paid compute would exceed $5;
4. G0 completes or reaches STOP.

Do not call another LLM/API.

## PURPOSE

Execute **DualGuard-FI G0 only**.

This is a cheap screening test. It asks whether execution + internal-activation + semantic witnesses contain complementary information for detecting **critical silent object-detection corruption**.

Do NOT train or replace the object detector.
Do NOT perform physical glitching in G0.
Do NOT start firmware or hardware work.
Do NOT write a paper.
Do NOT rescue-tune after held-out results.

## STEP 0 — PROTOCOL INTEGRITY

Before viewing any G0 held-out result:

1. Read both DualGuard docs.
2. Create:
   - `results/dualguard_g0/config_frozen.json`
   - `results/dualguard_g0/PROTOCOL_SNAPSHOT.txt`
   - `results/dualguard_g0/DEVIATIONS.md`
3. Record SHA256 of:
   - detector checkpoint;
   - frame/data manifest;
   - preprocessing source or digest;
   - preregistration;
   - novelty audit.
4. Freeze root seed.
5. Freeze the exact detector checkpoint based only on existing clean validation quality/deployability.

If several existing detectors are available, do not pick one based on fault-injection results.

## STEP 1 — REUSE EXISTING REAL DATA

Prefer existing real object-detection validation frames already used in the repository.

Use up to 300 distinct real frames.

Do not download a new large dataset unless absolutely necessary.

No synthetic images for the primary result.

Store one golden clean inference per frame.

If existing cached clean detector outputs are exact and reproducible, reuse them.

## STEP 2 — INSTRUMENT WITNESSES

Implement the three frozen witness families:

### W1 execution
- total inference time/cycles;
- selected phase timing if already easy to instrument;
- completion/heartbeat sequence;
- candidate counts around detection/NMS if available.

### W2 compact internal activations
SafeComp-style compact summaries from exactly 3 frozen layers: early / middle / late.
Use compact quantiles/extrema/distribution summaries only.
Do not copy full tensors into monitor features.

### W3 semantic/output
Use compact object-detection statistics and temporal consistency where sequential context exists.

### BF fusion
Use only a tiny monitor:
- logistic regression OR shallow tree/boosted model OR fixed score fusion.
No deep monitor network.

Freeze the monitor class before opening held-out results.

## STEP 3 — SOFTWARE FAULT EMULATION

Implement the frozen F1–F4 families exactly as possible in the existing detector:

- F1 transient activation corruption;
- F2 detector-head corruption;
- F3 control/completion corruption;
- F4 reversible weight/read corruption.

Primary campaign target:
- >=5000 faulted inferences;
- >=1000 critical SDCs if naturally produced.

Do not change injection distributions after seeing results just to create more positives.

If fewer than 500 critical SDCs occur:
**G0 STOP / insufficient critical events**.

Crashes and explicit errors are not silent corruptions; count them separately.

## STEP 4 — CRITICAL SDC LABELS

Apply the exact frozen rules from the preregistration.

Where ground truth exists, use it to verify safety severity.

Do not redefine criticality after viewing monitor performance.

## STEP 5 — SPLIT WITHOUT LEAKAGE

Split by clean frame identity:
- 60% monitor-train
- 20% monitor-validation
- 20% held-out test

All injected variants from one clean frame stay in one split.

Thresholds are selected on validation to satisfy FPR <=1%.

Open held-out test once.

## STEP 6 — BASELINES

Evaluate on the same held-out data:
- W1 only
- W2 only
- W3 only
- best pairwise fusion
- BF = W1+W2+W3
- idealized static CRC reference for F4 only

Do not weaken any single-monitor baseline.

## STEP 7 — METRICS

Primary:
critical-SDC TPR at <=1% FPR.

Report:
- bootstrap 95% CI clustered by clean frame;
- best-single vs fusion difference + CI;
- per-fault-family TPR;
- per-criticality-type TPR;
- precision / AUROC / AUPRC;
- false alarms / 1000 clean inferences;
- estimated witness extraction runtime overhead;
- witness payload bytes / inference;
- monitor decision latency estimate.

## FROZEN DECISION

PASS only if all hold:

G0-A:
- BF TPR >=95% at FPR <=1%;
- TPR CI lower bound >=92%.

G0-B:
- BF beats best single W1/W2/W3 by >=8 pp TPR;
- improvement CI lower bound >=4 pp.
- If best single is within 3 pp of BF => automatic STOP for novelty.

G0-C:
- >=90% TPR for each critical fault family with >=100 critical examples.

G0-D:
- estimated witness extraction overhead <=10%;
- payload <=2 kB/inference.
- If host-only estimate cannot establish embedded overhead credibly, mark G0-D PROVISIONAL, not PASS or FAIL.

All A/B/C and D pass/provisional => **G0 PASS**.
Anything else => **G0 STOP**.

No borderline rescue.

## IMPORTANT PRIOR-ART BASELINE

The activation-only W2 baseline must be implemented seriously because SafeComp 2023 reports compact hidden-layer monitoring with very high detection performance and very low overhead.

If W2 alone nearly matches BF, the project is not novel enough even if absolute detection is excellent.

## COMPUTE

Use local CPU.
Cache golden inferences and layer summaries.
Use batched fault hooks where safe.
Reuse deterministic artifacts.
Do not retrain detector.
Do not use paid GPU/cloud.
Do not spend >$5.

Optimize implementation before changing scientific sample counts.

## REQUIRED OUTPUTS

Create:
- `results/dualguard_g0/config_frozen.json`
- `results/dualguard_g0/PROTOCOL_SNAPSHOT.txt`
- `results/dualguard_g0/STATUS.txt`
- `results/dualguard_g0/DEVIATIONS.md`
- `results/dualguard_g0/G0_REPORT.md`
- `results/dualguard_g0/G0_DECISION.txt`
- concise per-fault prediction/results files
- monitor split manifest
- checkpoint/data/preprocessing hashes
- overhead estimate

Do not commit or push unless explicitly asked.

## FINAL RESPONSE ONLY

When complete, reply only:

```
DUALGUARD-FI G0 COMPLETE

Detector/checkpoint:
Real frames:
Faulted inferences:
Critical SDCs:
Crashes/non-silent faults:
BF TPR @ <=1% FPR:
BF TPR 95% CI:
Best single witness:
Best single TPR:
Fusion advantage + CI:
Per-family F1/F2/F3/F4 TPR:
Estimated extraction overhead:
Witness payload:
G0-A:
G0-B:
G0-C:
G0-D:
Decision: G0 PASS / G0 STOP
Post-result protocol changes: NONE / list
Results: results/dualguard_g0/G0_REPORT.md
```

Start now. Work silently.
