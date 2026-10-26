# Final paper package

**Working title:** Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Deep Learning
**Target:** MDPI *Sensors* (Article)
**Built:** {{BUILD_DATE}} by `python3 -m src.build_paper_package` (figures, tables and manuscript are regenerated from the frozen result files; nothing is typed by hand)
**Basis:** phase-robust validation, decision **{{DECISION}}** (`phase_robust_final/FINAL_PHASE_ROBUST_REPORT.md`). No model was retrained and no earlier result was changed to build this package.

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

Manuscript numbering: [[TABLE_NUMBERS]]. Figures: [[FIGURE_NUMBERS]].

## 2. Contributions and the evidence for each

| contribution | key evidence (from the frozen results) | where |
|---|---|---|
| Two-point active self-test separates AFE and ADC faults | AFE–ADC cross-confusion ≤ {{C_MAX}} at ±20% reference amplitude in both domains; AFE recall ≥ {{C_MIN_AFE_REC}}, ADC recall ≥ {{C_MIN_ADC_REC}}; beats passive, single-probe, AFE-only and ADC-only baselines in all {{B_N}} pre-registered comparisons (smallest CI lower bound {{B_MIN_CI}}) | §4.3–4.4, Tables on separation and baselines, Figure on AFE/ADC separation; `phase_robust_results/decision_rules.json` (B, C) |
| Settled-plateau + phase-robust transient descriptors | layer macro-F1 range over five edge phases {{G_PRR_MIN}}–{{G_PRR_MAX}} (Revision-1: {{G_R1_BH}} behavioral, {{G_R1_SP}} ngspice); descriptors alone {{ATT_BH_DESC}} {{ATT_BH_DESC_CI}} | §3.2, §4.1, §5; `attribution_arms.csv`, `attribution_comparisons.csv` |
| Reference monitor handles known reference drift | retention ≥ {{A_MIN_RET_PCT}}% of nominal at ±20% (known / E ≤ 2%), ≥ {{D_MIN_RET_PCT}}% at E = ±5%; without monitor {{CTL_U_X08}} / {{CTL_U_X12}} at ×0.8 / ×1.2 | §2.3, §4.2; `decision_rules.json` (A, D), `no_monitor_control.json`, `amplitude_curves.csv` |
| Neural-network classifier for layer and fine-fault diagnosis | MLP 20-96-48, {{PARAMS_LAYER}} / {{PARAMS_FAULT}} parameters, {{MACS_LAYER}} MACs per layer decision; nominal layer macro-F1 {{N_BH}} | §3.4, §4.6; `timing_and_parameters.json` |
| Behavioral-to-ngspice validation across amplitudes, phases, tolerances, noise, quantisation | transfer loss {{E_DROP}} [{{E_DROP_LO}}, {{E_DROP_HI}}] (limit 0.10; previous stage {{PREV_E_DROP}}); {{N_SPICE_TOTAL}} per-sample ngspice runs | §3.5, §4.5; `decision_rules.json` (E), `reference_monitor_results/decision_rules.json` |

## 3. Items the brief asked to report, and where they are

| item | reported in |
|---|---|
| old Revision-1 failure under sampling-phase changes | §1, §4.1 (layer macro-F1 {{ARM_BH_R1_P0}} → {{ARM_BH_R1_P999}} from ψ = 0 to 0.999), Appendix A, Figure on phase effect |
| phase-robust descriptor improvement | §4.1, §5 ({{ATT_BH_DESC}} behavioral, {{ATT_SP_DESC}} ngspice) |
| monitor performance at 0%, ±1%, ±2%, ±5% | §4.2, amplitude table and robustness figure |
| ±20% reference-amplitude tests | §4.2–4.4 |
| behavioral-to-ngspice transfer | §4.5, transfer table, behavioral-vs-ngspice figure |
| AFE–ADC confusion | §4.4, separation table, Figures on separation and robustness |
| per-class recall | §4.4, per-class tables and figure (healthy recall {{REC_L_BH_PRR_HEALTHY}} stated as a limitation) |
| ablations: old descriptors, phase randomisation, mixed-domain training (+ Revision-2 conditioning, TCN) | §5, ablation table and figure |
| parameter count and inference complexity | §3.4, §4.6, complexity table |

## 4. What the paper does NOT claim

* No hardware validation, prototype or measurement; no energy, power, area or cost figures.
* No universal robustness: only the simulated factor ranges (±20% amplitude, E ≤ ±5%, the listed tolerances, one common edge phase per record).
* No improvement from Revision-2 conditioning (it was worse than the unconditioned descriptors; ablation only).
* No superiority of a temporal network over the MLP.
* The ngspice domain is not an independent validation of physical behaviour (both domains are first-order models by the same authors; noise-free agreement {{DEV_AGREE_MIN}}–{{DEV_AGREE_MAX}} mV).
* No claim of a deployable healthy/faulty detector (healthy recall {{REC_L_BH_PRR_HEALTHY}}).
* No priority/novelty claim until a systematic literature search is done.

## 5. Open items before submission

1. **References:** the reference list is placeholders ([REF-1…6]); a systematic IEEE Xplore/Scopus search is required and the research-gap paragraph must be rewritten against it. No citation has been invented.
2. **Title wording:** the classifier is a compact two-hidden-layer MLP. "Using Deep Learning" may be challenged by reviewers; consider "Using Neural-Network Classification" or "Using Learned Descriptors". The manuscript body describes the model accurately either way.
3. **Hardware or higher-fidelity circuit evidence:** a SPICE model with real op-amp, switch (charge injection) and reference-settling models, or a hardware pilot, would address the main limitation.
4. **Authors, affiliations, funding, CRediT, data-repository link, conflicts** are placeholders.
5. **Formatting:** convert the Markdown draft to the MDPI Word/LaTeX template; tables are already in final form; figures are vector PDFs.
6. **Language editing** of the draft.

## 6. Notes on numbers

* All numbers come from the files named in `NUMBER_PROVENANCE.csv` and `PAPER_TABLES.csv`. Values are means over three dataset seeds (each the mean of two initialisation seeds); intervals are pooled 95% paired cluster-bootstrap CIs ({{N_BOOT}} resamples).
* Some summary CSVs store four decimals; a table value can therefore differ by 0.001 in the third decimal from the same quantity taken from a decision file (e.g. N = {{N_BH}} in the text vs. ×1.0 "PRr known" in the amplitude table).
* Panels marked "development seed" use seed 20261097, which was never part of validation; they illustrate mechanisms and are not used for any decision.
