# Validation-only development iterations (all numbers on the R3 validation split)

## Iteration 1 (grid declared in scripts/r3/tune_r3.py at commit f449972, before any result)
ugs_event, 120 sampled configs: best under duty <= 0.25: UR_timely 0.795 (duty 0.218).
Legacy `event` reached 0.838 at duty 0.236; `fixed_threshold` 0.797 at 0.237. Gate B failed.
Diagnosis (wake audit, same validation runs): wakes that only re-confirmed an already
detected track: ugs_event 68 % (clean) / 62 % (noisy); event 41 % / 65 %;
fixed_threshold 57 % / 51 %. Cause: confirmed regions refreshed every dt_track = 1 s;
the track-level metric gives no credit for refreshing a known track.
Files: results/r3/tuning/iter1/.

## Iteration 2 (grid declared here, after iteration 1; development decision on validation data)
dt_track in {1000, 3000, 6000, 12000} ms (was 500-2000), k_retry in {2, 3, 5}, dt_retry in {200, 300, 500},
z0 in {0.5, 1, 2}, a_on in {4.5, 5, 6}, awake_factor in {0.5, 1}. 120 sampled of 648.
The baselines keep their iteration-1 grids (full factorial where <= 120 configs).
Result: best UR_timely 0.795 at duty 0.218 (unchanged; optimizer again chose dt_track = 1000). Files: iter2/.
Wake audit (clean+noisy, 3 seeds): 68 % of ugs wakes on clean video re-confirm known tracks, yet
ugs finds 111 new tracks vs 57 for `event` there. Per-scenario view of the iteration-1 point
(duty / UR_timely): clean ugs 0.248 / 0.910 (UR_track 0.989) vs motion_only 0.199 / 0.774,
mog2 0.230 / 0.774, robust 0.280 / 0.852, event 0.052 / 0.677;
noisy ugs 0.208 / 0.702 vs event 0.289 / 0.901, fixed 0.255 / 0.802.
Noisy diagnosis (segment 0006): 43 of 182 frames BELOW_THRESHOLD - low-contrast frames drain the
evidence accumulator below the release level mid-object.

## Iteration 3 (grid declared here, after iteration 2)
Full factorial (128): ugs_rho {0.7, 0.85}, ugs_a_off {1, 2}, ugs_a_on {4.5, 6}, ugs_z0 {0.5, 1},
ugs_dt_retry_ms {300, 500}, ugs_k_retry {3, 5}, ugs_dt_track_ms {1000, 3000}.
Result: best UR_timely 0.817 at duty 0.245 (noisy-only 0.784); selected rho 0.85, a_off 1, a_on 4.5, z0 0.5,
dt_retry 500, k_retry 5, dt_track 1000. Files: iter3/. Scheduler iteration stopped here (3 rounds, all disclosed).
