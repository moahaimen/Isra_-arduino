# Correction and verification report

Date: 11 November 2026. Scope: the five corrections requested for `Phase_Robust_Sensors_Manuscript.docx` and the submission ZIP. No simulation was rerun and no model was retrained.

## 1. Rounding

**Cause.** Two exact decimal ties were rounded through their binary representation. The float nearest to 0.0975 lies below the tie, so `format(x, ".3f")` printed 0.097.

**Fix.** Every reported number is now rounded by `analysis/rounding.py` and `mdpi_sensors_preparation/scripts/common.py: fmt`. The value is first expressed with 12 significant digits, which recovers the exact decimal, and then rounded once, half-to-even, in decimal arithmetic. This is the same rule as the corrected code on the project branch.

**Exact ties found.** The predictions were searched for all exact ties at two or three decimals (`analysis/exact_ties.csv`; formatting also logs ties in `analysis/ties_formatted_manuscript.txt`):

| Quantity | Counts (3 seeds × 2 initializations) | Value | Printed before | Printed now | Where printed |
|---|---|---|---|---|---|
| FS behavioral healthy-layer recall (`RL_bh_R1_HEALTHY`) | 1287/13200 | 0.0975 | 0.097 | **0.098** | Manuscript Table 12 |
| FSr ngspice cross-confusion at ×0.8 (`SEP_sp_R1R_x08_X`) | 759/13200 | 0.0575 | — | **0.058** | Not printed in the manuscript or supplement; corrected in `LAST_DIGIT_DIFFERENCES.csv` |
| PR behavioral AFE-layer recall (`RL_bh_PR_AFE`) | 12243/13200 | 0.9275 | 0.93 (2 decimals) | 0.93 (2 decimals) | Table S3; the 3-decimal value 0.928 appears only in the CSV |

No other printed value was an exact tie.

**Registry fix.** Exact rounding exposed a second problem. The preparation-package registry read some four-decimal CSV values: FSr − FS in ngspice is stored as 0.0295, and exact rounding sends that to 0.030, but the full-precision value is 0.029455 (printed 0.029). The registry now recomputes these families from the predictions at full precision before rounding, as the branch does (`registry_build.refine_full_precision`).

**Bootstrap bounds.** The two bounds stored as −0.0055 and 0.0255 are no longer constants. `analysis/values.py` recomputes them with the original deterministic resampling seeds: −0.005543 and +0.025469, printed −0.006 and +0.025.

**`LAST_DIGIT_DIFFERENCES.csv`.** `mdpi_sensors_preparation/verification/LAST_DIGIT_DIFFERENCES.csv` (52 tokens) is regenerated inside the package by `scripts/last_digit_report.py`. It is identical to the corrected file on branch `claude/project-thread-vvkfv4` (commit 8e1d737), except that the two bootstrap bounds carry more digits because they are recomputed rather than entered as constants. `analysis/exact_fraction_crosscheck.csv` cross-checks the 27 original tokens independently from integer counts.

**Underlying results.** These are unchanged: 488 recomputation checks and 475 evidence checks, 0 mismatches.

## 2. Reproducible package

**Self-contained.** All paths are relative to the package root. The package now includes everything the scripts read:

- the frozen evidence package, including `paper_package/figure_data`;
- the simulator and training source code;
- the preparation scripts, the manuscript sources and the MDPI template;
- the literature records.

**Commands.** These are documented in `README.md`, with dependencies listed in `requirements.txt`. One command, `sh run_all.sh [--pdf]`, runs the full build.

**Fresh-extraction test.** See Section 6.

## 3. Training method

See `reports/TRAINING_METHOD_VERIFICATION.md`.

- **Hashes.** All 38 frozen source files match `source_hashes_at_freeze.txt`.
- **What the code does.** `run_phase_robust.py` trains every network with `run_feasibility._classifier`: Adam, `early_stopping=True`, `validation_fraction=0.15`, `n_iter_no_change=35`, `tol` 1e-4 (the default) and `max_iter` 700.
- **What executed in scikit-learn 1.7.2.**
  - The hold-out is a class-stratified random 15% of the training rows, drawn by row, not by operating condition.
  - Validation is by accuracy, and training stops after more than 35 epochs without improvement.
  - The best weights are restored at the end.
