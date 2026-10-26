# Final paper package

**Working title:** Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Deep Learning
**Target:** MDPI *Sensors* (Article)
**Built:** 2026-10-14 by `python3 -m src.build_paper_package` (figures, tables and manuscript are regenerated from the frozen result files; nothing is typed by hand)
**Basis:** phase-robust validation, decision **GO** (`phase_robust_final/FINAL_PHASE_ROBUST_REPORT.md`). No model was retrained and no earlier result was changed to build this package.

## 1. Contents

| file | what it is |
|---|---|
| `MANUSCRIPT_SENSORS_DRAFT.md` | complete manuscript draft in MDPI *Sensors* structure (abstract to appendices); every number filled from result files |
| `PAPER_TABLES.csv` | every table cell in long format with its manuscript table number and source file(s) |
| `NUMBER_PROVENANCE.csv` | every number used in the text: token, value, source file, exact key/locator |
| `PAPER_FIGURE_MAP.md` | figure ↔ file ↔ data source ↔ generator, and which figures are results vs illustrative |
| `REPRODUCIBILITY_CHECKLIST.md` | environment, seeds, frozen protocols, commands for every stage, checks |
| `figures/` | 9 figures, PDF (vector) + PNG (300 dpi), named by content |
| `figures_manuscript_numbering/` | the same figures renamed in manuscript order (`Figure01_…` to `Figure09_…`) |
| `figure_data/` | data behind the illustrative / development-seed panels and the derived confusion matrices |
| `templates/` | manuscript and package templates (numbers are double-brace placeholders filled by the builder) |

Manuscript numbering: T1 → Table 1, ARMS → Table 2, T2 → Table 3, TG → Table 4, T7 → Table 5, T3 → Table 6, T4 → Table 7, T5 → Table 8, T9 → Table 9, T9b → Table 10, T6 → Table 11, T10 → Table 12, T8 → Table 13, T11 → Table A1, DESC → Table B1. Figures: fig01 → Figure 1, fig02 → Figure 2, fig03 → Figure 3, fig04 → Figure 4, fig07 → Figure 5, fig05 → Figure 6, fig09 → Figure 7, fig06 → Figure 8, fig08 → Figure 9.

## 2. Contributions and the evidence for each

| contribution | key evidence (from the frozen results) | where |
|---|---|---|
| Two-point active self-test separates AFE and ADC faults | AFE–ADC cross-confusion ≤ 0.089 at ±20% reference amplitude in both domains; AFE recall ≥ 0.863, ADC recall ≥ 0.773; beats passive, single-probe, AFE-only and ADC-only baselines in all 70 pre-registered comparisons (smallest CI lower bound +0.112) | §4.3–4.4, Tables on separation and baselines, Figure on AFE/ADC separation; `phase_robust_results/decision_rules.json` (B, C) |
| Settled-plateau + phase-robust transient descriptors | layer macro-F1 range over five edge phases 0.005–0.011 (Revision-1: 0.081 behavioral, 0.081 ngspice); descriptors alone +0.042 [+0.033, +0.051] | §3.2, §4.1, §5; `attribution_arms.csv`, `attribution_comparisons.csv` |
| Reference monitor handles known reference drift | retention ≥ 91.6% of nominal at ±20% (known / E ≤ 2%), ≥ 92.4% at E = ±5%; without monitor 0.310 / 0.237 at ×0.8 / ×1.2 | §2.3, §4.2; `decision_rules.json` (A, D), `no_monitor_control.json`, `amplitude_curves.csv` |
| Neural-network classifier for layer and fine-fault diagnosis | MLP 20-96-48, 6,868 / 7,113 parameters, 6,720 MACs per layer decision; nominal layer macro-F1 0.659 | §3.4, §4.6; `timing_and_parameters.json` |
| Behavioral-to-ngspice validation across amplitudes, phases, tolerances, noise, quantisation | transfer loss 0.002 [-0.003, 0.006] (limit 0.10; previous stage 0.119); 41,634 per-sample ngspice runs | §3.5, §4.5; `decision_rules.json` (E), `reference_monitor_results/decision_rules.json` |

## 3. Items the brief asked to report, and where they are

| item | reported in |
|---|---|
| old Revision-1 failure under sampling-phase changes | §1, §4.1 (layer macro-F1 0.649 → 0.568 from ψ = 0 to 0.999), Appendix A, Figure on phase effect |
| phase-robust descriptor improvement | §4.1, §5 (+0.042 behavioral, +0.041 ngspice) |
| monitor performance at 0%, ±1%, ±2%, ±5% | §4.2, amplitude table and robustness figure |
| ±20% reference-amplitude tests | §4.2–4.4 |
| behavioral-to-ngspice transfer | §4.5, transfer table, behavioral-vs-ngspice figure |
| AFE–ADC confusion | §4.4, separation table, Figures on separation and robustness |
| per-class recall | §4.4, per-class tables and figure (healthy recall 0.142 stated as a limitation) |
| ablations: old descriptors, phase randomisation, mixed-domain training (+ Revision-2 conditioning, TCN) | §5, ablation table and figure |
| parameter count and inference complexity | §3.4, §4.6, complexity table |

## 4. What the paper does NOT claim

* No hardware validation, prototype or measurement; no energy, power, area or cost figures.
* No universal robustness: only the simulated factor ranges (±20% amplitude, E ≤ ±5%, the listed tolerances, one common edge phase per record).
* No improvement from Revision-2 conditioning (it was worse than the unconditioned descriptors; ablation only).
* No superiority of a temporal network over the MLP.
* The ngspice domain is not an independent validation of physical behaviour (both domains are first-order models by the same authors; noise-free agreement 0.14–0.27 mV).
* No claim of a deployable healthy/faulty detector (healthy recall 0.142).
* No priority/novelty claim until a systematic literature search is done.

## 5. Open items before submission

1. **References:** the reference list is placeholders ([REF-1…6]); a systematic IEEE Xplore/Scopus search is required and the research-gap paragraph must be rewritten against it. No citation has been invented.
2. **Title wording:** the classifier is a compact two-hidden-layer MLP. "Using Deep Learning" may be challenged by reviewers; consider "Using Neural-Network Classification" or "Using Learned Descriptors". The manuscript body describes the model accurately either way.
3. **Hardware or higher-fidelity circuit evidence:** a SPICE model with real op-amp, switch (charge injection) and reference-settling models, or a hardware pilot, would address the main limitation.
4. **Authors, affiliations, funding, CRediT, data-repository link, conflicts** are placeholders.
5. **Formatting:** convert the Markdown draft to the MDPI Word/LaTeX template; tables are already in final form; figures are vector PDFs.
6. **Language editing** of the draft.

## 6. Notes on numbers

* All numbers come from the files named in `NUMBER_PROVENANCE.csv` and `PAPER_TABLES.csv`. Values are means over three dataset seeds (each the mean of two initialisation seeds); intervals are pooled 95% paired cluster-bootstrap CIs (5000 resamples).
* Some summary CSVs store four decimals; a table value can therefore differ by 0.001 in the third decimal from the same quantity taken from a decision file (e.g. N = 0.659 in the text vs. ×1.0 "PRr known" in the amplitude table).
* Panels marked "development seed" use seed 20261097, which was never part of validation; they illustrate mechanisms and are not used for any decision.
