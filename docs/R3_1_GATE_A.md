# R3.1 Gate A — detector ceiling, cost model and datasets

## A1 detector ceiling (O1) — **NOT RESOLVED (blocked: no GPU)**
See `docs/R3_1_GPU_AUDIT.md`. Numbers below are the R3 validation results (`results/r3/gate_a/detectors_validation.csv`, 61 moving tracks, KITTI validation sequences, tiled inference), unchanged:

| detector | role | mAP50 | track-recall ceiling | timely-recall ceiling |
|---|---|---|---|---|
| EfficientDet-Lite0 INT8, 3 tiles | MCU-class (stage 1 of the cascade) | 0.688 | 0.98 | 0.92 |
| EfficientDet-Lite2 INT8, 3 tiles | host reference (stage 2) | 0.760 | 1.00 | 0.90 |
| YOLOv8s COCO @1248 | host reference | 0.811 | 1.00 | 0.97 |
| TinyissimoYOLO VOC-30ep, 3 tiles | MCU target (CPU-trained) | 0.481 | 0.87 | 0.57 |
| TinyissimoYOLO KITTI-20ep fine-tune, 3 tiles | MCU target (CPU-trained) | 0.407 | 0.41 | 0.28 |

Reading: the *CPU-trained* TinyissimoYOLO checkpoints are inadequate (timely ceiling ≤ 0.57) and are **not** evidence about TinyissimoYOLO's real capability; the audited full recipe could not be run.
Whether the Lite0 INT8 tiled detector is "MCU-feasible" on the Portenta (latency/memory) is unmeasured. Gate A1 is therefore **not passed**.

## A2 cost model (O5) — passed
Tiled inference is now charged physically (`docs/R3_1_BASELINE.md`, commit 73ce38e): per-tile lognormal draws summed, merge cost per extra tile of every executed stage,
tiled always-on background frames, tests in `tests/test_r3_1.py` (6 tests). Consequence: R3's reported scheduler duty 0.245 was an artifact of uncharged tiling (same config → 0.715).
`tile_merge_ms` = 1.0 ms/extra tile is an **assumption**, not measured.

## A3 second dataset (partially complete)
MEVA (static surveillance cameras, many quiet periods), immutable camera-disjoint splits fixed before decoding any frame (`data/splits/r3_1_meva_splits.json` + `.sha256`); the 4 test clips are not downloaded.
No human boxes are available here → *detector-referenced* evaluation (YOLOv8s @1280 + IoU tracker, confirmed-track rule fixed in `scripts/r3_1/meva_reference.py`), which measures agreement with a stronger always-on detector, not annotation accuracy.
Licence not verified. MEVA reference tracks are still being computed (CPU-bound); MEVA results will be added to Gates B/C when available. If they cannot be completed, the paper must state that only one annotated temporal dataset (KITTI) was used.
