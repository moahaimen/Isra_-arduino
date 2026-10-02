# Hardware validation plan (future work, not performed)

No physical measurement has been made. This plan lists what must be measured
on an Arduino Portenta H7 to calibrate the simulator, and which simulator
parameter each measurement replaces. Until then every value below remains a
simulation assumption.

## Measurement setup (suggested)

* Portenta H7 (STM32H747, M7 @ 480 MHz, M4 @ 240 MHz) + Vision Shield camera.
* Power: a source-measure unit or a shunt + high-side current amplifier on the
  board supply (e.g. Nordic PPK2, Joulescope or Keysight N6705 with ≥ 100 kHz
  sampling), with the 3V3 rail isolated where possible to separate core and
  camera current.
* Timing: GPIO markers from the firmware skeletons (`firmware/`) on a logic
  analyser (≥ 10 MHz): M4 trigger mark (PIN_TRIGGER_MARK), M7 active mark
  (PIN_ACTIVE_MARK), plus per-stage `micros()` timestamps written to a RAM log.
* Same firmware decision logic as the simulator (`watcher.h`,
  `security_gate.h` are shared headers).

## Measurements → parameters

| quantity | method | calibrates | minimum repetitions |
|---|---|---|---|
| RPC latency (M4→M7 request) | GPIO toggle before `RPC.call` on M4 and at handler entry on M7 | `rpc_latency_ms`, `rpc_jitter_ms` (fit half-normal) | 1000 calls, 3 boards if available |
| M7 wake latency | GPIO edge from RPC interrupt to first instruction after stop-mode exit | `m7_wakeup_ms` | 500 wakes |
| stage-1 inference latency | `micros()` around inference for the chosen model and resolution | `inference_ms`, `inference_sigma` (log-normal fit) | 1000 frames over ≥ 3 scenes |
| second-pass latency | same, stage 2 | `second_pass_cost_ms` | 1000 frames |
| postprocessing time vs boxes | same, regress on box count | `postprocess_base_ms`, `postprocess_per_box_ms` | 500 frames |
| active duration per event | M7 active GPIO high time | validates the simulated wake→sleep sequence | 500 events |
| idle power (both cores idle) | current at steady state | `M4_IDLE`, baseline | 3 × 60 s |
| M4 monitoring power | M4 running the watcher loop, M7 asleep | `M4_MONITOR` (dominant term for event modes) | 3 × 60 s per sampling rate |
| M4 processing / security power | current during watcher and gate computation (GPIO-gated window) | `M4_PROCESS`, `SECURITY_PROCESSING`, `RPC_COMMUNICATION` | 1000 windows |
| M7 sleep power | M7 in stop mode | `M7_SLEEP` | 3 × 60 s |
| M7 wake-up power | current during the wake window | `M7_WAKEUP` | 500 wakes |
| M7 inference power | current during inference (incl. camera) | `M7_INFERENCE`, `M7_SECOND_PASS` | 1000 frames |
| M7 postprocess power | current in postprocess window | `M7_POSTPROCESS` | 500 frames |
| total energy | integrate current × voltage over a scripted replay of a workload trace (stimuli injected via GPIO/LED panel) | end-to-end check of E_total and duty cycle | ≥ 3 scenarios × 3 seeds × 10 min |
| detector quality | run the real detector on annotated frames; export `data/detector_traces` CSV with boxes | replaces `synthetic_distribution` by `trace_replay`; enables mAP | ≥ 500 annotated frames per class |

## Minimum experiment set

1. Component calibration: the rows above (power per state with the core
   held in that state; latencies with GPIO markers).
2. Model update: write measured values into `config/power_model.json`
   (`source: measured`, `calibrated: true`, with instrument, date, board id
   and uncertainty) and into a calibrated config JSON; re-run the campaigns.
3. End-to-end validation: replay at least 3 workload traces (normal,
   trigger_spam, replay) on hardware for 3 seeds each and compare measured
   energy, duty cycle and latency distributions with the simulator (report
   relative error and a Kolmogorov–Smirnov distance for latency).
4. Only after step 3 agrees within a pre-stated tolerance may energy results
   be described as calibrated estimates.

## Interfaces already in place

* `config/power_model.json` schema with `source` and `calibrated` fields.
* `--power-model`, timing parameters and `--detector-backend trace_replay`
  are CLI/config options; no code change is needed to calibrate.
* `firmware/` sketches mark trigger and active windows on GPIO and share the
  decision logic with the simulator; `firmware/host_check.cpp` checks that
  logic on a PC with mocked `millis()`/`delay()`/RPC.
