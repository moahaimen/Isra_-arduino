// Cortex-M7 detector for the Portenta H7 (FUTURE HARDWARE VALIDATION SKELETON).
// Not compiled or flashed in this repository's CI; see firmware/README.md.
#include <RPC.h>

static const int PIN_ACTIVE_MARK = LEDG;  // high while the M7 is active (duty-cycle probe)

int detect(int t_trigger_ms) {
  digitalWrite(PIN_ACTIVE_MARK, HIGH);
  const unsigned long t0 = micros();
  // 1. capture frame, 2. stage-1 inference, 3. optional second pass,
  // 4. postprocessing. Replace with the real detector; log per-stage micros()
  // to calibrate inference_ms / second_pass_cost_ms / postprocess_*_ms.
  const unsigned long t1 = micros();
  digitalWrite(PIN_ACTIVE_MARK, LOW);
  (void)t_trigger_ms;
  return (int)(t1 - t0);
}

void setup() {
  RPC.begin();
  pinMode(PIN_ACTIVE_MARK, OUTPUT);
  RPC.bind("detect", detect);
}

void loop() {
  // Enter low-power sleep until the next RPC interrupt (HSEM/mailbox).
}
