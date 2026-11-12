# Phase-Robust Active Self-Test: reproduction and submission package (MDPI Sensors)

This package regenerates every statistic, table, figure and document of the manuscript from the saved per-record predictions of the frozen validation run. **No simulation is rerun and no model is retrained.**

The original simulator and training source code is included so that the implementation can be inspected and checked against the hashes recorded at the protocol freeze. Rerunning that code (about 20 minutes per seed with ngspice-47) is not part of the documented build and was not repeated for this package.

## Contents

| Path | Contents |
|---|---|
| `manuscript/` | Outputs: `Phase_Robust_Sensors_Manuscript.docx/.pdf`, `Phase_Robust_Sensors_Supplementary.docx/.pdf`, `Cover_Letter_DRAFT.docx`, `references.bib`, `REFERENCE_VERIFICATION.md`, `AUTHOR_CONFIRMATIONS_REQUIRED.md`, `QC_REPORT.md`, `figures/` |
| `reports/` | `VERIFICATION_REPORT.md` (corrections, verification status, open items), `TRAINING_METHOD_VERIFICATION.md` |
| `logs/` | Build logs of the clean-directory tests and their environments |
| `evidence_package_2026-10-26/` | Frozen evidence (read-only): `phase_robust_final/PROTOCOL_PHASE_ROBUST_FROZEN.md`, final report, `phase_robust_results/seed_*/predictions.npz` (saved predictions), metadata, summary results, `source_hashes_at_freeze.txt`, development-seed figure data |
| `source_code/active_sensor_diagnosis/src/` | Original simulator, descriptor, training and analysis source of the validation run. `source_code/verify_source_hashes.py` checks it against the freeze record |
| `analysis/` | `values.py` recomputes all reported values and bootstrap intervals from the predictions; `rounding.py` does exact decimal rounding. Outputs: `values.json`, `values_check.csv`, `exact_fraction_crosscheck.csv`, `exact_ties.csv` |
| `mdpi_sensors_preparation/` | Figure and table scripts, Figures 1–10 (PNG/PDF/SVG), figure source data, `verification/LAST_DIGIT_DIFFERENCES.csv` |
| `manuscript_build/` | Manuscript text (`text_main.md`), verified reference database (`refs.py`), the MDPI Word template, DOCX/PDF builders, QC script and literature records |

## Requirements

**Required for the analysis, figures, tables and DOCX files (any platform):**

- Python 3.11 or later.
- numpy, pandas, matplotlib, python-docx and Pillow (`pip install -r requirements.txt`). scikit-learn is *not* needed, because no model is trained.
- pandoc 3.x.

**Optional, for PDFs only:**

- `--pdf`: Microsoft Word for Mac, driven through AppleScript. This is macOS only and is the route used for the delivered PDFs. On first use macOS asks permission for the terminal to control Word. The DOCX is copied into Word's sandbox folder (`~/Library/Containers/com.microsoft.Word/Data/Documents/pr_build/`), exported there and copied back; that is the only location outside the package that the build writes to.
- `--pdf=libreoffice`: LibreOffice (`soffice`) on any platform. The layout differs from the Word PDF: 31 pages with LibreOffice on macOS, and 42 and 7 pages with LibreOffice 24.2 on Linux, against 30 and 5 from Word.

If the chosen PDF tool is missing, the build prints a one-line explanation and exits with code 3. The DOCX files are unaffected.

**Versions used for the original results** (validation run, 14 October 2026): Python 3.12.12, NumPy 2.2.6, pandas 2.3.3, SciPy 1.16.3, scikit-learn 1.7.2, matplotlib 3.10.7 and ngspice-47 on macOS arm64. These are needed only to rerun the simulator and training, which this package does not do.

**Versions tested for regenerating this package** (see `logs/`):

| Test | Python | numpy | pandas | matplotlib | python-docx | Pillow | pandoc | PDF |
|---|---|---|---|---|---|---|---|---|
| Reference build (delivered files) | 3.12.12 | 2.2.6 | 2.3.3 | 3.10.7 | 1.2.0 | 12.0.0 | 3.12.1 | Word for Mac |
| Second build (macOS 27.2, arm64) | 3.13.7 | 2.5.3 | 3.0.5 | 3.11.2 | 1.2.0 | 13.0.0 | 3.12.1 | LibreOffice |
| Independent test (Linux x86_64, clean extraction, separate machine) | 3.13.17 | 2.5.3 | 3.0.5 | 3.11.2 | 1.2.0 | 12.3.0 | 3.1.3 | LibreOffice 24.2.7.2 |

The first two builds ran on macOS 27.2 (arm64). The independent Linux test (`logs/test_C_linux_clean_extraction.log`) ran `sh run_all.sh --pdf=libreoffice` on a machine without any of the author's files. It exited 0 in 1 min 15 s, with 38/38 hashes, 488/488 and 475/475 checks, and 89/89 QC.

**What is expected to match under other versions:**
- `values.json`, every printed number and the DOCX text outside equations matched exactly in all three builds.
- All CSV files matched, except that on Linux two figure-source files (`Fig02_timing_c.csv`, `Fig04_fault_signatures.csv`) differ by at most 4.4e-16, a floating-point difference.
- Equations: with pandoc 3.1.3 the 151 equation objects are present, but brackets inside equations are encoded differently in the XML than with pandoc 3.12.1.
- Figure PNG pixels differ between matplotlib 3.10 and 3.11, because rendering changes; the plotted data are the same.
- DOCX/PDF bytes, PDF page breaks and file sizes may differ with other pandoc, Word or LibreOffice versions.

## Commands

From the package root (the script also works when called from another directory):

```bash
sh run_all.sh                     # analysis, figures, tables, DOCX files, references, QC; no PDF
sh run_all.sh --pdf               # the same, plus PDFs through Microsoft Word for Mac (macOS)
sh run_all.sh --pdf=libreoffice   # the same, plus PDFs through LibreOffice
```

`run_all.sh` runs these steps in order and stops at the first failure:

```bash
python3 manuscript_build/check_environment.py                       # versions; clear error if something is missing
python3 source_code/verify_source_hashes.py                         # 38/38 frozen source files vs freeze record
python3 analysis/values.py                                          # recompute all values; 488 checks against stored results
python3 mdpi_sensors_preparation/scripts/build_figures_tables.py    # Figures 1–10 and tables; 475 evidence checks
python3 mdpi_sensors_preparation/scripts/last_digit_report.py       # verification/LAST_DIGIT_DIFFERENCES.csv
python3 manuscript_build/build_manuscript.py                        # manuscript DOCX
python3 manuscript_build/build_supplementary.py                     # supplement DOCX
python3 manuscript_build/build_bib.py                               # references.bib
python3 manuscript_build/build_reference_report.py                  # REFERENCE_VERIFICATION.md
python3 manuscript_build/build_cover_letter.py                      # cover-letter draft
python3 manuscript_build/qc_manuscript.py                           # automated checks -> manuscript/QC_REPORT.md
python3 manuscript_build/export_pdfs.py --pdf | --pdf=libreoffice   # only when a PDF option is given
```

The build takes about one minute without PDF export.

## Rounding rule

Differences are computed from unrounded values. Each reported number is then expressed with 12 significant digits and rounded once, half-to-even, in decimal arithmetic (`analysis/rounding.py` and `mdpi_sensors_preparation/scripts/common.py: fmt`). Exact ties such as 1287/13200 = 0.0975 are therefore rounded correctly (to 0.098), regardless of their binary representation.

## Status

The manuscript is **not submission-ready**. The author information listed in `manuscript/AUTHOR_CONFIRMATIONS_REQUIRED.md` is still missing.
