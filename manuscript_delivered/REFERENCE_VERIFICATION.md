# Reference verification record

Manuscript: *Phase-Robust Active Self-Test for Fault Localization in Mixed-Signal Sensor Interfaces: A Simulation Study*.  
Checked 11 November 2026. **56 references**, all cited in the text and numbered by first appearance.

## 1. Method

Each reference was checked twice, and the two checks are reported separately.

1. **Bibliographic record.** Authors, title, year, venue, volume, issue, pages or article number and DOI were compared field by field with the Crossref record of the DOI. This was done when the list was built and again in an automated recheck (`manuscript_build/literature/crossref_recheck_2026-11-11.json`). For the three items without a DOI, the publisher page was used: JMLR for scikit-learn, arXiv for Adam, and the ngspice documentation for the ngspice-47 manual.
2. **Support for the citing sentence.** The full text was read for the closest prior works where a legal copy exists. For all other references the abstract was read (Crossref or OpenAlex) and compared with the sentence that cites it. Standards were checked against their scope statements. References whose record has no abstract are cited only for what their title and record state.

## 2. Full texts of the closest prior works

| No. | Reference | What was read | Finding used in the manuscript |
|---:|---|---|---|
| 7 | Nessler, S. et al., 2018 | Abstract only; full text not accessible | Self-test that characterises the readout ASIC separately from the sensor element by reconfiguring the readout into an electrical ΔΣ loop at wafer level. Full text not accessible (IEEE, no open copy found via Unpaywall, OpenAlex or Semantic Scholar). |
| 14 | Czaja, Z. et al., 2013 | Full text (author's postprint, MOST Wiedzy repository) | Full text read (author's postprint, MOST Wiedzy repository of Gdansk University of Technology): in test mode the sensor signal is replaced by a microcontroller-generated square pulse; N = 32 samples of the response of a second-order MFB low-pass filter are taken by a 16-bit ADC with conversions triggered by a timer synchronized with the pulse; a modified-DFT transformation maps them onto localization curves of a simulation-before-test fault dictionary; fault detection and single soft-fault localization to individual components (0.2 to 5 times nominal); experimental verification with an ATmega16 and an AD7694 ADC; ADC and its reference treated as fault-free (reference checked with a multimeter). |
| 15 | Hu, G. et al., 2008 | Full text (J-STAGE publisher PDF, free) | Full text read (J-STAGE, free publisher PDF): production self-test; analog portion reconfigured into a triangle or sinusoidal oscillator (state-variable filter benchmark) that provides the histogram stimulus of an 8-bit ADC; digital checker evaluates oscillation frequency, amplitude and code histogram; analog fault coverage 92.2% (triangle) and 94.3% (sinusoid) in HSPICE fault simulation; notes that analog and ADC gain errors can compensate each other and treats this as unlikely. |
| 16 | Pavlidis, A. et al., 2021 | Full text (HAL author version hal-03171195) | Full text read (HAL author version hal-03171195): invariances such as V1+V2 = 2Vcm of fully differential signals checked against Monte Carlo tolerance windows; off-line defect-oriented and on-line modes; demonstrated by defect simulation on a 65 nm 10-bit SAR ADC IP; flags invariance violations (pass/fail), no stage-level localization. |

**Not fully read:** Nessler et al. (2018), IEEE TCSI. It is paywalled, and Unpaywall, OpenAlex and Semantic Scholar list no open copy. The manuscript describes it only as far as its abstract states and says so in the text (Section 2.5).

**Effect of reading Czaja (2013) in full.** The earlier comparison was correct that the ADC serves as the measuring device rather than as a fault location. It was incomplete in three respects, which Sections 2.2, 2.5 and 8.2 now state:
- the method also replaces the sensor signal by a known stimulus during the test;
- it localizes single soft faults to individual components, which is finer than the layer-level localization here, and it was verified in hardware;
- it synchronizes stimulus and sampling with the microcontroller's timers, so the sampling-phase problem studied here does not arise in it. The manuscript therefore presents phase robustness as relevant to interfaces in which such synchronization is not available, not as a shortcoming of that work.

## 3. Search scope

This was a focused search, not a systematic review. It used the OpenAlex works search on 11 November 2026, limited to articles and reviews published from 1 January 2020, sorted by relevance; the first 12 results of each query were screened by title, venue and abstract. Foundational pre-2020 work was added from the earlier package's candidate list after each record was re-checked.

