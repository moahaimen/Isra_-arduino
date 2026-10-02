# R3.1 Gate B (preliminary) — does the scheduler beat simple baselines? (KITTI validation, corrected tiled cost)

**Scope.** KITTI validation groups only (7 groups; clean + noisy; seeds 1001–1003). MEVA results are pending (reference tracks still being
computed) and the leave-one-group-out (LOGO) analysis is not yet done; the Pareto comparison below is *selection-free* (all configs shown),
so it does not depend on any selection rule. Validation is object-dense (known limitation, `docs/R3_1_BASELINE.md`). No locked-test frame was used.

**Method.** Every config evaluated once on identical workloads with the corrected physically-composed tiled cost
(`results/r3_1/validation/pareto_kitti_val_all.csv`, produced by `scripts/r3_1/exp_sched.py`, `exp_baselines.py`, `pareto_summary.py`).
UR = timely tracks (method) / timely tracks (always-on), mean of the clean and noisy condition; duty = M7 active time / time.
Grids: R3 baselines' own grids (≤36 sampled configs per family); scheduler: {R3, +noise-norm, +hold, +value-rule, all} × a_on {3,4.5,6,8} × z0 {0.5,1,2}
around the R3 validation-selected point.

| family | best UR with duty ≤ 0.25 | its duty | minimum duty reached by any config |
|---|---|---|---|
| event (legacy) | 0.643 | 0.230 | 0.140 |
| mog2_event | 0.614 | 0.202 | 0.126 |
| robust_event (R2) | 0.530 | 0.233 | 0.157 |
| R3.1 scheduler variants (noise-norm / all) | 0.150 / 0.098 | 0.227 / 0.188 | 0.157 / 0.137 |
| R3 scheduler (defaults of R3 mechanisms) | none ≤ 0.25 | — | 0.662 |
| R3 + hold / + value-rule | none ≤ 0.25 | — | 0.773 / 0.508 |

## Findings (negative results kept)
1. **The R3 scheduler cannot reach the duty budget under the corrected cost.** Its minimum duty over the grid is 0.66 (R3 duty "0.245" came from
   uncharged tiling). Its best UR overall is 0.80 at duty 0.74.
2. **The R3.1 mechanisms that do reduce duty (noise-normalised evidence with bootstrap) do so by suppressing almost all wakes**:
   UR ≤ 0.15 at duty ≤ 0.25. Confirmed hold and the value rule alone did not lower duty below 0.5.
3. **Simple baselines dominate at the 25 % duty budget**: the legacy event trigger, MOG2 and R2 robust_event reach UR 0.53–0.64 at duty ≤ 0.25,
   versus ≤ 0.15 for any scheduler variant. No scheduler config is on the Pareto frontier in the ≤ 0.25 duty region.
4. No method of any family reaches UR ≥ 0.90 at duty ≤ 0.25 here.

## Decision (O6)
**Scheduler-superiority is NOT supported and is dropped.** The paper must not claim that the utility-gated scheduler beats simple
baselines. Pending: MEVA and LOGO confirmation (expected to be consistent given the margin, but not yet shown).
Outcome-A-style claims on the scheduler are off the table; the contribution pivots to the security side (O3/O4) with the
availability-preserving gate evaluated against rate-limit baselines, subject to Gates C/D.
