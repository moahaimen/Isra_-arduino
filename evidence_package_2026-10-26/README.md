# Active Self-Diagnosing Mixed-Signal Sensor Interface

This is the new simulation project for the electronic-sensors direction. It
models a sensor-to-ADC chain and tests whether a small, bounded diagnostic
stimulus helps a neural classifier distinguish faults in the sensor, analog
front-end (AFE), and ADC.

## Scope of the first feasibility test

The first run is deliberately small and behavioral. It is not yet the final
SPICE experiment. It contains:

- a physical sensor signal with operating-condition variation;
- sensor faults (bias, gain, and excess noise);
- an instrumentation amplifier/low-pass AFE;
- AFE offset and bandwidth faults;
- ADC gain and offset faults, quantization, and noise;
- a reference-path pulse injected after the sensor and before the AFE;
- an optional second reference pulse injected between the AFE and ADC;
- passive, single-point active, and two-point active MLP classifiers;
- a scene/operating-condition-disjoint test split;
- macro-F1, accuracy, per-class recall, confusion matrices, and severity error.

The first single-point stimulus is injected after the sensor so that its
response is informative about the AFE/ADC path while the passive signal remains
informative about the physical sensor. Because a single pre-ADC stimulus cannot
uniquely separate AFE gain/offset from ADC gain/offset, the simulator also
contains a two-point diagnostic path: a known two-level reference temporarily
replaces the sensor at the AFE input, and a second known two-level reference
bypasses the AFE at the ADC input. This is the revised electronic architecture
under test.

The proposed paper contribution is the identifiability-constrained two-point
self-test, followed by a physics-guided temporal classifier. The two reference
paths are not an energy-management or power-converter contribution: they are
electronic test/multiplexer paths that make internal sensor-interface faults
observable.

## Run on macOS or Linux

```bash
cd active_sensor_diagnosis
python3 -m src.run_feasibility --samples-per-class 350 --seed 20261014
```

The script uses NumPy, SciPy, pandas, scikit-learn, and Matplotlib. It does not
require MATLAB, a physical board, or PyTorch for this first feasibility gate.

## Stage 2 validation

```bash
python3 -m src.stage2_validation \
  --samples-per-class 180 \
  --seeds 20261014,20261015,20261016 \
  --output stage2_results
```

This produces the multi-seed comparison, held-out ADC-noise shift, CSV table,
and a cost/F1 figure. The exploratory adaptive selector can be run separately:

```bash
python3 -m src.run_adaptive --samples-per-class 180 --seed 20261014
```

Its current result is intentionally treated as an ablation; because passive
probabilities are poorly calibrated, it usually chooses the two-point test.

## Optional publication model

`src/tcn_model.py` and `src/run_tcn.py` contain a causal TCN with a physics
descriptor branch and multi-task layer/fault/severity/transfer-parameter heads.
They require PyTorch, but the rest of the simulator does not:

```bash
python3 -m src.run_tcn --samples-per-class 350 --epochs 40
```

When PyTorch is absent, the command records `SKIPPED` rather than making the
feasibility pipeline fail.

## Interpretation gate

Continue to the SPICE model and adaptive-stimulus stage only if the active
physics-guided model shows a meaningful macro-F1 improvement over the passive
baseline and retains class-wise recall under unseen operating conditions. The
first run is a feasibility result, not a publication result.
