---
journal: Sensors (MDPI)
article_type: Article
status: DRAFT generated from frozen result files — every number is filled from the files listed in NUMBER_PROVENANCE.csv
---

# Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Deep Learning

**[Author 1] <sup>1</sup>, [Author 2] <sup>1,*</sup>**

<sup>1</sup> [Affiliation, City, Country]
<sup>*</sup> Correspondence: [e-mail]

---

**Abstract:** Attributing a fault in a mixed-signal sensor interface to the sensor, the analog front-end (AFE) or the analog-to-digital converter (ADC) is ill-posed from the output signal alone. We propose an active self-test that switches two known two-level references into the chain—one replacing the sensor at the AFE input, one bypassing the AFE at the ADC input—so that AFE and ADC transfer errors become separately observable. A high-impedance monitor channel measures the reference levels, settled-plateau calibration estimates both transfer functions against them, and phase-robust transient descriptors from a whole-window fit with a free edge time remove the dependence on the unknown phase between reference edges and ADC samples. A compact neural network ({{PARAMS_LAYER}} parameters) classifies the faulty layer and nine fault classes. In a pre-registered simulation study with three unseen dataset seeds and paired behavioral and ngspice test sets including tolerances, noise and 12-bit quantisation, the method retained ≥{{A_MIN_RET_PCT}}% of nominal layer macro-F1 under ±20% reference-amplitude changes and ≥{{D_MIN_RET_PCT}}% with a ±5% monitor error, kept AFE–ADC cross-confusion ≤{{C_MAX}}, varied by ≤{{G_PRR_MAX}} across sampling phases (fixed-sample descriptors: {{G_R1_BH}}) and lost {{E_DROP}} (95% CI {{E_DROP_LO}} to {{E_DROP_HI}}) from behavioral to ngspice data, versus {{PREV_E_DROP}} before. Results are simulation-only.

**Keywords:** built-in self-test; mixed-signal sensor interface; fault diagnosis; reference monitor; analog front-end; ADC calibration; sampling phase; neural network; ngspice

---

## 1. Introduction

Sensor systems increasingly have to report not only a measurement but also whether that measurement can be trusted. In a typical interface the physical sensor is followed by an analog front-end (AFE) that filters and amplifies the signal and by an analog-to-digital converter (ADC). A fault in any of the three layers changes the digitised signal, but the location of the fault determines the corrective action: a drifting sensor must be recalibrated or replaced, whereas an AFE or ADC fault is an electronics problem. Built-in self-test (BIST) for analog and mixed-signal circuits and data-driven fault diagnosis of electronic circuits are established research areas [REF-1: mixed-signal / MEMS BIST review], [REF-2: neural-network fault diagnosis of analog circuits], [REF-3: on-line sensor fault detection]. However, the specific problem of attributing a fault to the sensor, the AFE or the ADC from a single digitised output remains ill-posed when only passive data are available.

The difficulty is one of identifiability. For a linear chain observed at its output, $y = g_\mathrm{ADC}\,(G_\mathrm{AFE}\,x + o_\mathrm{AFE}) + o_\mathrm{ADC}$, only the composite gain $g_\mathrm{ADC} G_\mathrm{AFE}$ and the composite offset are observable; an AFE gain error and an ADC gain error with the same product produce identical outputs. A single test stimulus injected before the AFE does not change this. A second, known stimulus that bypasses the AFE does: it measures the ADC transfer alone, after which the AFE transfer follows from the first stimulus. We therefore use an electronic two-point self-test with two reference-replacement paths.

Two practical problems appear when this architecture is combined with a learned classifier, and both were found during the staged, pre-registered validation of this work (Appendix A). First, if the reference amplitude changes and the classifier is not told so, a rescaled reference is indistinguishable from an ADC gain or offset fault; in our earlier frozen test this made almost every sample look like an ADC fault. Second, transient descriptors read at fixed samples after a reference step depend on where the reference edge falls between two ADC samples. This sampling phase is not controlled in practice, and in our previous behavioral-to-circuit-simulation test the resulting mismatch cost {{PREV_E_DROP}} in layer macro-F1 (95% CI {{PREV_E_LO}}–{{PREV_E_HI}}), above our pre-registered limit of 0.10.

To the best of our knowledge—pending a systematic literature search, which we have not yet completed [REF-4…]—the combination studied here has not been reported: (i) two physically separated reference-replacement points chosen from an identifiability argument, (ii) a monitored reference path, (iii) sampling-phase-robust transient descriptors and (iv) a neural-network classifier evaluated under unseen operating conditions and in two simulation domains. The contributions of this paper are:

