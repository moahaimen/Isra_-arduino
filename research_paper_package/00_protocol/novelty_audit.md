# Novelty audit (prior art 2020–2026, focus 2023–2026)

Scope: the proposed contribution is "a Cortex-M4 companion core predicts the minimum sufficient detector workload
a_t ∈ {SKIP, LOW, ROI, FULL} for the Cortex-M7, to preserve timely detection at lower M7 utilisation".
This audit builds on the project's own earlier screens, which were read in full:
`docs/R3_1_NOVELTY_REVIEW.md`, `docs/D1_DISCOVERY_REFRESH_KILL.md`, `docs/Q1_NOVELTY_SCREEN_ROUND2.md`
(branches research/q1-contribution-r3.1, research/q1-discovery-refresh-kill, research/q1-novelty-screen-round2),
plus a new search pass on 2026-10-26. Absence from search is not proof of novelty; abstracts were read, not full papers,
unless marked.

## Closest prior work and collisions

| # | Work | Year / venue | What it already does | Collides with |
|---|---|---|---|---|
| 1 | Lee, Kim & Hong, "Dual-Core-Based Microcontrollers Inference Design and Performance Analysis", DOI 10.1109/ACCESS.2024.3443406 | 2024, IEEE Access | Same STM32H747 class: camera input + pre-processing on Cortex-M4, DNN inference on Cortex-M7, SRAM4 shared buffer, concurrent execution, latency and power vs single core | the M4/M7 split itself (architecture claim) |
| 2 | AdaPyramid, Shi et al., DOI 10.1109/TMC.2023.3343448 | 2023/24, IEEE TMC | per-region choice of the cheapest detector configuration meeting a recall target; dedicated new-object detector; region restriction | "minimum sufficient workload" + ROI + timely new-object detection |
| 3 | FrameBoost, Yang et al., DOI 10.1109/ACCESS.2025.3558251 | 2025, IEEE Access | selects detector-trigger frames under resource constraints; names redundant and delayed triggers | SKIP vs run decision, timeliness |
| 4 | Albireo, Taherin, Cano, Ren, Wang, Kaeli, arXiv:2609.29648 | Aug 2026, preprint | per-frame skip/invoke from Kalman-filter uncertainty + lightweight empty-scene screen; BDD100K MOT; Jetson Thor/Orin; −12–18 % energy at ±1.2 pp AP50 | SKIP decision from cheap state, energy-aware detection |
| 5 | Statues, Kim, Kim & Ryu, DOI 10.1145/3665314.3670822 | 2024, ISLPED | pixel-difference score decides to skip the rest of the DNN on edge security devices; −44 % energy | motion-triggered SKIP on low-power devices |
| 6 | AdaDet, DOI 10.1109/TCDS.2023.3274214 | 2023, IEEE TCDS | uncertainty-based early exit for object detection | LOW/FULL depth selection |
| 7 | E4, DOI 10.1609/aaai.v39i1.32104 | 2025, AAAI | joint early-exit and energy optimisation for edge video analytics | energy-aware workload selection |
| 8 | Vago et al., DOI 10.1109/ACCESS.2026.3655109 | 2026, IEEE Access | implementation-aware latency/energy model of tiled inference on edge hardware | ROI/tile cost accounting |
| 9 | EHCI, DOI 10.1109/JIOT.2024.3424235 | 2024, IEEE IoT-J | coarse pass then high-resolution inference only on selected ROIs | ROI mode |
| 10 | Kaiser et al., arXiv:2409.17341 | 2024, preprint | sensor-side skipping of uneventful rows/regions with task feedback (BDD100K, ImageNet-VID) | ROI/SKIP at the sensor |
| 11 | ApproxDet (SenSys 2020, arXiv:2010.10754), SmartAdapt (CVPR 2022), LiteReconfig (EuroSys 2022) | 2020–2022 | content- and contention-aware choice among detector branches (input resolution, proposals, detect vs track interval) under a latency budget, predicted from cheap content features | the whole "predict the cheapest sufficient configuration" idea (pre-2023 but direct) |
| 12 | Remix, MobiCom 2021 | 2021 | budget-driven non-uniform image partition: more compute on regions likely to hold objects | ROI allocation under budget |
| 13 | Conformal routing / risk-controlled early exit (arXiv:2510.17543; KBS 2026; TinyHAR-UQ, IoT 36 (2026) 101889) | 2025–2026 | statistically controlled defer/skip decisions, including MCU-ready early exits | guarantees on SKIP/LOW decisions |
| 14 | Temporal-coverage / worst-case detection-delay scheduling (TCSVT 2014; ICC 2023 network calculus) | older + 2023 | maximum time an event stays undetected under an energy budget | timely-first-detection objective |

## Verdict

* **Direct collision on the mechanism.** Choosing per frame among skip / reduced resolution / ROI / full detection from cheap
  content features, to meet an accuracy or timeliness target at minimum compute, is occupied by #2, #3, #11, #12 and,
  for SKIP alone, #4 and #5. The project's own round-2 screen already killed this direction (S2: "adaptive tiling / ROI /
  early exit") and the timeliness objective (S3).
* **Direct collision on the architecture.** The M4 front end + M7 detector split on STM32H747 is #1.
* **What is left** is the intersection "this mechanism, on an asymmetric MCU, with the predictor on the small core and
  measured M7 utilisation". That is a platform study. It can support an application/engineering paper if the hardware
  numbers are strong, but it is not a new mechanism and would be weak as the primary Q1 contribution.
* No 2023–2026 work was found that reports a **privileged-oracle bound** for four-mode selection on an MCU; that is an
  evaluation device, not a contribution by itself.

Novelty risk: **high**. This audit does not stop the work by itself (the prompt stops on the oracle gate), but any GO must be
read together with it.

## Search record (2026-10-26)

Queries: content-aware adaptive input resolution detection edge 2024; adaptive configuration skip/low/ROI/full energy embedded
2025; MCU TinyML adaptive inference dual-core M7/M4 2025; ApproxDet/LiteReconfig follow-ups 2023–2024; ROI selective inference
low-power camera frame skipping YOLO 2024; ROI detection microcontroller always-on 2024–2025; per-frame resolution selection
predictor 2023. Abstracts of #4, #5, #10, #12 and arXiv:2606.02894 (multi-board MCU fusion, not a collision) were fetched.
