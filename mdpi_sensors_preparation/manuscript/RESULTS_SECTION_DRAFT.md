# 7. Results (draft)

All values are means over the 3 dataset seeds (each the mean of two initializations); intervals are pooled 95% paired cluster-bootstrap CIs (5000 resamples). Unless stated otherwise, "layer macro-F1" refers to the four-class layer decision.

## 7.1. Pre-registered decision

Table 4 summarizes the main classification results and Table 5 the pre-registered criteria. The primary method PRr met every criterion in both domains (decision GO). Its nominal layer macro-F1 with a known reference at ×1.0 was N = 0.659 (behavioral) and 0.660 (ngspice). With monitor E = ±2%, pooled over amplitudes and phases, PRr reached a layer macro-F1 of 0.656 on the behavioral grid and 0.649 on the ngspice grid, and a fault macro-F1 of 0.668 (behavioral) and 0.662 (ngspice). The two grids differ (five versus three amplitudes), so these two values are not a transfer comparison; the matched-grid comparison is given in Section 7.5. The evidence for the individual criteria is given in Table 6 (criterion B, baselines), Table 7 (criteria A and D, reference amplitude and monitor error), Table 8 (criterion G, edge phase), Table 9 (criterion E, domain transfer) and Table 10 (criterion C, AFE/ADC separation).

## 7.2. Sampling-phase sensitivity

Fixed-sample descriptors are sensitive to the edge phase: the layer macro-F1 of R1 fell from 0.649 at ψ = 0 to 0.568 at ψ = 0.999 in the behavioral domain (range 0.081) and from 0.642 to 0.561 in ngspice (range 0.081) (Figure 5, Table 8). PRr varied by 0.006 (behavioral) and 0.010 (ngspice); over the four gate-G variants (known reference and E = ±2%, both domains) the PRr range was 0.005–0.011, below the limit of 0.05.

## 7.3. Reference-amplitude robustness and monitor error

With a known or monitored reference, PRr retained at least 0.916 of N at ×0.8 and ×1.2 (worst case: ngspice, monitor E = ±1%, ×0.8) and at least 0.924 with a ±5% monitor error (worst case: ngspice, ×0.8) (Figure 6, Table 7). Without monitoring, the same classifier given the nominal levels reached 0.310 at ×0.8 and 0.237 at ×1.2, against 0.615 and 0.643 with the known reference (behavioral domain; the no-monitor control was not run in ngspice).

## 7.4. Comparison with baselines and AFE/ADC separation

In all 70 pre-registered superiority comparisons (behavioral, ×0.8 and ×1.2, known reference and E = 0 to ±5%), two-point PRr exceeded the old two-point method, the passive, single-probe, AFE-only and ADC-only baselines; the smallest pooled CI lower bound was +0.112 (known reference, ×1.2, vs AFE-only PRr) (Table 6). Against the old two-point descriptors pooled at E = ±2% (behavioral), the difference was +0.375 [+0.363, +0.387].

AFE–ADC cross-confusion stayed at or below 0.089 (behavioral, known reference, ×1.2) for every known/monitored condition at ×0.8 and ×1.2, with AFE recall ≥ 0.863 and ADC recall ≥ 0.773 (Figure 7, Table 10). Without monitoring (behavioral), cross-confusion rose to 0.230 (×0.8) and 0.336 (×1.2) and AFE recall fell to 0.426 and 0.375.

## 7.5. Behavioral-to-ngspice transfer

On the matched ngspice grid with E = ±2%, the behavioral-trained PRr classifier reached 0.650 on behavioral data and 0.649 on ngspice data, a transfer loss of 0.002 [-0.003, +0.006] (limit 0.10); across all reference conditions the loss stayed within the range of Table 9 (Figure 8). In the previous design stage, with fixed-sample descriptors, the same comparison lost 0.119 [0.107, 0.132]. The secondary mixed-domain variant PRrM reached 0.663 on ngspice data (+0.014 [+0.005, +0.024] relative to PRr); it is reported as a secondary result.

## 7.6. Ablation

Pooled at E = ±2% (Figure 9), the phase-robust descriptors alone (PR − R1) improved layer macro-F1 by +0.042 [+0.033, +0.051] (behavioral) and +0.041 [+0.032, +0.049] (ngspice); phase randomization alone (R1r − R1) by +0.030 [+0.023, +0.038] and +0.029 [+0.022, +0.037]; and the descriptors given randomization (PRr − R1r) by +0.012 [+0.004, +0.019] and +0.014 [+0.006, +0.022]. Randomization given the phase-robust descriptors (PRr − PR) had no resolvable effect (+0.000 [-0.005, +0.006] behavioral, +0.003 [-0.004, +0.009] ngspice). Mixed-domain training (PRrM − PRr) added +0.017 [+0.008, +0.025] (behavioral) and +0.014 [+0.005, +0.024] (ngspice); PRrM remains a secondary variant.

## 7.7. Per-class recall

Per-class recall (Figure 10, Table 11) shows where the method is weak. For PRr (behavioral, E = ±2%) recall was high for sensor noise (0.984), AFE offset (0.857), AFE bandwidth (0.955), ADC offset (0.997) and ADC gain (0.922), but low for healthy records (0.294), sensor bias (0.260), sensor gain (0.314) and ADC clipping (0.447). At the layer level, healthy recall was 0.142 (behavioral) and 0.134 (ngspice); healthy records are mostly assigned to the sensor layer.

## 7.8. Model size and cost

The layer classifier has 6,868 parameters (6,720 multiply-accumulates) and the fault classifier 7,113 (Table 12). In Python on a desktop CPU, phase-robust descriptor extraction took 0.79 ms per record (Revision-1: 0.47 ms) and batched MLP inference 0.68 µs per record. These are not embedded-target measurements.