1. an electronic **two-point active self-test** that makes AFE and ADC faults separable (Section 2);
2. **settled-plateau calibration** and **phase-robust transient descriptors** that are invariant to the reference amplitude and to the sampling phase of the reference edge (Section 3);
3. an electronic **reference-monitor path** that compensates known reference drift, evaluated with 0%, ±1%, ±2% and ±5% monitor gain error (Sections 2.3 and 4.2);
4. a compact **neural-network classifier** for layer-level (healthy/sensor/AFE/ADC) and nine-class fault diagnosis (Section 3.4);
5. a **pre-registered behavioral-to-ngspice validation** across reference amplitudes, sampling phases, component tolerances, noise and ADC quantisation, with ablations that identify which ingredient is responsible for the robustness (Sections 4 and 5).

Section 2 describes the electronic architecture, Section 3 the descriptors, classifier and simulation protocol, Section 4 the results, Section 5 the ablations, and Section 6 the limitations.

## 2. Electronic System Architecture

### 2.1. Measurement Chain and Fault Model

The interface ({{FREF:fig01}}) consists of a sensor, an AFE modelled as a first-order RC low-pass filter with time constant $\tau$ followed by a gain $G$ and an offset, and a 12-bit ADC sampling at 1 kS/s. Each operating condition draws its own baseline, signal amplitude and frequency, sensor noise, AFE gain and AFE time constant ({{TREF:T1}}), so the classifier is always tested on operating conditions it has not seen. Nine fault classes are simulated: healthy; sensor bias, gain and excess noise; AFE offset and bandwidth (time constant) faults; and ADC offset, gain and clipping faults ({{TREF:T1}}).

{{TABLE:T1}}

![{{FIGNUM:fig01}}](figures/fig01_architecture.png)

**{{FIGNUM:fig01}}.** Electronic architecture. Switches S1/S2 replace the sensor by the AFE reference; S3/S4 replace the AFE output by the ADC reference; S5 and the buffered monitor ADC measure the reference levels. Fault locations are marked. Source: drawn by `src/paper_figures.py::fig_architecture` (schematic, not a result).

### 2.2. Two-Point Reference Multiplexer

During the AFE test window the AFE input is connected to a two-level reference $r^\mathrm{AFE}_1 \rightarrow r^\mathrm{AFE}_2$ (nominally 0.90 V and 1.30 V); during the ADC test window the ADC input is connected to a second two-level reference $r^\mathrm{ADC}_1 \rightarrow r^\mathrm{ADC}_2$ (nominally 1.15 V and 1.75 V) that bypasses the AFE. Writing the settled ADC outputs on the two ADC plateaus as $m_1, m_2$,

$$\hat g_\mathrm{ADC} = \frac{m_2-m_1}{r^\mathrm{ADC}_2-r^\mathrm{ADC}_1},\qquad \hat o_\mathrm{ADC} = m_1-\hat g_\mathrm{ADC}\,r^\mathrm{ADC}_1, \tag{1}$$

which isolates the ADC. The waveform is then ADC-calibrated, $y_c[n]=(y[n]-\hat o_\mathrm{ADC})/\hat g_\mathrm{ADC}$, and the AFE transfer follows from the settled outputs $a_1,a_2$ on the AFE plateaus,

$$\hat G_\mathrm{AFE} = \frac{a_2-a_1}{r^\mathrm{AFE}_2-r^\mathrm{AFE}_1},\qquad \hat o_\mathrm{AFE} = a_1-\hat G_\mathrm{AFE}\,r^\mathrm{AFE}_1. \tag{2}$$

Gains are normalised by the reference *difference* and are therefore insensitive to a common scaling of the reference; offsets are absolute intercepts and are deliberately not normalised.

### 2.3. Reference-Monitor Circuit

Equations (1) and (2) require the actual reference levels. If the reference drifts and the nominal values are used instead, the drift is misread as an AFE or ADC fault (Section 4.2). The proposed monitor taps both reference nodes through a 2:1 switch (S5 in {{FREF:fig01}}) and a unity-gain buffer with an input impedance of at least 10 MΩ (loading error below 0.01%) into a dedicated 12-bit SAR ADC channel (0–3.3 V, LSB 0.806 mV). Each level is reported as the mean of 16 samples with 1 mV rms input-referred noise per sample. The monitor's gain error (its own reference and resistor tolerance) is bounded by $\pm E$ and is common to the four levels of a test; its offset is assumed trimmed:

$$\hat r = Q\!\left(r\,(1+e)+n\right),\qquad e\sim\mathcal U(-E,E),\quad n\sim\mathcal N\!\left(0,(1\,\mathrm{mV}/\sqrt{16})^2\right), \tag{3}$$

