# C1.5 report — measured host forward vs NMS cost of the real Tinyissimo checkpoint

**Status: MEASURED, HOST CPU ONLY (1 thread). Not Portenta timing, not energy.**
* Checkpoint: `/home/claude/data_r3/tinyissimo_kitti/tiles_e20/weights/best.pt`, SHA-256 `047b09fa8bbc7d06aae161f1f69e5b33e31754e8590913f82938ea4223ccec88` (R3 KITTI-tile fine-tune, 20 epochs, CPU-trained; an *inadequate-accuracy* detector, used here only as a fixed compute workload). Not retrained.
* Images: 300 real KITTI tiles from the **detector-validation sequences 0013/0018** (`kitti_tiles/images/val`; locked test never touched): the 100 tiles with the most GT boxes (4–5 boxes) + 200 random others (seed 0). Input fixed at 256×256, preprocessing/file I/O excluded from timings. 5 timed repeats per image after 5 warm-ups; per-image median over repeats used below. Within-image repeat CV ≈ 3.5–5 % (host noise).
* Script `scripts/cage/c15_tinyissimo_profile.py` (smoke-tested on one image first; ran without modification: raw layout `[B,4+nc,N]` matched). Data: `results/cage/c15/*.csv`, `*.summary.json`, `c15_summary_by_conf.csv`.
* "Controlled candidate amplification" was done **only as a benign workload parameter sweep on the same natural images**: lowering the confidence threshold (0.25→0.001) feeds more candidates into NMS. No inputs were modified or crafted.

| conf | candidates med / p95 / max | total ms med / p95 / p99 / max | forward ms med | NMS ms med / p95 / max | NMS share (med) | paired NMS ratio vs 0.25 | paired total ratio |
|---|---|---|---|---|---|---|---|
| 0.25 (natural) | 0 / 30 / 34 | 13.1 / 16.6 / 19.4 / 30.7 | 12.9 | 0.12 / 0.30 / 0.40 | 0.8 % | 1.00 | 1.00 |
| 0.10 | 2.5 / 41 / 48 | 12.8 / 17.0 / 19.1 / 20.4 | 12.6 | 0.24 / 0.32 / 0.41 | 1.8 % | 1.04 | 0.98 |
| 0.05 | 6 / 51 / 56 | 13.3 / 16.8 / 19.3 / 20.3 | 13.1 | 0.24 / 0.31 / 0.39 | 1.8 % | 1.04 | 1.01 |
| 0.01 | 22.5 / 73 / 84 | 13.2 / 16.8 / 20.1 / 23.0 | 12.9 | 0.25 / 0.32 / 0.45 | 1.9 % | 1.13 | 1.01 |
| 0.001 | 79.5 / 136 / 199 | 12.9 / 16.3 / 19.6 / 21.2 | 12.6 | 0.26 / 0.35 / 0.49 | 2.0 % | 1.75 | 0.99 |

## Findings
1. **Forward pass dominates**: ≥ 98 % of total time (≈ 12.9 ms of ≈ 13.1 ms); it is essentially input-independent (corr(candidates, forward) = 0.16).
2. **NMS cost does scale with candidates** (corr 0.55; 10 images with ≈ 170 candidates: 0.31 ms vs 0.10 ms for 0 candidates; paired NMS ratio 1.75× at 79 median candidates) but is **≤ 0.5 ms absolute (≤ 2 % of total)**, so the *total* paired amplification is ≈ 1.0× (0.98–1.01).
3. Natural-image total-latency spread (max/median up to 2.3×, p99/median 1.5×) is dominated by host scheduling noise (single maxima, 30.7 ms at conf 0.25, not reproduced in the other sweeps), not by candidate count.
**Measured candidate-dependent amplification of this detector's total processing time: ≈ 1.0× (NMS-only up to 1.75× on a 0.1–0.5 ms term).**

## Limitations
Host CPU, 256×256 single tile, PyTorch/Ultralytics NMS (not the MCU post-processing; MCU NMS implementation and memory limits may differ); candidates counted by confidence filter (proxy, not NMS comparisons); at most 199 candidates reached (Ultralytics' pre-NMS cap 30,000 was never approached); EfficientDet Lite0/Lite2 cost (which the C1 simulator used for stage 2) was **not** measured here, so this says nothing about the cascade's stage-2 variation; no adversarial or crafted inputs were generated or tested; no energy.

## Is another C1 experiment justified?
**Not on candidate/NMS amplification for this detector:** the measured input-dependent term is ≤ 2 % of processing time, far below what a ≥ 1.5× cross-stage gain would need. The C1 NO-GO is therefore *reinforced* for the Tinyissimo-style single-stage detector. The only input-dependent cost that C1 found (stage-2 invocation, ≈ 2–3× per activation in the cascade) comes from the cascade's confidence-gated second stage, which was modeled, not measured; a further experiment would first need measured Lite0 vs Lite2 latencies for stage-1-ambiguous vs confident frames on the target (ideally Portenta). No such experiment is run here.
