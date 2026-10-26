**Table 3.** Simulation and validation protocol.

| Item | Setting |
|---|---|
| Simulator domains | Behavioral discrete-time model; ngspice per-sample netlist of the same circuit |
| Dataset seeds | 20261026, 20261027, 20261028 (3 seeds, unseen before the protocol freeze) |
| Conditions per seed | 350 operating conditions × 9 fault classes |
| Train / validation / test split | 222 / 40 / 88 conditions per seed; overlap 0 |
| Test records per test cell | 792 (88 conditions × 9 classes) |
| Edge phases ψ (test) | 0, 0.25, 0.5, 0.75, 0.999 (5 phases); training ψ ~ U[0,1) for randomized arms |
| Reference amplitudes | Behavioral ×0.8, ×0.9, ×1, ×1.1, ×1.2; ngspice ×0.8, ×1, ×1.2 |
| Monitor gain-error bound E | 0%, ±1%, ±2%, ±5% (matched training) and known reference |
| Component tolerances | AFE gain ±5%, AFE tau ±10%, ADC gain ±2%, ADC offset ±10 mV, sensor baseline ±5% (uniform per sample) |
| Noise | ADC noise 2.5 mV rms; ngspice adds 0.5 mV rms amplifier-input noise and 0.5 mV rms on each reference rail |
| Quantization | 12-bit ADC over 0-3.3 V |
| ngspice runs | 13,878 per seed; 41,634 in total |
| Initializations | Two initialization seeds per model, averaged |
| Primary metric | Layer macro-F1 (4 classes); also fault macro-F1 (9 classes), balanced accuracy, per-class recall |
| Statistics | Paired condition-level cluster bootstrap, 5000 resamples per seed; pooled CI of the mean of the three per-seed differences |
| Pre-registration | Protocol, descriptors, arms, thresholds and decision rule frozen before validation data (source hashes recorded) |

*Sources: seed_*/meta.json, PROTOCOL_PHASE_ROBUST_FROZEN.md, paper_package/PAPER_TABLES.csv (T1).*