with $Q(\cdot)$ the 12-bit quantiser and $E\in\{0,1,2,5\}\%$. $E=0$ still includes noise and quantisation. The measured levels $\hat r$ replace $r$ in Equations (1) and (2). The monitor is a modelling assumption; it was not built.

### 2.4. Active Self-Test Sequence

Each 512 ms record ({{FREF:fig02}}) contains a passive sensor segment, the AFE test window (140–260 ms, two 60 ms plateaus), a recovery segment, the ADC test window (340–460 ms, two 60 ms plateaus) and a final sensor segment. The reference and multiplexer edges are generated by a sequencer whose clock is not phase-locked to the ADC: an edge occurs a fraction $\psi\in[0,1)$ of a sampling period $T$ after the preceding ADC sample, $t_\mathrm{edge}=t_{i-1}+\psi T$. The first sample on the new level has therefore settled for $(1-\psi)T$, and any descriptor that reads fixed samples after the edge depends on $\psi$.

![{{FIGNUM:fig02}}](figures/fig02_timing.png)

**{{FIGNUM:fig02}}.** Active self-test sequence: multiplexer states, reference levels and an illustrative healthy ADC record (development seed 20261097). Shaded: 30% settling guard and settled plateaus; bars: transient-fit window and sensor-domain segments. Data: `figure_data/fig02_timing_example.csv`.

## 3. Methods

### 3.1. Settled-Plateau Calibration

Each two-level window is split into its two plateaus of $L=60$ samples. The first 30% of every plateau (a guard of 18 samples, fixed before validation) is discarded and the remaining samples are averaged:

$$m_k=\frac{1}{L-\lceil 0.3L\rceil}\sum_{n=n_k+\lceil 0.3L\rceil}^{n_k+L-1} y[n],\qquad k=1,2, \tag{4}$$

and analogously $a_k$ on $y_c$. The plateau-settling errors $\varepsilon_k=(\bar y_{k,\mathrm{tail}}-a_k)/|a_2-a_1|$ (tail: last six samples) and the residual noise (standard deviation of the linearly detrended settled samples) are separate descriptors.

### 3.2. Phase-Robust Transient Descriptors

The transient of the second AFE plateau carries the bandwidth information. Revision-1 descriptors sampled it at fixed offsets (2, 5, 10, 20 and 30 samples after the step) and are therefore phase-dependent. The proposed descriptors are estimated from the whole plateau. Let $d_j=y[n_2-1+j]-y[n_2-1]$, $j=1,\dots,L$, be the response relative to the last pre-step sample, at times $u_j=jT$. The model

$$d(u)=S\left(1-e^{-(u-t_e)/\tau}\right)\mathbb 1[u\ge t_e] \tag{5}$$

has the edge time $t_e$ as a free parameter, which absorbs the unknown phase. For fixed $(\tau,t_e)$ the span has the closed-form least-squares value $S^\star=\sum_j g_j d_j/\sum_j g_j^2$ with $g_j=(1-e^{-(u_j-t_e)/\tau})\mathbb 1[u_j\ge t_e]$, and the residual is $\mathrm{RSS}=\|d\|^2-S^\star\sum_j g_j d_j$ (variable projection). $(\tau,t_e)$ are found by a deterministic grid search—56 log-spaced values of $\tau$ between 1 and 400 ms and 7 values of $t_e$ between $-0.25T$ and $1.25T$—followed by one local refinement ($\tau\times[0.9,1.1]$, $t_e\pm0.2T$, 9×9 points). The search has no convergence failure mode; a documented multi-sample fallback for a degenerate span ($|S^\star|<10^{-4}$) was triggered {{DEV_FALLBACK_COUNT}} times in {{DEV_FALLBACK_N}} development-seed records. With $r_j=d_j/S^\star$ and plateau length $P=LT$, the five transient descriptors are

$$\frac{\tau}{P},\quad \frac{t_{50}-t_{10}}{P},\quad \frac{t_{90}-t_{50}}{P},\quad A=\frac{T}{P}\sum_j(1-r_j),\quad \rho=\frac{\sqrt{\mathrm{RSS}/L}}{|S^\star|}, \tag{6}$$

where $t_q$ is the time at which the monotone envelope of $r_j$ crosses $q\%$ (linear interpolation, capped at the window end). Rise-time *differences* are shift-invariant, and all five quantities are invariant to the ADC gain and offset and to the monitored levels. The edge time $t_e$ itself is not used, because it only encodes the phase. On the development seed, moving $\psi$ from 0 to 0.999 shifted the Revision-1 descriptor `rise_2` by {{DEV_RISE2_SHIFT}} standard deviations, but no phase-robust descriptor by more than {{DEV_PR_MAX_SHIFT}} ($\tau/P$: {{DEV_TAU_SHIFT}}) ({{FREF:fig04}}d).

