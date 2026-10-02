# Simulation baseline (Phase 0 audit)

## Audit result: the repository was empty

The task description states that the repository already contains a working
functional simulator (`sim_runner.cpp`, `sim_mocks.h`, Arduino and RPC mocks,
watcher/detector/security code, `scripts/eval_energy/metrics.py`,
`scripts/eval_energy/aggregate.py`, five-seed developmental results).

The audit performed on 2026-10-02 found **none of these files**:

| check | command | result |
|---|---|---|
| local clone | `git status`, `git log -5 --oneline` | branch `master`, *"No commits yet"* |
| remote refs | `git ls-remote origin` | no refs at all |
| GitHub API | list branches of `moahaimen/Isra_-arduino` | `[]` (no branches) |
| project files | shared project folder | empty |

Therefore, for each item Phase 0 asks to identify:

| item | found in repository |
|---|---|
| simulator entry point / `sim_runner.cpp` | no |
| `sim_mocks.h`, Arduino mocks, RPC mocks | no |
| watcher, detector, security implementation | no |
| protocol definitions, configuration headers | no |
| `metrics.py`, `aggregate.py` | no |
| existing results (five seeds) | no |
| existing tests, build instructions | no |

Consequently the prototype could not be compiled or smoke-tested, and its
behaviour could not be recorded. **No claim in this repository is based on the
earlier prototype or on its developmental five-seed results.** If that code
exists elsewhere (for example on a local machine) it should be pushed to a
separate branch so it can be compared against the framework built here.

## What was built instead

The research framework was implemented from scratch, following the
architecture the task description attributes to the prototype so that the
concepts carry over:

| prototype concept (as described) | research implementation |
|---|---|
| dual-core logical model, M4 watcher + M7 detector | `simulation/watcher/`, `simulation/detector/`, `simulation/core/simulator.cpp` |
| MONITORING -> TRIGGER -> WAKE -> DETECT -> RESULT -> SLEEP | same flow, extended with SECURITY gate, RPC queue, early exit / second pass and postprocessing (see `docs/SIMULATION_METHOD.md`) |
| RPC simulation | `simulation/communication/rpc_model.h` (latency, jitter, contention, queue, loss) |
| simulated `millis()` / `delay()` | discrete-event simulated time; `simulation/core/arduino_mocks.h` provides mocked `millis()`, `delay()` and RPC for the firmware host check |
| JSON/JSONL logging | `simulation/logging/event_log.*` (deterministic JSONL) |
| reproducible seeds | platform-independent RNG (`simulation/core/rng.h`) with keyed per-event streams |
| modes always_on / event / secure | kept, plus motion_only, fixed_threshold, event_no_early_exit |
| metrics (triggers, blocked, wakes, results, sleeps, active time, duty cycle, latency mean/median/p95) | all kept in `scripts/eval_energy/metrics.py` and extended (Phase 12) |
| `scripts/eval_energy/metrics.py`, `aggregate.py` | re-created at the same paths |
| probability-based secure-mode blocking | **not used** in research mode. It exists only behind the explicit debug flag `--debug-random-block-prob` and every such run is marked `research_valid: false` |

## Current event format (JSONL)

Each line of `events.jsonl` is `{"t": <ms>, "ev": "<TYPE>", ...}`. Types:
`SIM_START, OBSERVATION, WATCHER_SCORE, WATCHER_DECISION, TRIGGER,
TRIGGER_SUPPRESSED, SECURITY_ACCEPT, SECURITY_BLOCK, RPC_SEND, RPC_RECEIVE,
RPC_ENQUEUE, RPC_DEQUEUE, RPC_DROP, WAKE, WAKE_DONE, DETECT_START,
STAGE1_DONE, EARLY_EXIT, SECOND_PASS, RESULT, RESULT_DELIVERED, SLEEP,
SIM_END`. Every event-scoped line carries the workload `event_id`.

## Verified build and smoke commands

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
bash tests/run_tests.sh                 # unit + integration tests
bash scripts/smoke_test.sh 300          # 5 scenarios x 6 modes x 2 seeds, 300 s
```

## Scientific weaknesses the task attributes to the prototype, and how they are addressed

| weakness | correction |
|---|---|
| random-probability security blocking | algorithmic gate: consistency, duplicate, replay, burst, rate limit (`simulation/security/security_gate.h`) |
| triggers generated automatically, not by a watcher algorithm | deterministic feature-score watcher with threshold, cooldown and noise-adaptive threshold |
| modes possibly consuming different random event streams | workloads are generated once and replayed by every mode; per-event detector/RPC draws are keyed by (seed, event_id) |
| duty cycle reported as if it were energy | separate state-based modeled energy with explicit, uncalibrated power assumptions |
| five seeds, no statistics | 10 seeds, matched-pair Wilcoxon tests, effect sizes, Holm correction |
| no ground truth for triggers/attacks | every workload observation carries ground-truth legitimacy, object presence/class and attack labels |
