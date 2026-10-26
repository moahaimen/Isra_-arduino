# Abstract (draft, MDPI Sensors, ≤ 200 words)

**Title:** Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Neural-Network Classification

**Abstract:** Locating a fault in a mixed-signal sensor interface—in the sensor, the analog front-end (AFE) or the analog-to-digital converter (ADC)—is ill-posed from the digitized output alone. We propose an active self-test that switches two known two-level references into the chain, one replacing the sensor at the AFE input and one bypassing the AFE at the ADC input, making AFE and ADC transfer errors separately observable. A monitor channel measures the reference levels, and phase-robust transient descriptors, obtained from a whole-transient fit with a free edge time, remove the dependence on the unknown phase between reference edges and ADC samples. A compact multilayer perceptron (6,868 parameters) classifies the faulty layer and nine fault classes. In a pre-registered simulation study with 3 unseen dataset seeds and paired behavioral and ngspice test sets with component tolerances, noise and 12-bit quantization, the method retained at least 0.916 of its nominal layer macro-F1 under ±20% reference-amplitude changes and 0.924 with a ±5% monitor error, kept AFE–ADC cross-confusion at or below 0.089, varied by at most 0.011 across edge phases (fixed-sample descriptors: 0.081), and lost 0.002 (95% CI [-0.003, +0.006]) from behavioral to ngspice data, against 0.119 in the previous design stage. All results are simulation-based.

**Keywords:** built-in self-test; mixed-signal sensor interface; fault diagnosis; reference monitoring; analog front-end; analog-to-digital converter; sampling phase; neural network; ngspice

---
*Word count is checked by `scripts/qc.py`. Numbers are filled from `NUMBER_PROVENANCE_MDPI.csv`; edit this template, not the rendered file.*
