# Detector modes: resources and deployability

All four modes use the same EfficientDet-Lite0 INT8 weights; mode switching changes only the input crop/resize (no weight reload,
same arena), so its overhead is modelled as 0 (primary) or 0.25 invocation units (sensitivity). Source: `mode_resources.json`
(`scripts/mode_feasibility.py`), `run_meta_*.json`, `timing.csv` inside `03_oracle_gate/mode_outputs/`.

| mode | input pixels | invocations | GMAC | weights | peak activations (lower bound) | host invoke ms, median / P95 (1 thread, NOT Cortex-M7) | candidate boxes ≥ 0.45 per frame (test, mean) |
|---|---|---|---|---|---|---|---|
| SKIP | — | 0 | 0 | — | — | 0 | — |
| LOW | full 1242×375 frame squashed to 320×320 | 1 | 0.97 | 4.1 MB | 3.07 MB (CNN), 8.7 MB incl. 90-class decode | 19.9 / 28.3 | 0.49 |
| ROI_k | one ~456×375 tile → 320×320 | 1 | 0.97 | 4.1 MB | same | 20.2 / 26.6 | 1.14 / 1.99 / 1.66 (k = 0/1/2) |
| FULL | three tiles + NMS | 3 | 2.92 | 4.1 MB | same (tiles run sequentially) | ≈ 60 (3 × ROI) | 4.64 |

Peak activations are a tensor-liveness lower bound over the reference-kernel execution order (no fragmentation or scratch).

## STM32H747 / Portenta H7 check

* Internal SRAM ≈ 1.03 MB in total (largest contiguous block 512 KB AXI SRAM); internal flash 2 MB.
* Lite0 needs ≥ 3.07 MB activation memory and 4.1 MB weights → **nondeployable within internal memory, in every mode**.
* Portenta H7 adds 8 MB SDRAM and 16 MB QSPI flash, so an external-memory build is conceivable, but its latency is unmeasured and
  would be dominated by SDRAM bandwidth at ~1 GMAC per invocation. Not claimed.
* Consequence: the main **hardware-feasible** comparison has no detector with real mode-specific outputs. The only MCU-class detector
  tried in this project (TinyissimoYOLO) failed its accuracy gate in R3.
