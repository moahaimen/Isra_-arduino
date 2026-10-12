# TopoEMI-ZS — novelty screen and target framing

Status: **candidate only; novelty not yet proven**.

Target journal requested by supervisor: **MDPI Sensors**, preferably the Electronic Sensors / sensing-measurement scope.

Working title:
**Layout-Conditioned Zero-Shot Phaseless EMI Source Localization from Sparse Near-Field Measurements**

## What is NOT novel enough by itself

Do not claim novelty for any of the following alone:

- EMI/EMC near-field scanning;
- equivalent-dipole source reconstruction;
- phaseless source reconstruction;
- sparse near-field scanning;
- compressive-sensing EMI localization;
- neural-network source reconstruction;
- physics-informed near-field reconstruction;
- probe-height correction/calibration;
- PCB source reconstruction from measured near fields.

These areas already have direct prior art.

## Closest prior art that must be treated as strong competition

1. **Ma et al., Sensors 2026, 26, 939**, "A Phaseless Source Reconstruction Method Based on Adam Optimization Algorithm Combined with Regularization", DOI 10.3390/s26030939.
   - phaseless equivalent-dipole source reconstruction;
   - Adam + L2;
   - simulation and physical PCB validation.

2. **Wang et al., IEEE Transactions on Electromagnetic Compatibility 2025, 67(1), 158–173**, "Bayesian Compressive Sensing Enabled EMI Source Localization in Shielding Enclosures From Complex and Phaseless Near-Field Scanning", DOI 10.1109/TEMC.2024.3482849.
   - sparse/compressive source localization;
   - complex and phaseless near-field data;
   - must be considered a strong classical baseline conceptually.

3. **Ma et al., IEEE Transactions on Electromagnetic Compatibility 2025**, "Reconstruction of EMI Sources for PCBs Based on Adaptive Differential Evolution Algorithm", DOI 10.1109/TEMC.2025.3605016.
   - phaseless PCB source reconstruction using L-SHADE / adaptive differential evolution.

4. **Zhang et al., International Journal of Circuit Theory and Applications 2024, 52(2), 523–535**, "A highly accurate and robust source reconstruction method of printed circuit boards based on complex-valued neural network", DOI 10.1002/cta.3802.
   - neural-network PCB source reconstruction;
   - comparison against Tikhonov.

5. **Han et al., IEEE Transactions on Instrumentation and Measurement 2025, vol. 74, 2540108**, "A Field Reconstruction Method for EMI Near-Field Scanning Based on Wave Equation-Informed Neural Network", DOI 10.1109/TIM.2025.3585216.
   - physics-informed DL near-field reconstruction.

6. **Feng et al., IEEE Antennas and Wireless Propagation Letters 2024, 23, 3937–3941**, "Multi-frequency and Multi-component Sparse Near-Field Scanning Based on Active Machine Learning".
   - sparse near-field scanning.

7. **Active-Learning-Based Sparse Near-Field Scanning With Time-Domain Current Measurement for Conductive Coupling Path Visualization**, IEEE TIM 2024, DOI 10.1109/TIM.2024.3363792.
   - active-learning sparse scanning for EMI coupling-path visualization.

## Remaining candidate gap

The candidate gap is deliberately narrower:

> **Amortized, layout-conditioned localization of multiple EMI sources on a completely unseen PCB/layout from sparse, phaseless near-field measurements, with explicit robustness to practical scan nuisance variables, without target-board retraining.**

The intended distinction is not "deep learning instead of regularization." It is:

- train across many board/layout graphs;
- test on an unseen layout family and unseen board instances;
- condition inference on the target layout/trace/component geometry;
- use only a sparse subset of phaseless near-field samples;
- infer a sparse set of source locations and strengths;
- do not retrain on the target board;
- evaluate under scan-height, probe-gain and XY-registration perturbations;
- compare fairly with target-specific phaseless inverse solvers.

K0 must determine whether this intersection produces a material advantage. If it does not, the project is stopped.

## Sensors framing if the project survives

The paper must remain a **measurement/sensing paper**, not a generic GNN paper:

- near-field probe measurements are the sensing modality;
- sparse measurement reduction is an explicit objective;
- phaseless acquisition reduces measurement complexity;
- source localization/reconstruction is the sensing inverse problem;
- calibration and positioning perturbations are part of robustness;
- final paper requires physical or at minimum high-fidelity full-wave validation; synthetic K0 alone is not publishable.

No claim of novelty or publishability is made until K0 and the later literature/full-wave/measurement gates pass.
