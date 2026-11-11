# Submission package: Phase-Robust Active Self-Test (MDPI Sensors)

Built on 11 November 2026 from `mdpi_sensors_preparation_reviewed_2026-10-26.zip`. No simulation was rerun and no model was retrained.

## Contents

| File / folder | What it is |
|---|---|
| `Phase_Robust_Sensors_Manuscript.docx` | Manuscript in the official MDPI Sensors Word template (v2, August 2026): 10 embedded figures, 12 native Word tables, 12 editable Office Math equations, 56 numbered references |
| `Phase_Robust_Sensors_Manuscript.pdf` | PDF exported from the same DOCX with Microsoft Word (30 pages) |
| `Phase_Robust_Sensors_Supplementary.docx` / `.pdf` | Figure S1 and Tables S1–S6 |
| `figures/` | Figures 1–10 and S1: 600 dpi PNG (as embedded), plus PDF and SVG vector originals |
| `figure_source_data/` | Every plotted value as CSV |
| `references.bib` | The 56 verified references, in citation order |
| `REFERENCE_VERIFICATION.md` | Search scope, metadata and claim-support check for every reference, and what happened to the earlier candidate entries |
| `AUTHOR_CONFIRMATIONS_REQUIRED.md` | The open author-side items (author list and affiliation, contributions, funding, conflicts, repository, GenAI wording) |
| `QC_REPORT.md` | Automated checks of the final DOCX files (80 checks) |
| `analysis/` | `values.py` recomputes every manuscript number from the saved predictions; `values.json` (unrounded values); `values_check.csv` (488 comparisons with the stored results, 0 mismatches) |
| `evidence/phase_robust_final/` | Frozen protocol, final report, per-seed predictions, metadata and summary results (unchanged copies) |
| `build_scripts/` | Scripts that produce the DOCX, PDF and supplement, including the patched figure script |

## Figure mapping (preparation package → manuscript)

| Preparation package | Manuscript | Change |
|---|---|---|
| Fig01_architecture | Figure 1 | None |
| Fig02_timing | Figure 2 | None |
| Fig03_pipeline | Figure 3 | None |
| Fig04_fault_signatures | Figure 4 | Red in-figure "ILLUSTRATIVE" banner removed; the caption states that the figure is illustrative |
| Fig05_phase_sensitivity | Figure 5 | Arm labels R1/R1r renamed FS/FSr, so that "R1" means only the first reference signal |
| Fig06_reference_amplitude | Figure 6 | Regenerated from saved data: the delivered PNG was truncated and unreadable. Overlapping value labels removed. FS label |
| Fig07_afe_adc_separation | Figure 7 | None |
| Fig08_domain_transfer | Figure 8 | Panel (a) redrawn as points (the bars started at 0.55); panel (c) recomputed on the matched ×0.8/×1.0/×1.2 grid in both domains (before, the behavioral curve pooled five amplitudes) |
| Fig09_ablation | Figure 9 | FS/FSr labels |
| Fig10_per_class_recall | Figure 10 | FS/FSr labels |
| — | Figure S1 | New: fine-fault confusion matrices, computed from the saved predictions |

## Table mapping (preparation package → manuscript / supplement)

| Preparation package | Manuscript | Notes |
|---|---|---|
| Table01 system components | Table 1 | Optimizer row moved to Section 5 |
| Table02 fault taxonomy | Table 2 | — |
| — | Table 3 (new) | Descriptor sets FS and PR |
| Table03 protocol | Table 4 | "Pre-registration" reworded as an internally frozen protocol |
| Table05 gates | Table 5 | — |
| Table04 main results | Table 6 | FS rows added |
| Table07 reference monitor | Table 7 | A0 and FS rows added |
| Table10 AFE/ADC separation | Table 8 (known, ±2%, ±5%, no monitor) | All conditions in Table S2 |
| Table09 domain transfer | Table 9 | Fault macro-F1 loss column added |
| — | Table 10 (new) | Attribution, layer and fault macro-F1 |
| Table06 baselines | Table 11 | All 70 gate-B comparisons in Table S4 |
| Table11 per-class recall | Table 12 (PRr, PRrM, FS) | All arms in Table S3 |
| Table08 phase ablation | Table S1 | Also shown in Figure 5 |
| Table12 complexity | Table S5 | Key figures in Section 7.8 |
| — | Table S6 (new) | Software versions and SHA-256 of the evidence files |

## Rebuilding

From `build_scripts/`, with Python 3, pandoc 3, python-docx and Microsoft Word on macOS:

```bash
python3 build_manuscript.py && python3 build_supplementary.py && python3 qc_manuscript.py
```

Each run regenerates the PDF through Word. The figures come from `build_scripts/figures_package/figures.py`, run inside the original preparation package.
