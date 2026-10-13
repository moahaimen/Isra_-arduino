# LOCAL EXECUTION PROMPT — TopoEMI-ZS R1 robustness gate, minimal-token mode

Work only in the current local repository.

The current local tree already contains the completed TopoEMI K0 implementation and results. Do not pull, checkout, reset, rebase, or overwrite unrelated work.

R1 is a **new prospective robustness gate**. K0 remains STOP. Do not reinterpret K0.

If this file is not present locally, read it from the already-fetched ref without checking out the branch:
`origin/research/topoemi-zs-k0:docs/topoemi/TOPOEMI_R1_ROBUSTNESS_PREREG.md`

Read that preregistration first and obey it literally.

## TOKEN MODE

Work silently.
Do not narrate routine work.
Keep detailed logs locally.
Only message me if:
1. the frozen R1 protocol cannot be executed;
2. a real implementation blocker needs my decision;
3. paid compute would exceed $10;
4. R1 is complete.

Update only:
`results/topoemi_r1/STATUS.txt`

Maximum 6 short lines.

## CORE RULES

- **NO RETRAINING** of TopoEMI-ZS.
- **NO FINE-TUNING** on R1 boards.
- Use the exact frozen K0-B TopoEMI-ZS and D0 weights.
- Use fresh boards and a new seed not used in K0.
- Prove zero board-hash overlap against all K0 train/val/test boards.
- Freeze R1 config before any R1 held-out result.
- Do not alter thresholds, nuisance ranges, scan pattern, source regimes, metrics, architecture, or baseline after seeing R1 results.

## OBJECTIVE

Test whether the frozen layout-conditioned TopoEMI-ZS model has a material robustness advantage over a strong nuisance-aware sparse Bayesian inverse under realistic phaseless near-field scan/calibration uncertainty on unseen PCB layouts.

Primary comparator:
**C3-R nuisance-aware sparse Bayesian/compressive inverse**.

C3-R must be strong and must be allowed to estimate nuisance variables from their frozen ranges.
Every forward evaluation counts.

## DATA

Generate exactly the fresh R1 dataset specified in the preregistration:
- 4 layout families;
- 80 fresh boards per family;
- source regimes R1/R2/R3;
- primary 48/576 scan points;
- same K0 frequencies and phaseless |Hx|, |Hy|, |Hz|;
- new root seed;
- no K0 overlap.

Cache deterministic forward operators/fields.

## NUISANCE GRID

Run all frozen slices from the preregistration.

Primary decision slices:
- E1 moderate:
  25 dB SNR, ±15% height, ±0.75 grid-step XY, ±2 dB gain.
- E2 severe:
  20 dB SNR, ±20% height, ±1.0 grid-step XY, ±3 dB gain.

E3 is characterization only and must not enter the decision.

## METHODS

Evaluate:
1. frozen TopoEMI-ZS;
2. frozen D0;
3. C3-R @1024 forward evaluations;
4. C3-R @4096 forward evaluations;
5. original K0 C3 without nuisance estimation as a diagnostic reference.

Do not add a new learned model.

## PRIMARY METRIC

Sample-level exact-location set-F1 on pooled R1+R2+R3.

Also report the preregistered secondary metrics.

Use clustered bootstrap 95% CI over board instances.

## DECISION — DO NOT CHANGE

R1-A:
On pooled E1+E2, TopoEMI-ZS minus strongest C3-R must be:
- >= +8 pp set-F1;
- CI lower bound >= +4 pp;
- positive in >=3/4 families;
- no family worse by >3 pp.

R1-B:
TopoEMI-ZS absolute performance:
- E1 set-F1 >=0.60;
- E2 set-F1 >=0.50.

R1-C:
TopoEMI-ZS minus frozen D0 on pooled E1+E2:
- >= +10 pp;
- CI lower bound >= +5 pp.

All three pass => **R1 STRONG PASS**.
Anything else => **R1 STOP**.

No borderline rescue.

## IMPLEMENTATION FIXES

A genuine bug may be corrected only if:
- it is documented in `results/topoemi_r1/DEVIATIONS.md`;
- it does not alter the scientific protocol;
- affected outputs only are rerun.

Do not tune after held-out results.

## COMPUTE

Use local CPU.
Reuse K0 code and frozen model weights.
Vectorize/batch forward calculations.
Cache Green matrices.
Use detached execution if long-running.
Do not use paid cloud/GPU or another LLM.

Because there is no retraining, R1 should be much cheaper than K0-B. If the estimate unexpectedly becomes large, optimize implementation/caching before changing sample counts.

## REQUIRED OUTPUTS

Create:
- `results/topoemi_r1/config_frozen.json`
- `results/topoemi_r1/PROTOCOL_SNAPSHOT.txt`
- `results/topoemi_r1/STATUS.txt`
- `results/topoemi_r1/DEVIATIONS.md`
- `results/topoemi_r1/R1_REPORT.md`
- `results/topoemi_r1/R1_DECISION.txt`
- concise per-sample/per-family/per-slice result files
- forward-evaluation accounting
- proof of no board-hash overlap with K0

Do not commit or push unless I explicitly ask.

## FINAL RESPONSE ONLY

When complete, reply only:

```
TOPOEMI R1 COMPLETE

Fresh-board overlap check:
TopoEMI E1 set-F1:
TopoEMI E2 set-F1:
Strongest C3-R pooled E1+E2 set-F1:
TopoEMI pooled E1+E2 set-F1:
R1-A: PASS/FAIL — margin + 95% CI + folds
R1-B: PASS/FAIL
R1-C: PASS/FAIL — TopoEMI vs D0 margin + CI
C3-R forward-evaluation budget:
Decision: R1 STRONG PASS / R1 STOP
Post-result protocol changes: NONE / list
Results: results/topoemi_r1/R1_REPORT.md
```

Start now. Do not retrain. Do not narrate routine work.