| Query | Hits | Screened |
|---|---:|---:|
| analog circuit fault diagnosis deep learning | 3,296 | 12 |
| analog circuit soft fault diagnosis convolutional neural network | 936 | 12 |
| mixed-signal circuit fault diagnosis machine learning | 4,987 | 12 |
| built-in self-test sensor interface | 87,547 | 12 |
| MEMS sensor self-test readout | 3,496 | 12 |
| ADC built-in self-test gain offset | 1,593 | 12 |
| ADC calibration reference voltage error | 6,598 | 12 |
| sensor fault detection isolation signal conditioning electronics | 6,608 | 12 |
| analog front-end fault detection | 4,497 | 12 |
| step response feature extraction fault diagnosis time constant | 9,000 | 12 |
| sampling phase misalignment robustness | 41,890 | 12 |
| sub-sample time delay estimation step response | 52,227 | 12 |
| simulation to real domain shift fault diagnosis circuit | 5,897 | 12 |
| self-validating sensor fault isolation | 11,991 | 12 |
| test stimulus design analog fault diagnosis | 308 | 12 |
| domain randomization simulation training transfer | 122,912 | 12 |
| sine wave fitting ADC test four-parameter | 366 | 12 |
| time-interleaved ADC timing skew calibration | 281 | 12 |
| equivalent-time sampling ADC | 20,982 | 12 |
| analog circuit fault diagnosis transfer learning domain adaptation | 754 | 12 |
| analog circuit fault diagnosis tolerance component variation | 1,059 | 12 |
| smart sensor self-calibration self-diagnosis | 14,045 | 12 |
| sensor readout drift detection reference | 7,062 | 12 |
| mixed-signal integrated circuit built-in self-test analog | 4,234 | 12 |
| fault diagnosis time-domain response analog circuit test | 2,237 | 12 |
| data augmentation time series classification robustness | 80,938 | 12 |
| bootstrap confidence interval classifier comparison clustered | 13,363 | 12 |

Not covered: a PRISMA-style systematic review, patents, theses and non-English literature.

## 4. Per-reference record (citation order)

