# Author confirmations required before submission

These items cannot be settled from the research package, the source code or the run records. Each is highlighted in yellow in `Phase_Robust_Sensors_Manuscript.docx`, or is otherwise noted below. Everything else in the manuscript has been completed and checked.

## 1. Author list, affiliation and corresponding author (highlighted on page 1)

The manuscript lists **Moahaimen Talib** as the sole author, because the earlier project brief ("Prepared by: Dr. Moahaimen Talib", 14 October 2026) names only this person. Please confirm:

- the complete author list and order, including any supervisor or co-author;
- each author's affiliation in MDPI format: department, institution, city, postal code, country;
- the corresponding author's e-mail address (it will be published), and ORCID iDs if available.

## 2. Author contributions (highlighted)

Add the CRediT statement, for example "Conceptualization, M.T.; Methodology, M.T.; …". For a sole author, MDPI accepts a single line listing all roles.

## 3. Funding (highlighted)

Either "This research received no external funding." or the funder name and grant number, spelled as in the Crossref Funder Registry.

## 4. Conflicts of interest (highlighted)

Either "The authors declare no conflicts of interest." or the declaration.

## 5. Data availability: public repository (highlighted)

The statement already says that the protocol, predictions, results, figure data and scripts are provided with the submission. Please decide:

- whether to also deposit them publicly (for example Zenodo) and add the DOI; and
- whether the simulator source code (`israa_final/active_sensor_diagnosis/src/`) will be released. It exists on your Mac, and its SHA-256 hashes match the freeze record, but it is not part of the evidence package. If it is released, the statement can say that the simulations and training can be rerun; at present it only claims that the statistics and figures can be regenerated from the saved predictions.

## 6. Generative-AI disclosure (please check the wording; not highlighted)

MDPI requires this disclosure in the Methods section and the Acknowledgments. The manuscript states that Claude Code (Anthropic) was used to implement the simulation, descriptor, training and analysis software, to draft the frozen protocols and stage reports, and, for this article, to search and verify the literature, regenerate figures, recompute statistics and draft the text.

This is based on the following evidence. A Claude Code session dated 14 October 2026 in the `israa_final` project wrote the source files (`phase_features.py`, `run_phase_robust.py`, `spice_phase.py`, `summarize_phase_robust.py` and others), and this manuscript was drafted with Claude Code. Please:

- confirm the description of your own role ("the author reviewed the design decisions, the code and the results");
- add the model or version information if MDPI's editor asks for it;
- add any other tool you used that is not mentioned.

## 7. Article title (optional)

The working title was refined to "Phase-Robust Active Self-Test for Fault Localization in Mixed-Signal Sensor Interfaces: A Simulation Study". The suffix makes the scope explicit, because no hardware was measured. Please confirm, or remove the suffix if you prefer the original working title.

## 8. Cover letter (not drafted)

MDPI requires a cover letter with two fixed statements: the manuscript is not under consideration elsewhere, and all authors approve the submission. Please also state any earlier submission of this work to an MDPI journal.

---

### Items that were resolved and need no action

- **Optimizer and early stopping.** The source code (`run_feasibility.py: _classifier`, hash unchanged since the freeze) uses Adam with scikit-learn's internal early stopping (15% of training rows, patience 35). The protocol's "unused validation split, no early-stopped model" refers to the separate 40-condition split. The manuscript describes both.
- **Software versions.** Python 3.12.12, scikit-learn 1.7.2 and ngspice-47 were recorded on the day of the run, on the same machine. Their installation dates (ngspice 3 Oct 2026; scikit-learn 18 Nov 2025) precede the run.
- **"Preregistered".** No external registration record exists, so the manuscript says "internally frozen protocol".
- **Headline numbers.** All values were recomputed from the saved predictions: 488 checks, 0 mismatches (`analysis/values_check.csv`).
