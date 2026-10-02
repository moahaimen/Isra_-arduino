// Host-side check that the firmware decision logic (shared headers) behaves
// identically to the simulator when driven by mocked millis()/delay()/RPC.
#include <cstdio>

#include "core/arduino_mocks.h"
#include "security/security_gate.h"
#include "watcher/watcher.h"

int main() {
    sim::WatcherParams wp;
    sim::SecurityParams sp;
    sim::Watcher watcher(wp);
    sim::SecurityGate<256> gate(sp);
    sim_mock::RpcMock rpc;
    int served = 0;
    rpc.bind("detect", [&](double, double) { return ++served; });

    struct In { double m, v, t, c, n; unsigned long long sig; };
    const In frames[] = {
        {0.70, 0.75, 0.72, 0.90, 0.10, 1},  // strong legitimate object -> trigger
        {0.70, 0.75, 0.72, 0.90, 0.10, 2},  // within cooldown -> suppressed
        {0.20, 0.20, 0.25, 0.85, 0.10, 3},  // weak -> no trigger
        {0.95, 0.60, 0.30, 0.20, 0.10, 4},  // inconsistent spoof -> blocked
        {0.70, 0.75, 0.72, 0.90, 0.10, 1},  // same signature replayed later -> blocked (REPLAY)
    };
    const double gaps[] = {0, 500, 3000, 3000, 3000};
    const int expect_rpc = 1;
    int i = 0;
    for (const In& f : frames) {
        delay(static_cast<uint32_t>(gaps[i++]));
        const double t = millis();
        sim::WatcherDecision d = watcher.evaluate(t, {f.m, f.v, f.t, f.c, f.n});
        sim::SecurityFrame fr{t, f.m, f.v, f.t, f.c, f.sig};
        if (d.raw_positive) gate.note_candidate(t);
        if (d.trigger) {
            sim::SecurityDecision s = gate.decide(fr);
            std::printf("t=%.0f score=%.3f trigger accept=%d reason=%s\n", t, d.score, s.accept,
                        sim::security_reason_name(s.reason));
            if (s.accept) rpc.call("detect", t, 0);
        } else {
            std::printf("t=%.0f score=%.3f no trigger (suppress=%d)\n", t, d.score, d.suppress);
        }
        gate.observe(fr);
    }
    const bool ok = static_cast<int>(rpc.calls.size()) == expect_rpc && served == expect_rpc;
    std::printf("firmware_host_check: %s (rpc calls=%zu)\n", ok ? "PASS" : "FAIL", rpc.calls.size());
    return ok ? 0 : 1;
}
