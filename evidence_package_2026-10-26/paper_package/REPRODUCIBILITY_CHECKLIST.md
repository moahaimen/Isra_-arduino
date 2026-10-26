# Reproducibility checklist

Generated 2026-10-14. Project root: `active_sensor_diagnosis/`. All commands run from the project root.

## Environment

| component | version |
|---|---|
| Python | 3.12.12 |
| NumPy | 2.2.6 |
| pandas | 2.3.3 |
| SciPy | 1.16.3 |
| scikit-learn | 1.7.2 |
| matplotlib | 3.10.7 |
| PyTorch (earlier TCN stages only) | 2.10.0 |
| ngspice | ** ngspice-47 : Circuit level simulation program |
| platform | macOS-27.0.1-arm64-arm-64bit |

## Stages, frozen protocols, seeds and commands

Each stage was frozen (protocol + SHA-256 of `src/*.py`) before its validation data were generated, and used new dataset seeds.

| stage | protocol / hashes | dataset seeds | commands (per seed, then summary) | outputs |
|---|---|---|---|---|
| SPICE netlist check | — | — | `python3 -m src.run_spice_validation --output spice_fixed` ; `python3 -m src.compare_spice --spice-dir spice_fixed` | `spice/`, `spice_fixed/` |
| TCN vs baseline | — | 20261014 | `python3 -m src.run_tcn_v2 --samples-per-class 350 --epochs 40 --seed 20261014` ; `python3 -m src.summarize_tcn_comparison` | `tcn_v2_results/`, `tcn_comparison/` |
| multi-seed (old descriptors) | `multiseed_results/PROTOCOL_FROZEN.md`, `source_hashes_at_freeze.txt` | 20261017–19 | `python3 -m src.run_multiseed --dataset-seed S` ; `python3 -m src.summarize_multiseed --n-boot 5000` ; `python3 -m src.build_multiseed_report` | `multiseed_results/`, `FINAL_MULTISEED_REPORT.md` |
| reference-v2 | `PROTOCOL_REFERENCE_V2_FROZEN.md`, `reference_v2_results/source_hashes_at_freeze.txt` | 20261020–22 | `python3 -m src.run_reference_v2 --dataset-seed S` ; `python3 -m src.summarize_reference_v2 --n-boot 5000` ; `python3 -m src.build_reference_v2_report` | `reference_v2_results/`, `FINAL_REFERENCE_V2_REPORT.md` |
| reference monitor + ngspice | `reference_monitor_final/PROTOCOL_REFERENCE_MONITOR_FROZEN.md`, `.../source_hashes_at_freeze.txt` | 20261023–25 | `python3 -m src.run_reference_monitor --dataset-seed S --workers 3` ; `python3 -m src.summarize_reference_monitor --n-boot 5000` ; `python3 -m src.build_reference_monitor_report` | `reference_monitor_final/` (decision REVISE) |
| **phase-robust (this paper)** | `phase_robust_final/PROTOCOL_PHASE_ROBUST_FROZEN.md`, `.../source_hashes_at_freeze.txt` | **20261026, 20261027, 20261028** | `python3 -m src.run_phase_robust --dataset-seed S --workers 3` ; `python3 -m src.summarize_phase_robust --n-boot 5000` ; `python3 -m src.build_phase_robust_report` | `phase_robust_final/` (decision GO) |
| paper package | — | — | `python3 -m src.build_paper_package` | `paper_package/` |

Development / debugging seeds (never used for validation decisions): 20261097 (phase-robust stage and paper illustrations), 20261098 (monitor stage diagnostics), 20261099 (reference-v2 guard check).

## Checks

- [x] Splits by operating condition; train/val/test condition counts 222/40/88 per seed; zero overlap asserted at run time (`seed_*/meta.json`).
- [x] Standardisation, early stopping, descriptor design, guard (30%), fit grid and thresholds fixed before validation; no test-set tuning.
- [x] Default behaviour of the simulator unchanged by the added options (`ref_scale`, tolerance scales, `ref_phase`): verified by SHA-256 of generated records (`multiseed_results/.simulate_regression_hash`).
- [x] Behavioral and ngspice samples paired (same conditions, faults, noise streams, tolerance and monitor draws).
- [x] Noise-free behavioral/ngspice agreement per phase 0.14–0.27 mV mean RMS (`paper_package/figure_data/dev_seed_verification.json`).
- [x] Paired condition-level cluster bootstrap, 5000 resamples; two initialisation seeds (11, 22) averaged.
- [x] Every manuscript number traceable (`NUMBER_PROVENANCE.csv`); every table cell traceable (`PAPER_TABLES.csv`).
- [x] Earlier failures kept and reported (multi-seed ROBUSTNESS FAILURE; monitor stage REVISE).
- [ ] Code and data deposited in a public repository with a DOI (to do).
- [ ] Independent re-run on a second machine (to do; ngspice and scikit-learn are deterministic for fixed seeds, the earlier PyTorch TCN runs were not bit-reproducible on CPU).

## Cost of a full re-run (phase-robust stage)

13,878 ngspice runs per seed, ≈908 s wall time per seed with 3 ngspice workers (three seeds were run in parallel); descriptor extraction 0.79 ms per record; MLP training about one second per model.
