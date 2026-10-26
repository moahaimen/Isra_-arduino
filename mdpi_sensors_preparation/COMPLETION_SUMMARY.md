# MDPI Sensors package — completion summary (2026-10-26)

**Status:** ready for manuscript writing (simulation-only evidence; author details and reference checks still needed).
**Repository:** branch `claude/project-thread-vvkfv4`, directory `mdpi_sensors_preparation/`.
**Regenerate:** `python3 mdpi_sensors_preparation/scripts/build_all.py` (from the repo root). Regenerates from saved results and predictions only; no end-to-end re-simulation (simulator source not in the package).

## Verification
85 evidence files hash-checked (0 changed); 475 saved quantities recomputed from per-record predictions (0 mismatches); 36 brief facts checked (0 mismatches, 10 with caution notes); 16/16 QC checks pass.

## Primary numbers (PRr)
- Decision: GO (all gates A–G passed, both domains)
- Layer macro-F1, E = ±2%: 0.656 behavioral grid (5 amplitudes), 0.649 ngspice grid (3 amplitudes)
- Transfer loss (matched grid): 0.650 − 0.649 = 0.002 [-0.003, +0.006]; previous stage 0.119
- Phase range: PRr 0.005–0.011; R1 0.081 (E = ±2%)
- Max AFE–ADC cross-confusion 0.089; worst retention ×0.8/×1.2 0.916; at ±5% monitor error 0.924; min superiority CI lower bound +0.112
- No monitor (behavioral): 0.310 at ×0.8, 0.237 at ×1.2 (known: 0.615, 0.643)
- MLP 20–96–48: 6,868 / 7,113 parameters

## Cautions found in the audit
- Do not subtract 0.656 − 0.649: different amplitude grids.
- PRr phase spread is 0.005–0.011, not 0.006–0.011.
- R1 spread 0.081 holds at E = ±2%; known-reference values are 0.082 (behavioral) and 0.085 (ngspice).
- No-monitor results exist only for the behavioral domain.
- Previous-stage 0.119 comes only from paper_package text/provenance; its decision file is not in the package.
- Early stopping: the frozen protocol says the validation split was unused; earlier package text says "Adam, early stopping". Authors must confirm.

## Needed from the authors
Authors, affiliations, funding, conflicts, data repository URL/DOI, optimizer/early-stopping confirmation, ngspice version, systematic literature search, and checks of references marked VERIFY in references.bib.
