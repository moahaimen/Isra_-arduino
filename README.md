# Secure Dual-Core Event-Triggered Object Detection for Always-On Edge Vision

A simulation-first research study of an event-triggered vision pipeline for
the Arduino Portenta H7 (STM32H747): a low-power **M4 watcher** scores cheap
sensing features and passes candidate events through an **algorithmic
security gate** before waking the **M7 detector**, which runs a two-stage
detector with early exit and goes back to sleep.

> **Status: simulation only.** No physical Portenta measurements have been
> made. All energy figures are **modeled energy** computed from uncalibrated
> power assumptions (`config/power_model.json`, `calibrated: false`). Detector
> quality is a synthetic distribution, so no mAP is reported. See
> `docs/HARDWARE_VALIDATION_PLAN.md` for what must be measured before any
> physical claim.

## Layout

| path | contents |
|---|---|
| `simulation/` | C++17 discrete-event simulator: workload generator, watcher, security gate, detector backends, RPC model, energy model, logging |
| `firmware/` | Portenta sketches (M4 watcher, M7 detector) sharing the watcher and security headers with the simulator, plus a host check with mocked Arduino APIs |
| `config/` | default parameters and power model |
| `scripts/` | campaign runners (main, ablation, sensitivity), metrics, validation, statistics, figures, report, scientific audit |
| `tests/` | C++ unit tests and Python integration tests |
| `results/campaigns/` | committed campaign outputs (aggregates, tables, figures, report, audit); raw runs are archived outside git |
| `docs/` | method, protocol, energy model, threat model, reproducibility, scientific validation, hardware plan |

## Quick start

```bash
pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
bash tests/run_tests.sh

# one run
./build/edge_sim --scenario trigger_spam --mode secure --seed 1 --seconds 600 --out-dir /tmp/run1

# the full study (all campaigns, report, audit)
bash scripts/reproduce_all.sh
```

Six operating modes are compared on identical workloads: `always_on`,
`motion_only`, `fixed_threshold`, `event`, `event_no_early_exit`, `secure`;
across eight scenarios: `quiet`, `normal`, `busy`, `burst`, `noisy`,
`trigger_spam`, `replay`, `mixed`. Run `./build/edge_sim --help` for every
option, including the ablation switches.

## Documentation

* `docs/SIMULATION_BASELINE.md`: audit of the starting repository.
* `docs/SIMULATION_METHOD.md`: model, equations, parameters, limitations.
* `docs/EXPERIMENT_PROTOCOL.md`: design, statistics, test mapping.
* `docs/ENERGY_MODEL.md`, `docs/THREAT_MODEL.md`.
* `docs/REPRODUCIBILITY.md`: commands, determinism, what is stored where.
* `docs/SCIENTIFIC_VALIDATION.md`: every validity check and its result, and
  the known weaknesses of the method.
* `docs/HARDWARE_VALIDATION_PLAN.md`: measurements needed for calibration.
* `results/campaigns/main_*/RESULTS_SUMMARY.md`: results tables A–G.