The full processing chain is summarised in {{FREF:fig03}}. The complete phase-robust vector has 20 entries: ADC gain, offset and noise; AFE gain, offset, two settling errors and noise; the five transient descriptors; five sensor-domain statistics of the fully calibrated waveform outside the test windows (mean, standard deviation, high-frequency noise, peak-to-peak and slope); and two saturation descriptors (maximum level and top-of-range fraction) (Appendix B).

![{{FIGNUM:fig03}}](figures/fig03_pipeline.png)

**{{FIGNUM:fig03}}.** Processing pipeline. Source: drawn by `src/paper_figures.py::fig_pipeline`.

### 3.3. Arms Compared

The arms compared are listed in {{TREF:ARMS}}.

{{TABLE:ARMS}}

### 3.4. Neural-Network Classifier

The classifier is a fully connected multilayer perceptron with two hidden layers (96 and 48 ReLU units) on the standardised 20-dimensional descriptor vector, trained with Adam (learning rate $8\times10^{-4}$, batch 64, L2 penalty $10^{-4}$, early stopping on an internal 15% split, at most 700 epochs). Two networks are trained: one for the four fault layers and one for the nine fault classes. The layer network has {{PARAMS_LAYER}} parameters and {{MACS_LAYER}} multiply-accumulates per inference; the fault network has {{PARAMS_FAULT}} parameters ({{TREF:T10}}). Standardisation is fitted on training data only. In the primary method (PRr) each training record draws a random edge phase $\psi\sim\mathcal U[0,1)$, and the monitor error of the training data is drawn from the same bound $E$ as at deployment (matched training; the monitor specification is a design parameter, not a test-set choice). A temporal convolutional network evaluated in an earlier frozen stage on the older descriptors was not consistently better than this MLP (Section 5) and is not used here.

### 3.5. Simulation Protocol

**Behavioral simulator.** Records are generated at 1 kS/s with the operating-condition and fault distributions of {{TREF:T1}}, ADC noise of 2.5 mV rms and 12-bit quantisation. The reference edge phase is implemented exactly: in the sample interval containing an edge the first-order AFE is advanced in two steps,

$$y_\mathrm{mid}=x_{i-1}+(y_{i-1}-x_{i-1})e^{-\psi T/\tau},\qquad y_i=x_i+(y_\mathrm{mid}-x_i)e^{-(1-\psi)T/\tau}, \tag{7}$$

which reduces to the standard zero-order-hold update for $\psi=0$.

**ngspice simulator.** Every ngspice test sample is a separate netlist of the circuit of {{FREF:fig01}}: the sensor waveform as a piecewise-linear source, the reference levels and switch controls as piecewise-linear sources with 1 µs edges placed at $t_{i-1}+\psi T$, voltage-controlled switches ($R_\mathrm{on}=0.5\,\Omega$, $R_\mathrm{off}=1\,\mathrm{M}\Omega$), the RC filter, behavioural gain/offset stages and an ADC input clamp for the clipping fault. Additional 0.5 mV rms noise is added at the amplifier input and on each reference rail. ADC noise and 12-bit quantisation are applied to the ngspice output with the same random stream as the behavioral model, so the two domains are paired sample by sample. Without the extra noise the two domains agree to {{DEV_AGREE_MIN}}–{{DEV_AGREE_MAX}} mV mean RMS per phase (worst sample {{DEV_AGREE_WORST}} mV; development seed, {{FREF:fig06}}b). The fixed netlist itself had earlier been checked against the behavioral model: replacing ramped reference sources by steps reduced the ADC-output RMSE from {{NETLIST_OLD_RMSE}} mV to {{NETLIST_FIX_RMSE}} mV.

**Test conditions.** All test sets include component tolerances (AFE gain ±5%, AFE time constant ±10%, ADC gain ±2%, ADC offset ±10 mV, sensor baseline ±5%, drawn per sample), shared between the domains. Behavioral tests cover reference amplitudes ×0.8–×1.2 in steps of 0.1 and edge phases $\psi\in\{0,0.25,0.5,0.75,0.999\}$; ngspice tests cover ×0.8, ×1.0 and ×1.2 with the same five phases ({{N_SPICE_PER_SEED}} ngspice runs per seed, {{N_SPICE_TOTAL}} in total). $\psi=0.999$ reproduces the edge placement that caused the earlier transfer failure. Behavioral training data use the nominal amplitude and no tolerances; the ngspice training rows of the mixed-training ablation (PRrM) use the nominal amplitude with tolerances and the extra noise.

**Data and splits.** Three new dataset seeds ({{SEEDS}}) were used, each with 350 operating conditions × 9 faults, split by operating condition into {{TRAIN_CONDITIONS}} training, {{VAL_CONDITIONS}} validation and {{TEST_CONDITIONS}} test conditions with no overlap ({{TREF:T2}}). Two initialisation seeds were averaged per model.

