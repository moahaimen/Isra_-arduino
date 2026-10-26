# Complete review package — Active self-diagnosing sensor interface

## Start here
1. paper_package/FINAL_PAPER_PACKAGE.md — overview of the paper, claims vs evidence, open items
2. paper_package/MANUSCRIPT_SENSORS_DRAFT.md — full manuscript draft (MDPI Sensors); figures in paper_package/figures_manuscript_numbering/
3. paper_package/PAPER_TABLES.csv, NUMBER_PROVENANCE.csv, PAPER_FIGURE_MAP.md, REPRODUCIBILITY_CHECKLIST.md

## Validation reports (in order; each stage keeps its own frozen protocol and decision)
| # | report | outcome |
|---|---|---|
| 1 | FEASIBILITY_REPORT.md | feasibility signal |
| 2 | FINAL_TCN_COMPARISON_REPORT.md | TCN ≈ MLP; no TCN superiority claim |
| 3 | FINAL_MULTISEED_REPORT.md | ROBUSTNESS FAILURE (±20% reference amplitude) |
| 4 | FINAL_REFERENCE_V2_REPORT.md | REFERENCE REVISION VALIDATED (known reference) |
| 5 | reference_monitor_final/FINAL_REFERENCE_MONITOR_REPORT.md | REVISE (ngspice transfer loss 0.119) |
| 6 | phase_robust_final/FINAL_PHASE_ROBUST_REPORT.md | GO (transfer loss 0.002; all gates pass) |

Results and figures of each stage are in the folder next to its report. Source code and data caches are not included.
