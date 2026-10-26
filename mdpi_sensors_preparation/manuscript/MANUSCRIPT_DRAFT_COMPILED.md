# Abstract (draft, MDPI Sensors, ≤ 200 words)

**Title:** Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Neural-Network Classification

**Abstract:** Locating a fault in a mixed-signal sensor interface—in the sensor, the analog front-end (AFE) or the analog-to-digital converter (ADC)—is ill-posed from the digitized output alone. We propose an active self-test that switches two known two-level references into the chain, one replacing the sensor at the AFE input and one bypassing the AFE at the ADC input, making AFE and ADC transfer errors separately observable. A monitor channel measures the reference levels, and phase-robust transient descriptors, obtained from a whole-transient fit with a free edge time, remove the dependence on the unknown phase between reference edges and ADC samples. A compact multilayer perceptron (6,868 parameters) classifies the faulty layer and nine fault classes. In a pre-registered simulation study with 3 unseen dataset seeds and paired behavioral and ngspice test sets with component tolerances, noise and 12-bit quantization, the method retained at least 0.916 of its nominal layer macro-F1 under ±20% reference-amplitude changes and 0.924 with a ±5% monitor error, kept AFE–ADC cross-confusion at or below 0.089, varied by at most 0.011 across edge phases (fixed-sample descriptors: 0.081), and lost 0.002 (95% CI [-0.003, +0.006]) from behavioral to ngspice data, against 0.119 in the previous design stage. All results are simulation-based.

**Keywords:** built-in self-test; mixed-signal sensor interface; fault diagnosis; reference monitoring; analog front-end; analog-to-digital converter; sampling phase; neural network; ngspice

---
*Word count is checked by `scripts/qc.py`. Numbers are filled from `NUMBER_PROVENANCE_MDPI.csv`; edit this template, not the rendered file.*


# 1. Introduction (draft)

Sensor systems increasingly have to report not only a measurement but also whether that measurement can be trusted. In a typical sensor interface the physical sensor is followed by an analog front-end (AFE) that amplifies and filters the signal and by an analog-to-digital converter (ADC). A fault in any of these layers changes the digitized signal, yet the corrective action depends on where the fault is: a drifting sensor must be recalibrated or replaced, whereas an AFE or ADC fault is an electronics fault. Built-in self-test (BIST) of analog, mixed-signal and MEMS circuits [mir2006bist; deb2002bist], data-driven fault diagnosis of analog circuits [aminian2000wavelet; sun2004wavelet; zhao2018dbn] and self-validating sensors [henry1993svs] are established research areas.

Attributing a fault to the sensor, the AFE or the ADC from the output alone is, however, an identifiability problem. For a linear chain observed at its output, y = g_ADC (G_AFE x + o_AFE) + o_ADC, only the composite gain and composite offset are observable: an AFE gain error and an ADC gain error with the same product produce identical outputs. A single test stimulus injected before the AFE does not change this. A second known stimulus that bypasses the AFE does: it measures the ADC transfer alone, after which the AFE transfer follows from the first stimulus. We therefore study an electronic two-point active self-test with two reference-replacement paths.

Two practical problems appear when this architecture is combined with a learned classifier, and both were found during the staged, pre-registered validation of this work. First, if the reference amplitude drifts and the classifier is not informed, a rescaled reference looks like an ADC or AFE gain/offset fault: with the nominal levels assumed, the layer macro-F1 of the classifier falls from 0.615 to 0.310 at ×0.8 and from 0.643 to 0.237 at ×1.2 reference amplitude (behavioral domain). Second, transient descriptors read at fixed samples after a reference step depend on where the reference edge falls between two ADC samples. This sampling phase is not controlled in a practical design; in our previous design stage the resulting mismatch between the behavioral and the circuit-level (ngspice) simulations cost 0.119 in layer macro-F1 (95% CI [0.107, 0.132]), above the pre-registered limit of 0.10.

This paper addresses both problems with an electronic reference monitor and with phase-robust transient descriptors, and evaluates the complete system under a pre-registered protocol. The novelty lies in integrating two-point electronic observability, reference-amplitude monitoring, phase-robust transient descriptors and neural fault classification within a complete sensor-to-ADC interface. The specific contributions are:

1. an electronic two-point active self-test architecture that makes AFE and ADC faults separately observable (Section 3);
2. settled-plateau calibration and phase-robust transient descriptors, estimated by a whole-transient fit with a free edge time, which remove the dependence on the sampling phase of the reference edge (Section 4);
3. a reference-monitor path that compensates reference-amplitude drift, evaluated with 0%, ±1%, ±2% and ±5% monitor gain error (Sections 3 and 7);
4. a compact neural-network classifier (20–96–48 multilayer perceptron, 6,868 parameters) for layer-level and nine-class fault diagnosis (Section 5);
5. a pre-registered behavioral-to-ngspice validation across reference amplitudes, edge phases, component tolerances, noise and ADC quantization, with ablations that attribute the robustness to its ingredients (Sections 6 and 7).

The remainder of the paper is organized as follows. Section 2 reviews related work and the research gap; Section 3 describes the electronic architecture; Section 4 the phase-robust descriptors; Section 5 the classifier; Section 6 the simulation and validation protocol; Section 7 the results; Section 8 discusses them; Section 9 lists the limitations; and Section 10 concludes.

# 2. Related Work and Research Gap (draft)

**Neural-network diagnosis of analog circuits.** Fault diagnosis of analog circuits with neural networks typically maps a measured response—often after wavelet or other preprocessing—to a fault dictionary of component deviations [aminian2000wavelet; sun2004wavelet; zhao2018dbn]. These works usually treat a single analog circuit under test with a designed stimulus; they do not address the attribution of faults across a sensor, an AFE and an ADC in one signal chain, nor drift of the test stimulus itself.

**Sensor and MEMS built-in self-test.** BIST for sensors and MEMS applies electrical or electromechanical test stimuli on chip and checks the response against limits [mir2006bist; deb2002bist], and self-validating sensors report a measurement-quality indicator together with the measurement [henry1993svs]. These approaches mainly verify the sensor element or a single block; they do not by themselves separate AFE and ADC faults, and they do not use a learned classifier over phase-robust transient descriptors.

**ADC testing and calibration.** ADC test and calibration methods estimate the converter transfer from known stimuli and address stimulus non-idealities [ieee1241; jin2005seir]. They isolate the ADC but are not designed to localize faults in the preceding AFE or sensor.

