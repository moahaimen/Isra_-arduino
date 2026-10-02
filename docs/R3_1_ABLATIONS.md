# R3.1 validation-only ablations (KITTI validation, seeds 1001–1003; no test data)

Security stack on the legacy event watcher (`scripts/r3_1/exp_ablations.py`, table `results/r3_1/validation/ablation_security_kitti_val.csv`).

| variant | FRR (clean+noisy) | replay-exact success | replay-perturbed | mixed | spam ×8 success | spam ×8 energy mJ/min |
|---|---|---|---|---|---|---|
| full gate (replay + budget + shift tol) | 0 | 0.000 | 0.028 | 0.073 | 0.071 | 9959 |
| − shift tolerance | 0 | 0.000 | 0.028 | 0.073 | 0.071 | 9959 |
| − budget / − novelty budget | 0 | 0.000 | 0.028 | 0.073 | 0.071 | 9959 |
| − replay verification | 0 | 0.041 | 0.063 | 0.119 | 0.077 | 10249 |
| plain rate limit only | 0 | 0.041 | 0.063 | 0.119 | 0.077 | 10249 |
| no security | 0 | 0.041 | 0.063 | 0.119 | 0.077 | 10249 |

**Reading.** Only replay verification has any effect; the global/novelty budgets and shift tolerance are inert under this watcher and attack set
(a 2 s cooldown already caps the wake rate; the existing shift variants are ≤ 4 px). Utility (clean timely recall) is identical across variants.
Ablations of the scheduler mechanisms (noise adaptation, persistence, region novelty, M7 feedback, confirmed hold, value rule) are in
`docs/R3_1_GATE_B.md` / `results/r3_1/validation/pareto_kitti_val_all.csv` (R3 scheduler: feedback-off ablation from the earlier R3.1 baseline experiment was
worse); persistence/novelty ablations were not re-run because the scheduler is dropped as a contribution.
No claim is made for components that show no effect.
