# 8. Discussion (draft)

The results support a specific, simulation-based claim: under the simulated conditions, a two-point electronic self-test with a monitored reference and phase-robust descriptors localizes AFE and ADC faults reproducibly under unseen operating conditions, ±20% reference-amplitude changes, monitor errors up to ±5%, component tolerances and arbitrary edge phase, in a behavioral and a circuit-level simulation domain.

**Why the two-point path matters.** One-point variants that observe only the AFE or only the ADC path were clearly worse than the two-point PRr classifier (Table 6), and the cross-confusion between AFE and ADC faults remained at or below 0.089 whenever the reference levels were known or monitored. This is consistent with the identifiability argument: the R2 window fixes the ADC transfer, so the R1 window can be attributed to the AFE.

**Why the monitor matters.** The no-monitor control (behavioral domain) shows that the two-point architecture is not sufficient on its own: a ±20% reference change that is not measured is read as an ADC gain/offset fault, AFE recall drops to 0.375 at ×1.2 and the layer macro-F1 falls to 0.237. Measuring the levels restores 0.643 (behavioral) and keeps the degradation at E = ±5% small (retention ≥ 0.924).

**What made the domain transfer work.** The earlier transfer failure (0.119) was traced to the sampling-phase convention of the reference edge. The ablation attributes the improvement mainly to the descriptors: replacing fixed-sample rise fractions by a whole-transient fit with a free edge time improved layer macro-F1 by +0.042 (behavioral) and +0.041 (ngspice), and once these descriptors are used, phase-randomized training adds no resolvable benefit (+0.000 [-0.005, +0.006], behavioral). In the behavioral domain, phase randomization alone helps the fixed-sample descriptors (R1r − R1: +0.030) but leaves a phase range of 0.025, whereas PRr stays at 0.006. Because the behavioral and ngspice models are both first-order RC plus affine-ADC models that agree to 0.14–0.27 mV without extra noise, a near-zero transfer loss is expected once the timing convention is handled; it does not show that hardware would behave the same.

**Primary versus secondary method.** The mixed-domain variant PRrM was more accurate (+0.017 behavioral, +0.014 ngspice relative to PRr), but it uses circuit-level training data and was not the pre-registered primary method; it is reported as a secondary result.

**Absolute performance.** A nominal layer macro-F1 of 0.659 is modest. The weak classes—healthy records, sensor bias, sensor gain and ADC clipping—are unchanged by the phase-robust revision. The self-test is therefore best viewed as an AFE/ADC fault-localization aid, not as a healthy/faulty detector.

# 9. Limitations (draft)

1. **Simulation only.** No hardware was built or measured. Both domains are first-order RC plus affine-ADC models written by the same authors; the ngspice test probes extra noise, tolerances, switch on/off resistance and circuit-level edge handling, not unmodelled effects such as charge injection, amplifier bandwidth and slew, reference settling, leakage or temperature.
2. **Reference monitor.** The monitor is simulated with a common gain error, white noise and a trimmed offset; its nonlinearity, offset drift and own failures were not modelled, and matched training assumes the error bound is known.
3. **Phase model.** All edges share one phase that is constant within a record; edge jitter, phase drift and different phases for the two references were not tested.
4. **Absolute accuracy.** Healthy-layer recall is 0.142 (behavioral); sensor bias/gain and ADC clipping remain weak.
5. **Statistical scope.** Three dataset seeds with 88 test conditions each; intervals resample conditions, not datasets. The ngspice grid has three amplitudes; the no-monitor control was run in the behavioral domain only.
6. **No energy, power, area or embedded-timing measurement**; timings are desktop Python measurements.
7. **Reproducibility of this package.** The evidence package contains frozen results, per-sample predictions and figures but not the simulator source code or data caches; end-to-end re-simulation is therefore not possible from this package alone.
8. **Literature.** The research-gap statement is provisional until a systematic search is completed.
