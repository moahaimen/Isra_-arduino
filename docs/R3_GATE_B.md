# Gate B: watcher / scheduler utility retention (validation only)

**Verdict: PARTIAL. PASS on clean video, FAIL on noisy video and on the pooled criterion.
The pre-set targets (UR >= 0.90, duty <= 0.25) are not met pooled; the R3 scheduler does not beat
the legacy EWMA rule on the pooled/noisy Pareto frontier. Final test not unlocked.**

## Procedure (declared in `scripts/r3/tune_r3.py`, commit f449972, before any result)

Conditions clean (seeds 1001-1003) and noisy (1001-1010), both validation segments pooled; per
configuration UR_timely = pooled timely-tracks(method) / pooled timely-tracks(always_on); operating
point = max UR_timely subject to pooled duty <= 0.25; full frontier stored. Same procedure, same
workloads and identical detector traces for every method. Grids: `docs/R3_GATE_B.md` table below,
sampled to <= 120 configurations (UGS: 120 of 128; legacy `event`: full 80; others full).

## Selected points (`results/r3/gate_b_summary.csv`)

| method | configs | UR_timely | UR_track | UR_burst | noisy UR_timely | duty | modeled energy (mJ/min) |
|---|---|---|---|---|---|---|---|
| ugs_event (R3, iteration 3) | 120 | 0.817 | 0.977 | 0.838 | 0.784 | 0.245 | 9,976 |
| event (legacy EWMA) | 80 | **0.838** | 0.909 | 0.867 | **0.896** | 0.236 | 9,755 |
| fixed_threshold | 36 | 0.797 | 0.961 | 0.844 | 0.819 | 0.237 | 9,823 |
| motion_only | 24 | 0.795 | 0.986 | 0.840 | 0.803 | 0.245 | 10,026 |
| mog2_event (literature baseline) | 24 | 0.749 | 0.970 | 0.784 | 0.740 | 0.201 | 8,944 |
| robust_event (R2) | 120 | 0.763 | 0.942 | 0.801 | 0.731 | 0.248 | 10,034 |

Energy is MODELED. Frontiers: `results/r3/figures/fig_pareto_duty_utility_validation.png`.

## Per-scenario view of the same selected points (3 seeds; `results/r3/tuning/ITERATIONS.md`)

Clean: duty / UR_timely / UR_track: ugs 0.248 / **0.910** / **0.989** (iteration-1 point); motion_only 0.199 / 0.774 / 0.956; mog2
0.230 / 0.774 / 0.940; robust_event 0.280 / 0.852 / 0.956; fixed 0.179 / 0.735 / 0.874; event 0.052 / 0.677 / 0.643.
Noisy: ugs 0.208 / 0.702; event 0.289 / 0.901; fixed 0.255 / 0.802; motion 0.259 / 0.794.
Hence the scheduler meets both targets on clean video and is the best of the methods compared there,
but the pooled optimum (which mixes clean and noisy) hides this and the noisy scene is a clear weakness.

## Diagnosis (three validation iterations, all disclosed in ITERATIONS.md)

1. Iteration 1: UR 0.795. Wake audit: 68 % of the scheduler's clean-video wakes re-confirm already
   detected tracks (refresh every 1 s). Slowing the refresh (iteration 2, dt_track up to 12 s) changed nothing:
   the optimizer kept 1 s, so redundancy was not the binding constraint.
2. Noisy segment audit (0006): 43 of 182 frames `BELOW_THRESHOLD`; low-contrast frames drain the evidence
   accumulator below the release level mid-object. Iteration 3 (leak rho and release level a_off added to the search):
   UR 0.817, noisy 0.784, duty 0.245.
3. The legacy rule's noisy retention (0.90) comes with a flood of triggers caused by uncompensated auto-exposure
   changes (duty 0.289, 65 % of its noisy wakes redundant); because every validation scene is object-rich,
   false triggers still land on real objects. The validation set contains almost no empty / benign-motion
   periods (wake hit rate 0.87-1.0 for every method), so it cannot reward a method for avoiding useless wakes.
   This dataset property limits what Gate B can show for ANY gating scheme.
4. The scheduler's frontier covers only duty 0.12-0.38 (its grid); it was not explored at higher duty.

## Criteria

| criterion | result |
|---|---|
| high utility retention (>= 0.90) | clean YES (0.91), pooled NO (0.817), noisy NO (0.784) |
| materially lower M7 duty | YES (0.245 vs 1.0; modeled energy 9,976 vs 25,200 mJ/min) |
| improved legitimate-burst handling | NO vs legacy event (0.838 vs 0.867); vs R2 robust_event YES (0.838 vs 0.801) |
| robust noisy-scene behaviour | NO |
