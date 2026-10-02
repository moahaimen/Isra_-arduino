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

## R2: real-detector-trace study (this branch)

R2 keeps R1 unchanged as the archived synthetic baseline and adds a second
study built on REAL data: real pretrained detectors (EfficientDet-Lite0/Lite2,
SSD-MobileNetV2, TinyissimoYOLO trained here), standard pycocotools mAP,
watcher features computed from real KITTI frames, image-domain noise /
spam / replay overlays, a robust watcher and a diversity-aware security gate,
a MOG2 literature baseline, validation-only tuning and a pre-registered test
campaign. Timing and power remain simulated (calibration pending).

* Results: `results/r2/RESULTS_R2.md` (generated), detectors:
  `results/r2/DETECTORS.md`; honest audit: `docs/Q1_READINESS_R2.md`.
* Method: `docs/R2_METHOD.md`; plan: `docs/PREREGISTERED_R2_ANALYSIS.md`;
  hardware calibration: `docs/HARDWARE_MINIMAL_R2.md`.
* Reproduce: `bash scripts/r2/reproduce_r2.sh` (downloads data, builds the
  image bank, tunes on validation, runs the frozen test campaign).
* Headline (test split, 30 realizations): the robust watcher cuts M7 duty
  and modeled energy versus always-on (confirmed) and the R2 gate cuts the
  false-rejection rate of the legacy gate (0.27 vs 0.65 under spam x8,
  confirmed), but neither improves detection recall: the robust watcher is
  significantly WORSE than the legacy rule on the noisy scenario, and all
  methods are limited by the detector (always-on moving-track recall 0.28).

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