**Sampling-transient analysis.** Step-response and transition-duration measurements of sampled waveforms are standardized [ieee181], and fitting a parametric model with separable linear parameters is a classical technique [golub1973varpro]. Their use to make learned fault descriptors invariant to the sampling phase of a self-test edge is, to our knowledge, not reported; this statement is provisional until a systematic literature review is completed.

**Research gap.** We found no work that combines (i) two physically separated reference-replacement points chosen from an identifiability argument, (ii) a monitored reference path, (iii) sampling-phase-robust transient descriptors and (iv) a neural-network classifier evaluated under unseen operating conditions in two simulation domains. Table/matrix: `RESEARCH_GAP_MATRIX.md`. **[AUTHORS: complete a systematic search (IEEE Xplore, Scopus, Web of Science) before submission and revise this section; no priority claim is made.]**


# 3. Proposed Electronic Architecture (draft)

The interface (Figure 1, Table 1) consists of a sensor, an AFE modelled as a first-order RC low-pass filter with time constant τ followed by a gain and an offset, and a 12-bit ADC sampling at 1 kS/s. Each operating condition draws its own baseline, signal amplitude and frequency, sensor noise, AFE gain and AFE time constant (Table 1), so the classifier is always tested on operating conditions it has not seen. Nine fault classes are simulated (Table 2): healthy; sensor bias, gain and excess noise; AFE offset and bandwidth faults; and ADC offset, gain and clipping faults.

**Two-point reference multiplexer.** During the AFE test window, multiplexer MUX 1 (switches S1/S2) replaces the sensor by a two-level reference R1 at the AFE input; during the ADC test window, MUX 2 (S3/S4) connects a second two-level reference R2 directly to the ADC input, bypassing the AFE (Figure 2). With m₁, m₂ the settled ADC outputs on the two R2 plateaus and r₁ᴬᴰᶜ, r₂ᴬᴰᶜ the reference levels,

ĝ_ADC = (m₂ − m₁)/(r₂ᴬᴰᶜ − r₁ᴬᴰᶜ),  ô_ADC = m₁ − ĝ_ADC r₁ᴬᴰᶜ,   (1)

which isolates the ADC. The record is then ADC-calibrated, y_c = (y − ô_ADC)/ĝ_ADC, and the AFE transfer follows from the settled outputs a₁, a₂ on the R1 plateaus,

Ĝ_AFE = (a₂ − a₁)/(r₂ᴬᶠᴱ − r₁ᴬᶠᴱ),  ô_AFE = a₁ − Ĝ_AFE r₁ᴬᶠᴱ.   (2)

**Reference monitor.** Equations (1) and (2) need the actual reference levels. A buffered monitor channel (switch S5, high-impedance buffer and a dedicated 12-bit converter) measures the four reference levels; its gain error e is drawn uniformly from ±E and is common to the four levels of a test, and its offset is assumed trimmed. The measured levels replace the nominal levels in Equations (1) and (2). The monitor is a modelling assumption; it was not built.

**Active self-test sequence.** Each record of 512 samples contains passive sensor segments, the R1 window and the R2 window (Figure 2; window timing in Table 1). The reference and multiplexer edges are generated by a sequencer that is not phase-locked to the ADC: an edge occurs a fraction ψ ∈ [0, 1) of the sampling period T after the preceding ADC sample, so the first sample on the new level has settled for (1 − ψ)T.

# 4. Phase-Robust Descriptor Method (draft)

The processing chain from circuit simulation and fault injection to descriptor extraction, classification and evaluation is summarized in Figure 3.

**Settled-plateau calibration.** Each two-level window is split into its two plateaus; the first 30% of every plateau (settling guard, fixed before validation) is discarded and the remaining samples are averaged to obtain m_k and a_k. Plateau-settling errors and the residual noise of the settled samples are separate descriptors.

**Phase-robust transient descriptors.** The transient of the second R1 plateau carries the AFE bandwidth information. The earlier fixed-sample descriptors (R1) read it at fixed offsets after the step and therefore depend on ψ. The proposed descriptors fit the whole plateau with

d(u) = S (1 − exp(−(u − t_e)/τ)) for u ≥ t_e, and 0 otherwise,   (3)

where the edge time t_e is a free parameter that absorbs the unknown phase. For fixed (τ, t_e) the span S has a closed-form least-squares solution (variable projection [golub1973varpro]); (τ, t_e) are found by a deterministic grid search with one local refinement, so the fit has no convergence failure mode. A documented fallback for a degenerate span was triggered 0 times in 16,200 development-seed records. Five quantities are used: τ/P (P = plateau length), the 10–50% and 50–90% rise-time differences divided by P, the transient area normalized by the fitted span, and the fit residual relative to the span. Rise-time differences are shift-invariant, and all five quantities are invariant to the ADC gain and offset and to the monitored levels; t_e itself is not used. The complete descriptor vector has 20 entries (ADC gain, offset and noise; AFE gain, offset, two settling errors and noise; five sensor-domain statistics; two saturation descriptors; and the five transient descriptors). Figure 4 shows six of these descriptors for the nine fault classes on the development seed (illustrative): the ADC estimates from the bypassing R2 window separate ADC gain and offset faults, and the AFE estimates separate AFE offset and bandwidth faults. On the development seed, moving ψ from 0 to 0.999 shifted the fixed-sample descriptor rise_2 by 1.39 standard deviations and no phase-robust descriptor by more than 0.15 (Figure 5c, illustrative).

**Phase-randomized training.** In the primary method PRr, each training record draws ψ ~ U[0, 1). The arms compared in the ablation are A0 (old descriptors), R1 (fixed-sample Revision-1 descriptors, ψ = 0 training), R1r (R1 with phase randomization), PR (phase-robust descriptors, ψ = 0 training), PRr (phase-robust descriptors with phase randomization; pre-registered primary method) and PRrM (PRr with additional ngspice training rows; secondary mixed-domain variant).

# 5. Neural-Network Classifier (draft)

The classifier is a fully connected multilayer perceptron with two hidden layers (20–96–48; ReLU) on the standardized 20-dimensional descriptor vector. Two networks are trained, one for the four fault layers (healthy, sensor, AFE, ADC; 6,868 parameters, 6,720 multiply-accumulates per inference) and one for the nine fault classes (7,113 parameters). Standardization is fitted on training data only. Monitored variants are trained with monitor errors drawn from the same bound E as at test time (matched training). Two initialization seeds are trained per model and their test metrics averaged. **[AUTHORS: confirm optimizer settings and the early-stopping split; the frozen protocol states that the 15% validation split was unused, whereas the earlier package lists "Adam, early stopping" — see QUALITY_CONTROL_REPORT.md.]**

