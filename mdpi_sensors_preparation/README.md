# MDPI Sensors preparation package

**Phase-Robust Reference-Monitored Active Self-Test of Mixed-Signal Sensor Interfaces Using Neural-Network Classification**

This directory is a verified evidence and manuscript-preparation package. It is built only from the frozen
evidence package in `../evidence_package_2026-10-26/`, which is a verbatim, read-only copy of the uploaded ZIP
(SHA-256 `3e2f034dacfa1c66c8b554220dedb78a1527692ba7e62830d0270815d7687bec`; per-file hashes in
`SHA256SUMS_EXTRACTED.txt`). No model was retrained, no simulation was rerun, and the frozen protocol was not changed.

## Regenerate everything

From the repository root:

```bash
python3 mdpi_sensors_preparation/scripts/build_all.py
```

This runs, in order: number registry → verification → figures → tables → documents/drafts → quality control
(about 30 s). It exits non-zero if verification or any QC check fails.

Requirements: Python ≥ 3.11, numpy, pandas, matplotlib, python-docx (tested with Python 3.13, numpy 2.5.3,
pandas 3.0.5, matplotlib 3.11.2, python-docx 1.2.0). `pandoc` (optional) produces the compiled Word draft.
Figures use Liberation Sans; another sans-serif font is substituted if it is missing.

**Scope of reproducibility.** The build regenerates every figure, table and number from the saved results and the
per-record predictions. The evidence package does not contain the simulator source code or data caches, so
re-simulation and retraining are **not** reproducible from this package.

## Contents

| Path | What it is |
|---|---|
| `RESULTS_EVIDENCE_REPORT.md` | Sections 1–12 of the brief plus the discrepancy audit; every number with source file, key, calculation and rounding |
| `NUMBER_PROVENANCE_MDPI.csv` | All registered numbers (token, value, raw value, status, source, key, calculation, rounding) |
| `verification/` | Hash check, 475 quantities recomputed from predictions, frozen-fact check against the brief |
| `figures/` | Figures 1–10 (PNG 600 dpi, PDF, SVG), `FIGURE_CAPTIONS.md`, `FIGURE_SOURCE_DATA_MAP.csv` |
| `figure_source_data/` | Every plotted value as CSV |
| `tables/` | Tables 1–12 as CSV, Markdown, LaTeX (booktabs) and Word; combined `ALL_TABLES.*` |
| `manuscript/` | Outline, abstract, introduction + related work, methods, results, discussion + limitations, conclusions + back matter, compiled draft (.md/.docx), figure/table order, `TOKENS_USED.csv` |
| `RESEARCH_GAP_MATRIX.md`, `NOVELTY_AND_CONTRIBUTIONS.md` | Gap and contribution statements (no priority claim) |
| `CLAIM_TO_EVIDENCE_MAP.csv`, `LITERATURE_COMPARISON_TABLE.csv` | Claim → token → source map; five-category literature comparison |
| `references.bib` | Bibliography; entries marked `VERIFY` have not been checked |
| `QUALITY_CONTROL_REPORT.md` | Results of the section-9 checks |
| `templates/` | Draft text with `{{TOKEN}}` placeholders — edit these, not the rendered drafts |
| `scripts/` | `common.py`, `registry_build.py`, `verify.py`, `figures.py`, `tables.py`, `docs.py`, `qc.py`, `build_all.py` |

## Editing the drafts

Edit `templates/*.md.tmpl` and rebuild. Numbers are written as `{{TOKEN}}` (or `{{CI:LO:HI}}` for an interval),
where `TOKEN` is a row in `NUMBER_PROVENANCE_MDPI.csv`. An unknown token stops the build, and QC rejects any decimal
number in the text that has no provenance.

## Still needed from the authors

Authors, affiliations, funding, conflicts, data-repository URL/DOI, optimizer and early-stopping confirmation
(protocol and earlier package text disagree), ngspice version, a systematic literature search, and verification of
`VERIFY` references. Hardware, energy and real-sensor results do not exist and are not claimed.
