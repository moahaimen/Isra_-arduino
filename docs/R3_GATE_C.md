# Gate C: security quality (validation only)

**Verdict: PARTIAL.** The R3 secure scheduler passes the availability criteria (FRR < 0.05, secure
utility retention >= 0.85) and clearly beats the R2 and R1 gates on false rejection, and it
strongly reduces exact and photometric replay. It does NOT suppress trigger spam, handles shifted
replay poorly, and its budget costs legitimate availability at spam x8. Final test not unlocked.

## Procedure (declared in `scripts/r3/tune_r3.py` before any Gate-C result)

Watcher fixed at the Gate-B point of the non-secure counterpart (`ugs_event` iteration 3, `event`,
`robust_event`); gate parameters searched on validation: conditions clean, noisy, spam x1, spam x8,
replay_exact, replay_perturbed, mixed x1; 5 overlay seeds (1001-1005); 40 sampled configurations per
method (compute budget fixed before the run). Selection: max secure utility retention
SUR = timely recall under attack / the same method's clean timely recall, s.t. FRR <= 0.05; ties ->
lower attack success. If no configuration meets the FRR constraint the least-bad one is reported and
`constraint_met` is false.

## Selected points (`results/r3/gate_c_summary.csv`)

| method | FRR <= 0.05 met | SUR | min SUR | FRR | attack success | UR_timely vs always-on | duty (all) | duty (attack conditions) |
|---|---|---|---|---|---|---|---|---|
| ugs_secure (R3) | yes | 0.982 | 0.970 | **0.024** | 0.219 | 0.828 | 0.246 | 0.278 |
| robust_secure (R2) | **no** | 1.024 | 1.000 | 0.616 | 0.072 | 0.603 | 0.110 | 0.108 |
| secure (R1 legacy) | **no** | 1.060 | 0.983 | 0.879 | 0.018 | 0.284 | 0.013 | 0.013 |

SUR is a ratio to each method's own clean recall and can exceed 1; it must be read together with the
absolute UR_timely column. A gate that rejects 62-88 % of legitimate requests has a "perfect" SUR
because its clean recall is already destroyed. Those two gates' low attack success is bought with
that rejection.

## Per-attack results at the selected points (5 seeds x 2 segments; `results/r3/tuning/gateC_selected_runs.csv`)

Attack success = attack frames whose request reached the M7 / attack frames.

| condition | ugs_event (no gate) | ugs_secure | robust_secure | secure |
|---|---|---|---|---|
| exact replay | 0.173 | **0.027** (gate detection 0.964) | 0.000 | 0.000 |
| perturbed replay (all) | 0.211 | **0.106** (0.808) | 0.052 | 0.003 |
| of which shifted replay | 0.217 | 0.178 | 0.102 | 0.006 |
| trigger spam x1 | 0.288 | **0.284** (gate detection 0.015) | 0.093 | 0.038 |
| trigger spam x8 | 0.289 | **0.280** | 0.090 | 0.024 |
| mixed x1 | 0.265 | 0.201 | 0.064 | 0.010 |
| FRR (replay_exact / perturbed / spam x1 / spam x8 / mixed / clean) | n/a | 0.007 / 0.029 / 0.014 / **0.107** / 0.001 / 0.020 | 0.64 / 0.62 / 0.64 / 0.60 / 0.64 / 0.65 | 0.81-0.84 |
| timely recall (clean / spam x8) | 0.770 / 0.748 | 0.770 / 0.748 | 0.557 / 0.597 | 0.197 / 0.246 |

## What this shows

* Temporal-context replay detection works where the R2 rule failed on availability: exact replays are
  blocked at 96 %, brightness/noise/JPEG replays mostly, with 0.7-2.9 % FRR instead of 62-65 %.
* Shifted replay (+-3-4 px) is largely missed (0.178 vs 0.217 unsecured): block differences exceed the
  match tolerance. Open problem.
* The scheduler's novelty priority is exploitable by diverse spam: the four flash-patch positions and
  the flicker variants appear as new content, so spam passes (28 % of spam frames wake the M7, same as
  without the gate). The barren back-off needs k_retry = 5 wakes per region before it engages, and
  iteration 3 selected k_retry = 5 for retention. Spam protection thus trades against retention in this design.
* At spam x8 the global budget starts rejecting legitimate requests (FRR 0.107) without reducing
  spam success: the budget protects the M7 duty (0.33 vs 1.0) but not availability.
* All of the above are validation results on 2 video groups with parameters selected on the same data;
  they are not confirmatory.
