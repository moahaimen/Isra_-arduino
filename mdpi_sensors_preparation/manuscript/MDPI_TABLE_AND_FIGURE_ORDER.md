# MDPI Table and Figure Order

Figures and tables are numbered in order of first citation in the text (MDPI rule). The section of first citation is checked against the rendered drafts by `scripts/qc.py`.

| Order | Item | File | First cited in section | Type |
|---|---|---|---|---|
| 1 | Figure 1 | `figures/Fig01_architecture.png|.pdf|.svg` | 3 | schematic |
| 2 | Table 1 | `tables/Table01_system_components.csv|.md|.tex|.docx` | 3 | table |
| 3 | Figure 2 | `figures/Fig02_timing.png|.pdf|.svg` | 3 | illustrative (development seed) |
| 4 | Table 2 | `tables/Table02_fault_taxonomy.csv|.md|.tex|.docx` | 3 | table |
| 5 | Figure 3 | `figures/Fig03_pipeline.png|.pdf|.svg` | 4 | schematic |
| 6 | Figure 4 | `figures/Fig04_fault_signatures.png|.pdf|.svg` | 4 | illustrative (development seed) |
| 7 | Figure 5 | `figures/Fig05_phase_sensitivity.png|.pdf|.svg` | 4 | result (a,b); illustrative (c) |
| 8 | Table 3 | `tables/Table03_protocol.csv|.md|.tex|.docx` | 6 | table |
| 9 | Table 4 | `tables/Table04_main_results.csv|.md|.tex|.docx` | 7.1 | table |
| 10 | Table 5 | `tables/Table05_gates.csv|.md|.tex|.docx` | 7.1 | table |
| 11 | Table 6 | `tables/Table06_baselines.csv|.md|.tex|.docx` | 7.1 | table |
| 12 | Table 7 | `tables/Table07_reference_monitor.csv|.md|.tex|.docx` | 7.1 | table |
| 13 | Table 8 | `tables/Table08_phase_ablation.csv|.md|.tex|.docx` | 7.1 | table |
| 14 | Table 9 | `tables/Table09_domain_transfer.csv|.md|.tex|.docx` | 7.1 | table |
| 15 | Table 10 | `tables/Table10_afe_adc_separation.csv|.md|.tex|.docx` | 7.1 | table |
| 16 | Figure 6 | `figures/Fig06_reference_amplitude.png|.pdf|.svg` | 7.3 | result |
| 17 | Figure 7 | `figures/Fig07_afe_adc_separation.png|.pdf|.svg` | 7.4 | result |
| 18 | Figure 8 | `figures/Fig08_domain_transfer.png|.pdf|.svg` | 7.5 | result |
| 19 | Figure 9 | `figures/Fig09_ablation.png|.pdf|.svg` | 7.6 | result |
| 20 | Figure 10 | `figures/Fig10_per_class_recall.png|.pdf|.svg` | 7.7 | result |
| 21 | Table 11 | `tables/Table11_per_class_recall.csv|.md|.tex|.docx` | 7.7 | table |
| 22 | Table 12 | `tables/Table12_complexity.csv|.md|.tex|.docx` | 7.8 | table |

## Figure captions

See `figures/FIGURE_CAPTIONS.md` (rendered from the registry).

## Table titles

- **Table 1.** Electronic system and circuit components of the simulated sensor interface.
- **Table 2.** Fault taxonomy: nine fault classes and their physical location.
- **Table 3.** Simulation and validation protocol.
- **Table 4.** Main classification results of the primary (PRr) and secondary (PRrM) methods.
- **Table 5.** Pre-registered gate results for the primary method PRr.
- **Table 6.** Baseline comparison (layer macro-F1, behavioral domain).
- **Table 7.** Reference-monitor robustness: layer macro-F1 versus actual reference amplitude.
- **Table 8.** Phase-robustness ablation: layer macro-F1 per edge phase.
- **Table 9.** Behavioral-to-ngspice domain transfer (layer macro-F1).
- **Table 10.** AFE/ADC fault separation of PRr at ±20% reference amplitude.
- **Table 11.** Per-class recall (fine-fault and layer classes).
- **Table 12.** Model and computational complexity.