{{TABLE:T2}}

### 3.6. Pre-Registration and Statistics

The protocol, descriptor definitions, arms, test grids, thresholds and decision rule were written to a frozen protocol file (with source-code hashes) before the validation seeds were generated. Development and debugging used separate seeds only. Seven criteria were pre-registered for the primary method ({{TREF:TG}}): A, retention ≥ 0.85·N at ±20% reference amplitude (known or monitored reference, $E\le2\%$), where N is the nominal-amplitude, known-reference layer macro-F1 of the same method in the same domain; B, superiority over the old method and the one-point baselines; C, AFE–ADC cross-confusion below 0.15; D, retention ≥ 0.70·N at $E=\pm5\%$; E, behavioral-to-ngspice transfer loss ≤ 0.10; F, every claimed improvement supported by a paired bootstrap confidence interval; G, layer macro-F1 range over the five phases ≤ 0.05. Confidence intervals come from a condition-level paired cluster bootstrap with {{N_BOOT}} resamples, applied per seed; the pooled interval is that of the mean of the three per-seed differences. AFE–ADC cross-confusion is the fraction of AFE- and ADC-fault samples assigned to the other of the two layers.

## 4. Results

The primary method (phase-robust descriptors with phase-randomised training, PRr) met every pre-registered criterion in both domains ({{TREF:TG}}). Its nominal layer macro-F1 was N = {{N_BH}} (behavioral) and {{N_SP}} (ngspice).

{{TABLE:TG}}

### 4.1. Sampling-Phase Sensitivity of Fixed-Sample Descriptors

With Revision-1 descriptors and training at $\psi=0$, layer macro-F1 fell from {{ARM_BH_R1_P0}} at $\psi=0$ to {{ARM_BH_R1_P999}} at $\psi=0.999$ (behavioral; range {{G_R1_BH}}; ngspice range {{G_R1_SP}}) ({{TREF:T7}}, {{FREF:fig04}}). The phase-robust method varied by {{G_PRR_BH}} (behavioral) and {{G_PRR_SP}} (ngspice). This is the mechanism behind the earlier transfer failure. In the earlier stage, a post-hoc development-seed test moved the ngspice edges onto the behavioral timing convention and the ngspice score rose from {{ALIGN_FROZEN}} to {{ALIGN_ZOH}} (behavioral {{ALIGN_BB}}), with the `rise_2` shift dropping from {{ALIGN_RISE2_FROZEN}} σ to near zero.

{{TABLE:T7}}

![{{FIGNUM:fig04}}](figures/fig04_phase_effect.png)

**{{FIGNUM:fig04}}.** Sampling-phase effect. (a) Analytic step response sampled at three edge phases. (b, c) Layer macro-F1 versus edge phase for each arm (monitor $E=\pm2\%$, pooled over amplitudes). (d) Shift of descriptors with phase (development seed). Sources: `phase_robust_results/attribution_arms.csv`; `figure_data/dev_seed_verification.json`.

### 4.2. Reference-Amplitude Robustness and Monitor Error

{{TREF:T3}} and {{FREF:fig07}} show layer macro-F1 versus the actual reference amplitude. With a known or monitored reference the method kept at least {{A_MIN_RET_PCT}}% of N at ×0.8 and ×1.2 (criterion A), and at $E=\pm5\%$ at least {{D_MIN_RET_PCT}}% (criterion D). Monitor errors of 0%, ±1%, ±2% and ±5% changed the pooled behavioral layer macro-F1 only within {{AMP_BH_MON_POOLED_MIN}}–{{AMP_BH_MON_POOLED_MAX}} (ngspice {{AMP_SP_MON_POOLED_MIN}}–{{AMP_SP_MON_POOLED_MAX}}) ({{TREF:T3}}; matched training). Without a monitor—the same known-reference classifier given the nominal levels although the amplitude changed—layer macro-F1 fell to {{CTL_U_X08}} at ×0.8 and {{CTL_U_X12}} at ×1.2 (with the reference known: {{CTL_K_X08}} and {{CTL_K_X12}}). In that control the non-ADC layers were largely lost (layer recall: AFE {{REC_L_UNMON_AFE}}, sensor {{REC_L_UNMON_SENSOR}}, healthy {{REC_L_UNMON_HEALTHY}}, ADC {{REC_L_UNMON_ADC}}), consistent with the earlier frozen stage, in which an unexplained reference change was read as an ADC fault. The old descriptor set (A0) collapsed to {{AMP_BH_A0_X08}} and {{AMP_BH_A0_X12}} at ×0.8 and ×1.2.

