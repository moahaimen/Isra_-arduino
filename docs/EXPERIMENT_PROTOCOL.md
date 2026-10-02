# Experiment protocol

## Design

* **Factors:** scenario (8) × operating mode (6), seeds 1–10, 3600 simulated
  seconds per run: 480 runs (main campaign).
* **Matched design:** for each (scenario, seed) one workload is generated and
  saved *before* any mode runs; all six modes replay that exact file
  (verified by hash in `logs/workload_equality.csv`). Per-event detector and
  RPC randomness is keyed by (seed, event_id), so an event that two modes
  both process gets identical detector outcomes (common random numbers).
* **No per-method tuning:** all shared parameters come from
  `config/default_config.json`; modes only switch components on or off
  (`apply_mode_defaults`). The defaults were fixed before the campaigns were
  run and were not changed after seeing results.
* **Ablation campaign:** the full secure system with exactly one component
  removed (security, cooldown, early exit, adaptive trigger, replay+duplicate
  protection, rate limit, burst detection, consistency check) plus always-on as
  energy reference; scenarios normal, busy, trigger_spam, replay, mixed; seeds
  1–10; 3600 s.
* **Sensitivity campaign:** one-at-a-time sweeps around the defaults
  (`scripts/run_sensitivity.py::SWEEPS`), seeds 1–10, 3600 s. Workload
  parameters (attack intensity, arrival rate) produce one shared workload per
  value. The queue-capacity sweep is run without cooldown (documented stress
  context) because with the default cooldown the queue is never occupied.
  Energy-model parameters are swept exactly by re-weighting stored state
  times.

## Procedure

1. Build (`cmake`), run the test suite (`tests/run_tests.sh`).
2. Smoke campaign (`scripts/smoke_test.sh 300`): 5 scenarios × 6 modes ×
   2 seeds × 300 s, every run validated.
3. Validation campaign: full matrix at 600 s.
4. Main, ablation and sensitivity campaigns at 3600 s.
5. Per-run metrics + structural validation (`validate_run.py`) for every run.
6. Aggregation, statistics, tables, figures, report (`aggregate.py`,
   `plots.py`, `make_report.py`), scientific audit (`audit_scientific.py`).

## Statistics

* Descriptive: mean, SD (ddof = 1), median and the 95 % confidence interval of
  the mean (Student t, n − 1 df) across the 10 seeds of a (scenario, mode)
  cell. Seeds are independent replications; observations inside a run are
  not treated as independent samples.
* Paired comparisons: modes compared within a scenario on the same seeds are
  matched pairs. Two-sided Wilcoxon signed-rank test on paired differences
  (no normality assumption; the per-seed differences are often skewed and n is
  small). Zero differences are discarded (Wilcoxon's treatment); with fewer
  than 6 non-zero pairs the test cannot reach p < 0.05 two-sided and is
  reported as not tested. Exact p-values are used for n ≤ 50 without ties.
* Effect size: matched-pairs rank-biserial correlation r = (R⁺ − R⁻)/(R⁺ + R⁻)
  and the median paired difference.
* Multiplicity: Holm–Bonferroni. Family = all comparisons of one metric in one
  scenario (7 comparisons: secure vs always_on, motion_only, fixed_threshold,
  event; event vs fixed_threshold, event_no_early_exit, always_on). A
  campaign-wide Holm correction over all comparisons is also reported. Note:
  with n = 10 the smallest exact two-sided p-value is 2/2¹⁰ = 0.00195, so a
  campaign-wide correction over several hundred tests cannot reject any
  hypothesis by construction; that column is reported for transparency, and
  more seeds would be needed for campaign-wide control (the simulator is fast
  enough: `--seeds 1:30`).
* Metrics compared: modeled energy, duty cycle, p95 onset latency, episode
  recall, false alarms, attack success rate, FRR on real objects.

## Test suite

`bash tests/run_tests.sh` builds and runs:

* `build/unit_tests` (C++): RNG determinism and distribution moments, energy
  integration against a hand-computed value, watcher threshold/cooldown/
  adaptive/motion rules, every security check and its disabled state,
  byte-identical workload generation for all scenarios, label consistency,
  mode-independence of workloads, simulator determinism, per-core time
  conservation, blocked-trigger isolation, always-on duty 100 %, empty workload.
* `build/firmware_host_check`: the shared firmware decision logic driven by
  mocked `millis()`/`delay()`/RPC.
* `tests/test_pipeline.py` (Python, 21 tests). Required tests → test names:

| # | requirement | test |
|---|---|---|
| 1 | same seed → identical workload | test_01 |
| 2 | same workload → identical ground truth in every mode | test_02 |
| 3 | simulator deterministic | test_03 |
| 4 | security cannot modify ground truth | test_04 |
| 5 | blocked trigger never wakes M7 | test_05 |
| 6 | every WAKE has a SLEEP | test_06_to_13 (wake_sleep_paired) |
| 7 | no overlapping active windows | test_06_to_13 (no_overlap_active) |
| 8 | trigger/result mapping | test_06_to_13 (trigger_result_map) |
| 9 | event ids consistent through the pipeline | test_09 |
| 10 | energy integration | test_10 (+ C++ test_energy_tracker) |
| 11 | latency non-negative | test_11_12 |
| 12 | queue delay non-negative | test_11_12 (incl. queue stress) |
| 13 | no event after SIM_END | test_06_to_13 (no_event_after_end) |
| 14 | workload duration obeyed | test_14 |
| 15 | always_on duty ≈ 100 % | test_15 |
| 16 | empty workload | test_16 |
| 17 | zero attacks | test_17 |
| 18 | 100 % attack workload | test_18 |
| 19 | loss = 0 → no artificial drops | test_19 |
| 20 | CSV columns | test_20 |
| – | no random blocking in research mode | test_21 |
| – | gzip outputs readable | test_22 |
| – | statistics helpers | test_23 |
| – | trace_replay backend | test_24 |
| – | mAP only with boxes | test_25 |
