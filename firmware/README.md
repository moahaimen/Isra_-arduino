# Firmware interface (future hardware validation)

This folder holds the Portenta H7 firmware skeletons that will be used for
**future** hardware validation. Nothing here has been flashed or measured.

* `m4_watcher/m4_watcher.ino` runs the always-on watcher and the security gate
  on the Cortex-M4 and sends `detect` RPC requests to the M7.
* `m7_detector/m7_detector.ino` serves those requests on the Cortex-M7 and
  marks where the real detector, timing probes and GPIO markers go.
* Both sketches include the SAME decision logic as the simulator:
  `simulation/watcher/watcher.h` and `simulation/security/security_gate.h`
  (header-only, no heap allocation). Copy those two headers next to the
  sketches (or add the `simulation/` folder to the include path) when building
  with arduino-cli.
* `host_check.cpp` compiles the shared logic on a PC against
  `simulation/core/arduino_mocks.h` (mocked `millis()`, `delay()` and RPC) and
  checks that firmware and simulator take the same decisions. It is built and
  run by `tests/run_tests.sh`.

The GPIO marker pins and timestamps listed in the sketches are the hooks for
the measurements described in `docs/HARDWARE_VALIDATION_PLAN.md`.