{{TABLE:T3}}

![{{FIGNUM:fig07}}](figures/fig07_robustness.png)

**{{FIGNUM:fig07}}.** (a, b) Layer macro-F1 versus actual reference amplitude, pooled over the five phases; dotted: 0.85·N. (c) AFE–ADC cross-confusion at ±20%; dashed: limit 0.15. Sources: `phase_robust_results/amplitude_curves.csv`, `no_monitor_control.json`, `decision_rules.json`.

### 4.3. Comparison with the Old Method and One-Point Baselines

In all {{B_N}} pre-registered comparisons at ±20% reference amplitude (five monitor conditions × two amplitudes × seven baselines), the two-point phase-robust method was better than the passive, single-probe, AFE-only and ADC-only baselines and than the two-point method with old descriptors, with the smallest pooled CI lower bound at {{B_MIN_CI}} ({{TREF:T4}}). The pooled advantage over the old two-point method was {{ATT_BH_VS_A0}} {{ATT_BH_VS_A0_CI}} (behavioral, $E=\pm2\%$).

{{TABLE:T4}}

### 4.4. AFE–ADC Separation and Per-Class Recall

At ±20% the AFE–ADC cross-confusion stayed at or below {{C_MAX}} in both domains, with AFE recall ≥ {{C_MIN_AFE_REC}} and ADC recall ≥ {{C_MIN_ADC_REC}} ({{TREF:T5}}; {{FREF:fig05}}). {{FREF:fig05}}a shows why the separation works: ADC gain and offset faults change only the ADC calibration descriptors, AFE offset changes the AFE offset estimate, and AFE bandwidth changes the transient descriptors and the AFE gain estimate. Per-class recall is uneven ({{TREF:T9b}} and {{TREF:T9}}; {{FREF:fig09}}). At layer level, behavioral recall was {{REC_L_BH_PRR_AFE}} (AFE), {{REC_L_BH_PRR_ADC}} (ADC), {{REC_L_BH_PRR_SENSOR}} (sensor) and only {{REC_L_BH_PRR_HEALTHY}} for healthy records, most of which were classified as sensor faults. At fine-fault level, sensor noise ({{REC_F_BH_PRR_SENSOR_NOISE}}), ADC offset ({{REC_F_BH_PRR_ADC_OFFSET}}), AFE bandwidth ({{REC_F_BH_PRR_AFE_BANDWIDTH}}), ADC gain ({{REC_F_BH_PRR_ADC_GAIN}}) and AFE offset ({{REC_F_BH_PRR_AFE_OFFSET}}) were recognised well, whereas healthy ({{REC_F_BH_PRR_HEALTHY}}), sensor bias ({{REC_F_BH_PRR_SENSOR_BIAS}}), sensor gain ({{REC_F_BH_PRR_SENSOR_GAIN}}) and ADC clipping ({{REC_F_BH_PRR_ADC_CLIPPING}}) were not. Sensor bias and gain faults change the measurand itself, which also varies between operating conditions, and the self-test provides no reference for the sensor element; this is a limitation of the architecture, not of the classifier.

{{TABLE:T5}}

![{{FIGNUM:fig05}}](figures/fig05_afe_adc_separation.png)

**{{FIGNUM:fig05}}.** AFE/ADC fault separation. (a) Fault signatures: mean absolute deviation of selected descriptors from the healthy mean, in units of the healthy standard deviation (development seed). (b, c) Row-normalised layer confusion of PRr ($E=\pm2\%$, pooled). (d) AFE–ADC cross-confusion per arm. Sources: `figure_data/fig05_*`; `phase_robust_results/predictions` via `figure_data/fig05_layer_confusion_PRr_E2.json`; `afe_adc_separation.csv`.

{{TABLE:T9}}

{{TABLE:T9b}}

![{{FIGNUM:fig09}}](figures/fig09_per_class_recall.png)

**{{FIGNUM:fig09}}.** Fine-fault recall per arm ($E=\pm2\%$, pooled over amplitudes and phases). Source: `phase_robust_results/per_class_recall_fault.csv`.

### 4.5. Behavioral-to-ngspice Transfer

Trained on behavioral data only, the phase-robust method scored {{E_BB}} on the behavioral and {{E_BS}} on the ngspice test grid: a loss of {{E_DROP}} (95% CI {{E_DROP_LO}} to {{E_DROP_HI}}; criterion E). Across all monitor conditions the loss ranged from {{E_DROP_MIN}} to {{E_DROP_MAX}}. The earlier descriptor set lost {{PREV_E_DROP}} ({{PREV_E_LO}}–{{PREV_E_HI}}) in the previous frozen stage ({{TREF:T6}}; that stage used a single, fixed edge placement and amplitudes ×0.8–×1.2). Adding ngspice samples to the training data (PRrM) raised the ngspice score to {{E_MS}} ({{E_MS_GAIN}}, 95% CI {{E_MS_GAIN_LO}} to {{E_MS_GAIN_HI}}), but it was not required to meet the criterion.

