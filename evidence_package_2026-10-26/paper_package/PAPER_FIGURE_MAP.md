# Paper figure map

Generated 2026-10-14 by `python3 -m src.build_paper_package`. Every figure exists as PDF (vector) and PNG (300 dpi) in `paper_package/figures/`.
Result panels read only frozen validation outputs; illustrative and verification panels are marked and use the development seed 20261097 or analytic curves.

| manuscript figure | file | content | type | data sources | generator |
|---|---|---|---|---|---|
| Figure 1 | `figures/fig01_architecture.pdf` / `.png` | Electronic architecture: two-point reference multiplexer, AFE, ADC and buffered reference-monitor channel; fault locations. | schematic | — | `src/paper_figures.py::fig_architecture` |
| Figure 2 | `figures/fig02_timing.pdf` / `.png` | Active self-test sequence: multiplexer states, reference levels and an illustrative ADC record with settling guards, settled plateaus, transient-fit window and sensor segments. | illustrative (development seed 20261097) | `paper_package/figure_data/fig02_timing_example.csv`<br>`src/simulate.py (_afe_reference, _adc_reference, simulate_sample)` | `src/paper_figures.py::fig_timing` |
| Figure 3 | `figures/fig03_pipeline.pdf` / `.png` | Processing pipeline and training procedure. | schematic | — | `src/paper_figures.py::fig_pipeline` |
| Figure 4 | `figures/fig04_phase_effect.pdf` / `.png` | Phase effect before/after the proposed descriptors: (a) analytic sampled step responses; (b, c) layer macro-F1 vs edge phase per arm (behavioral, ngspice); (d) descriptor shift vs phase. | result (b, c); analytic (a); development-seed verification (d) | `phase_robust_final/phase_robust_results/attribution_arms.csv`<br>`paper_package/figure_data/dev_seed_verification.json` | `src/paper_figures.py::fig_phase` |
| Figure 6 | `figures/fig05_afe_adc_separation.pdf` / `.png` | AFE/ADC fault separation: (a) fault signatures of the descriptors; (b, c) pooled layer confusion matrices of PRr; (d) AFE–ADC cross-confusion per arm. | development seed (a); result (b–d) | `paper_package/figure_data/fig05_fault_signature_descriptors_dev_seed.csv`<br>`paper_package/figure_data/fig05_fault_signatures_standardised_dev_seed.csv`<br>`paper_package/figure_data/fig05_layer_confusion_PRr_E2.json (derived from phase_robust_final/phase_robust_results/seed_*/predictions.npz)`<br>`phase_robust_final/phase_robust_results/afe_adc_separation.csv` | `src/paper_figures.py::fig_separation` |
| Figure 8 | `figures/fig06_behavioral_vs_ngspice.pdf` / `.png` | Behavioral versus ngspice: (a) one record in both domains; (b) noise-free agreement per phase; (c) transfer loss, previous vs phase-robust; (d) layer macro-F1 per phase in both domains. | development seed (a, b); result (c, d) | `paper_package/figure_data/fig06_example_waveforms_dev_seed.csv`<br>`paper_package/figure_data/dev_seed_verification.json`<br>`phase_robust_final/phase_robust_results/decision_rules.json`<br>`reference_monitor_final/reference_monitor_results/decision_rules.json`<br>`phase_robust_final/phase_robust_results/attribution_arms.csv` | `src/paper_figures.py::fig_domain` |
| Figure 5 | `figures/fig07_robustness.pdf` / `.png` | Robustness: layer macro-F1 vs actual reference amplitude for known/monitored reference, old descriptors and the no-monitor control; AFE–ADC cross-confusion at ±20%. | result | `phase_robust_final/phase_robust_results/amplitude_curves.csv`<br>`phase_robust_final/phase_robust_results/no_monitor_control.json`<br>`phase_robust_final/phase_robust_results/decision_rules.json` | `src/paper_figures.py::fig_robustness` |
| Figure 9 | `figures/fig08_ablation.pdf` / `.png` | Ablation forest plot: descriptors, phase randomisation, mixed training, Revision-2 conditioning, TCN vs MLP. | result | `phase_robust_final/phase_robust_results/attribution_comparisons.csv`<br>`reference_v2_results/decision_rules.json`<br>`multiseed_results/decision_rules.json` | `src/paper_figures.py::fig_ablation` |
| Figure 7 | `figures/fig09_per_class_recall.pdf` / `.png` | Fine-fault recall per arm in both domains. | result | `phase_robust_final/phase_robust_results/per_class_recall_fault.csv` | `src/paper_figures.py::fig_recall` |

Requested figure types and where they are:

| requested | manuscript figure |
|---|---|
| electronic block/circuit diagram | Figure 1 (`fig01_architecture`) |
| active self-test timing diagram | Figure 2 (`fig02_timing`) |
| complete processing pipeline | Figure 3 (`fig03_pipeline`) |
| phase effect before and after the proposed descriptors | Figure 4 (`fig04_phase_effect`) |
| AFE/ADC fault-separation diagram | Figure 6 (`fig05_afe_adc_separation`) |
| behavioral-versus-ngspice comparison | Figure 8 (`fig06_behavioral_vs_ngspice`) |
| robustness results | Figure 5 (`fig07_robustness`) |
| ablation comparison | Figure 9 (`fig08_ablation`) |
| per-class recall (additional) | Figure 7 (`fig09_per_class_recall`) |

Copies named in manuscript order are in `paper_package/figures_manuscript_numbering/` (e.g. `Figure05_robustness.pdf`).
