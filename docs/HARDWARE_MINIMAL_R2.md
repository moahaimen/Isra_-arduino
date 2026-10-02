# Minimal Portenta H7 experiment for calibrating the R2 simulator

Simulation remains the primary method. This experiment only supplies the
physical constants that the simulator currently ASSUMES. Nothing listed
here has been measured yet; every value in `config/power_model.json` and the
M7 timing parameters remain `calibrated: false` until this is done.

## Hardware

* Arduino Portenta H7 (STM32H747: M7 @ 480 MHz, M4 @ 240 MHz) and, for the
  camera-front-end measurement only, the Portenta Vision Shield (HM01B0).
* Power: Nordic PPK2 or Joulescope JS220 on the board supply (>= 100 kHz),
  logic analyser (>= 10 MHz) on the GPIO markers.

## Firmware

* M4: `firmware/m4_watcher_r2/m4_watcher_r2.ino`. Same C++ headers as the
  simulator (`frame_features.h` float variant, `robust_watcher.h`,
  `robust_gate.h`), parameters from `results/r2/frozen_params.json`. GPIO
  markers: PIN_FEATURE_MARK (feature extraction + decision), PIN_TRIGGER_MARK
  (accepted request -> RPC).
* M7: `firmware/m7_detector/m7_detector.ino` with the selected detector
  linked in (TinyissimoYOLO INT8 via TFLite Micro / X-CUBE-AI when the trained
  model is exported, see `scripts/detector/tinyissimo/`), PIN_ACTIVE_MARK high
  while awake.
* `firmware/host_check_r2.cpp` (run by `tests/run_tests.sh`) compiles the M4
  loop on a PC and reports static memory: frame-feature state 76.8 KB (float),
  robust watcher 1.5 KB, gate with a 128-entry history 20.9 KB.

## Fixed trace for the end-to-end check

Store the frames of ONE R2 test workload (e.g. segment 0015_0090, scenario
`mixed`, seed 1: 286 frames, 96x32 + 17x16 bytes each = 0.86 MB) in QSPI
flash and feed them at 10 Hz (`FRAME_SOURCE_TRACE`). The M4 then sees exactly
the frames the simulator saw, so the accepted-request sequence must be
identical to the simulator's (`observations.csv` of that run). Repeat 10 x.

## Measurements and the parameter each one calibrates

| # | quantity | how | replaces |
|---|---|---|---|
| 1 | M4 monitoring power | M7 in stop mode, M4 running the R2 loop on the trace, mean current over 60 s | `M4_MONITOR` |
| 2 | M4 feature + decision time and power | PIN_FEATURE_MARK window, 1000 frames | `m4_process_ms`, `M4_PROCESS`, `SECURITY_PROCESSING`, `security_process_ms` |
| 3 | M7 sleep power | M7 in stop mode, M4 idle | `M7_SLEEP` |
| 4 | M7 wake latency | RPC interrupt edge -> first instruction after wake, 500 wakes | `m7_wakeup_ms` |
| 5 | RPC latency | GPIO before `RPC.call` -> handler entry, 1000 calls | `rpc_latency_ms`, `rpc_jitter_ms` |
| 6 | M7 inference power | PIN_ACTIVE_MARK window, current integral | `M7_INFERENCE`, `M7_SECOND_PASS`, `M7_POSTPROCESS` |
| 7 | detector latency on the M7 | micros() around stage 1 / stage 2 / NMS, 1000 frames | `inference_ms`, `inference_sigma`, `second_pass_cost_ms`, `postprocess_*` |
| 8 | end-to-end energy of the fixed trace | integrate V x I over the 28.6 s trace, 10 repetitions | validation of the modeled energy of that run |

Acceptance: the simulated energy and duty cycle of the fixed trace, re-run
with the calibrated parameters, must agree with measurement 8 within the
measurement's 95 % interval (+-10 % if the interval is narrower); otherwise
the energy model is reported as not validated.

## What will still be simulated afterwards

Attack and noise overlays, the replay/spam threat model and all campaign
statistics remain simulation; only the physical constants above become
measured.