{{TABLE:T6}}

![{{FIGNUM:fig06}}](figures/fig06_behavioral_vs_ngspice.png)

**{{FIGNUM:fig06}}.** Behavioral versus ngspice. (a) One record at $\psi=0.5$ in both domains (development seed; inset: difference). (b) Noise-free agreement per phase (development seed). (c) Transfer loss of the earlier descriptor set (previous stage) and of PRr, with 95% CIs. (d) Layer macro-F1 per phase in both domains. Sources: `figure_data/dev_seed_verification.json`, `figure_data/fig06_example_waveforms_dev_seed.csv`, `phase_robust_results/decision_rules.json`, `reference_monitor_results/decision_rules.json`, `phase_robust_results/attribution_arms.csv`.

### 4.6. Model Size and Computational Cost

{{TABLE:T10}}

The phase-robust descriptors cost {{DESC_MS_PR}} ms per record against {{DESC_MS_R1}} ms for Revision-1 descriptors (single-core Python, not optimised), dominated by the grid search of Equation (5). The classifier needs {{MACS_LAYER}} multiply-accumulates per layer decision, a load typically within reach of microcontroller-class processors; no embedded implementation was built or measured.

## 5. Ablation Study

{{TREF:T8}} and {{FREF:fig08}} decompose the effect of the descriptors, phase randomisation and mixed-domain training (monitor $E=\pm2\%$, pooled over amplitudes and phases).

* **Phase-robust descriptors** are the main ingredient. With training at $\psi=0$ they improved layer macro-F1 by {{ATT_BH_DESC}} {{ATT_BH_DESC_CI}} (behavioral) and {{ATT_SP_DESC}} {{ATT_SP_DESC_CI}} (ngspice) over Revision-1 descriptors, and removed the phase dependence ({{TREF:T7}}).
* **Phase randomisation** helped the fixed-sample descriptors ({{ATT_BH_RAND}} {{ATT_BH_RAND_CI}}) but left a phase range of {{ARM_BH_R1R_RANGE}}. Given the robust descriptors it added nothing ({{ATT_BH_RAND_GIVEN_DESC}} {{ATT_BH_RAND_GIVEN_DESC_CI}} behavioral; {{ATT_SP_RAND_GIVEN_DESC}} {{ATT_SP_RAND_GIVEN_DESC_CI}} ngspice). It is kept in the primary method because it is free and was pre-registered.
* **Descriptors given randomisation** still helped ({{ATT_BH_DESC_GIVEN_RAND}} {{ATT_BH_DESC_GIVEN_RAND_CI}}).
* **Mixed behavioral + ngspice training** gave a small further gain ({{ATT_BH_MIXED}} {{ATT_BH_MIXED_CI}} behavioral; {{ATT_SP_MIXED}} {{ATT_SP_MIXED_CI}} ngspice) but requires circuit-level training data.
* **Revision-2 conditioning** (feeding the commanded reference levels and training with amplitude jitter) did not improve the system. In the earlier frozen stage it was worse than the same descriptors with jitter but without conditioning ({{V2_COND_M20}} {{V2_COND_M20_CI}} at ×0.8, {{V2_COND_P20}} {{V2_COND_P20_CI}} at ×1.2). In the monitor stage it scored {{RM_A2_E2_X08}} / {{RM_A2_E2_X12}} at ×0.8 / ×1.2 against {{RM_A1_E2_X08}} / {{RM_A1_E2_X12}} for Revision 1 ($E=\pm2\%$). It is reported only as an ablation.
* **Temporal convolutional network versus MLP** (earlier frozen stage, old descriptors): the TCN was better on nominal layer macro-F1 ({{TCN_NOM_L}} {{TCN_NOM_L_CI}}), slightly worse on nominal fine-fault macro-F1 ({{TCN_NOM_F}} {{TCN_NOM_F_CI}}), and statistically similar under tolerance ({{TCN_TOL_L}} {{TCN_TOL_L_CI}}) and unseen fault severity ({{TCN_SEV_L}} {{TCN_SEV_L_CI}}). No superiority of the temporal architecture is claimed.
* **Old descriptors** (A0) were far below every descriptor arm under amplitude shift (Section 4.2).

{{TABLE:T8}}

![{{FIGNUM:fig08}}](figures/fig08_ablation.png)

