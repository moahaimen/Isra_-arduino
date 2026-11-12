# Verification report

Date: 12 November 2026. Package: `Phase_Robust_Sensors_Submission_Package_2026-11-11.zip`. The saved predictions and frozen results are unchanged; no simulation was rerun and no model was retrained.

## A. Verified corrections

| # | Correction | How it was verified |
|---|---|---|
| 1 | **Early stopping (Section 5).** The two paragraphs now describe a *random* 15% hold-out of the training rows, *not stratified by class*. The stopping criterion is that hold-out accuracy fails to exceed its best value by at least 1e-4 in more than 35 consecutive epochs; the best-accuracy weights are then restored. The disagreement between the written protocol ("no early-stopped model") and the frozen code is kept and stated as a discrepancy, and the unused 40-condition validation split is kept distinct. | In the installed scikit-learn 1.7.2, stratification applies only when `n_outputs_ == 1` (`_multilayer_perceptron.py` lines 642–653); multiclass targets are one-hot encoded, so `n_outputs_` is 4 and 9, confirmed on synthetic data. Stopping (lines 755–758, 809–817) and restoration (lines 790–793) are quoted in `TRAINING_METHOD_VERIFICATION.md`. QC checks that the text contains no "class-stratified" and that both the restoration and the 40-condition split are described. |
| 2 | **Frozen source and hashes.** The original source of the validation run is included (`source_code/active_sensor_diagnosis/src/`). | `verify_source_hashes.py`: **38 of 38** files in `source_hashes_at_freeze.txt` match and none are missing. Eight later files (reporting and literature scripts, not used by the run) are listed as additions. No source was recreated. |
| 3 | **Rounding.** Table 12 prints the FS behavioral healthy-layer recall as **0.098**. `LAST_DIGIT_DIFFERENCES.csv` gives `SEP_sp_R1R_x08_X` as **0.058** and `RL_bh_R1_HEALTHY` as **0.098**, now with unreduced counts. | Exact counts summed over 3 seeds × 2 initializations: **1287/13200** and **759/13200**. The third exact tie, PR AFE-layer recall, is **24486/26400 = 0.9275**, printed 0.93 to two decimals in Table S3 (the earlier report wrongly gave 12243/13200). Counts come from integer confusion matrices in `analysis/exact_fraction_crosscheck.csv` and from row totals in `LAST_DIGIT_DIFFERENCES.csv`; the two agree. No other printed value in the tables, figures or supplement is an exact tie (`analysis/exact_ties.csv`, `ties_formatted_manuscript.txt`). Rounding is exact decimal, half-to-even, the same rule as the project branch. |
| 4 | **Czaja 2013 [14], read in full** (author's postprint, MOST Wiedzy). Sections 2.2, 2.5 and 8.2 were revised. They now acknowledge that the method also replaces the sensor by a stimulus, that it localizes single soft faults to individual components, and that it was verified in hardware. The phase problem is no longer presented as a gap in that work, because there stimulus and sampling are synchronized by the microcontroller's timers. The distinction that remains (ADC and reference treated as sound, no ADC fault localization) is stated as supported by the full text. | `REFERENCE_VERIFICATION.md`, Section 2 |
| 5 | **Reproduction package.** All paths are relative to the package root; missing inputs were added; `README.md` lists exact commands, requirements and the versions behind the original results versus those tested for regeneration. The PDF step is separate and fails with a one-line message when Word or LibreOffice is absent. | Clean-directory tests in `logs/` (Section D) |
| 6 | **Submission documents.** All author facts are consolidated in `AUTHOR_CONFIRMATIONS_REQUIRED.md`. The cover-letter draft keeps the required declarations as highlighted placeholders. | QC: exactly five highlighted author fields in the manuscript |

## B. Claims not verified, or verified only in part

- **Nessler et al. 2018 [7].** The full text is not accessible (paywalled; no open copy found). It is cited from its abstract, and Section 2.5 says so.
- **The other 52 references.** These were checked against Crossref records and their abstracts, not their full texts. The full texts of [14], [15] and [16] were read.
- **Link between the code and the run.** The hashes show the code equals the frozen code. The run logs do not record the code hash, the software versions or the number of epochs; versions come from the reproducibility checklist written on the day of the run on the same machine.
- **No retraining or re-simulation.** Simulation and training were not rerun on any machine, so reproducibility is shown from the saved predictions onwards only.
- **No other platforms.** Windows and pandoc versions other than 3.1.3 and 3.12.1 were not tested.
- **Simulation only.** The results come from simulation and are not a hardware validation (manuscript, Section 8.4).

## C. Author information still required

See `manuscript/AUTHOR_CONFIRMATIONS_REQUIRED.md`: author order; affiliations; corresponding author and e-mail; contributions; funding; conflicts of interest; repository; the submission declarations; confirmation of the AI disclosure. **The package is not submission-ready until these are supplied.**

## D. Clean-directory tests of the final ZIP

Two clean-directory tests were run on macOS 27.2 (arm64). In each, the ZIP was extracted into a new, empty directory outside the project folder, and the documented command was run using only the package contents. Full logs, including the environment line, every step's output and the exit code, are in `logs/`.

| Test | Environment | Command | Result |
|---|---|---|---|
| A | Python 3.12.12, numpy 2.2.6, pandas 2.3.3, matplotlib 3.10.7, python-docx 1.2.0, Pillow 12.0.0, pandoc 3.12.1, Microsoft Word for Mac | `sh run_all.sh --pdf` | **Pass** (exit 0, 1 min 19 s). Hashes 38/38, recomputation 488/488, evidence 475/475, QC 89/89. Every output is identical to the packaged one: values, all CSVs, DOCX text, PDF text (30 and 5 pages) and all 10 figure PNGs pixel for pixel. |
| B | Python 3.13.7, numpy 2.5.3, pandas 3.0.5, matplotlib 3.11.2, python-docx 1.2.0, Pillow 13.0.0, pandoc 3.12.1, LibreOffice | `sh run_all.sh --pdf=libreoffice` | **Pass** (exit 0, 39 s). The same checks pass. Values, all CSVs and the DOCX text are identical. Figure pixels differ (matplotlib 3.11) and the LibreOffice PDF has 31 pages instead of 30; both are expected and documented in `README.md`. |

**Missing-tool behavior.** With LibreOffice absent, `export_pdfs.py --pdf=libreoffice` prints a one-line message and exits with code 3. With pandas absent or Python older than 3.11, `check_environment.py` stops with a clear message. The second case occurred on this Mac after a system update put the system Python 3.9 first on PATH.

**Independent Linux test (C).** This was run separately on a Linux machine without any of the author's files (`logs/test_C_linux_clean_extraction.log`): Linux x86_64, Python 3.13.17, numpy 2.5.3, pandas 3.0.5, matplotlib 3.11.2, python-docx 1.2.0, Pillow 12.3.0, pandoc 3.1.3, LibreOffice 24.2.7.2. The command was `sh run_all.sh --pdf=libreoffice`.

- **Result:** passed (exit 0, 1 min 15 s). Hashes 38/38, recomputation 488/488, evidence 475/475, QC 89/89.
- **Identical to the shipped files:** `values.json`, and the text outside equations in the manuscript (89,454 characters), the supplement and the cover letter. All CSV files are identical except `Fig02_timing_c.csv` and `Fig04_fault_signatures.csv`, which differ by at most 4.4e-16.
- **Expected differences:**
  - pandoc 3.1.3 encodes brackets inside equations differently from 3.12.1, so the equation XML differs; all 151 equation objects are present.
  - Figure pixels differ.
  - The LibreOffice PDFs have 42 and 7 pages, against 30 and 5 from Word.

**Final ZIP.** After these tests, three changes were made: the intermediate manuscript Markdown now uses package-relative image paths (absolute home-directory paths removed), the Linux log was added, and the README and this report were updated. The final ZIP was then rebuilt and the clean-extraction test was rerun (`logs/clean_build_D_final_zip.log`).