# 6. Simulation and Validation Protocol (draft)

**Domains.** The behavioral simulator implements the fractional edge phase exactly by advancing the first-order AFE in two steps within the edge interval. The ngspice domain uses a separate netlist per test record with piecewise-linear sources, voltage-controlled switches and the RC filter, plus extra amplifier and reference-rail noise (Table 1); ADC noise and 12-bit quantization are applied with the same random stream, so the two domains are paired record by record. Without the extra noise the two domains agree to 0.14–0.27 mV mean RMS per phase (development seed).

**Data and splits.** Three new dataset seeds (20261026, 20261027, 20261028) were generated after the protocol was frozen. Each contains 350 operating conditions × 9 fault classes, split by operating condition into 222 training, 40 validation and 88 test conditions with zero overlap (Table 3). Training uses the nominal reference amplitude (×1.0) and no tolerances. All test sets include component tolerances, noise and 12-bit quantization. Behavioral tests cover reference amplitudes ×0.8, ×0.9, ×1, ×1.1, ×1.2 and the edge phases ψ = 0, 0.25, 0.5, 0.75, 0.999; ngspice tests cover ×0.8, ×1, ×1.2 with the same phases (13,878 ngspice runs per seed, 41,634 in total). The monitor gain-error bound takes the values 0%, ±1%, ±2%, ±5%, and a known-reference variant is also evaluated.

**Metrics and statistics.** The primary metric is layer macro-F1; fault macro-F1, balanced accuracy, per-class recall, AFE recall, ADC recall and AFE–ADC cross-confusion (fraction of AFE- and ADC-fault records assigned to the other of the two layers) are also reported. Pooling over phases and amplitudes sums confusion matrices. Confidence intervals come from a paired condition-level cluster bootstrap [field2007clustered; efron1993bootstrap] with 5000 resamples per seed; the pooled interval is that of the mean of the three per-seed differences, and an improvement is stated only when the pooled interval excludes zero.

**Pre-registered criteria.** Seven criteria were frozen for PRr before the validation data were generated (results in Section 7.1): A, retention ≥ 0.85·N at ×0.8 and ×1.2 (known reference or E ≤ ±2%), where N is the nominal known-reference layer macro-F1 in the same domain; B, superiority over the old method and one-point baselines; C, AFE–ADC cross-confusion < 0.15; D, retention ≥ 0.70·N at E = ±5%; E, behavioral-to-ngspice transfer loss ≤ 0.10 at E = ±2%; F, every claimed improvement supported by a paired bootstrap interval excluding zero; G, layer macro-F1 range over the five phases ≤ 0.05. PRrM is evaluated against the same ngspice-domain gates but is not the pre-registered primary method. Development and debugging used separate seeds only.


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


# 10. Conclusions (draft)

A two-point active self-test makes AFE and ADC faults of a sensor interface separately observable. With reference levels measured by a monitor channel and transfer parameters estimated from settled plateaus, the diagnosis tolerated ±20% reference-amplitude changes (retention ≥ 0.916) and monitor errors up to ±5% (retention ≥ 0.924) in simulation. Replacing fixed-sample transient descriptors by a whole-transient fit with a free edge time removed the dependence on the unknown sampling phase: layer macro-F1 varied by at most 0.011 across phases instead of 0.081, and the behavioral-to-ngspice loss fell from 0.119 in the previous design stage to 0.002 [-0.003, +0.006]. A compact neural network (6,868 parameters) is sufficient for the classification. Next steps are a circuit model with realistic amplifier and switch behavior, a hardware prototype with an actual monitor channel, and a systematic comparison with published BIST approaches.

---

# Back matter (MDPI; placeholders — do not invent)

**Author Contributions:** [AUTHORS: CRediT statement, e.g. Conceptualization, X.X.; Methodology, …]

**Funding:** [AUTHORS: funding source and grant number, or "This research received no external funding."]

**Institutional Review Board Statement:** Not applicable (simulation study; no humans or animals involved). [AUTHORS: confirm.]

**Informed Consent Statement:** Not applicable. [AUTHORS: confirm.]

**Data Availability Statement:** The frozen protocol, per-seed predictions, result tables and figure-generation scripts are available at [AUTHORS: repository URL / DOI]. The simulator source code is [AUTHORS: state whether and where it will be released]. Every number in this article is traceable to a result file through `NUMBER_PROVENANCE_MDPI.csv`.

**Acknowledgments:** [AUTHORS: optional.]

**Conflicts of Interest:** [AUTHORS: declare, or "The authors declare no conflicts of interest."]

**Abbreviations:** ADC, analog-to-digital converter; AFE, analog front-end; BIST, built-in self-test; CI, confidence interval; MLP, multilayer perceptron; MUX, multiplexer; PR, phase-robust descriptors; PRr, phase-robust descriptors with phase-randomized training (primary method); PRrM, PRr with mixed behavioral + ngspice training (secondary variant); R1, Revision-1 fixed-sample descriptors; R1r, R1 with phase-randomized training; A0, previous (old) descriptors.


# Figures

# Figure captions (MDPI Sensors)

Generated by `scripts/build_all.py`; every number in a caption is filled from `NUMBER_PROVENANCE_MDPI.csv`.
Figures are in `figures/` as PNG (600 dpi), PDF and SVG. Type: result, illustrative or schematic.

**Figure 1.** Electronic architecture of the reference-monitored two-point active self-test. During the AFE test window MUX 1 (S1/S2) replaces the sensor by the two-level reference R1, so the response passes through the AFE and the ADC; during the ADC test window MUX 2 (S3/S4) injects the two-level reference R2 directly at the ADC input, so its response depends on the ADC only. The ADC transfer estimated from R2 is removed before the AFE transfer is estimated from R1, which separates AFE and ADC fault observability. A buffered reference-monitor channel (S5) measures the actual reference levels (gain error bounded by ±E). The digital back-end computes settled-plateau calibration and phase-robust transient descriptors and classifies them with a compact 20–96–48 multilayer perceptron into the faulty layer (4 classes) and the fault class (9 classes). Stars mark the simulated fault locations. Schematic; not a measured result.

*File:* `figures/Fig01_architecture.png|.pdf|.svg` · *Type:* schematic