- **Validation split.** The 40-condition split is never generated or used.
- **Discrepancy.** The protocol's "no early-stopped model" contradicts the frozen code. The manuscript (Sections 5, 6.5 and 8.4) now states this as a discrepancy, rather than resolving it by interpretation. The epoch counts actually run were not recorded.

## 4. Text and references

**Prose.** Repeated project-history and audit wording was reduced in the Introduction and Sections 6.5, 6.6, 7.1, 7.5, 8.1 and 9. Absolute wording ("does not depend", "removes the dependence", "absorbs the shift") was replaced by statements of reduced sensitivity over the tested range. The weak-class results, the simulation-only scope, the PRr/PRrM distinction and the matched-grid transfer are kept.

**References.**
- **Full texts read:** [15] Hu et al. 2008 (J-STAGE) and [16] Pavlidis et al. 2021 (HAL author version). The comparison in Sections 2.2, 2.5 and 8.2 was revised from them: Hu is a production pass/fail test that accepts possible masking between analog and ADC gain errors; SymBIST checks invariances against Monte Carlo windows and does not localize to a stage.
- **Not accessible:** [7] Nessler et al. 2018 and [14] Czaja 2013. They are paywalled with no legal open copy found, so they are characterized only as far as their abstracts state, and the text says so.
- **Records.** All 56 records were re-verified against Crossref (`manuscript_build/literature/crossref_recheck_2026-11-11.json`) and cross-checked against the independent 53-reference set on the branch (17 shared DOIs, all in agreement). Two earlier dispositions were corrected: Henry & Clarke 1993 does exist (DOI 10.1016/0967-0661(93)91382-7), and Efron & Tibshirani 1993 also has a Springer DOI. "Louërat" is now spelled as the author does.

## 5. Submission materials

- `manuscript/Cover_Letter_DRAFT.docx`, with the author-dependent statements highlighted rather than asserted.
- `manuscript/AUTHOR_CONFIRMATIONS_REQUIRED.md`, a list of seven items.

**The package is not submission-ready while those items are open.**

## 6. Verification of the delivered ZIP

**Platform.** macOS 27.0.1 (arm64), Python 3.12.12, numpy 2.2.6, pandas 2.3.3, matplotlib 3.10.7, python-docx 1.2.0, Pillow 12.0.0, pandoc 3.12.1, and Microsoft Word for Mac for the PDF step.

**Procedure.**
1. The finished ZIP was extracted into a new directory outside the project folder.
2. The shipped outputs were moved aside: `manuscript/`, the figures, `values.json`, `values_check.csv` and `LAST_DIGIT_DIFFERENCES.csv`.
3. The documented command `sh run_all.sh --pdf` was run there. It took 1 min 15 s.

**Result.**
- All steps completed: 38/38 source hashes matched, 488/488 recomputation checks and 475/475 evidence checks passed, and QC passed 84 of 84 checks.
- The regenerated outputs match the shipped ones:
  - `values.json`, `values_check.csv` and `LAST_DIGIT_DIFFERENCES.csv` are byte-identical.
  - The manuscript, supplement and cover-letter DOCX files have identical text.
  - Both PDFs have identical text (30 and 5 pages).
  - `references.bib` and `REFERENCE_VERIFICATION.md` are identical.
  - All 10 figure PNGs are identical pixel for pixel.
- No script refers to a path outside the package.

**PDF-specific requirement.** The PDF step needs Microsoft Word for Mac and AppleScript permission. The DOCX is exported inside Word's sandbox folder (`~/Library/Containers/com.microsoft.Word/Data/Documents/pr_build/`); that is the only location outside the package that the build writes to. Without `--pdf` the build needs only Python and pandoc.
