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
