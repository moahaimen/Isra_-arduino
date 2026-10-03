# Q1 novelty screen — round 2 (2026-10-03)

Status: **novelty-first screening only. No algorithm is authorized yet.**

Goal: avoid repeating R3/CAGE/D1 by killing directions before implementation. Five distinct directions were screened against recent and established prior art. A direction survives only if the exact problem/mechanism space is not already substantially occupied.

## Executive decision

| ID | Direction | First-pass decision | Why |
|---|---|---|---|
| S1 | Drift-aware self-calibrating M4 watcher using M7 feedback | KILL | Edge video model drift detection/adaptation and on-edge teacher/student active learning are already established. |
| S2 | Uncertainty-aware early exit / adaptive tiling / ROI escalation | KILL | Adaptive object-detection early exits, energy-aware early exiting, adaptive tiling, and ROI selective inference are already direct prior art. |
| S3 | Hard temporal-coverage / maximum first-detection-delay scheduling under energy | KILL as primary novelty | Worst-case event-detection delay/temporal coverage, hard-deadline edge scheduling, and even network-calculus analysis of real-time object detection already exist. |
| S4 | **Interference-aware asymmetric dual-core MCU vision isolation** | **SURVIVES FIRST PASS** | Generic multicore interference is known, but no indexed work was found in this pass that characterizes and controls M7↔M4 shared-resource/power-domain interference specifically for an always-on MCU vision pipeline on STM32H747-class asymmetric MCUs. Requires a deeper K0.5 audit before any algorithm. |
| S5 | Conformal/risk-limited wake suppression with statistical miss guarantees | KILL as primary novelty | Conformal cascades, risk-controlled early exit, edge/cloud conformal routing, and conformal object detection already occupy the core routing/guarantee idea. A temporal MCU implementation alone would likely be application-level. |

Absence from search is **not** proof of novelty. S4 is only a survivor for deeper audit.

---

## S1 — Drift-aware self-calibrating M4 watcher

Hypothesis considered:
- M4 watcher detects distribution/scene drift.
- M7 acts as a stronger teacher and periodically labels/validates M4 decisions.
- trigger thresholds or a small watcher are adapted online to keep false wake and miss rates stable.

### Prior art collision
Direct overlaps include:
- EdgeMA: detects domain shift in real-time edge video analytics and adapts the deployed model.
- Domain-adaptive online active learning for edge video analytics: teacher + student coexist on the edge, key frames trigger teacher execution / retraining.
- Recent on-device concept-drift surveillance frameworks.

### Decision
**KILL.** The architecture “cheap edge model monitors/adapts under drift using a stronger model or drift detector” is already established. Porting it to M4/M7 would not create enough conceptual distance.

References:
- EdgeMA, arXiv:2308.08717.
- Boldo et al., IEEE TCAD 2024, DOI 10.1109/TCAD.2024.3453188.
- Future Generation Computer Systems 150 (2024), DOI 10.1016/j.future.2023.08.023.

---

## S2 — Uncertainty-aware early exit / adaptive tiling / ROI escalation

Hypothesis considered:
- M4 cheaply estimates spatial difficulty/uncertainty.
- M7 runs only selected tiles or chooses a shallow/deep detection path.
- budget is allocated according to uncertainty.

### Prior art collision
This space is heavily occupied:
- AdaDet explicitly performs uncertainty-based early exiting for object detection.
- E4 jointly optimizes early exits and energy behavior in edge video analytics.
- 2026 implementation-aware tiling work models latency/energy of tiled inference on edge hardware.
- Recent adaptive tiling systems run a coarse detector and infer only selected high-resolution ROIs.
- Edge video systems already crop/patch key regions to reduce compute.

### Decision
**KILL.** A new threshold, uncertainty score, or M4 implementation would be incremental.

References:
- AdaDet, IEEE TCDS 16(1), DOI 10.1109/TCDS.2023.3274214.
- E4, AAAI 2025, DOI 10.1609/aaai.v39i1.32104.
- Vago et al., IEEE Access 2026, DOI 10.1109/ACCESS.2026.3655109.
- EHCI, IEEE IoT Journal 2024, DOI 10.1109/JIOT.2024.3424235.

---

## S3 — Hard temporal coverage / maximum first-detection delay

Hypothesis considered:
- optimize not average recall/FPS but a guarantee on the maximum time an event/object may remain unseen;
- enforce it under a hard M7 duty/energy budget.

### Prior art collision
The metric sounds fresh in edge-video language, but the underlying concept is old and direct:
- sensor-network literature defines worst-case object-detection delay / stealth distance and energy-aware sensing schedules;
- temporal coverage has explicitly been defined as maximum delay from event occurrence to detection;
- network calculus has already been used to derive maximum delay/backlog bounds in an edge-enabled real-time object-detection platform;
- hard-deadline edge task scheduling is mature and continues to be published.

### Decision
**KILL as primary novelty.** It can remain an evaluation metric, but “guaranteed first-detection delay under energy” is not a sufficient core contribution by itself.

References:
- temporal-coverage adaptive sensing, Sensors 2009.
- visual sensor spatio-temporal coverage, IEEE TCSVT 2014, DOI 10.1109/TCSVT.2014.2329378.
- network-calculus real-time object detection analysis, ICC 2023.
- predictive edge computing with hard deadlines, DOI 10.1109/LANMAN.2018.8475056.

---

## S4 — Interference-aware asymmetric dual-core MCU vision isolation

### Problem
Our architecture assumes:
- Cortex-M4 continuously executes the low-cost watcher with predictable frame deadlines;
- Cortex-M7 wakes for expensive detector inference;
- M4 and M7 can therefore be treated as mostly independent compute domains.