**Figure 2.** Active self-test timing. (a) Multiplexer states: MUX 1 connects the two-level reference R1 to the AFE input (140–260 ms) and MUX 2 connects R2 to the ADC input (340–460 ms). (b) Illustrative ADC record from development seed 20261097 (not validation data): sensor intervals, R1 and R2 reference windows with their 30% settling guards (dark) and settled plateaus (light); ADC samples are taken every 1 ms. (c) Analytic illustration of the edge phase ψ: a reference edge occurring ψT after an ADC sample shifts every sampled value of the first-order response (τ = 12 ms, the midpoint of the simulated AFE time-constant range), so a descriptor that reads fixed samples after the edge depends on ψ, whereas a fit over the whole transient with a free edge time does not. Panels (b) and (c) are illustrative.

*File:* `figures/Fig02_timing.png|.pdf|.svg` · *Type:* illustrative

**Figure 3.** Processing and evaluation pipeline. Behavioral and ngspice circuit simulations generate records with injected faults (9 classes), component tolerances, noise and 12-bit quantization; the two-point active reference test is applied at five edge phases ψ; the reference monitor reports the reference levels with a bounded gain error E; 20 phase-robust descriptors are extracted and classified by the compact MLP (20–96–48); performance is evaluated with macro-F1, the pre-registered gates A–G and a 5000-resample paired condition-level cluster bootstrap. Schematic.

*File:* `figures/Fig03_pipeline.png|.pdf|.svg` · *Type:* schematic

**Figure 4.** Example fault signatures (illustrative, development seed 20261097, 60 records per class; not used for any decision). Box plots (median, interquartile range, whiskers at 1.5 IQR; outliers hidden) of six of the 20 descriptors for the nine classes, colored by faulty layer. (a) ADC gain and (b) ADC offset, estimated from the R2 window that bypasses the AFE, separate ADC gain and ADC offset faults and stay flat for sensor and AFE faults. (c) AFE gain and (d) AFE offset, estimated from the R1 window after ADC calibration, shift for AFE faults: offset faults widen the offset distribution, while bandwidth faults lower the apparent gain and raise the apparent offset because the plateaus do not fully settle. (e) The fitted time constant τ/P marks AFE bandwidth faults. (f) Sensor-domain high-frequency noise marks sensor-noise faults (and, more weakly, AFE bandwidth faults). Sensor bias and sensor gain faults are not separated by these six descriptors, which is consistent with their low recall (Figure 10). Raw per-fault waveforms are not included in the evidence package, so descriptor-level signatures are shown instead of waveforms.

*File:* `figures/Fig04_fault_signatures.png|.pdf|.svg` · *Type:* illustrative

**Figure 5.** Sampling-phase sensitivity. Layer macro-F1 (monitor E = ±2%, pooled over reference amplitudes; mean of 3 dataset seeds × 2 initializations) versus edge phase ψ in (a) the behavioral and (b) the ngspice domain. The fixed-sample Revision-1 descriptors (R1) lose accuracy as ψ grows (phase spread 0.081 behavioral, 0.081 ngspice), whereas the proposed PRr is nearly flat (0.006 and 0.010); over the pre-registered gate-G variants (known reference and E = ±2%, both domains) the PRr spread is 0.005–0.011 (threshold 0.05). R1r, PR and PRrM are shown for attribution. (c) Illustrative mechanism on development seed 20261097: mean absolute descriptor shift relative to ψ = 0 in units of the across-record standard deviation; the fixed-sample rise fraction rise_2 shifts by up to 1.39 σ, the phase-robust descriptors by at most 0.15 σ.

*File:* `figures/Fig05_phase_sensitivity.png|.pdf|.svg` · *Type:* result (a,b); illustrative (c)

**Figure 6.** Reference-amplitude robustness. Layer macro-F1 (pooled over the five edge phases; mean of three dataset seeds) versus the actual reference amplitude for the primary PRr classifier with a known reference and with the simulated reference monitor (gain error E = 0, ±1, ±2, ±5%), for the Revision-1 descriptors (R1, known reference) and the old descriptors (A0), in (a) the behavioral and (b) the ngspice domain. In (a) the no-monitor control applies the same PRr known-reference classifier with the nominal (assumed) reference levels: at ×0.8 and ×1.2 its layer macro-F1 falls to 0.310 and 0.237, against 0.615 and 0.643 with the known reference. The no-monitor control was evaluated in the behavioral domain only; ngspice was simulated at ×0.8, ×1.0 and ×1.2.

*File:* `figures/Fig06_reference_amplitude.png|.pdf|.svg` · *Type:* result

**Figure 7.** AFE/ADC fault separation of the primary PRr classifier in the behavioral domain (pooled over the five edge phases; mean of three dataset seeds × two initializations). (a,b) Row-normalized layer confusion matrices with the known reference at ×0.8 and ×1.2 reference amplitude; (c,d) the same classifier without reference monitoring (nominal levels assumed). H = healthy, S = sensor; red boxes mark the AFE↔ADC cells. (e) AFE recall, ADC recall and AFE–ADC cross-confusion for the known reference, the monitor with E = 0 to ±5% and the no-monitor control at ×0.8 and ×1.2. With a known or monitored reference the cross-confusion stays at or below 0.089 (gate C limit 0.15); without monitoring it rises to 0.230 (×0.8) and 0.336 (×1.2). Panels (a–d) and the no-monitor bars in (e) are computed from the saved per-sample predictions; the other bars are read from decision_rules.json. The ngspice values are listed in Table 10.

*File:* `figures/Fig07_afe_adc_separation.png|.pdf|.svg` · *Type:* result

**Figure 8.** Behavioral-to-ngspice transfer. (a) Layer macro-F1 on the ngspice test grid (×0.8, ×1.0, ×1.2 × five phases) of the behavioral-trained PRr classifier on behavioral (BB) and ngspice (BS) data and of the mixed-domain secondary variant PRrM on ngspice data (MS), for each reference condition. (b) Transfer loss BB − BS with paired 5000-resample cluster-bootstrap 95% CIs; for the pre-registered primary case (E = ±2%) the loss is 0.002 [-0.003, +0.006], against 0.119 [0.107, 0.132] in the previous, failed validation stage (previous-stage value, shown for context only); dashed line: gate E limit 0.10. (c) Layer macro-F1 per edge phase (E = ±2%, pooled over amplitudes) of PRr and PRrM in both domains. PRrM is a secondary mixed-training variant, not the pre-registered primary method.

*File:* `figures/Fig08_domain_transfer.png|.pdf|.svg` · *Type:* result (previous-stage point marked)

