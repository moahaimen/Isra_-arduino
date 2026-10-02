// Host-side check of the R2 M4 pipeline (frame features -> robust watcher ->
// robust gate) exactly as wired in firmware/m4_watcher_r2/m4_watcher_r2.ino,
// with the FLOAT feature extractor used on the M4. Prints the static memory
// of every component (reported in docs/R2_METHOD.md) and checks decisions on
// a synthetic frame stream: one moving object triggers, its later replay is
// blocked, a 1-frame flash does not trigger.
#include <cstdio>
#include <cstring>

#include "core/arduino_mocks.h"
#include "security/robust_gate.h"
#include "watcher/frame_features.h"
#include "watcher/robust_watcher.h"

static sim::FrameFeatureExtractor<float> fx;

int main() {
    sim::RobustWatcherParams wp;
    sim::RobustGateParams gp;
    gp.replay_min_age_ms = 2000.0;
    static sim::RobustWatcher w(wp);
    static sim::RobustGate<128> g(gp);
    sim_mock::RpcMock rpc;
    int served = 0;
    rpc.bind("detect", [&](double, double) { return ++served; });

    static uint8_t bg[96 * 32], L[96 * 32], F[17 * 16];
    for (int i = 0; i < 96 * 32; ++i) bg[i] = static_cast<uint8_t>(60 + (i * 37) % 120);
    for (int i = 0; i < 17 * 16; ++i) F[i] = static_cast<uint8_t>((i * 53) % 251);
    auto frame_with_object = [&](int x) {
        std::memcpy(L, bg, sizeof(L));
        for (int y = 8; y < 20; ++y)
            for (int xx = x; xx < x + 6 && xx < 96; ++xx) L[y * 96 + xx] = 250;
    };
    int accepted_obj = 0, accepted_replay = 0, accepted_flash = 0, triggers = 0;
    const int N = 160;
    for (int i = 0; i < N; ++i) {
        const double t = i * 100.0;
        int kind = 0;  // 0 background, 1 object, 2 replay of object frames, 3 flash
        if (i >= 30 && i < 45) { frame_with_object(10 + 3 * (i - 30)); kind = 1; }
        else if (i >= 110 && i < 125) { frame_with_object(10 + 3 * (i - 110)); kind = 2; }
        else if (i == 80) { std::memcpy(L, bg, sizeof(L)); for (int y = 4; y < 28; ++y) for (int x = 60; x < 80; ++x) L[y * 96 + x] = 255; kind = 3; }
        else std::memcpy(L, bg, sizeof(L));
        sim::FrameFeaturesOut f = fx.step(L, F);
        sim::RobustDecision d = w.evaluate(t, {f.r2_motion, f.r2_visual, f.r2_temporal, f.r2_consistency, f.motion_cells});
        sim::RobustFrame fr{};
        fr.t_ms = t;
        fr.consistency = f.r2_consistency;
        fr.cells = f.motion_cells;
        for (int k = 0; k < 4; ++k) fr.fp[k] = f.fp[k];
        for (int k = 0; k < 12; ++k) fr.fg[k] = f.fg[k];
        fr.fg_count = f.fg_count;
        bool acc = false;
        if (d.trigger) {
            ++triggers;
            acc = g.decide(fr, d.novel, d.z).accept;
            if (acc) rpc.call("detect", t, 0);
        }
        g.observe(fr);
        accepted_obj += acc && kind == 1;
        accepted_replay += acc && kind == 2;
        accepted_flash += acc && kind == 3;
    }
    std::printf("memory: FrameFeatureExtractor<float>=%zu B, RobustWatcher=%zu B, RobustGate<128>=%zu B, "
                "RobustGate<512>=%zu B\n",
                sizeof(sim::FrameFeatureExtractor<float>), sizeof(sim::RobustWatcher), sizeof(sim::RobustGate<128>),
                sizeof(sim::RobustGate<512>));
    std::printf("triggers=%d accepted object=%d replay=%d flash=%d rpc=%zu\n", triggers, accepted_obj,
                accepted_replay, accepted_flash, rpc.calls.size());
    const bool ok = accepted_obj >= 1 && accepted_replay == 0 && accepted_flash == 0 &&
                    static_cast<int>(rpc.calls.size()) == served;
    std::printf("firmware_host_check_r2: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
