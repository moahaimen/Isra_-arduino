# Independent draft of the manuscript (not the delivered version)

The manuscript "Phase-Robust Active Self-Test for Fault Localization in Mixed-Signal Sensor Interfaces: A Simulation
Study" that was delivered on 11 November 2026 was built on the author's computer, where the original simulator and
training code are available. Its files are in `phase_robust_submission/deliverables/` there and in the ZIP
`Phase_Robust_Sensors_Submission_Package_2026-11-11.zip`.

This directory holds a second draft that was written in parallel from the evidence package alone. **It was never
built into a document and never inspected, and it is not the delivered manuscript.** It is kept because three parts of
it are useful as an independent cross-check:

| Path | Content |
|---|---|
| `cloud_draft/refs.py` | Bibliographic records of 53 references, each with the record it was checked against, the statement it is used for, what was actually read (abstract, full text, or title only) and the candidates that were dropped and why |
| `cloud_draft/src/*.md` | Draft section texts (introduction to conclusions) in which every result is a token that is filled from the number registry |
| `cloud_draft/ms_tokens.py`, `ms_tables.py` | Number registry and table definitions that read the full-precision values (see below) |
| `cloud_draft/build_manuscript.py`, `ms_docx.py`, `ms_refs.py` | Unfinished builder (pandoc and python-docx) |

## Last-digit check

Several result CSVs of the evidence package store four decimals. Rounding a stored value again to three decimals can
differ in the last digit from the correctly rounded value. `mdpi_sensors_preparation/scripts/registry_build.py`
(`refine_full_precision`) therefore recomputes these values from the saved per-record predictions before rounding.
`mdpi_sensors_preparation/verification/LAST_DIGIT_DIFFERENCES.csv` lists the 25 point estimates whose printed value
changes, and two confidence-interval bounds whose stored fourth decimal is 5. Those two bounds were recomputed with the
original code on the author's computer (-0.005543 and +0.025469). The delivered manuscript was built from full-precision
values from the start and needed no correction. The headline
values (0.656, 0.649, transfer loss 0.002 with interval [-0.003, +0.006], phase spread 0.005 to 0.011) are not affected.