**Figure 9.** Ablation study. (a) Layer macro-F1 (monitor E = ±2%, pooled over amplitudes and phases) of the old descriptors (A0), the fixed-sample Revision-1 descriptors (R1), R1 with phase-randomized training (R1r), the phase-robust descriptors (PR), the proposed PRr and the mixed-domain secondary variant PRrM; solid bars behavioral, hatched bars ngspice (A0 was not simulated in ngspice). (b) Phase spread (max − min over the five edge phases); dashed line: gate G limit 0.05. (c) Paired-bootstrap differences with 95% CIs: descriptors alone (PR − R1) +0.042 behavioral / +0.041 ngspice; randomisation alone (R1r − R1) +0.030 / +0.029; descriptors given randomisation (PRr − R1r) +0.012 / +0.014; randomisation given robust descriptors (PRr − PR) +0.000 [-0.005, +0.006] / +0.003 [-0.004, +0.009] (not resolvable); mixed-domain training (PRrM − PRr) +0.017 / +0.014.

*File:* `figures/Fig09_ablation.png|.pdf|.svg` · *Type:* result

**Figure 10.** Per-class recall (monitor E = ±2%, pooled over amplitudes and phases; mean of three dataset seeds). (a,b) Fine-fault recall of every arm in the behavioral and ngspice domains (PRr, the primary method, in bold). (c) Layer recall of R1, PRr and PRrM in both domains and of the no-monitor control (behavioral, ×0.8/×1.2). Red outlines mark weak classes with recall below 0.50 (display threshold chosen for this figure, not a pre-registered criterion). For PRr the weak fine classes are healthy, sensor bias, sensor gain, adc clipping; healthy-layer recall is 0.142 (behavioral) and 0.134 (ngspice), so the classifier is a fault-localisation aid rather than a healthy/faulty detector.

*File:* `figures/Fig10_per_class_recall.png|.pdf|.svg` · *Type:* result


# Tables

# Tables (MDPI Sensors)

Generated by `scripts/build_all.py` from the frozen result files; every cell is traceable through `NUMBER_PROVENANCE_MDPI.csv`. Each table is also available as CSV, LaTeX (`.tex`, booktabs) and Word (`.docx`).

**Table 1.** Electronic system and circuit components of the simulated sensor interface.

| Block | Model / parameters (simulation) | Role in the self-test | Source (code constant) |
|---|---|---|---|
| Sensor model | baseline U(0.78,1.18) V; carrier amplitude U(0.045,0.18) V; frequency U(0.45,3.0) Hz; sensor noise U(2,14) mV; slow component 25 mV at 0.12 Hz; random-walk drift 1.5 mV/step | Physical signal source; replaced by R1 during the AFE test window | src/simulate.py: make_condition, _base_signal |
| MUX 1 / reference R1 | 140-260 ms; 0.90 V then 1.30 V (two 60 ms plateaus); replaces the sensor at the AFE input | Two-level reference at the AFE input; its response passes through AFE and ADC | src/simulate.py: _afe_reference |
| AFE / filter | AFE gain U(1.65,2.05); AFE tau U(8,16) ms; first-order RC low-pass with gain and offset | Amplifies and filters; faults: offset, bandwidth | src/simulate.py: make_condition, _base_signal |
| MUX 2 / reference R2 | 340-460 ms; 1.15 V then 1.75 V; bypasses the AFE at the ADC input | Two-level reference at the ADC input, bypassing the AFE; isolates the ADC transfer | src/simulate.py: _adc_reference |
| ADC | 1 kHz, 512 samples per record (0.512 s), 12-bit ADC over 0-3.3 V, ADC noise 2.5 mV rms | Digitises all paths; faults: offset, gain, clipping | src/simulate.py: simulate_sample |
| Reference monitor | buffered 12-bit channel, 16-sample mean, 0.25 mV rms after averaging, common gain error U(-E,E), E in {0,1,2,5}% | Measures the actual reference levels used in calibration (simulated, not built) | src/monitor_model.py |
| Switches (ngspice) | Ron = 0.5 Ohm, Roff = 1 MOhm, threshold 2.5 V, hysteresis 0.1 V; 1 us edges | Circuit-level multiplexer model | src/spice_phase.py: render_phase |
| Extra ngspice noise | 0.5 mV rms amplifier-input noise and 0.5 mV rms on each reference rail | Circuit-domain noise not present in the behavioral model | src/spice_domain.py: AMP_NOISE_V, REF_NOISE_V |
| Digital classifier | MLP 20-96-48-{4 or 9}, ReLU, Adam, early stopping; 6,868 (layer) / 7,113 (fault) parameters; input: 20 (15 settled-plateau / calibration / sensor-domain + 5 phase-robust transient) | Classifies faulty layer (4 classes) and fault (9 classes) | phase_robust_results/timing_and_parameters.json; src/run_feasibility.py: _classifier |
| Component tolerances (test) | AFE gain ±5%, AFE tau ±10%, ADC gain ±2%, ADC offset ±10 mV, sensor baseline ±5% (uniform per sample) | Applied in both domains, drawn per sample | src/run_reference_monitor.py: _draw_tol |

*Values are code constants copied programmatically from paper_package/PAPER_TABLES.csv (Table T1/T10); the simulator source code is not part of the evidence package, so these constants cannot be re-verified here.*

**Table 2.** Fault taxonomy: nine fault classes and their physical location.

| # | Fault class | Layer | Physical location | Severity range (simulated) | Primary observability |
|---|---|---|---|---|---|
| 0 | Healthy | — | — | no fault injected | — |
| 1 | Sensor bias | Sensor | Sensor element / sensor output | ±U(0.06,0.24) V | Passive sensor segments only (references replace the sensor) |
| 2 | Sensor gain | Sensor | Sensor element (sensitivity) | ±U(6,28)% | Passive sensor segments only (references replace the sensor) |
| 3 | Sensor noise | Sensor | Sensor element (excess noise) | U(25,95) mV rms | Passive sensor segments only (references replace the sensor) |
| 4 | AFE offset | AFE | Amplifier stage (offset) | ±U(0.06,0.24) V | R1 window, after removing the ADC transfer from R2 |
| 5 | AFE bandwidth | AFE | RC low-pass filter (time constant τ) | tau x U(1.8,4.5) | R1 window, after removing the ADC transfer from R2 |
| 6 | ADC offset | ADC | ADC (offset) | ±U(0.06,0.24) V | R2 window (bypasses the AFE) |
| 7 | ADC gain | ADC | ADC (gain) | ±U(6,28)% | R2 window (bypasses the AFE) |
| 8 | ADC clipping | ADC | ADC input range (clipping) | full scale x U(0.72,0.93) | R2 window (bypasses the AFE) |

