# R3.1 security design: ablation and replay severity (KITTI validation only)

Scripts `scripts/r3_1/exp_security_ablation.py`, `exp_severity.py`; tables `results/r3_1/validation/security_ablation_kitti_val.csv`, `replay_severity_kitti_val.csv`.
Legacy event watcher, threshold 0.25; cooldown = its global 2 s cooldown; "rate" = global token bucket (capacity 10, 1/s); "replay" = stale-frame gate with gradient tolerance c = 0.5.
Pooled over 7 groups × seeds 1001–1003. Energy is modeled. **No claim is made that replay is solved**; absolute counts are small (see severity table).

## Ablation (is each mechanism independently useful?)
| config | FRR (clean+noisy) | clean timely recall | clean duty | replay exact | perturbed | mixed | shifted/crop | spam ×16 success | spam ×16 duty | spam ×16 energy J/min |
|---|---|---|---|---|---|---|---|---|---|---|
| none (no cooldown, no security) | 0 | 0.36 | 0.76 | 0.186 | 0.276 | 0.404 | 0.465 | 0.240 | 0.99 | 28.3 |
| cooldown only | 0 | 0.41 | 0.17 | 0.041 | 0.063 | 0.119 | 0.081 | 0.066 | 0.26 | 10.5 |
| rate limit only (no cooldown) | **0.79** | 0.39 | 0.61 | 0.099 | 0.203 | 0.394 | 0.326 | 0.184 | 0.81 | 23.9 |
| replay gate only (no cooldown) | 0.004 | 0.36 | 0.76 | 0.000 | 0.077 | 0.193 | 0.372 | 0.196 | 0.89 | 25.8 |
| cooldown + rate limit | 0 | 0.41 | 0.17 | 0.041 | 0.063 | 0.119 | 0.081 | 0.066 | 0.26 | 10.5 |
| **cooldown + replay gate** | 0.007 | 0.41 | 0.17 | 0.000 | 0.007 | 0.073 | 0.047 | 0.053 | 0.22 | 9.5 |
| full (cooldown + replay + rate + novelty reserve) | 0.007 | 0.41 | 0.17 | 0.000 | 0.007 | 0.073 | 0.047 | 0.053 | 0.22 | 9.5 |
| full with the R3 gate (no gradient tolerance) | 0 | 0.41 | 0.17 | 0.000 | 0.028 | 0.073 | 0.081 | 0.058 | 0.24 | 10.0 |

Findings
1. The **cooldown** carries almost all of the spam/energy protection: duty 0.99 → 0.26 and energy 28.3 → 10.5 J/min at spam ×16, and clean energy 22.7 → 8.2 J/min — it is also the *trigger* design (it lowers duty with no attack at all), not an attack-specific defence.
2. A **plain rate limiter alone** is harmful: it blocks 79 % of legitimate requests (FRR 0.79) because legitimate event traffic without the cooldown exceeds its rate, and it still leaves duty at 0.61. Behind the cooldown it is inert (identical to cooldown only).
3. The **replay gate** is the only independent contribution: with the cooldown it lowers replay success (exact 0.041→0, perturbed 0.063→0.007, mixed 0.119→0.073, shifted 0.081→0.047), spam ×16 energy by a further 9 % (10.5→9.5 J/min), at FRR 0.007. Without the cooldown it does not stop spam.
4. The **token bucket, novelty reserve, per-content bucket and block-shift search** add nothing measurable in this configuration (full ≡ cooldown + replay, to the digit) and are **demoted: not part of the defended design**. They remain as flags (off) for reproducibility of the R3.1 tests.
**Simplest defensible design: global cooldown + gradient-tolerant stale-frame (replay) gate.** The gradient tolerance is what matters for shifted replay (R3 gate: 0.081 vs 0.047).

## Replay success by transformation (frames that reached the M7 / replay frames; 3 seeds × 7 groups)
| variant | transformation | replay frames | started: cooldown only | cooldown + R3 gate | cooldown + gradient gate |
|---|---|---|---|---|---|
| 0 | exact | 172 | 7 | 0 | 0 |
| 1 | bright x0.85 | 39 | 3 | 0 | 1 |
| 2 | bright x1.15 | 37 | 3 | 2 | 1 |
| 3 | noise s6 | 33 | 1 | 0 | 0 |
| 4 | jpeg q40 | 27 | 2 | 0 | 0 |
| 5 | shift 3,2 px | 60 | 6 | 5 | 0 |
| 6 | bright+noise+jpeg | 30 | 1 | 0 | 0 |
| 7 | shift -4 px + noise | 60 | 2 | 1 | 0 |
| 20 | shift 10 px | 29 | 4 | 4 | 0 |
| 21 | shift 24,8 px | 26 | 2 | 2 | 1 |
| 22 | shift 48 px | 25 | 1 | 1 | 1 |
| 23 | crop 95% | 46 | 3 | 3 | 2 |
| 24 | crop 90% | 15 | 1 | 1 | 1 |
| 25 | shift24+crop95+gain+noise | 31 | 3 | 3 | 3 |

The gradient gate stops exact, photometric (brightness/noise/JPEG) and small-shift (≤ 10 px, 0.8 px at M4 resolution) replays almost completely, partially stops 24–48 px shifts and 95 %/90 % crops, and fails on the mixed transform (3/31, the same as no gate).
Overall 39 → 22 (R3 gate) → 10 started frames out of 630. Counts are small (1–7 frames per cell), so per-transformation differences are indicative only; the aggregate difference is not a significance test. The severity ordering (larger geometric change → weaker detection) is expected from the thumbnail comparison and was not tuned for. The variants 20–25 are synthesised from the 96×32 M4 input, not re-rendered full-resolution images.
Residual successes are mostly the first frames of a replay session (recognition latency) and stronger geometric changes. The attack model here is a single attacker class (replay of recorded frames, bounded transformations); an adaptive attacker who knows the gate (e.g. slowly drifting replays) was not evaluated.
