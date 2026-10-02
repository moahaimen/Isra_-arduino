# Scientific validation

This document lists every check made on the method and the final campaigns,
its result, and the weaknesses the results expose. Final campaigns (all from
commit `a753e83`, clean tree, 10 seeds × 3600 s unless noted):
`smoke_20261002T092602Z` (60 runs, 300 s), `validation600_20261002T092602Z`
(480 runs, 600 s), `main_20261002T092602Z` (480), `ablation_20261002T092602Z`
(500), `sensitivity_20261002T092602Z` (2550). Every one of the 4070 runs
passed structural validation and every run matched its shared workload hash.

## 1. Automated audit (`scripts/audit_scientific.py`)

Output: `results/campaigns/main_20261002T092602Z/logs/scientific_audit.md`.
All 15 checks pass:

| check | evidence (main campaign) |
|---|---|
| identical workload for every mode | 80 (scenario, seed) groups, one hash each |
| no per-method tuning | shared parameters take exactly one value across all 480 runs |
| watcher/security cannot read ground truth (static) | no ground-truth identifier in watcher or gate code |
| decisions unchanged when ground truth is scrambled (dynamic) | 0 differing decisions in event and secure mode on mixed seed 1 |
| no random blocking | all runs `research_valid`, 0 DEBUG_RANDOM blocks |
| no perfect detector | 0 runs with precision = recall = 1; detector recall 0.70–0.98 |
| no oracle security gate | attack detection 0.39–0.88, FRR 0.03–0.16 across secure attack runs |
| no impossible timing | 0 negative latencies/queue delays; min event onset 114.5 ms > 10.5 ms fixed floor |
| no double-counted energy | per-core state time sums to T within 0.001 ms; Python and C++ energy agree to 2·10⁻⁶ mJ |
| structural validity | 480/480 runs |
| no duplicated workload events | 0 |
| paired tests on matched workloads only | 392/392 comparisons |
| raw outputs preserved | 480 raw directories |
| power model flagged uncalibrated | `calibrated: false` everywhere |
| mAP not fabricated | 0 runs report mAP |

## 2. Test suite

142 C++ unit checks, the firmware host check, and 21 Python integration
tests (covering all 20 required tests; mapping in
`docs/EXPERIMENT_PROTOCOL.md`) pass at the final commit; `reproduce_all.sh`
ran them before the campaigns.

## 3. Determinism

Interim campaigns (deleted) and the final campaigns produced identical
pooled results to the printed precision for every mode, consistent with the
byte-identical-workload and simulator-determinism tests.

## 4. Changes made during development (disclosed)

| change | why | effect |
|---|---|---|
| always-on empty-frame noise taken from the scenario's background noise instead of the first workload event | bug: always-on false alarms depended on an unrelated event | always-on false alarms now scenario-consistent |
| wake-up wait separated from queue delay | queue delay was over-reported by M7 wake time | queue delay is now pure waiting time; wake wait reported separately |
| Holm correction family changed from campaign-wide to per (scenario, metric) | **post hoc**: with 10 seeds the minimum exact p is 0.00195, so the campaign-wide correction over 257 tests rejects nothing by construction | 236/257 significant per family; campaign-wide column still reported (0 significant). A pre-registered alternative would be more seeds |
| queue-capacity sweep run with cooldown 0 | with the default 1.5 s cooldown the queue is never occupied, so the sweep would be vacuous | queue behaviour is shown only in this stress context, labelled as such |
| figure layout fixes | readability | none on data |

No parameter default was changed after results were seen.

## 5. What the results support, and what they do not

Supported (in simulation, under the stated assumptions):

* Event triggering cuts M7 duty cycle from 100 % to 0.9–1.7 % and modeled
  energy by about 82–83 %, for every event-driven mode alike.
* The security gate reduces attack success relative to the unprotected event
  mode: trigger spam 17.0 % → 2.5 %, replay 51.2 % → 24.6 %, mixed 19.7 % →
  4.7 % (Holm-family p ≤ 0.0098, rank-biserial −1.0 in each), and cuts false
  alarms per hour from 11.9 to 5.4 pooled.

Not supported, or contrary to the hypothesis:

* **Security costs recall.** Secure mode has the lowest episode recall of the
  event-driven modes (0.685 pooled vs 0.735 event, 0.795 fixed threshold);
  FRR on real objects is 7–11 % and rises to 35 % at 8× spam intensity, so a
  strong enough spam attack still degrades detection (denial of detection),
  even though it no longer reaches the M7.
* **The adaptive threshold hurts in the noisy scenario**: event recall 0.486
  vs 0.799 for the fixed threshold. It raises the threshold when the noise
  floor rises, which suppresses real objects too. It is not an improvement in
  this model.
* **Burst handling is poor**: recall in the burst scenario is 0.43–0.48 for
  all event modes and 0.303 in secure mode, because the global cooldown and
  the burst detector treat legitimate bursts like spam. Raising the burst
  threshold to 40 lifts secure recall in the burst scenario to 0.433 but
  raises spam success from 2.5 % to 6.5 % in the trigger-spam scenario.
* **Early exit lowers recall slightly** (event 0.735 vs no-early-exit 0.756)
  for a modeled saving of 0.4 percentage points.
* **Energy differences between event-driven modes are small** (82.2–83.0 %)
  and are dominated by the assumed always-on M4 monitoring power (83.9 % of
  secure-mode energy). Scaling M4_MONITOR by 4× drops the saving to 40 %;
  scaling M7_INFERENCE by 0.25× drops it to 65 %. The headline saving is only
  as good as these two uncalibrated numbers.
* Some secure components are redundant under the defaults: removing the rate
  limit or the adaptive trigger changes nothing measurable in the ablation,
  because the cooldown already caps the trigger rate below the rate limit.
* Replay protection only catches about half of replays (attack detection
  52 %), because perturbed replays exceed the near-duplicate tolerance.

## 6. Threats to validity

* **Construct**: the watcher features, detector outcomes and attack processes
  are parametric models, not camera data or a trained network; "recall" is
  recall of this model.
* **Internal**: one author designed both the system and the workload; the
  defaults are plausible but untuned, and a different workload model could
  change the ranking of modes.
* **External**: no hardware; power, inference latency, wake latency and RPC
  timing are assumptions (`docs/HARDWARE_VALIDATION_PLAN.md`).
* **Statistical**: 10 seeds per cell; the per-family Holm correction is a
  post-hoc choice (section 4); effect sizes and confidence intervals are
  reported so readers can judge magnitude independently of p-values.
