# R3.1 diagnosis: why does the R3 scheduler need ≈ 0.66–0.79 M7 duty under corrected tiled cost?

Diagnosis only — **no parameter was tuned**. KITTI validation (7 groups × clean/noisy × seeds 1001–1003), R3 scheduler at its R3 validation-selected parameters, legacy event trigger at its Gate-B point,
real 3-tile cost vs a counterfactual single-tile cost (tile columns of `det.csv` set to 1; trigger timing can shift slightly because result latency feeds back).
Script `scripts/r3_1/exp_diagnose_duty.py`; tables `results/r3_1/validation/diag_duty_decomposition.csv`, `diag_duty_usefulness.csv`. Energy/timing are modeled/simulated, not Portenta measurements.

| quantity (3 tiles; clean / noisy) | R3 scheduler | legacy event trigger |
|---|---|---|
| (1) wake-request rate (RPC requests / s) | 1.58 / 1.44 | 0.35 / 0.52 |
| (2) M7 wakes per min (sleep→awake transitions) | 28 / 18 | 21 / 31 |
| (3) tile evaluations per activation (3 stage-1 tiles + 3 per stage-2) | 3.7 / 3.9 | 3.4 / 4.2 |
| (4) stage-2 activation rate | 24 % / 29 % | 14 % / 39 % |
| (5a) simulated M7 time per activation (stage1+stage2+post) | 515 / 532 ms | 482 / 565 ms |
| (5b) share of M7 active time: stage-1 inference / stage-2 / post / wake-up | 82 % / 15 % / 3 % / 0.2 % | 86 % / 9 % / 3.5 % / 0.6 % |
| (6) first-detection ("useful") share of activations | 0.23 / 0.27 | 0.69 / 0.61 |
| redundant-refresh share of activations | 0.65 / 0.62 | 0.15 / 0.08 |
| resulting M7 duty | **0.79 / 0.74** | 0.17 / 0.29 |

Identity check: duty ≈ request rate × time per activation (scheduler 1.58 × 0.515 = 0.81; event 0.35 × 0.482 = 0.17). The scheduler's wakes are few (28/min) only because its requests arrive back-to-back and the M7 stays awake (mean 1.7–2.5 s awake per wake).

Single-tile counterfactual (same trigger code): time per activation 186 / 190 ms (scheduler), 168 / 195 ms (event); duty 0.27 / 0.24 (scheduler) vs 0.06 / 0.10 (event). The 0.24–0.27 reproduces R3's reported scheduler duty (0.245), i.e. the R3 number was internally consistent with uncharged tiling.

## Conclusion: both, in a quantifiable split
* **Detector cost**: charging three tiles (+ the stage-2 tiles) multiplies the time per activation by ≈ 2.8× (186 → 515 ms). That alone takes the scheduler from ≈ 0.25 to ≈ 0.75 and takes even the event trigger from 0.06/0.10 to 0.17/0.29.
* **Scheduling**: independent of cost, the scheduler issues 3–4× more requests than the event trigger (1.4–1.6 vs 0.35–0.52 per s), 62–65 % of them redundant refreshes (vs 8–15 %), and only 23–27 % of its activations produce a first detection. With the corrected activation cost the budget (duty ≤ 0.25) implies ≤ ≈ 0.49 requests/s; the scheduler is ≈ 3× above that, the event trigger is below it.
* So 0.66–0.79 is **not** only the three-tile cost (the event trigger stays near the budget under the same cost) and **not** only poor scheduling (at single-tile cost the scheduler would sit at the budget edge). Both are required to explain it; the scheduler's design (periodic refresh of confirmed regions, retry of unverified regions) buys frame-level coverage (UR_frame 0.82) that the ≤ 0.25 duty budget cannot pay for under the three-tile detector.
No claim is made that a different scheduler could not meet the budget; none was tried (by instruction).
