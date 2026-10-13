# DualGuard-FI — final novelty kill-screen before compute

Status: **SURVIVES NARROWLY AS A CANDIDATE; NOVELTY NOT YET PROVEN**
Date: 2026-10-13
Target domain: Electronics / embedded systems / hardware security / embedded AI
Target application workload: embedded object detection

## Candidate research question

Can an **independent secondary MCU core** detect and contain **physically induced silent object-detection failures** on the primary core by fusing low-cost execution, internal-activation, and semantic witnesses, with materially better critical-SDC coverage than any witness alone and with bounded embedded overhead?

Working name:
**DualGuard-FI**

Working title:
**Cross-Core Runtime Detection and Containment of Physical Fault-Induced Silent Failures in Embedded Object Detection**

## What is already prior art and MUST NOT be claimed as novelty

1. **Physical clock-glitch attacks against neural networks on microcontrollers**
   - Fukuda, Yoshida, Fujino, IEICE Trans. Fundamentals, 2022, DOI 10.1587/transfun.2021CIP0015.
   - Sensors 2025, "Clock Glitch Fault Attacks on Deep Neural Networks and Their Countermeasures", DOI 10.3390/s25092793.
   - These demonstrate physical glitch-induced DNN misclassification on MCU-class devices.

2. **Fault injection / resilience studies for object detectors**
   - Qutub et al., "Hardware Faults that Matter: Understanding and Estimating the Safety Impact of Hardware Faults on Object Detection DNNs".
   - Electronics 2026, "Evaluating and Enhancing YOLOv8's Soft Error Resilience" / YOLO-FI.
   - Therefore fault injection into YOLO/object detection by itself is not novel.

3. **Low-cost runtime monitoring of DNN hidden activations**
   - Geissler et al., SafeComp 2023, "A Low-Cost Strategic Monitoring Approach for Scalable and Interpretable Error Detection in Deep Neural Networks", DOI 10.1007/978-3-031-40923-3_7.
   - Uses selected hidden-layer activation quantile markers and reports up to ~96% precision / ~98% recall with very low overhead.
   - Therefore an activation-witness monitor alone is not novel.

4. **Runtime monitoring of object-detector outputs**
   - Yan et al., Software: Practice and Experience 2026, "Runtime Monitoring Abnormalities in Object Detection With Spatial and Temporal Abstractions", DOI 10.1002/spe.70031.
   - Therefore spatial/temporal semantic consistency alone is not novel.

5. **General SDC runtime monitoring**
   - Hardware-counter and checksum/ABFT-style SDC detection exists.
   - Therefore timing/checksum/performance-counter monitoring alone is not novel.

6. **Dual-core MCU inference architectures**
   - Prior work already uses asymmetric dual-core MCUs for AI inference/offload.
   - Therefore "M7 runs AI, M4 does another task" is not novelty.

## Candidate gap that remains

The only defensible candidate gap is the **specific cross-layer integration under real physical fault injection**:

- embedded object detection rather than classification;
- physically induced timing/voltage/clock faults rather than only synthetic bit flips;
- independent asymmetric secondary core as a runtime security/containment island;
- fusion of three complementary witness families:
  1. execution/timing/control-flow witness,
  2. compact internal-activation witness,
  3. object-detection semantic/temporal witness;
- safety-oriented critical-SDC definition at detection level;
- containment action (reject / rerun / safe fallback), not only offline fault characterization;
- real embedded latency/energy/false-alarm overhead;
- comparison against each witness alone and against a SafeComp-style activation monitor.

This is a **candidate novelty intersection**, not a proven novelty claim.

## Why the physical experiment is mandatory

If the final study uses only software bit flips, the novelty becomes weak because:
- YOLO/object-detector software fault injection already exists;
- low-cost internal activation monitoring already exists;
- semantic runtime monitoring already exists.

Therefore a final paper MUST include a real physical fault-injection campaign or an equivalently strong hardware fault mechanism.

Acceptable later-stage physical mechanisms:
- clock glitch;
- voltage glitch if platform access allows controlled/safe injection;
- externally controlled clock fault path on a suitable target board.

The feasibility and safety of physical fault injection are later gates. G0 does **not** authorize unsafe board modification.

## G0 purpose

G0 is a cheap screening test only.

It asks:
> Do the three witness classes contain complementary information about **critical silent object-detection corruptions** under a controlled software fault-emulation campaign?

If not, there is no reason to build the cross-core hardware system.

## G0 novelty-kill conditions

Stop the direction immediately if any of these occur:
- a single prior monitor class already matches fused performance within 3 pp at the required FPR;
- fused monitor cannot reach the frozen critical-SDC detection target;
- the witness extraction overhead estimate is >10% before cross-core communication;
- critical SDCs are too rare under the frozen emulation campaign to support a meaningful study;
- physical-validation feasibility later proves impractical.

## Publication framing if later gates survive

Electronics-first framing:
- embedded electronics architecture;
- hardware-fault security/reliability;
- asymmetric dual-core MCU;
- object detector as safety-critical workload;
- physical fault injection and containment.

Do not frame the paper as "a new YOLO model".

## Current decision

**Proceed to G0 only.**
No long training, no physical glitching, no new detector training, and no paper-writing phase are authorized before G0 passes.