| No. | Key | First author, year, venue | DOI / URL | Record check | Cited for | Support check |
|---:|---|---|---|---|---|---|
| 1 | `hantos2021` | Hantos, G., 2021, *Micromachines* | https://doi.org/10.3390/mi12010040 | Crossref: published online 31 Dec 2020 in volume 12 (2021); cited with the volume year, as the journal does | MEMS BIST taxonomy; testing is a large share of MEMS cost (Intro, §2.1) | abstract: Review and taxonomy of MEMS BIST methods; abstract states that testing represents about 50% of MEMS product cost. |
| 2 | `mir2006` | Mir, S., 2006, *Microelectron. J.* | https://doi.org/10.1016/j.mejo.2006.04.016 | Crossref: all fields agree | Earlier overview of MEMS BIST (Intro, §2.1) | title/record only: Early overview of BIST for MEMS (cited as background only). |
| 3 | `ozel2017` | Ozel, M.K., 2017, *IEEE Sens. J.* | https://doi.org/10.1109/JSEN.2016.2636861 | Crossref: all fields agree | Electrical stimulus can replace the physical one; 0.55% sensitivity agreement (Intro, §2.1) | abstract: Electrical stimulus replaces the physical stimulus; sensitivity extracted within 0.55% of the physical-stimulus value. |
| 4 | `mason2007` | Mason, A., 2007, *IEEE Sens. J.* | https://doi.org/10.1109/JSEN.2007.897957 | Crossref: all fields agree | Readout with on-chip calibration and self-test (Intro, §2.1) | abstract: Capacitive sensor readout chip with self-test and online calibration. |
| 5 | `chen2018` | Chen, D., 2018, *Micromachines* | https://doi.org/10.3390/mi9090444 | Crossref: all fields agree | Sigma-delta interface with digital self-test (Intro, §2.1) | abstract: Sigma-delta MEMS interface with in-situ digital self-test and calibration. |
| 6 | `basith2013` | Basith, I.I., 2013, *IEEE Trans. Comput.-Aided Des. Integr. Circuits Syst.* | https://doi.org/10.1109/TCAD.2012.2218602 | Crossref: all fields agree | Charge-controlled BIST stimuli for structural defects (Intro, §2.1) | abstract: Readout with integrated BIST using charge-controlled stimuli to detect structural MEMS defects. |
| 7 | `nessler2018` | Nessler, S., 2018, *IEEE Trans. Circuits Syst. I Regul. Pap.* | https://doi.org/10.1109/TCSI.2017.2767199 | Crossref title contains LaTeX markup ($\Delta \Sigma$); title printed as ΔΣ | Readout ASIC characterised separately from the sensor element (Intro, §2.1, §2.5, §8.2) | abstract only (full text inaccessible): Self-test that characterises the readout ASIC separately from the sensor element by reconfiguring the readout into an electrical ΔΣ loop at wafer level. Full text not accessible (IEEE, no open copy found via Unpaywall, OpenAlex or Semantic Scholar). |
| 8 | `ieee1241` | IEEE Std 1241-2010, 2011, *IEEE* | https://doi.org/10.1109/IEEESTD.2011.5692956 | Crossref standard record: approved 17 Jun 2010, published 2011 | ADC terminology and test methods incl. gain/offset and sine fitting (Intro, §2.2, §2.4, §8.2) | standard scope: Defines ADC terminology and test methods, including gain and offset errors. |
| 9 | `jin2005` | Jin, L., 2005, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2005.847240 | Crossref: all fields agree | SEIR: testing with imprecise stimuli (Intro, §2.2) | abstract: SEIR: identifies and removes stimulus nonlinearity using two functionally related imprecise excitations. |
| 10 | `parthasarathy2003` | Parthasarathy, K., 2003, *ACM Trans. Des. Autom. Electron. Syst.* | https://doi.org/10.1145/944027.944035 | Crossref: all fields agree | ADC BIST with imprecise stimulus (Intro, §2.2) | abstract: ADC BIST with stimuli less linear than the device under test. |
| 11 | `varier2021` | Varier, V., 2021, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2020.3031208 | Crossref: all fields agree | Relaxed reference-voltage precision/constancy for ADC BIST (Intro, §2.2) | abstract: Relaxes the precision and constancy requirements on the reference voltage of on-chip ADC BIST by extending SEIR; shows that reference behaviour is itself a test-accuracy issue. |
| 12 | `feng2021` | Feng, R., 2021, *Micromachines* | https://doi.org/10.3390/mi12091115 | Crossref: all fields agree | Online self-test during operation via an internal signal (§2.1) | abstract: Online self-test during operation by monitoring an internal (quadrature error) signal, because electrostatic self-test cannot run during operation. |
| 13 | `alraho2022` | Alraho, S., 2022, *Chips* | https://doi.org/10.3390/chips1020008 | Crossref: all fields agree | Sensor AFEs with self-x capabilities (§2.1) | abstract: Review of sensor AFEs with self-monitoring/self-calibration (self-x) capabilities and the robustness demands on AFEs. |
| 14 | `czaja2013` | Czaja, Z., 2013, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2013.2272867 | Crossref: all fields agree | Self-test of analog parts terminated by ADCs from sampled step responses; soft-fault localisation in the analog part (§2.2, §2.5, §8.2) | full text: Full text read (author's postprint, MOST Wiedzy repository of Gdansk University of Technology): in test mode the sensor signal is replaced by a microcontroller-generated square pulse; N = 32 samples of the response of a second-order MFB low-pass filter are taken by a 16-bit ADC with conversions triggered by a timer synchronized with the pulse; a modified-DFT transformation maps them onto localization curves of a simulation-before-test fault dictionary; fault detection and single soft-fault localization to individual components (0.2 to 5 times nominal); experimental verification with an ATmega16 and an AD7694 ADC; ADC and its reference treated as fault-free (reference checked with a multimeter). |
| 15 | `hu2008` | Hu, G., 2008, *IEICE Trans. Inf. Syst.* | https://doi.org/10.1093/ietisy/e91-d.8.2134 | Crossref: all fields agree | Combined oscillation-based self-test of analog portion and ADC (§2.2, §2.5) | full text: Full text read (J-STAGE, free publisher PDF): production self-test; analog portion reconfigured into a triangle or sinusoidal oscillator (state-variable filter benchmark) that provides the histogram stimulus of an 8-bit ADC; digital checker evaluates oscillation frequency, amplitude and code histogram; analog fault coverage 92.2% (triangle) and 94.3% (sinusoid) in HSPICE fault simulation; notes that analog and ADC gain errors can compensate each other and treats this as unlikely. |
| 16 | `pavlidis2021` | Pavlidis, A., 2021, *IEEE Trans. Circuits Syst. I Regul. Pap.* | https://doi.org/10.1109/TCSI.2021.3067180 | Crossref: all fields agree; Crossref spells the second author 'Louerat'; the author's own spelling Louërat (HAL full text) is printed | SymBIST invariance checking, on-line capable (§2.2, §2.5) | full text: Full text read (HAL author version hal-03171195): invariances such as V1+V2 = 2Vcm of fully differential signals checked against Monte Carlo tolerance windows; off-line defect-oriented and on-line modes; demonstrated by defect simulation on a 65 nm 10-bit SAR ADC IP; flags invariance violations (pass/fail), no stage-level localization. |
| 17 | `ho2001` | Ho, C.K., 2001, *IEEE Trans. Circuits Syst. I Fundam. Theory Appl.* | https://doi.org/10.1109/81.940182 | Crossref stores the first author as one string 'Chung Kin Ho'; printed as Ho, C.K. | Hierarchical block-level analog diagnosis (§2.2) | abstract: Hierarchical, block-level fault diagnosis of analog/mixed-signal ICs with test-point selection. |
| 18 | `hafed2002` | Hafed, M.M., 2002, *IEEE J. Solid-State Circuits* | https://doi.org/10.1109/4.991388 | Crossref: all fields agree | On-chip test core: stimulus generation and coherent digitisation (§2.2, §2.4) | abstract: On-chip test core that generates stimuli and coherently digitises periodic responses; high effective sample rate through coherent (sub-sample) acquisition. |
| 19 | `wibbenmeyer2007` | Wibbenmeyer, J., 2007, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2007.908343 | Crossref: all fields agree | On-chip test-signal generation for ADC BIST (§2.2) | abstract: BIST architecture with on-chip test-signal generation for high-speed ADCs. |
| 20 | `santin2019` | Santin, E., 2019, *IEEE Instrum. Meas. Mag.* | https://doi.org/10.1109/MIM.2019.8917897 | Crossref: all fields agree | ADC BIST overview incl. field testing (§2.2) | abstract: Overview: ADCs need testing after fabrication and, where possible, during field operation; test cost is a significant share of production cost. |
| 21 | `mohammedali2024` | Mohammedali, M.A., 2024, *J. Electr. Comput. Eng.* | https://doi.org/10.1155/jece/8824886 | Crossref: all fields agree | Online SAR-ADC gain/offset self-test (§2.2, §8.2) | abstract: Online detection and correction of SAR-ADC gain and offset errors. |
| 22 | `thirunakkarasu2015` | Thirunakkarasu, S., 2015, *IEEE Trans. Very Large Scale Integr. (VLSI) Syst.* | https://doi.org/10.1109/TVLSI.2014.2321761 | Crossref: all fields agree | Built-in self-calibration of SAR-ADC DAC mismatch (§2.2) | abstract: Built-in self-calibration of SAR-ADC DAC mismatch. |
| 23 | `meijer2001` | Meijer, G.C.M., 2001, *IEEE Sens. J.* | https://doi.org/10.1109/JSEN.2001.954835 | Crossref stores 'Guijie Wang' as one string; printed as Wang, G. | Sources of CMOS reference inaccuracy (§2.2) | abstract: CMOS voltage references: mismatch, 1/f noise and mechanical stress limit accuracy; dynamic element matching and auto-calibration mitigate them. |
| 24 | `aminian2000` | Aminian, M., 2000, *IEEE Trans. Circuits Syst. II Analog Digit. Signal Process.* | https://doi.org/10.1109/82.823545 | Crossref: all fields agree | NN diagnosis from wavelet/PCA features of impulse response (§2.3) | abstract: Backpropagation NN on wavelet/PCA features of the impulse response identifies faulty components. |
| 25 | `aminian2002` | Aminian, F., 2002, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2002.1017726 | Crossref: all fields agree | NN diagnosis of actual circuits; measured features closer together than simulated (§2.3) | abstract: NN diagnosis on measured (not simulated) circuits; reports that features from actual circuits lie closer together than in simulation. |
| 26 | `yuan2010` | Yuan, L., 2010, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2009.2025068 | Crossref stores full names as single strings; printed as Yuan, L.; He, Y.; Huang, J.; Sun, Y. | Kurtosis/entropy features for NN diagnosis (§2.3) | abstract: Kurtosis/entropy features of output signals as NN inputs. |
| 27 | `liu2017` | Liu, Z., 2017, *IEEE Trans. Ind. Inform.* | https://doi.org/10.1109/TII.2017.2690940 | Crossref: all fields agree | Deep belief network features for electronics-rich analog systems (§2.3) | abstract: FDI of electronics-rich analog systems cast as multiclass classification of output-signal features; variable operating conditions make it hard. |
| 28 | `zhao2018` | Zhao, G., 2018, *Measurement* | https://doi.org/10.1016/j.measurement.2018.02.044 | Crossref: all fields agree | Deep belief network for analog circuit diagnosis (§2.3) | title/record only: Deep belief network for analog-circuit fault diagnosis (cited only as an example of deep models). |
| 29 | `yang2020` | Yang, H., 2020, *IEEE Access* | https://doi.org/10.1109/ACCESS.2020.2968744 | Crossref: all fields agree | 1D-CNN on raw responses (§2.3, §8.2) | abstract: 1D-CNN learns features from raw output signals under soft faults. |
| 30 | `he2020` | He, W., 2020, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2020.2969008 | Crossref: all fields agree | GAN with wavelet spectra (§2.3) | abstract: Cross-wavelet spectral images and GANs for analog-circuit fault diagnosis. |
| 31 | `ji2021` | Ji, L., 2021, *IEEE Trans. Circuits Syst. I Regul. Pap.* | https://doi.org/10.1109/TCSI.2021.3076282 | Crossref: all fields agree | ResNet on STFT spectrum maps (§2.3, §8.2) | abstract: STFT spectrum maps of time-domain outputs classified by a ResNet. |
| 32 | `jia2021` | Jia, Z., 2021, *IEEE Trans. Ind. Electron.* | https://doi.org/10.1109/TIE.2020.3020252 | Crossref: all fields agree | Deep forest motivated by data/parameter demands of deep networks (§2.3) | abstract: Deep-forest classifier motivated by the parameter count, training effort and data demands of deep networks. |
| 33 | `zhou2025` | Zhou, N., 2025, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2025.3612648 | Crossref: all fields agree | Contrastive representation learning for soft faults (§2.3, §8.2) | abstract: Self-supervised contrastive representation learning with a 1D-CNN/attention encoder for soft faults. |
| 34 | `gao2025` | Gao, Z., 2025, *IEEE Internet Things J.* | https://doi.org/10.1109/JIOT.2025.3547957 | Crossref: all fields agree | Transfer learning for few-shot circuits (§2.3) | abstract: Transfer learning for few-shot circuit samples using circuit-structure priors. |
| 35 | `zhang2024` | Zhang, C., 2024, *Actuators* | https://doi.org/10.3390/act13090379 | Crossref: all fields agree | Domain adaptation because varying conditions alter circuit parameters (§2.3) | abstract: Varying external or internal conditions alter circuit parameters and reduce diagnostic accuracy; domain adaptation is proposed. |
| 36 | `liu2025` | Liu, X., 2025, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2025.3588964 | Crossref: all fields agree | Test-stimulus optimisation combined with CNN (§2.3) | abstract: Optimised test stimuli that amplify normal/faulty response differences, combined with a CNN. |
| 37 | `halgas2025` | Hałgas, S., 2025, *Electronics* | https://doi.org/10.3390/electronics14224427 | Crossref: all fields agree | Review of open problems in nonlinear analog diagnosis (§2.3) | abstract: Review: analog (nonlinear) circuit diagnosis remains unresolved after decades; covers testability, test selection and AI tools. |
| 38 | `qiu2023` | Qiu, S., 2023, *Sensors* | https://doi.org/10.3390/s23031305 | Crossref: all fields agree | Review of deep learning for industrial fault diagnosis (§2.3) | abstract: Review of deep learning for industrial fault diagnosis and prognosis. |
| 39 | `shen2012` | Shen, Z., 2012, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2012.2205509 | Crossref: all fields agree | FDIR of a self-validating sensor from output signals (§2.3) | abstract: Data-driven (RVM + PCA) failure detection, isolation and recovery for a self-validating sensor from its output signals. |
| 40 | `chen2025` | Chen, Y., 2025, *Measurement* | https://doi.org/10.1016/j.measurement.2024.116025 | Crossref: all fields agree | Review of self-validating sensors (§2.3) | title/record only: Recent review of self-validating sensor technology (cited as a pointer to the field). |
| 41 | `wang2026` | Wang, M., 2026, *IEEE Trans. Instrum. Meas.* | https://doi.org/10.1109/TIM.2026.3744022 | Crossref lists the article number as a range 3525214–3525214; printed as 3525214 | FDI for self-validating MOX sensor arrays with hardware electrical faults (§2.3) | abstract: Electrical faults caused by hardware failures distort sensor-array outputs; FDI method for concurrent faults. |
| 42 | `tosoni2024` | Tosoni, F., 2024, *IEEE Trans. Comput.* | https://doi.org/10.1109/TC.2023.3345135 | Crossref: all fields agree | Fault models for the analog side of smart/CPS systems (§2.3) | abstract: Fault models for the analog/heterogeneous side of smart systems, injected into combined behavioural simulations. |
| 43 | `ieee181` | IEEE Std 181-2011, 2011, *IEEE* | https://doi.org/10.1109/IEEESTD.2011.6016198 | Crossref: all fields agree | State levels and transition durations of pulse waveforms (§2.4, §4.3) | standard scope: Defines transition duration, state levels and the algorithms to compute them for two-state waveforms. |
| 44 | `gu2025` | Gu, M., 2025, *IEEE Open J. Solid-State Circuits Soc.* | https://doi.org/10.1109/OJSSCS.2024.3519486 | Crossref: all fields agree | Timing skew limits TI-ADC performance; calibration methods (§2.4) | abstract: Review: timing skew between sampling instants significantly limits ADC performance; calibration techniques classified. |
| 45 | `svatos2023` | Svatos, J., 2023, *Measurement* | https://doi.org/10.1016/j.measurement.2023.113392 | Crossref: all fields agree | Equivalent-time sampling with a microcontroller ADC (§2.4) | title/record only: Equivalent-time sampling implemented with a microcontroller ADC (cited for the existence of sub-sample timing techniques on MCU ADCs; title-level claim only). |
| 46 | `renczes2021` | Renczes, B., 2021, *IET Signal Process.* | https://doi.org/10.1049/sil2.12061 | Crossref: all fields agree | Sine fitting estimating phase with amplitude/offset (§2.4) | abstract: Least-squares four-parameter sine fit (phase among the fitted parameters) made non-iterative with predictable cost, as an alternative to the iterative IEEE-standard procedure. |
| 47 | `golub1973` | Golub, G.H., 1973, *SIAM J. Numer. Anal.* | https://doi.org/10.1137/0710036 | Crossref: all fields agree | Variable projection (§2.4, §4.3) | abstract: Variable projection: linear parameters eliminated in closed form from separable nonlinear least squares. |
| 48 | `golub2003` | Golub, G., 2003, *Inverse Probl.* | https://doi.org/10.1088/0266-5611/19/2/201 | Crossref: all fields agree | Variable projection review (§2.4, §4.3) | abstract: Review: eliminating the linear variables reduces the parameter space and improves conditioning. |
| 49 | `pedregosa2011` | Pedregosa, F., 2011, *J. Mach. Learn. Res.* | https://jmlr.org/papers/v12/pedregosa11a.html | Publisher page checked | scikit-learn software (§5) | publisher/software page: Software reference for the MLP implementation. |
| 50 | `kingma2015` | Kingma, D.P., 2015, *Proceedings of the 3rd International Conference on Learning Representations (ICLR)* | https://arxiv.org/abs/1412.6980 | Publisher page checked | Adam optimizer (§5) | publisher/software page: Optimizer used to train the MLP. |
| 51 | `tobin2017` | Tobin, J., 2017, *Proceedings of the 2017 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)* | https://doi.org/10.1109/IROS.2017.8202133 | Crossref: all fields agree | Randomising a nuisance parameter in simulation-based training (§5) | abstract: Randomising simulator parameters during training so that real data appear as another variation. |
| 52 | `iwana2021` | Iwana, B.K., 2021, *PLoS ONE* | https://doi.org/10.1371/journal.pone.0254841 | Crossref: all fields agree | Time-series data augmentation survey (§5) | abstract: Survey and taxonomy of time-series augmentation (including transformation-based methods such as time shifting/warping). |
| 53 | `ngspice47` | Ngspice Developers, 2026, ** | https://ngspice.sourceforge.io/docs/ngspice-47-manual.pdf | Publisher page checked | ngspice-47 simulator (§6.1) | publisher/software page: Circuit simulator used for the ngspice domain (ngspice-47). |
| 54 | `sokolova2009` | Sokolova, M., 2009, *Inf. Process. Manag.* | https://doi.org/10.1016/j.ipm.2009.03.002 | Crossref: all fields agree | Macro-averaged F-score definition (§6.4) | abstract: Definitions and properties of macro-averaged precision/recall/F-score for multiclass classification. |
| 55 | `field2007` | Field, C.A., 2007, *J. R. Stat. Soc. Ser. B Stat. Methodol.* | https://doi.org/10.1111/j.1467-9868.2007.00593.x | Crossref: all fields agree | Bootstrapping clustered data (§6.5) | abstract: Properties of bootstraps for clustered (one-way) data; supports resampling whole clusters. |
| 56 | `davison1997` | Davison, A.C., 1997, *Cambridge University Press* | https://doi.org/10.1017/CBO9780511802843 | Crossref: all fields agree | Bootstrap percentile intervals (§6.5) | abstract: Bootstrap confidence intervals (percentile intervals). |

