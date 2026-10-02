# R3.1 baseline: the R3 state this branch starts from (verified before any change)

Branch `research/q1-contribution-r3.1`, created from exactly `1526a52` (R3 checkpoint). R1, R2 and R3
files are not modified; R3.1 writes to `results/r3_1/`, `scripts/r3_1/`, `docs/R3_1_*`.

## Verification (2026-10-02, container restart, same disk)

| check | result |
|---|---|
| HEAD / tree | `1526a52`, clean; equals `origin/research/q1-contribution-r3` |
| tests (`tests/run_tests.sh`) | 223 C++ unit checks passed; firmware host checks R1, R2, R3 PASS; 54 Python tests OK |
| R3 gate reports | `docs/R3_GATE_A.md`, `R3_GATE_B.md`, `R3_GATE_C.md` present |
| locked split | `data/splits/r3_splits.json` SHA-256 verified against `r3_splits.sha256` |
| R3 test partition (723 frames, KITTI raw drives 17, 19, 29, 51, 57, 84) | never evaluated: no `raw/` image directory exists under the R3 data root, no R3 script ran with `--allow-test` |
| environment | 4 CPU cores, **no GPU**, 13 GB free disk |

## R3 validation findings carried forward (not rewritten)

**Gate A.** Tiling the 1242x375 frame into three near-square tiles removed most of the R2 detector-ceiling
problem: frame-level track-recall ceiling 0.33 (squashed) -> 0.984 (Lite0 tiles) / 1.000 (Lite2 tiles);
validation mAP50 0.688 (Lite0 tiled) and 0.760 (Lite2 tiled). The MCU-class detector remained inadequate:
TinyissimoYOLO after 30 CPU epochs reached validation mAP50 0.481 / track ceiling 0.869 (timely 0.574); +20 KITTI
CPU epochs made it worse (0.407 / 0.410). R3 test set untouched.

**Gate B.** Final pooled (clean+noisy) timely utility retention of the R3 scheduler 0.817 at duty 0.245; the legacy
`event` rule reached 0.838 at 0.236, fixed threshold 0.797, motion-only 0.795, MOG2 0.749, R2 robust 0.763.
R3 did NOT establish scheduler superiority. Per scenario: clean 0.910 (iteration-1 configuration, duty 0.248) vs
noisy 0.784; legacy event noisy 0.896. The R3 scheduler is not claimed to be superior.

**Gate C.** R3 security preserved legitimate availability: SUR 0.982, selected FRR 0.024 (R2 gate FRR 0.616,
R1 gate 0.879). Exact replay suppression strong (attack success 0.173 -> 0.027); perturbed 0.211 -> 0.106;
shifted replay weak (0.217 -> 0.178); trigger spam essentially unsolved (0.288 -> 0.284); FRR rose to 0.107 at spam x8.

## Known defects of the R3 evaluation (to be corrected in R3.1)

1. **Tiled inference was not charged correctly.** The R3 detector traces come from 3-tile Lite0 (stage 1) and
   3-tile Lite2 (stage 2) predictions, but the simulator charged the single-pass latencies
   (`inference_ms` 140 ms, `second_pass_cost_ms` 110 ms) per frame. R3 duty and modeled energy are therefore
   under-estimated for the tiled detector.
2. Scheduler parameters were selected on pooled validation data with three disclosed iterations on the same
   two scene groups; no held-out evaluation exists.
3. The validation scenes are object-dense, so avoiding useless wakes cannot be rewarded.
4. All hardware quantities (M4/M7 power, wake, RPC, inference timing) are simulated assumptions;
   no Portenta measurement exists. Host detector timing is host timing only.