On STM32H747 this assumption is not automatically valid. The cores share memories, bus/interconnect resources, peripherals and system-level clock/power dependencies. ST's own safety material explicitly treats cross-core shared-resource interference as something final applications must mitigate. The chip's low-power behavior is also domain-coupled: peripherals/memory allocation can prevent D1/D2/D3 from entering intended low-power states.

A potentially publishable systems question is therefore:

> **When a high-performance M7 performs vision inference, how much does it perturb the latency, deadline predictability, camera/DMA service and energy behavior of an always-on M4 watcher, and can a lightweight interference-aware memory/power/scheduling policy preserve M4 real-time service without materially sacrificing detector throughput?**

This is not generic “use two cores.” The candidate contribution would have to center on **measured interference channels + a general control/isolation mechanism**.

### What prior art already occupies
Do not overclaim:
- multicore shared-resource interference and WCET analysis are established research topics;
- RT-Gang++ and related systems mitigate memory/cache/GPU interference on larger heterogeneous multicore platforms;
- interference-generator methodology is established in safety-critical multicore evaluation;
- ST documentation already explains spatial/temporal separation requirements and power-domain behavior.

### Why it survives this first pass
In the searches performed for:
- STM32H747 / Cortex-M7 + Cortex-M4 memory interference,
- dual-core MCU shared SRAM/bus interference,
- Portenta H7 dual-core computer vision,
- heterogeneous MCU vision isolation,

no indexed research paper was found that combines all of:
1. an always-on low-power watcher on the smaller core;
2. bursty DNN inference on the larger core;
3. measured cross-core interference on watcher deadline/jitter and sensing/DMA;
4. power-domain side effects;
5. an interference-aware policy evaluated as an embedded-vision system.

The closest material found for STM32H747 is vendor documentation, safety guidance, implementation examples and engineering reports, rather than a paper solving this vision-specific systems problem.

### K0.5 mandatory deeper novelty audit
Before code:
- IEEE Xplore / ACM DL / Scopus-style searches for asymmetric MCU, mixed-criticality MCU, memory interference, vision/TinyML co-scheduling.
- Search STM32H7/H745/H747/H755/H757, Cortex-M7/M4, i.MX RT dual core, Alif Ensemble, NXP asymmetric MCUs.
- Read citations of multicore interference papers, not just keyword hits.

**Kill S4** if a prior system already characterizes a low-power watcher + high-performance DNN core and controls the same interference channels with an equivalent policy.

### K1 hardware effect-size kill test
Only after K0.5 survives.

On the real Portenta H7:
- M4 runs a fixed 10 Hz watcher workload with cycle counter timing.
- M7 conditions: sleep/idle, compute-only, TinyML inference, memory-streaming aggressor, camera/DMA activity where applicable.
- vary memory placement: private/Tightly Coupled or domain-local RAM where possible vs shared SRAM;
- vary IPC/shared-buffer design.

Measure:
- M4 median/P95/P99/WCET-like observed frame processing time;
- missed 100 ms watcher deadlines;
- RPC/shared-buffer latency;
- camera frame loss / DMA stalls if observable;
- M7 inference latency;
- board current/energy if measurement hardware is available.

Pre-registered first effect gate:
- **KILL** if realistic M7 inference changes M4 P99 watcher latency by <10% and causes no deadline misses across stress conditions;
- **interesting but weak** at 10–25%;
- **proceed** only if >=25% P99 inflation, repeatable deadline failures, or a similarly material power-domain/throughput coupling is observed and can be mitigated.

No algorithm before this measurement.

Primary references:
- STM32H745/755/747/757 dual-core architecture application note.
- STM32H7 dual-core safety manual (shared-resource spatial/temporal separation).
- STM32H747/757 advanced power management application note.
- Bechtel & Yun, “Analysis and Mitigation of Shared Resource Contention on Heterogeneous Multicore,” 2023.
- VanderLeest & Thompson, “Measuring the Impact of Interference Channels on Multicore Avionics,” 2021.

---

## S5 — Conformal / risk-limited wake suppression

Hypothesis considered:
- M4 decides whether an M7 invocation can be safely skipped;
- conformal calibration gives a finite-sample bound on the probability of suppressing a useful invocation;
- controller trades a risk level against M7 duty.

### Prior art collision
The core idea is now too occupied:
- conformal prediction is already used for object-detection uncertainty;
- conformal alignment has been proposed for deciding whether an edge model may answer or must defer to a stronger model;
- conformal cascades explicitly trade compute against statistical guarantees;
- 2026 work combines conformal risk control and learned routing for early exits;
- TinyHAR-UQ already combines microcontroller-ready conformal inference, early exits and battery-aware control.

Also, temporal video violates the simplest exchangeability assumptions, so a valid guarantee would need substantially new time-series theory rather than merely adding conformal calibration to the M4 trigger.

### Decision
**KILL as the primary paper idea.** Conformal tools may later be useful for calibration/evaluation of another genuinely new system, but should not be the novelty claim.

References:
- Reliable Inference in Edge-Cloud Model Cascades via Conformal Alignment, arXiv:2510.17543.
- TinyHAR-UQ, Internet of Things 36 (2026), 101889.
- Probabilistic Object Detection with Conformal Prediction, PMLR 329 (2026).
- “When to stop: Learned routing and risk control for early exit networks,” Knowledge-Based Systems, 2026.

---

# Round-2 conclusion

Four directions are closed before implementation. **S4 is the only first-pass survivor.**

This does **not** mean S4 is novel or Q1-ready. It means only that it has earned the next, cheaper step: a deep K0.5 literature audit. If that survives, run the small real-hardware K1 effect-size experiment. If either fails, close it immediately.

Do not implement an interference-aware scheduler yet.