**{{FIGNUM:fig08}}.** Ablation forest plot (layer macro-F1 differences with 95% paired-bootstrap CIs). Sources: `phase_robust_results/attribution_comparisons.csv`; `reference_v2_results/decision_rules.json`; `multiseed_results/decision_rules.json`.

## 6. Discussion and Limitations

The results support a narrow but concrete claim. Under the simulated conditions, a two-point electronic self-test with a monitored reference and phase-robust descriptors localises AFE and ADC faults reproducibly under unseen operating conditions, ±20% reference-amplitude changes, monitor errors up to ±5%, component tolerances and arbitrary edge phase. It does so in a behavioral and a circuit-level simulation domain. The ablations show that robustness comes mainly from how the reference responses are measured (settled plateaus, measured levels, phase-free transient fit), not from the classifier architecture.

The limitations are important.

1. **Simulation only.** No hardware was built or measured. The ngspice model and the behavioral model are both first-order RC plus affine-ADC models written by the same authors; without extra noise they agree to {{DEV_AGREE_MIN}}–{{DEV_AGREE_MAX}} mV (mean RMS). The cross-domain test therefore probes noise, tolerances, switch non-idealities and the circuit-level edge timing, not unmodelled hardware effects such as charge injection, amplifier bandwidth and slew, reference settling, leakage or temperature.
2. **Reference monitor.** The monitor is simulated with a common gain error, white noise and a trimmed offset. Nonlinearity, offset drift, bandwidth and the monitor's own failures were not modelled. Matched training assumes the error bound is known when the classifier is trained.
3. **Phase model.** All edges share one phase that is constant within a record. Edge jitter, phase drift within a record and different phases for the AFE and ADC references were not tested.
4. **Absolute performance.** Nominal layer macro-F1 is {{N_BH}}. Healthy records are mostly classified as sensor faults (healthy recall {{REC_L_BH_PRR_HEALTHY}}), and sensor bias/gain and ADC clipping remain weak. The system is a fault-localisation aid for the AFE/ADC layers, not a deployable healthy/faulty detector.
5. **Statistical scope.** Three dataset seeds with {{TEST_CONDITIONS}} test conditions each; intervals resample conditions, not datasets.
6. **No energy, area or cost measurements**, and no claim of universal robustness.
7. **Literature.** The research-gap statement is provisional until a systematic search (IEEE Xplore, Scopus) is completed.

## 7. Conclusions

A two-point active self-test makes AFE and ADC faults of a sensor interface separately observable. With reference levels measured by a monitor channel and transfer parameters estimated from settled plateaus, the diagnosis tolerated ±20% reference-amplitude changes and monitor errors up to ±5%. Replacing fixed-sample transient descriptors with a whole-window fit that treats the edge time as a free parameter removed the dependence on the unknown sampling phase: layer macro-F1 varied by at most {{G_PRR_MAX}} across phases instead of {{G_R1_BH}}, and the behavioral-to-ngspice loss fell from {{PREV_E_DROP}} to {{E_DROP}}. A compact neural network ({{PARAMS_LAYER}} parameters) is sufficient for the classification. The next steps are a circuit model with real amplifier and switch models, a hardware prototype with an actual monitor channel, and a systematic comparison with published BIST approaches.

---

**Author Contributions:** [CRediT statement to be completed.]

**Funding:** [To be completed.]

**Institutional Review Board Statement:** Not applicable.

**Data Availability Statement:** All simulation code, frozen protocols, per-seed predictions and result tables are available at [repository to be specified]. Every number in this article is traceable to a result file through `NUMBER_PROVENANCE.csv`.

**Conflicts of Interest:** [To be completed.]

**Abbreviations:** ADC, analog-to-digital converter; AFE, analog front-end; BIST, built-in self-test; CI, confidence interval; MAC, multiply-accumulate; MLP, multilayer perceptron; PR, phase-robust descriptors; PRr, phase-robust descriptors with phase-randomised training; PRrM, PRr with mixed behavioral + ngspice training; R1, Revision-1 descriptors; TCN, temporal convolutional network.

## Appendix A. Pre-Registered Validation History

Each stage had its own frozen protocol and its own new dataset seeds; earlier outcomes were not revised.

{{TABLE:T11}}

## Appendix B. Descriptor List

{{TABLE:DESC}}

## References

*Placeholders — to be replaced after a systematic literature search; no reference has been verified yet.*

1. [REF-1] Review of built-in self-test for mixed-signal / MEMS sensors.
2. [REF-2] Neural-network fault diagnosis of analog and mixed-signal circuits.
3. [REF-3] On-line sensor fault detection and self-validating sensors.
4. [REF-4] Reference/ADC calibration and two-point gain–offset estimation.
5. [REF-5] Sampling-phase / timing effects in ADC-based measurement of step responses.
6. [REF-6] ngspice user manual.
