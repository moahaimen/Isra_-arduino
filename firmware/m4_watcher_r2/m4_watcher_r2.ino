// Cortex-M4 R2 watcher for the Portenta H7 (HARDWARE VALIDATION SKELETON).
// Not flashed yet; see docs/HARDWARE_MINIMAL_R2.md. Shares the decision code
// with the simulator: frame_features.h (float variant), robust_watcher.h,
// robust_gate.h. firmware/host_check_r2.cpp compiles the same loop on a PC.
//
// Frame source:
//   FRAME_SOURCE_TRACE  frames of a fixed R2 workload trace stored in QSPI
//                       flash (96x32 + 17x16 bytes per frame, 10 Hz) - used for
//                       the end-to-end energy experiment, so the hardware sees
//                       exactly the frames the simulator saw;
//   FRAME_SOURCE_CAMERA Vision Shield (HM01B0, 320x320 gray) binned to 96x32
//                       and 17x16 by the camera driver / DMA.
#include <RPC.h>
#include "frame_features.h"
#include "robust_watcher.h"
#include "robust_gate.h"

#define FRAME_SOURCE_TRACE 1
static const int PIN_TRIGGER_MARK = LEDR;  // high while an accepted request is sent
static const int PIN_FEATURE_MARK = LEDB;  // high during feature extraction + decision
static const uint32_t FRAME_PERIOD_MS = 100;

static sim::FrameFeatureExtractor<float> fx;   // ~45 KB state (see host check)
static sim::RobustWatcherParams wp;             // overwritten with results/r2/frozen_params.json values
static sim::RobustGateParams gp;
static sim::RobustWatcher* watcher;
static sim::RobustGate<128>* gate;              // 128-entry fingerprint history on the M4
static uint8_t lowres[96 * 32], thumb[17 * 16];

extern bool next_frame(uint8_t* lowres, uint8_t* thumb);  // trace or camera, board-specific

void setup() {
  RPC.begin();
  pinMode(PIN_TRIGGER_MARK, OUTPUT);
  pinMode(PIN_FEATURE_MARK, OUTPUT);
  static sim::RobustWatcher w(wp);
  static sim::RobustGate<128> g(gp);
  watcher = &w;
  gate = &g;
}

void loop() {
  const uint32_t t0 = millis();
  if (!next_frame(lowres, thumb)) return;
  digitalWrite(PIN_FEATURE_MARK, HIGH);
  sim::FrameFeaturesOut f = fx.step(lowres, thumb);
  sim::RobustDecision d = watcher->evaluate(t0, {f.r2_motion, f.r2_visual, f.r2_temporal, f.r2_consistency,
                                                 f.motion_cells});
  sim::RobustFrame fr{};
  fr.t_ms = t0;
  fr.consistency = f.r2_consistency;
  fr.cells = f.motion_cells;
  for (int k = 0; k < 4; ++k) fr.fp[k] = f.fp[k];
  for (int k = 0; k < 12; ++k) fr.fg[k] = f.fg[k];
  fr.fg_count = f.fg_count;
  bool accept = false;
  if (d.trigger) accept = gate->decide(fr, d.novel, d.z).accept;
  gate->observe(fr);
  digitalWrite(PIN_FEATURE_MARK, LOW);
  if (accept) {
    digitalWrite(PIN_TRIGGER_MARK, HIGH);
    RPC.call("detect", (int)t0).as<int>();  // wakes the M7
    digitalWrite(PIN_TRIGGER_MARK, LOW);
  }
  while (millis() - t0 < FRAME_PERIOD_MS) {
    __WFI();  // M4 sleeps until the next frame tick
  }
}
