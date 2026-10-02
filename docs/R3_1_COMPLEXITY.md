# R3.1 complexity and Cortex-M4 feasibility

Measured here (host + `arm-none-eabi-g++ 13.2` cross-compile, `-Os -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -fno-exceptions -fno-rtti`,
probe `results/r3_1/complexity/m4_probe.cpp`, sizes in `m4_probe_size.txt`). **No timing was measured on a Portenta; host timings are not Portenta timings.**

| item | value | source |
|---|---|---|
| Static RAM of the probe (feature extractor + scheduler + gate<256> + gate-state with R3.1 buckets) | 144,940 B (.bss) + 4 B (.data) | arm-none-eabi-size |
| – FrameFeatureExtractor<float> | 76,804 B | `firmware_host_check_r3` |
| – UgsScheduler (R3.1 fields included) | ≈ 2.0 KB (R3: 1,888 B; host check re-run output in `host_check_r3.txt`) | sizeof |
| – UgsGate<256> history | ≈ 54 KB (+ 8 content-bucket doubles) | sizeof |
| Code (.text) of the probe | 8,348 B | arm-none-eabi-size |
| Heap / exceptions / RTTI | none | build flags |
| Worst-case gate ops | R3: 256 history × 192 block compares = 49,152 per frame; **R3.1 shift tolerance**: up to 8 extra shifted comparisons for each history entry whose unshifted count ≤ `shift_try` (worst case ≈ 9× → ≈ 442 k block compares); `shift_try` bounds it in practice | code inspection |
| Scheduler ops | median/MAD sort 2 × 64²/2 = 4,096 compares; ≤ 48 × 8 dilations; 8 × 8 popcounts | code inspection |

## Feasibility statements and caveats
* **Fits the Portenta M4 on RAM/flash by size, subject to verification.** The STM32H747XI datasheet (recalled, not re-checked in this session) lists
  ~288 KB of D2-domain SRAM (SRAM1–3) plus 64 KB SRAM4 usable by the M4 and 2 MB flash shared with the M7; 145 KB of static state is below that, but
  the camera/frame buffers, the RPC buffers and the Arduino core are **not** included. Needs confirmation by linking the real sketch.
* **Floating point is a defect for the M4:** the core is single-precision FPU only, while scheduler, features and gate use `double`; the probe links against
  `__aeabi_dadd/dmul/ddiv/...` (software double arithmetic, `m4_probe_undefined.txt`). Frame-rate feasibility (10 fps ⇒ 100 ms/frame) is therefore
  **unverified**; porting to `float` (and re-validating parity) is required before any on-device timing claim.
* One portability bug was found by this cross-compile and fixed: `M_PI` was undefined under strict C++17 in `frame_features.h`.
* The Arduino sketch itself (`firmware/m4_watcher_r3`) was not rebuilt with the Arduino toolchain (not available here); the R3.1 mechanisms are simulation-side only so far.
* Portenta timing hooks: still the R3 hooks (`docs/` hardware-prep); the per-frame ops counts above are what the hooks should be compared against.
