# CAGE C1 attack kill test — result: **NO-GO**

Setup (`scripts/cage/c1_attack_kill.py`, results `results/cage/c1_attack_kill.csv`): 7 KITTI validation segments, identical real-frame bank, 10 fps, attacker controls the whole stream (upper bound on attacker time share), victim = legacy event trigger (threshold 0.25) with a 2 s (and 0.5 s) cooldown, 3-tile cascade, modeled energy (assumed power model, host-simulated timing). Attackers only *select and order natural frames/variants*; no adversarial perturbation was crafted, so this does **not** bound what crafted inputs could do. Single seed (1001), one run — a kill test, not a significance test.

| victim | attack | wake req/s | M7 busy ms/request | stage-2 rate | duty | energy J/min | CEAF |
|---|---|---|---|---|---|---|---|
| cooldown 2 s | benign | 0.35 | 474 | 0.14 | 0.16 | 8.1 | 1.00 |
| | wake-only | 0.53 | 463 | 0.11 | 0.25 | 10.1 | 1.25 |
| | inference-only | 0.00 | – | – | 0 | 4.1* | 0.51* |
| | naive wake+inference | 0.54 | 679 | 0.72 | 0.36 | 12.9 | **1.59** |
| | **joint cross-stage** | 0.51 | 670 | 0.70 | 0.34 | 12.3 | **1.52** |
| cooldown 0.5 s | benign | 1.18 | 501 | 0.20 | 0.58 | 18.2 | 1.00 |
| | wake-only | 2.00 | 464 | 0.10 | 0.91 | 26.2 | 1.44 |
| | naive | 2.01 | 563 | 0.38 | 0.96 | 27.6 | 1.52 |
| | joint | 1.75 | 633 | 0.58 | 0.91 | 26.3 | 1.45 |

*inference-only never wakes the M7 (a static frame produces no watcher event); its energy is the M4-only floor, below the benign scene.

**Cross-stage gain = CEAF(joint) / best baseline = 0.955 (2 s) and 0.954 (0.5 s) — target ≥ 1.5. The joint attack is not better than the naive combination (≈ 4–5 % worse), so there is no evidence of a cross-stage effect.**
Why (from the table): the cooldown fixes the wake rate; the only extra lever is cost per wake, which the natural-frame pool raises by ≤ 1.45× (463 → 670 ms) and the naive interleave already captures (stage-2 rate 0.72 vs 0.70). Making every change *also* expensive does not add anything because the interleaved cheap flicker frames wake the watcher just as well.
Caveats that keep this from being a refutation of the idea: natural frames only (crafted inputs could raise stage-2 rate to 1.0 and candidate count, but the stage-2 rate here is already 0.7); a single victim design; tiled stage-1 cost is input-independent in this simulator (cost variation comes only from stage-2 and box count), which structurally limits input-dependent amplification to ≈ 1.5–2×; no on-device measurements.
**Decision: NO-GO for the cross-stage attack as specified; C2 (CAGE defense) is not executed.** No tuning was done to change this.
