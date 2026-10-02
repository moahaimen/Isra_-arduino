// Cortex-M4 watcher for the Portenta H7 (FUTURE HARDWARE VALIDATION SKELETON).
// Not compiled or flashed in this repository's CI; see firmware/README.md.
#include <RPC.h>
#include "watcher.h"
#include "security_gate.h"

static sim::WatcherParams wp;     // defaults match config/default_config.json
static sim::SecurityParams sp;
static sim::Watcher* watcher;
static sim::SecurityGate<256>* gate;  // smaller history to fit M4 SRAM
static const int PIN_TRIGGER_MARK = LEDR;  // GPIO marker for logic-analyzer timing

// Placeholder feature extraction: replace with the real low-resolution
// sensing front end (PIR / frame differencing / ambient light).
static sim::WatcherFeatures read_features() {
  sim::WatcherFeatures f{0, 0, 0, 1, 0};
  return f;
}

void setup() {
  RPC.begin();
  pinMode(PIN_TRIGGER_MARK, OUTPUT);
  static sim::Watcher w(wp);
  static sim::SecurityGate<256> g(sp);
  watcher = &w;
  gate = &g;
}

void loop() {
  const double t = millis();
  sim::WatcherFeatures f = read_features();
  sim::WatcherDecision d = watcher->evaluate(t, f);
  sim::SecurityFrame fr{t, f.motion, f.visual, f.temporal, f.consistency, 0};
  if (d.raw_positive) gate->note_candidate(t);
  if (d.trigger) {
    sim::SecurityDecision s = gate->decide(fr);
    if (s.accept) {
      digitalWrite(PIN_TRIGGER_MARK, HIGH);  // t_trigger marker
      RPC.call("detect", (int)t).as<int>();  // wakes the M7
      digitalWrite(PIN_TRIGGER_MARK, LOW);
    }
  }
  gate->observe(fr);
  delay(50);  // watcher sampling period (simulation assumes event-driven sampling)
}