*Severity ranges parsed programmatically from the 'Faults (severity)' row of paper_package/PAPER_TABLES.csv (src/simulate.py: make_fault). Layer assignment follows the four-class layer label used by the classifier.*

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

**Table 4.** Main classification results of the primary (PRr) and secondary (PRrM) methods.

| Method | Role | Domain | Layer macro-F1 | Layer balanced acc. | Fault macro-F1 | Fault balanced acc. |
|---|---|---|---|---|---|---|
| PRr | Primary (pre-registered) | Behavioral | 0.656 | 0.660 | 0.668 | 0.670 |
| PRr | Primary (pre-registered) | ngspice | 0.649 | 0.654 | 0.662 | 0.665 |
| PRrM | Secondary (mixed-domain training) | Behavioral | 0.672 | 0.674 | 0.675 | 0.676 |
| PRrM | Secondary (mixed-domain training) | ngspice | 0.663 | 0.666 | 0.671 | 0.673 |

*Monitor E = ±2%, pooled over amplitudes (behavioral ×0.8–×1.2; ngspice ×0.8, ×1.0, ×1.2) and the five phases; mean of 3 dataset seeds × 2 initializations. The behavioral and ngspice rows use different amplitude grids and must not be subtracted; the matched-grid transfer comparison is in Table 9. Nominal reference value N (known reference, ×1.0, pooled over phases): 0.659 behavioral, 0.660 ngspice. Source: attribution_arms.csv; decision_rules.json (N).*

**Table 5.** Pre-registered gate results for the primary method PRr.

| Gate | Criterion | Threshold | Observed (PRr) | 95% CI | Behavioral | ngspice |
|---|---|---|---|---|---|---|
| A | Retention at ×0.8 and ×1.2 (known, E ≤ ±2%) | ≥ 0.85·N | worst 0.916 (ngspice, monitor E = ±1%, ×0.8) | — | PASS | PASS |
| B | Superiority over old method and one-point baselines (behavioral) | pooled CI lower bound > 0 | smallest lower bound +0.112 over 70 comparisons | per comparison, Table 6 | PASS | — |
| C | AFE–ADC cross-confusion at ×0.8 and ×1.2 | < 0.15 | largest 0.089 (behavioral, known reference, ×1.2) | — | PASS | PASS |
| D | Retention with monitor E = ±5% | ≥ 0.70·N | worst 0.924 (ngspice, ×0.8) | — | PASS | PASS |
| E | Behavioral → ngspice transfer loss (E = ±2%, ngspice grid) | ≤ 0.10 (point estimate) | 0.002 | [-0.003, +0.006] | PASS | — |
| F | Every claimed improvement supported by a paired-bootstrap CI excluding zero | CI excludes 0 | satisfied | 5000 resamples | procedural† | procedural† |
| G | Layer macro-F1 range over five phases (known, E = ±2%) | ≤ 0.05 | largest 0.011 (smallest 0.005) | — | PASS | PASS |

*Decision: GO (0 failed gates). N = PRr layer macro-F1 with known reference at ×1.0 (0.659 behavioral, 0.660 ngspice). †Gate F has no separate key in decision_rules.json; it was checked here against the saved CIs. The mixed-domain variant PRrM also passes the ngspice-domain gates (reported only). Source: decision_rules.json (gates, A–E, G details); PROTOCOL_PHASE_ROBUST_FROZEN.md §5 (thresholds).*

**Table 6.** Baseline comparison (layer macro-F1, behavioral domain).

| Method | Layer macro-F1 ×0.8 | Layer macro-F1 ×1.2 | PRr − method ×0.8 [95% CI] | PRr − method ×1.2 [95% CI] | PRr − method, E = ±2% pooled [95% CI] |
|---|---|---|---|---|---|
| Passive (sensor signal only), old descriptors | 0.259 | 0.259 | +0.356 [+0.341, +0.371] | +0.384 [+0.368, +0.400] | — |
| Single-probe active test, old descriptors | 0.349 | 0.396 | +0.266 [+0.250, +0.282] | +0.246 [+0.230, +0.261] | — |
| AFE-only reference, old descriptors | 0.320 | 0.295 | +0.295 [+0.280, +0.311] | +0.348 [+0.329, +0.366] | — |
| ADC-only reference, old descriptors | 0.120 | 0.122 | +0.495 [+0.482, +0.508] | +0.521 [+0.507, +0.534] | — |
| A0: two-point, old descriptors (previous method) | 0.140 | 0.121 | +0.475 [+0.461, +0.489] | +0.521 [+0.507, +0.535] | +0.375 [+0.363, +0.387] |
| AFE-only reference, PRr descriptors | 0.473 | 0.516 | +0.142 [+0.128, +0.155] | +0.126 [+0.112, +0.140] | — |
| ADC-only reference, PRr descriptors | 0.455 | 0.452 | +0.160 [+0.144, +0.175] | +0.190 [+0.176, +0.206] | — |
| R1: Revision-1 fixed-sample descriptors | 0.578 | 0.593 | — | — | +0.042 [+0.034, +0.050] |
| R1r: R1 + phase-randomized training | 0.626 | 0.634 | — | — | +0.012 [+0.004, +0.019] |
| PR: phase-robust descriptors, ψ = 0 training | 0.612 | 0.635 | — | — | +0.000 [-0.005, +0.006] |
| PRr: proposed (primary) | 0.615 | 0.643 | — | — | — |
| PRrM: PRr + mixed-domain training (secondary) | 0.660 | 0.670 | — | — | -0.017 [-0.025, -0.008] |

*Behavioral domain, known reference, pooled over the five phases. Absolute layer macro-F1 values are computed from the saved per-sample predictions (they are not stored in a summary file); for every baseline the difference PRr − method equals the saved paired difference in decision_rules.json (B) to within 1e-9. Paired differences and CIs: decision_rules.json (B) and attribution_comparisons.csv; PRr − PRrM is the sign-reversed PRrM − PRr comparison (CI bounds reversed accordingly).*

**Table 7.** Reference-monitor robustness: layer macro-F1 versus actual reference amplitude.

