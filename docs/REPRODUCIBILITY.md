# Reproducibility

## One command

```bash
pip install -r requirements.txt
bash scripts/reproduce_all.sh          # full study (10 seeds x 3600 s)
bash scripts/reproduce_all.sh --quick  # pipeline check (3 seeds x 600 s)
```

This builds the simulator, runs every test, then the smoke, validation, main,
ablation and sensitivity campaigns, the results report and the scientific
audit. Each campaign goes to `results/campaigns/<id>_<UTC timestamp>/`; the
runner refuses to write into an existing campaign directory, so nothing is
overwritten.

Toolchain used for the committed campaigns: g++ 13.3.0, CMake 3.28.3,
Python 3 with numpy 2.4.6, pandas 3.0.6, scipy 1.17.1, matplotlib 3.11.2,
Linux x86-64, 4 cores. The full study takes on the order of an hour on that
machine (the simulator itself runs a 3600 s scenario in well under a second;
most time is per-run Python metrics and compression).

## Determinism

* One RNG family (xoshiro256**, seeded via SplitMix64). Every stream is
  derived from (seed, tag, id), never from time or global state.
* Workloads are generated once per (scenario, seed) and saved with an FNV-1a
  hash in `workloads/*.meta.json`; all modes replay the saved file.
* Re-running the same command at the same commit gives byte-identical
  workloads and per-run outputs (unit tests and integration test 3 check this).
  Floating-point output may differ across compilers/architectures in the last
  printed digit; that is the only expected source of non-identity.

## What each run records

`raw/<run_id>/`: `command.txt` (exact command line), `config.json` (every
resolved parameter), `summary.json` (simulator version, seed, scenario, mode,
workload hash, detector backend, power-model source and calibration flag,
`research_valid`, counters, duty cycle, modeled energy), `observations.csv`,
`states.csv`, `wake_intervals.csv`, `events.jsonl` (large files gzipped by the
runner), and `metrics.json` from the Python layer.

Campaign level: `config/campaign.json` (git commit, dirty flag, compiler,
platform, Python and library versions, command line), `config/run_specs.json`,
copies of the default config and power model, `per_run/metrics.csv`,
`logs/validation.csv`, `logs/workload_equality.csv`, `logs/errors.json`,
`aggregate/*.csv`, `figures/*.{png,pdf}` (each drawn only from the saved
aggregate CSVs), `RESULTS_SUMMARY.md`, `logs/scientific_audit.md`.

## What is in git and what is archived

`raw/` and `workloads/` of each campaign are excluded from git by size
(hundreds of MB). They are archived as `tar.gz` outside the repository (the
project's shared files, `research_sim/`), and can be regenerated exactly with
the command recorded in `config/campaign.json`. Everything derived from them (per-run
metrics in `per_run/metrics.csv`, validation logs, aggregates, tables, figures, report,
audit) is committed.

## Campaign history

Interim campaigns were produced during development while bugs were fixed
(background-noise source for always-on empty frames, wake-wait separated from
queue delay, figure layout, Holm family definition). They were deleted, not
reported. The committed campaigns were all produced from one clean commit,
recorded in each campaign's `config/campaign.json` (`dirty: false`).