## 5. Cross-check with the independent reference set on the project branch

`manuscript_submission/cloud_draft/refs.py` (53 references) shares 17 DOIs with this list. For all 17, year, volume and pages agree. The only differing field was the spelling of Louërat in Pavlidis et al.: Crossref has "Louerat", while the author's own version (HAL) has "Louërat". The author's spelling is now printed. The cross-check also corrected two dispositions of the earlier candidate list (Section 6).

## 6. Earlier candidate entries

| Earlier key | Finding | Action |
|---|---|---|
| `aminian2000wavelet` | Confirmed; DOI 10.1109/82.823545 added | Kept |
| `sun2004wavelet` | Exists; the old author order was wrong (Crossref: He, Y.; Tan, Y.; Sun, Y.) and the volume (151) was missing | Not cited; more direct sources cited instead |
| `zhao2018dbn` | Confirmed | Kept |
| `mir2006bist` | Confirmed; DOI added; Crossref title 'Built-in-self-test techniques for MEMS' | Kept |
| `deb2002bist` | Exists (ITC 2002, pp. 1075–1084) | Not cited; superseded by the 2021 review |
| `henry1993svs` | Exists: Henry, M.P.; Clarke, D.W., Control Eng. Pract. 1993, 1, 585–610, DOI 10.1016/0967-0661(93)91382-7 (Crossref record found in the cross-check; an earlier, wrong DOI had been tried) | Not cited; self-validating sensors are covered by [39–41]. The earlier note that the record could not be confirmed is withdrawn |
| `ieee1241` | Edition resolved: IEEE Std 1241-2010, published 2011 | Kept |
| `jin2005seir` | Confirmed; DOI added | Kept |
| `ieee181` | Edition resolved: IEEE Std 181-2011 | Kept |
| `golub1973varpro` | Confirmed; DOI added | Kept |
| `field2007clustered` | Confirmed | Kept |
| `efron1993bootstrap` | Exists: Chapman & Hall 1993 (Springer DOI 10.1007/978-1-4899-4541-9; a CRC re-issue has DOI 10.1201/9780429246593) | Not cited; Davison & Hinkley (1997) covers the percentile intervals used |
| `ngspice47` | Version-47 manual listed on the ngspice documentation page; ngspice-47 was installed on the run machine before the run | Kept |

## 7. Statements removed or limited because a source could not support them

- No "first", "state-of-the-art" or superiority claim is made. The gap statement (Section 2.5) is limited to the literature reviewed and to simulation.
- For [1], the cost statement reads "a large share of product cost".
- [45] is cited only for the existence of equivalent-time sampling with microcontroller ADCs (title/record check).
- [7] is characterized only as far as its abstract states; the text says so.
- The comparison with [14] was revised after reading its full text (Section 2 above).

## 8. Limits

Support was checked against the full texts of [14], [15] and [16] and against abstracts or records for all other references. Page ranges and article numbers follow Crossref. IEEE TIM and OJSSCS items carry Crossref page ranges such as 1–9, which are reproduced as listed.
