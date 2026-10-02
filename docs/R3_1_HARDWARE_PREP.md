# R3.1 hardware preparation (no hardware measurements exist)

* `config/power_model_assumed.json` — assumed state powers (copy of `config/power_model.json`, the simulator default). **Not measured.**
* `config/power_model_calibrated.json` — **does not exist**; it is produced only by `scripts/import_hardware_measurements.py` from a real measurement CSV
  (the importer refuses to overwrite the assumed model). No energy number in R3.1 is measured; all are "modeled".
* Open items before any on-device claim: (1) port M4 path to single-precision (`double` ⇒ software float on the M4, see `docs/R3_1_COMPLEXITY.md`);
  (2) rebuild `firmware/m4_watcher_r3` with the Arduino toolchain including the R3.1 gate options (grad_c); (3) link and read the real M4 RAM/flash map;
  (4) measure per-frame M4 cycles with the existing timing hooks and compare with the ops counts; (5) measure state powers (M4 monitor, RPC, M7 wake/inference/stop) with a
  current probe following `docs/HARDWARE_VALIDATION_PLAN.md`, import with the importer.
* Remaining Portenta experiment (smallest that tests the R3.1 conclusion): run the legacy event trigger (threshold 0.25, cooldown 2 s) with and without the
  gradient-tolerant replay gate on a replayed-video bench, logging M7 wake count and energy per minute with a power analyser.