| Reference condition | Behavioral ×0.8 | Behavioral ×0.9 | Behavioral ×1.0 | Behavioral ×1.1 | Behavioral ×1.2 | ngspice ×0.8 | ngspice ×1.0 | ngspice ×1.2 |
|---|---|---|---|---|---|---|---|---|
| Known reference | 0.615 | 0.645 | 0.658 | 0.667 | 0.642 | 0.616 | 0.660 | 0.642 |
| Monitor E = 0% | 0.610 | 0.638 | 0.655 | 0.665 | 0.642 | 0.606 | 0.655 | 0.644 |
| Monitor E = ±1% | 0.608 | 0.638 | 0.658 | 0.670 | 0.644 | 0.604 | 0.655 | 0.644 |
| Monitor E = ±2% | 0.614 | 0.647 | 0.673 | 0.681 | 0.663 | 0.611 | 0.671 | 0.664 |
| Monitor E = ±5% | 0.611 | 0.644 | 0.661 | 0.676 | 0.649 | 0.610 | 0.663 | 0.646 |
| No-monitor control (nominal levels assumed) | 0.310 | 0.423 | 0.659 | 0.389 | 0.237 | — | — | — |

*PRr layer macro-F1 pooled over the five phases (mean of three seeds). Monitored variants are trained with the matching error bound E. The no-monitor control is the PRr known-reference classifier given the nominal levels; it was evaluated in the behavioral domain only. Retention relative to N: worst 0.916 at ±20% (known, E ≤ ±2%) and 0.924 at E = ±5%. Source: amplitude_curves.csv; no_monitor_control.json; decision_rules.json (A, D).*

**Table 8.** Phase-robustness ablation: layer macro-F1 per edge phase.

| Domain | Arm | ψ = 0 | ψ = 0.25 | ψ = 0.5 | ψ = 0.75 | ψ = 0.999 | Range (max − min) | ≤ 0.05 |
|---|---|---|---|---|---|---|---|---|
| Behavioral | A0 | 0.279 | 0.279 | 0.281 | 0.281 | 0.282 | 0.003 | yes |
| Behavioral | R1 | 0.649 | 0.636 | 0.614 | 0.590 | 0.568 | 0.081 | no |
| Behavioral | R1r | 0.651 | 0.650 | 0.648 | 0.641 | 0.626 | 0.025 | yes |
| Behavioral | PR | 0.657 | 0.656 | 0.655 | 0.655 | 0.653 | 0.004 | yes |
| Behavioral | PRr | 0.659 | 0.658 | 0.656 | 0.653 | 0.652 | 0.006 | yes |
| Behavioral | PRrM | 0.677 | 0.676 | 0.672 | 0.668 | 0.667 | 0.010 | yes |
| ngspice | R1 | 0.642 | 0.625 | 0.606 | 0.584 | 0.561 | 0.081 | no |
| ngspice | R1r | 0.643 | 0.642 | 0.638 | 0.631 | 0.617 | 0.026 | yes |
| ngspice | PR | 0.649 | 0.648 | 0.647 | 0.644 | 0.642 | 0.007 | yes |
| ngspice | PRr | 0.654 | 0.651 | 0.649 | 0.645 | 0.643 | 0.010 | yes |
| ngspice | PRrM | 0.667 | 0.665 | 0.664 | 0.659 | 0.658 | 0.009 | yes |

*Layer macro-F1 per edge phase, monitor E = ±2%, pooled over amplitudes; range computed as max − min of the five stored phase values. Gate G itself applies to PRr (known reference and E = ±2%; Table 5): PRr ranges 0.005 / 0.006 (behavioral known / E2) and 0.011 / 0.010 (ngspice). A0 was not simulated in ngspice; its flat profile reflects uniformly low accuracy. Source: attribution_arms.csv; decision_rules.json (G).*

**Table 9.** Behavioral-to-ngspice domain transfer (layer macro-F1).

| Reference condition | Behavioral BB (PRr) | ngspice BS (PRr) | Transfer loss BB − BS | 95% CI | ≤ 0.10 | ngspice MS (PRrM) | MS − BS [95% CI] |
|---|---|---|---|---|---|---|---|
| Known reference | 0.639 | 0.639 | -0.001 | [-0.005, 0.004] | PASS | 0.677 | +0.038 [+0.029, +0.047] |
| Monitor E = 0% | 0.636 | 0.635 | 0.001 | [-0.003, 0.004] | PASS | 0.675 | +0.040 [+0.031, +0.050] |
| Monitor E = ±1% | 0.637 | 0.634 | 0.002 | [-0.001, 0.006] | PASS | 0.670 | +0.036 [+0.027, +0.045] |
| Monitor E = ±2% | 0.650 | 0.649 | 0.002 | [-0.003, 0.006] | PASS | 0.663 | +0.014 [+0.005, +0.024] |
| Monitor E = ±5% | 0.640 | 0.640 | 0.001 | [-0.003, 0.005] | PASS | 0.655 | +0.015 [+0.006, +0.024] |
| Previous stage, E = ±2% (REVISE) | 0.658 | 0.539 | 0.119 | [0.107, 0.132] | FAIL | — | — |

*Matched grid: ×0.8, ×1.0, ×1.2 × five phases in both domains. BB and BS use the same behavioral-trained PRr classifier; MS is the mixed-trained secondary variant PRrM. The pre-registered gate E uses E = ±2%. The previous-stage row is the failed earlier validation (reference_monitor_final), read from paper_package/NUMBER_PROVENANCE.csv because its decision file is not in the evidence package. Source: decision_rules.json (E).*

**Table 10.** AFE/ADC fault separation of PRr at ±20% reference amplitude.

| Domain | Reference / monitor condition | Amplitude | AFE recall | ADC recall | AFE–ADC cross-confusion |
|---|---|---|---|---|---|
| Behavioral | Known reference | ×0.8 | 0.912 | 0.831 | 0.026 |
| Behavioral | Known reference | ×1.2 | 0.898 | 0.797 | 0.089 |
| Behavioral | Monitor E = 0% | ×0.8 | 0.883 | 0.843 | 0.035 |
| Behavioral | Monitor E = 0% | ×1.2 | 0.865 | 0.797 | 0.085 |
| Behavioral | Monitor E = ±1% | ×0.8 | 0.905 | 0.833 | 0.032 |
| Behavioral | Monitor E = ±1% | ×1.2 | 0.876 | 0.790 | 0.087 |
| Behavioral | Monitor E = ±2% | ×0.8 | 0.886 | 0.826 | 0.035 |
| Behavioral | Monitor E = ±2% | ×1.2 | 0.885 | 0.797 | 0.079 |
| Behavioral | Monitor E = ±5% | ×0.8 | 0.891 | 0.778 | 0.033 |
| Behavioral | Monitor E = ±5% | ×1.2 | 0.878 | 0.777 | 0.083 |
| ngspice | Known reference | ×0.8 | 0.909 | 0.833 | 0.028 |
| ngspice | Known reference | ×1.2 | 0.898 | 0.799 | 0.088 |
| ngspice | Monitor E = 0% | ×0.8 | 0.879 | 0.845 | 0.036 |
| ngspice | Monitor E = 0% | ×1.2 | 0.863 | 0.800 | 0.083 |
| ngspice | Monitor E = ±1% | ×0.8 | 0.899 | 0.835 | 0.033 |
| ngspice | Monitor E = ±1% | ×1.2 | 0.874 | 0.792 | 0.086 |
| ngspice | Monitor E = ±2% | ×0.8 | 0.883 | 0.832 | 0.036 |
| ngspice | Monitor E = ±2% | ×1.2 | 0.885 | 0.797 | 0.078 |
| ngspice | Monitor E = ±5% | ×0.8 | 0.887 | 0.773 | 0.034 |
| ngspice | Monitor E = ±5% | ×1.2 | 0.875 | 0.778 | 0.081 |
| Behavioral | No monitor (nominal levels assumed) | ×0.8 | 0.426 | 0.944 | 0.230 |
| Behavioral | No monitor (nominal levels assumed) | ×1.2 | 0.375 | 0.820 | 0.336 |

