# S4 K1 — hardware effect-size gate (Portenta H7)

Status: **PRE-REGISTERED, NOT YET RUN.** No algorithm or mitigation is authorized until this gate passes.

## Question

On STM32H747 / Portenta H7, does bursty M7 work materially perturb a latency-critical M4 watcher through shared buses/memory/peripherals/power-domain interactions?

This is an **effect-size test**, not a performance paper experiment.

## Prior-art boundary

The dual-core vision architecture itself is prior art. Lee, Kim & Hong (IEEE Access 2024, DOI 10.1109/ACCESS.2024.3443406) already use STM32H747 with M4 camera/preprocessing, M7 DNN inference, shared SRAM4, concurrent execution, and latency/power evaluation.

Generic multicore temporal-interference measurement and bandwidth regulation are also prior art (e.g. VanderLeest & Thompson; MemPol; RT-Gang++).

Therefore K1 tests only the remaining gap: **measurable cross-core temporal isolation failure in MCU-class concurrent vision-style workloads.**

## Primary endpoint

M4 execution-time inflation while M7 is active.

For each condition measure >= 10,000 M4 periods after >= 1,000 warm-up periods:
- median
- P95
- P99
- maximum observed execution time
- deadline misses for a 100 ms period
- run-to-run CV across >= 5 independent runs

Primary effect:
[
I_{99} = P99(T_{M4}|condition) / P99(T_{M4}|M7-idle)
]

## Pre-registered decision

- **KILL S4** if realistic M7 inference / realistic M7 workload gives <10% P99 inflation and no M4 deadline misses in every plausible shared-resource condition.
- **WEAK** if 10–25% P99 inflation with no meaningful deadline failures.
- **PROCEED** only if >=25% repeatable P99 inflation, repeatable deadline failures, or an equally material camera/DMA/power-domain coupling is observed.
- A synthetic memory hammer alone cannot pass K1. It may identify a channel, but at least one realistic M7 workload must reproduce a material effect.

No threshold may be changed after seeing results.

## Conditions

### A. Baseline
A0. M7 idle / WFI, M4 fixed watcher kernel.

### B. M7 compute without intentional memory pressure
B1. Dense integer/FPU compute loop whose working set fits local/cache memory where possible.

Purpose: separate shared-memory/bus effects from generic simultaneous-core/power effects.

### C. M7 memory pressure
C1. Sequential reads.
C2. Sequential writes.
C3. Read-modify-write.
C4. Strided/random access.

Test first with M7-local memory placement; then with a deliberately shared/reachable SRAM region **only after linker-map verification**. Never hard-code an SRAM address that can overlap Arduino RPC/MBED runtime buffers.

### D. Inter-core exchange
D1. Shared-buffer producer/consumer at low rate.
D2. Shared-buffer exchange at realistic camera-frame rate.
D3. High-rate stress only as channel characterization.

### E. Realistic M7 AI workload
E1. Existing deployable TFLM/X-CUBE-AI inference if available.
E2. If no existing Portenta detector exists, use a known-good fixed TFLM image model on M7 solely as a realistic memory/compute workload. Do not report its accuracy as a research result.

### F. Camera/DMA (if hardware stack is available)
F1. Camera capture/DMA with M7 idle.
F2. Camera capture/DMA + M7 inference.
F3. Same with alternative buffer placement.

## M4 workload

Use a fixed deterministic watcher kernel at 10 Hz. The kernel must:
- perform the same operations and touch the same memory on every period;
- not call RPC, Serial, malloc/free, file I/O, or logging inside the timed region;
- buffer timestamps/cycle counts locally and export only after each run;
- expose a GPIO high pulse exactly around the timed region for external validation.

Prefer:
1. the real R3 M4 feature-extraction kernel with a frozen in-RAM frame repeated every period; or
2. if board compilation of the watcher is blocked, a fixed-size surrogate that matches its measured memory footprint/ops, explicitly labeled surrogate.

## Timing

Preferred:
- DWT CYCCNT on Cortex-M4 for cycle counts.
- independent logic-analyzer measurement of the M4 GPIO pulse for validation.

Do not use Serial/RPC timing inside the critical window.

## Memory-placement matrix

Record linker map for every build.

Minimum comparison:
- M4 code/data in its intended/local domain where possible;
- M7 code/data in intended/local domain;
- shared inter-core data isolated to a small dedicated region;
- one intentionally contention-prone placement if safely supported.

Do not claim “memory isolation” merely because different C variables were used; physical SRAM/bus placement must be verified.

## Power/domain observations

If a power meter is available, log board current synchronously with M7 active marker. This is secondary to timing in K1.

Also record whether enabling M7 workload changes the ability to place D1/D2/D3 domains into intended low-power states. ST documentation notes that shared exchange buffers and domain availability can affect low-power behavior.

## Required artifacts

- firmware source + exact Arduino core/toolchain version
- linker map files
- board ID / board revision
- raw per-period timing CSV
- run metadata JSON
- analysis script
- plots/tables generated from raw data
- no manual removal of latency outliers

## Analysis

Report distributions, not only means.

For each condition:
- median/P95/P99/max
- I50, I95, I99 vs A0
- deadline-miss count/rate
- bootstrap 95% CI for paired/run-level P99 ratios when meaningful
- effect repeated across runs

K1 is not allowed to claim causality for a particular channel until a placement/aggressor ablation supports it.

## Stop conditions

Stop immediately and report rather than improvising if:
- the actual Portenta H7 is unavailable;
- both cores cannot be built/flashed reproducibly;
- linker placement cannot be verified;
- timing instrumentation changes the timed workload materially;
- only a synthetic aggressor produces an effect while realistic inference does not.

## After K1

If K1 fails: archive S4 as NO-GO.

If K1 passes: only then perform K2 channel decomposition and compare mitigation candidates. Static memory partitioning, ordinary HSEM locking, or generic bandwidth throttling are baselines, not novelty.
