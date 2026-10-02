// Host-side check of the R3 M4 pipeline exactly as it would run on the
// Cortex-M4: FrameFeatureExtractor<float> -> UgsScheduler -> UgsGate, with
// mocked RPC. Reports static memory of every component and worst-case
// per-frame operation counts (used in docs/R3_COMPLEXITY.md), and checks the
// decisions on a synthetic stream: two objects appearing together both get an
// M7 check, a one-frame flash never wakes the M7, a replay of an earlier
// object frame is blocked, a static scene is never blocked.
#include <cstdio>
#include <cstring>

#include "core/arduino_mocks.h"
#include "security/ugs_gate.h"
#include "watcher/frame_features.h"
#include "watcher/ugs_scheduler.h"

static sim::FrameFeatureExtractor<float> fx;
static sim::UgsScheduler sched{sim::UgsParams()};
static sim::UgsGate<256> gate{sim::UgsGateParams()};

int main() {
    sim_mock::RpcMock rpc;
    rpc.bind("detect", [&](double, double) { return 1; });
    static uint8_t bg[96 * 32], L[96 * 32], F[17 * 16];
    for (int i = 0; i < 96 * 32; ++i) bg[i] = static_cast<uint8_t>(60 + (i * 37) % 120);
    for (int i = 0; i < 17 * 16; ++i) F[i] = static_cast<uint8_t>((i * 53) % 251);
    auto draw = [&](int x, int y0) {
        for (int y = y0; y < y0 + 10; ++y)
            for (int xx = x; xx < x + 6 && xx < 96; ++xx) L[y * 96 + xx] = 250;
    };
    int sent = 0, sent_two = 0, sent_flash = 0, sent_replay = 0, blocked_static = 0;
    uint8_t frame_regions[400] = {};
    for (int i = 0; i < 400; ++i) {
        const double t = i * 100.0;
        std::memcpy(L, bg, sizeof(L));
        int kind = 0;
        if (i >= 50 && i < 80) { draw(10 + 2 * (i - 50), 4); draw(70 - 2 * (i - 50), 18); kind = 1; }  // two objects
        else if (i == 150) { for (int y = 2; y < 30; ++y) for (int x = 40; x < 60; ++x) L[y * 96 + x] = 255; kind = 2; }
        else if (i >= 250 && i < 262) { draw(10 + 2 * (i - 250), 4); draw(70 - 2 * (i - 250), 18); kind = 3; }  // replay
        else if (i >= 300) { draw(30, 10); kind = 4; }  // static object (parked)
        sim::FrameFeaturesOut f = fx.step(L, F);
        sim::UgsDecision d = sched.evaluate(t, {f.r2_motion, f.r2_visual, f.r2_temporal, f.r2_consistency, f.motion_cells,
                                                false, 0});
        sim::UgsGateFrame gf{};
        gf.t_ms = t;
        fx.thumb192(L, gf.thumb);
        gf.fg_count = f.fg_count;
        bool acc = false;
        if (d.trigger) {
            sim::UgsGateDecision g = gate.decide(gf, d.novel);
            acc = g.accept;
            if (!acc && kind == 4) ++blocked_static;
            if (acc) {
                sched.commit(t, d.region_mask);
                rpc.call("detect", t, 0);
                sched.feedback(d.region_mask, kind == 1 ? f.motion_cells : 0ULL, t + 300.0);  // M7 result
                ++sent;
                frame_regions[i] = d.region_mask;
            }
        }
        gate.observe(gf);
        sent_two += acc && kind == 1;
        sent_flash += acc && kind == 2;
        sent_replay += acc && kind == 3;
    }
    int regions_two = 0;
    uint8_t seen = 0;
    for (int i = 50; i < 80; ++i) seen |= frame_regions[i];
    for (int k = 0; k < 8; ++k) regions_two += (seen >> k) & 1;
    std::printf("memory: FrameFeatureExtractor<float>=%zu B, UgsScheduler=%zu B, UgsGate<256>=%zu B, UgsGate<64>=%zu B\n",
                sizeof(sim::FrameFeatureExtractor<float>), sizeof(sim::UgsScheduler), sizeof(sim::UgsGate<256>),
                sizeof(sim::UgsGate<64>));
    std::printf("worst-case ops/frame: scheduler median/MAD sort 2x64^2/2=4096 cmp, components <=48x8 dilations, "
                "region match 8x8 popcounts; gate: 2 medians (192) + history 256 x 192 block compares = 49152\n");
    std::printf("requests=%d two-object=%d (regions %d) flash=%d replay=%d static_blocked=%d\n", sent, sent_two,
                regions_two, sent_flash, sent_replay, blocked_static);
    const bool ok = sent_two >= 2 && regions_two >= 2 && sent_flash == 0 && sent_replay == 0 && blocked_static == 0;
    std::printf("firmware_host_check_r3: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
