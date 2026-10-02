# R3.1 Gate C (preliminary) — security with availability preserved (KITTI validation, legacy event watcher at its duty ≤ 0.25 point)

Scope: KITTI validation, seeds 1001–1003, `scripts/r3_1/exp_security.py`; summary `results/r3_1/validation/security_kitti_val_summary.csv`.
Watcher: legacy `event` trigger (threshold 0.25, cooldown 2 s, gain 1.0 — the Pareto point of Gate B, chosen *before* any attack was run).
Defences compared on identical workloads: none; plain global token bucket (cap 10, 1/s; and tight cap 5, 0.3/s); R3 gate (replay + budget);
R3.1 gate (+ one-block shift tolerance); legacy R1 `secure`. MEVA, per-content/novelty comparisons with the UGS watcher, shifted-replay
variants 20–25 and recovery-time analysis are **not done yet**.

| mode | clean duty | spam ×16 duty | spam ×16 energy/min (clean 8152 mJ) | malicious wake-time share @×16 | SUR spam×0.5…16 | FRR clean/noisy |
|---|---|---|---|---|---|---|
| none | 0.166 | 0.26 | 10466 | 0.63 | ≥1.00 | 0 |
| plain bucket | 0.166 | 0.26 | 10466 | 0.63 | ≥1.00 | 0 / 0 |
| tight bucket (5, 0.3/s) | 0.166 | 0.26 | 10466 | — | ≥1.00 | 0 / 0.031 |
| R3 gate | 0.166 | 0.24 | 9955 | 0.60 | ≥1.00 | 0 |
| R3.1 gate (shift tol) | = R3 gate | = R3 gate | = R3 gate | = R3 gate | = R3 gate | 0 |
| legacy secure (R1) | 0.012 | 0.01 | — | — | ~1–3 (meaningless) | **0.92–0.94** |

Replay (exact / perturbed / mixed) attack success: none 0.041 / 0.063 / 0.119 → R3 gate 0.000 / 0.028 / 0.073; plain bucket = none.

## Findings (honest)
1. **The attack barely hurts this watcher.** A global 2 s cooldown already caps wake rate: spam ×16 raises duty from 0.17 to 0.26 and energy by 28 %
   (+2.3 J/min); timely recall under attack does *not* fall (SUR ≥ 1: spam wakes also happen to see real objects). SUR therefore does not
   discriminate defences here, and no SUR improvement can be claimed.
2. **A plain global token bucket does nothing in this setting** (its rate never binds below the cooldown rate); a tight bucket binds only on noisy
   legitimate traffic (FRR 0.031) and still doesn't cut spam wakes. Same result as the unprotected watcher.
3. **The content-aware gate gives a small, real effect**: replay attack success 0.041→0.000 (exact), 0.063→0.028 (perturbed), 0.119→0.073 (mixed);
   spam ×16 energy −4.9 %. FRR 0 on clean/noisy. The one-block shift tolerance changed nothing with the existing ±3–4 px variants
   (identical results) — the dedicated shifted/crop variants (20–25) are still needed before any claim on shifted replay (O4 open).
4. **Legacy R1 `secure` destroys availability** (FRR ≈ 0.92 on legitimate traffic); it is kept as a negative baseline.
5. Per-content bucket and reserved novelty budget need the UGS watcher's regions; with the legacy watcher they are inert, so **O3 (trigger-spam defence
   beyond cooldown) is not demonstrated**. Given Gate B (UGS scheduler loses to the event trigger), the plausible honest claim is
   "a cooldown-limited event trigger is already robust to trigger spam in energy/utility terms; content-aware replay gating adds a modest reduction in
   replay success without hurting FRR", pending MEVA and the shifted-replay test.
