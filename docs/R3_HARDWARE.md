# R3 minimal Portenta H7 validation package (prepared, NOT executed)

Nothing in this document has been measured. Simulation is the main study; the hardware experiment
exists only to replace the assumed constants (`config/power_model.json`, `calibrated: false`; M7
timing assumptions) and to check that the M4 code runs at 10 Hz. Base procedure and instrument list:
`docs/HARDWARE_MINIMAL_R2.md`; R3 additions below.

## Code

* M4: `firmware/m4_watcher_r3/m4_watcher_r3.ino` (UGS scheduler + temporal-context gate, closed loop through the
  RPC return value). Host-checked, not board-compiled: `firmware/host_check_r3.cpp`.
* M7: `firmware/m7_detector/m7_detector.ino` must return the 12x4 cell mask of the boxes above the detection
  threshold (R3 closed loop); detector = fully trained INT8 TinyissimoYOLO if it fits
  (`scripts/detector/tinyissimo/train_full_gpu.sh` -> `evaluate.py --precision int8` -> TFLite-Micro/X-CUBE-AI export; the
  export step is not implemented in this repository). Three-tile inference (as simulated) multiplies the per-frame
  cost by 3; the on-board cost of tiling must be measured.
* Frozen parameters: none yet (R3 is not frozen); the sketch uses the default structs.

## Measurements (each yields a CSV row per trial for `scripts/import_hardware_measurements.py`)

| # | quantity | method | replaces |
|---|---|---|---|
| 1 | M4 monitoring power | M7 in stop mode, M4 running the R3 loop on the stored trace, mean current over 60 s, 3 repeats | `M4_MONITOR` |
| 2 | M4 feature + decision time and power | PIN_FEATURE_MARK window, >= 1,000 frames; report mean, p95, MAX (worst path) | `m4_process_ms`, `M4_PROCESS`, `security_process_ms`, `SECURITY_PROCESSING` |
| 3 | M7 sleep power | stop mode, M4 idle | `M7_SLEEP` |
| 4 | M7 wake latency and wake transient | RPC edge -> first instruction; current integral of the wake window, >= 500 wakes | `m7_wakeup_ms`, `M7_WAKEUP` |
| 5 | RPC latency | GPIO before `RPC.call` -> handler entry; result return, >= 1,000 calls | `rpc_latency_ms`, `rpc_jitter_ms` |
| 6 | M7 inference power and latency | per tile / per frame (3 tiles), stage 1 and stage 2, >= 1,000 frames | `M7_INFERENCE`, `M7_SECOND_PASS`, `inference_ms`, `second_pass_cost_ms` |
| 7 | post-processing | NMS over merged tiles | `postprocess_*` |
| 8 | M4 memory | linker map / `arm-none-eabi-size` of the real build; stack high-water mark | complexity table (docs/R3_COMPLEXITY.md) |
| 9 | end-to-end energy of one fixed trace | integrate V x I over the trace (e.g. segment `mixed`, seed 1), 10 repetitions; compare with the simulator run re-parameterised from 1-7 | validation of modeled energy / duty |

Acceptance (set now, before measuring): simulated energy and duty of the fixed trace, re-run with the
calibrated parameters, must be within the 95 % interval of measurement 9 (or +-10 % if narrower);
and the M4 per-frame worst-case time (measurement 2) must be below the 100 ms frame period with margin;
otherwise the energy model is reported as not validated / the M4 design as not real-time feasible.

## Importer

`scripts/import_hardware_measurements.py measurements.csv --out config/power_model_calibrated.json
--timing-out config/timing_calibrated.json`. Columns: state, voltage, current, duration, trial
(+ board_id, instrument, date). It refuses to overwrite `config/power_model.json`, marks states without
measurements as assumptions and sets `calibrated: true` only when every state is measured. Tested on a
synthetic fixture (`tests/test_r3.py::Importer`), which is NOT a measurement.
