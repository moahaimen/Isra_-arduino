// Cortex-M4 R3 utility-gated scheduler + temporal-context gate for the Portenta H7.
// HARDWARE VALIDATION SKELETON: not compiled for the board, not flashed, not measured.
// Same headers as the simulator: frame_features.h (float), ugs_scheduler.h, ugs_gate.h.
// firmware/host_check_r3.cpp compiles the identical loop on a PC (run by tests/run_tests.sh).
//
// M4 -> M7: RPC "detect"(t_ms) wakes the M7, which captures/infers and returns the cell mask
// (uint64, 12x4 grid, bit = row*12 + col) of the boxes above the detection threshold; the M4
// feeds it to UgsScheduler::feedback() (closed loop). FRAME_SOURCE_TRACE replays the stored
// frames of one workload from QSPI flash so the hardware sees what the simulator saw.
#include <RPC.h>
#include "frame_features.h"
#include "ugs_scheduler.h"
#include "ugs_gate.h"

#define FRAME_SOURCE_TRACE 1
static const int PIN_FEATURE_MARK = LEDB;   // feature extraction + decisions
static const int PIN_TRIGGER_MARK = LEDR;   // accepted request -> RPC
static const uint32_t FRAME_PERIOD_MS = 100;

static sim::FrameFeatureExtractor<float> fx;
static sim::UgsScheduler* sched;
static sim::UgsGate<64>* gate;               // 64-frame history (6.4 s); NOT the history used for tuning
static uint8_t lowres[96 * 32], thumb_fp[17 * 16];
static int outstanding = 0;
extern bool next_frame(uint8_t* lowres, uint8_t* thumb);  // trace or camera driver (board-specific)
extern bool m7_awake();                                   // M7 power state from the system controller

void setup() {
  RPC.begin();
  pinMode(PIN_TRIGGER_MARK, OUTPUT);
  pinMode(PIN_FEATURE_MARK, OUTPUT);
  static sim::UgsScheduler s{sim::UgsParams()};   // replace by results/r3/ frozen values when frozen
  static sim::UgsGate<64> g{sim::UgsGateParams()};
  sched = &s;
  gate = &g;
}

void loop() {
  const uint32_t t0 = millis();
  if (!next_frame(lowres, thumb_fp)) return;
  digitalWrite(PIN_FEATURE_MARK, HIGH);
  sim::FrameFeaturesOut f = fx.step(lowres, thumb_fp);
  sim::UgsDecision d = sched->evaluate(t0, {f.r2_motion, f.r2_visual, f.r2_temporal, f.r2_consistency,
                                            f.motion_cells, m7_awake(), outstanding});
  sim::UgsGateFrame gf{};
  gf.t_ms = t0;
  fx.thumb192(lowres, gf.thumb);
  gf.fg_count = f.fg_count;
  bool accept = d.trigger && gate->decide(gf, d.novel).accept;
  gate->observe(gf);
  digitalWrite(PIN_FEATURE_MARK, LOW);
  if (accept) {
    sched->commit(t0, d.region_mask);
    ++outstanding;
    digitalWrite(PIN_TRIGGER_MARK, HIGH);
    uint64_t cells = RPC.call("detect", (int)t0).as<uint64_t>();   // blocks until the M7 result returns
    digitalWrite(PIN_TRIGGER_MARK, LOW);
    --outstanding;
    sched->feedback(d.region_mask, cells, millis());
  }
  while (millis() - t0 < FRAME_PERIOD_MS) __WFI();
}