*PRr, layer classifier, pooled over the five phases (mean of three seeds × two initializations). Cross-confusion = fraction of AFE- and ADC-fault records assigned to the other of the two layers (gate C limit 0.15). Source: decision_rules.json (C); no-monitor rows computed from seed_*/predictions.npz with the same definition (the computation reproduces every saved C value exactly; see verification/RECOMPUTED_FROM_PREDICTIONS.csv).*

**Table 11.** Per-class recall (fine-fault and layer classes).

| Domain | Arm | Healthy | Sensor bias | Sensor gain | Sensor noise | AFE offset | AFE bandwidth | ADC offset | ADC gain | ADC clipping | Layer: Healthy | Layer: Sensor | Layer: AFE | Layer: ADC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Behavioral | A0 | 0.015 | 0.052 | 0.057 | 0.094 | 0.135 | 0.511 | 0.539 | 0.800 | 0.057 | 0.010 | 0.154 | 0.238 | 0.882 |
| Behavioral | R1 | 0.230 | 0.231 | 0.312 | 0.988 | 0.763 | 0.938 | 0.992 | 0.948 | 0.398 | 0.098 | 0.703 | 0.866 | 0.822 |
| Behavioral | R1r | 0.328 | 0.316 | 0.261 | 0.985 | 0.823 | 0.929 | 0.997 | 0.957 | 0.311 | 0.148 | 0.804 | 0.873 | 0.764 |
| Behavioral | PR | 0.276 | 0.279 | 0.323 | 0.983 | 0.855 | 0.955 | 0.995 | 0.918 | 0.429 | 0.132 | 0.782 | 0.927 | 0.803 |
| Behavioral | PRr | 0.294 | 0.260 | 0.314 | 0.984 | 0.857 | 0.955 | 0.997 | 0.922 | 0.447 | 0.142 | 0.780 | 0.911 | 0.806 |
| Behavioral | PRrM | 0.355 | 0.256 | 0.338 | 0.983 | 0.921 | 0.942 | 0.997 | 0.927 | 0.368 | 0.238 | 0.742 | 0.940 | 0.775 |
| ngspice | R1 | 0.229 | 0.235 | 0.312 | 0.988 | 0.755 | 0.918 | 0.990 | 0.938 | 0.382 | 0.094 | 0.694 | 0.860 | 0.815 |
| ngspice | R1r | 0.310 | 0.326 | 0.264 | 0.986 | 0.814 | 0.910 | 0.996 | 0.947 | 0.304 | 0.143 | 0.795 | 0.867 | 0.756 |
| ngspice | PR | 0.247 | 0.284 | 0.325 | 0.983 | 0.839 | 0.942 | 0.993 | 0.901 | 0.455 | 0.118 | 0.775 | 0.920 | 0.803 |
| ngspice | PRr | 0.266 | 0.263 | 0.310 | 0.982 | 0.845 | 0.942 | 0.995 | 0.907 | 0.475 | 0.134 | 0.773 | 0.901 | 0.810 |
| ngspice | PRrM | 0.320 | 0.256 | 0.347 | 0.983 | 0.912 | 0.928 | 0.995 | 0.915 | 0.399 | 0.220 | 0.735 | 0.933 | 0.776 |
| Behavioral | PRr, no monitor (×0.8/×1.2) | — | — | — | — | — | — | — | — | — | 0.000 | 0.039 | 0.400 | 0.882 |

*Recall, monitor E = ±2%, pooled over amplitudes and phases (mean of three seeds). Weak classes (recall < 0.5) for PRr: healthy, sensor bias, sensor gain and ADC clipping; healthy-layer recall 0.142 (behavioral) / 0.134 (ngspice). Source: per_class_recall_fault.csv; per_class_recall_layer.csv.*

**Table 12.** Model and computational complexity.

| Quantity | Value | Source |
|---|---|---|
| MLP architecture | 20–96–48 hidden layout; 20 inputs; ReLU; output 4 (layer) or 9 (fault) | PAPER_TABLES.csv T10; parameter count check |
| MLP parameters | 6,868 (layer head); 7,113 (fault head) | timing_and_parameters.json |
| Multiply-accumulates per inference | 6,720 (layer); 6,960 (fault) | derived from the architecture |
| MLP inference time | 0.68 µs per record (batched, Python, mean of 3 seeds) | timing_and_parameters.json |
| Descriptor extraction time | Phase-robust 0.79 ms; Revision-1 0.47 ms per record (Python, 1 core) | timing_and_parameters.json |
| MLP training time (PRr models) | mean 0.72 s, max 1.49 s per model | seed_*/model_info.json |
| ngspice runs | 13,878 per seed; 41,634 total | seed_*/meta.json |
| Validation runtime per seed | 20261026: total 1175.6 s (ngspice wall 908.1 s, behavioral 707.7 s); 20261027: total 1179.0 s (ngspice wall 908.9 s, behavioral 708.5 s); 20261028: total 1179.1 s (ngspice wall 905.9 s, behavioral 703.8 s) | seed_*/meta.json |
| ngspice workers | 3 parallel workers | timing_and_parameters.json |
| Important assumptions | Timings are desktop Python (macOS arm64) measurements, not microcontroller measurements; no energy, power, area or hardware cost was measured | REPRODUCIBILITY_CHECKLIST.md (environment) |

*No embedded-target timing or energy figure exists in the evidence package; none is claimed.*
