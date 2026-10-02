// Compile probe for the Cortex-M4 path (header-only classes, no heap, no exceptions).
#include <cstdint>
#include "security/ugs_gate.h"
#include "watcher/frame_features.h"
#include "watcher/ugs_scheduler.h"
static sim::FrameFeatureExtractor<float> fx;
static sim::UgsScheduler sched{sim::UgsParams()};
static sim::UgsGate<256> gate{sim::UgsGateParams()};
int m4_step(const uint8_t* L, const uint8_t* F, double t, sim::UgsGateFrame& gf) {
    sim::FrameFeaturesOut f = fx.step(L, F);
    sim::UgsDecision d = sched.evaluate(t, {f.r2_motion, f.r2_visual, f.r2_temporal, f.r2_consistency, f.motion_cells, false, 0});
    if (d.trigger) {
        sim::UgsGateDecision g = gate.decide(gf, d.novel, d.region);
        if (g.accept) sched.commit(t, d.region_mask);
        return g.accept;
    }
    gate.observe(gf);
    return 0;
}
