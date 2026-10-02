// C++ unit tests for the simulator components (no external framework).
// Build: cmake --build build --target unit_tests && ./build/unit_tests
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "config/sim_config.h"
#include "core/rng.h"
#include "core/simulator.h"
#include "energy/energy_model.h"
#include "security/security_gate.h"
#include "watcher/watcher.h"
#include "workload/workload.h"

using namespace sim;

static int g_fail = 0, g_pass = 0;
#define CHECK(cond)                                                              \
    do {                                                                         \
        if (cond) {                                                              \
            ++g_pass;                                                            \
        } else {                                                                 \
            ++g_fail;                                                            \
            std::printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);        \
        }                                                                        \
    } while (0)

static SimConfig cfg_for(const std::string& mode, const std::string& scenario, uint64_t seed, double seconds) {
    SimConfig c;
    load_config_file(c, "config/default_config.json");
    apply_mode_defaults(c, mode);
    c.scenario = scenario;
    c.seed = seed;
    c.seconds = seconds;
    c.log_level = "none";
    return c;
}

static std::string serialize(const Workload& wl) {
    std::string s;
    for (const auto& e : wl.events) s += workload_event_to_jsonl(e) + "\n";
    return s;
}

static void test_rng() {
    std::printf("test_rng\n");
    Rng a(42), b(42), c(43);
    bool same = true, diff = false;
    for (int i = 0; i < 1000; ++i) {
        uint64_t x = a.next_u64(), y = b.next_u64(), z = c.next_u64();
        same &= (x == y);
        diff |= (x != z);
    }
    CHECK(same);
    CHECK(diff);
    Rng k1 = Rng::keyed(7, "det_s1", 99), k2 = Rng::keyed(7, "det_s1", 99), k3 = Rng::keyed(7, "det_s2", 99);
    const double u1 = k1.uniform(), u2 = k2.uniform(), u3 = k3.uniform();
    CHECK(u1 == u2);
    CHECK(u1 != u3);
    Rng r(1);
    double sum = 0, sum2 = 0;
    const int n = 200000;
    for (int i = 0; i < n; ++i) {
        double x = r.normal(0, 1);
        sum += x;
        sum2 += x * x;
    }
    CHECK(std::fabs(sum / n) < 0.01);
    CHECK(std::fabs(sum2 / n - 1.0) < 0.02);
    double es = 0;
    for (int i = 0; i < n; ++i) es += r.exponential(2.0);
    CHECK(std::fabs(es / n - 0.5) < 0.01);
}

static void test_energy_tracker() {
    std::printf("test_energy_tracker\n");
    CoreStateTracker t(M7_SLEEP, 0.0);
    t.set(100.0, M7_WAKEUP);
    t.set(103.0, M7_INFERENCE);
    t.set(243.0, M7_POSTPROCESS);
    t.set(250.0, M7_SLEEP);
    t.finalize(1000.0);
    CHECK(std::fabs(t.time_in(M7_SLEEP) - 850.0) < 1e-9);
    CHECK(std::fabs(t.time_in(M7_WAKEUP) - 3.0) < 1e-9);
    CHECK(std::fabs(t.time_in(M7_INFERENCE) - 140.0) < 1e-9);
    CHECK(std::fabs(t.time_in(M7_POSTPROCESS) - 7.0) < 1e-9);
    PowerModel pm = load_power_model("config/power_model.json");
    const double e = (pm.power_mw[M7_SLEEP] * 850 + pm.power_mw[M7_WAKEUP] * 3 + pm.power_mw[M7_INFERENCE] * 140 +
                      pm.power_mw[M7_POSTPROCESS] * 7) / 1000.0;
    // 8*850 + 150*3 + 420*140 + 300*7 = 6800 + 450 + 58800 + 2100 = 68150 uJ = 68.15 mJ
    CHECK(std::fabs(e - 68.15) < 1e-9);
    CHECK(!pm.calibrated);
}

static void test_watcher() {
    std::printf("test_watcher\n");
    WatcherParams p;
    p.adaptive = false;
    Watcher w(p);
    WatcherDecision d1 = w.evaluate(0, {0.7, 0.7, 0.7, 0.9, 0.1});
    CHECK(d1.trigger);
    CHECK(std::fabs(d1.score - (0.3 * 0.7 + 0.35 * 0.7 + 0.2 * 0.7 + 0.15 * 0.9)) < 1e-12);
    WatcherDecision d2 = w.evaluate(1000, {0.7, 0.7, 0.7, 0.9, 0.1});
    CHECK(d2.raw_positive && !d2.trigger && d2.suppress == WS_COOLDOWN);
    WatcherDecision d3 = w.evaluate(1600, {0.7, 0.7, 0.7, 0.9, 0.1});
    CHECK(d3.trigger);
    WatcherDecision d4 = w.evaluate(5000, {0.1, 0.1, 0.1, 0.9, 0.1});
    CHECK(!d4.raw_positive && d4.suppress == WS_BELOW_THRESHOLD);
    // Adaptive threshold rises with sustained noise.
    WatcherParams pa;
    Watcher wa(pa);
    double thr = 0;
    for (int i = 0; i < 200; ++i) thr = wa.evaluate(i * 10000.0, {0.1, 0.1, 0.1, 0.5, 0.6}).threshold;
    CHECK(thr > pa.theta + 0.15);
    // Motion-only rule.
    WatcherParams pm;
    pm.motion_only = true;
    Watcher wm(pm);
    CHECK(wm.evaluate(0, {0.6, 0.0, 0.0, 0.0, 0.0}).trigger);
}

static void test_security_gate() {
    std::printf("test_security_gate\n");
    SecurityParams p;
    {
        SecurityGate<256> g(p);
        SecurityDecision d = g.decide({0, 0.9, 0.5, 0.2, 0.3, 1});
        CHECK(!d.accept && d.reason == SR_CONSISTENCY_FAILURE);
    }
    {
        SecurityGate<256> g(p);
        SecurityFrame f{0, 0.6, 0.7, 0.6, 0.9, 77};
        CHECK(g.decide(f).accept);
        g.observe(f);
        SecurityFrame dup = f;
        dup.t_ms = 1000;
        CHECK(g.decide(dup).reason == SR_DUPLICATE);
        SecurityFrame rep = f;
        rep.t_ms = 100000;
        CHECK(g.decide(rep).reason == SR_REPLAY);
        SecurityFrame old = f;
        old.t_ms = 700000;  // outside the replay window
        CHECK(g.decide(old).accept);
        SecurityFrame near{200000, 0.605, 0.695, 0.6, 0.9, 999};  // perturbed signature, near features
        CHECK(g.decide(near).reason == SR_REPLAY);
    }
    {
        SecurityGate<256> g(p);
        for (int i = 0; i < 11; ++i) g.note_candidate(1000 + i * 100);
        SecurityDecision d = g.decide({2200, 0.6, 0.7, 0.6, 0.9, 5});
        CHECK(!d.accept && d.reason == SR_BURST);
    }
    {
        SecurityParams q = p;
        q.rate_limit = 3;
        SecurityGate<256> g(q);
        for (int i = 0; i < 3; ++i) CHECK(g.decide({i * 10000.0, 0.6, 0.7, 0.6, 0.9, 100u + i}).accept);
        CHECK(g.decide({35000, 0.6, 0.7, 0.6, 0.9, 200}).reason == SR_RATE_LIMIT);
        CHECK(g.decide({70000, 0.6, 0.7, 0.6, 0.9, 201}).accept);  // window slid past
    }
    {
        SecurityParams off = p;
        off.consistency_on = off.duplicate_on = off.replay_on = off.burst_on = off.rate_limit_on = false;
        SecurityGate<256> g(off);
        CHECK(g.decide({0, 0.9, 0.5, 0.2, 0.1, 1}).accept);
    }
}

static void test_workload() {
    std::printf("test_workload\n");
    const char* scenarios[] = {"quiet", "normal", "busy", "burst", "noisy", "trigger_spam", "replay", "mixed"};
    for (const char* sc : scenarios) {
        SimConfig c = cfg_for("secure", sc, 5, 1800);
        Workload a = generate_workload(c), b = generate_workload(c);
        CHECK(serialize(a) == serialize(b));
        SimConfig c2 = c;
        c2.seed = 6;
        CHECK(serialize(a) != serialize(generate_workload(c2)) || a.events.empty());
        double prev = -1;
        bool sorted = true, inside = true, ids = true, labels = true;
        for (size_t i = 0; i < a.events.size(); ++i) {
            const auto& e = a.events[i];
            sorted &= e.obs.timestamp_ms >= prev;
            prev = e.obs.timestamp_ms;
            inside &= e.obs.timestamp_ms >= 0 && e.obs.timestamp_ms + e.obs.duration_ms <= 1800000.0 + 1e-6;
            ids &= e.obs.event_id == i + 1;
            labels &= (e.gt.attack_type == "none") == e.gt.is_legitimate;
            labels &= (e.gt.ground_truth_action == "block") == !e.gt.is_legitimate;
            if (e.gt.attack_type == "replay") labels &= e.gt.replay_id > 0 && e.gt.replay_id < (int64_t)e.obs.event_id;
        }
        CHECK(sorted);
        CHECK(inside);
        CHECK(ids);
        CHECK(labels);
        size_t attacks = 0;
        for (const auto& e : a.events) attacks += e.gt.is_legitimate ? 0 : 1;
        const std::string s(sc);
        if (s == "trigger_spam" || s == "replay" || s == "mixed") CHECK(attacks > 0);
        else CHECK(attacks == 0);
    }
    // Mode does not influence the workload.
    SimConfig ca = cfg_for("always_on", "mixed", 3, 900), cs = cfg_for("secure", "mixed", 3, 900);
    CHECK(serialize(generate_workload(ca)) == serialize(generate_workload(cs)));
    // Attack intensity 0 removes attacks; the legitimate background is unchanged.
    SimConfig z = cfg_for("secure", "trigger_spam", 3, 1800);
    z.attack_intensity = 0.0;
    Workload wz = generate_workload(z);
    bool none = true;
    for (const auto& e : wz.events) none &= e.gt.is_legitimate;
    CHECK(none);
    SimConfig n = cfg_for("secure", "normal", 3, 1800);
    Workload wn = generate_workload(n);
    CHECK(wz.events.size() == wn.events.size());
}

static void test_simulator() {
    std::printf("test_simulator\n");
    PowerModel pm = load_power_model("config/power_model.json");
    const char* modes[] = {"always_on", "motion_only", "fixed_threshold", "event", "event_no_early_exit", "secure"};
    for (const char* m : modes) {
        SimConfig c = cfg_for(m, "mixed", 2, 1200);
        Workload wl = generate_workload(c);
        Simulator s1(c, wl, pm), s2(c, wl, pm);
        s1.run();
        s2.run();
        CHECK(std::fabs(s1.energy_mj() - s2.energy_mj()) == 0.0);
        bool same = true;
        for (size_t i = 0; i < wl.events.size(); ++i) {
            const ObsRecord &a = s1.records()[i], &b = s2.records()[i];
            same &= a.triggered == b.triggered && a.detected == b.detected && a.result_m7_ms == b.result_m7_ms &&
                    a.sec_reason == b.sec_reason;
        }
        CHECK(same);
        double t4 = 0, t7 = 0, e = 0;
        for (int st = 0; st < NUM_POWER_STATES; ++st) {
            const double t = s1.state_time_ms(is_m4_state(st) ? 4 : 7, st);
            (is_m4_state(st) ? t4 : t7) += t;
            e += pm.power_mw[st] * t / 1000.0;
        }
        CHECK(std::fabs(t4 - 1200000.0) < 1e-6);
        CHECK(std::fabs(t7 - 1200000.0) < 1e-6);
        CHECK(std::fabs(e - s1.energy_mj()) < 1e-6);
        bool blocked_ok = true, lat_ok = true;
        for (const auto& r : s1.records()) {
            if (r.sec_evaluated && !r.sec_accept) blocked_ok &= !r.started && !r.caused_wake && r.rpc_send_ms < 0;
            if (r.result_delivered_ms >= 0 && r.decision_ms >= 0) lat_ok &= r.result_delivered_ms >= r.decision_ms;
            if (r.dequeue_ms >= 0) lat_ok &= r.queue_delay_ms >= 0 && r.wake_wait_ms >= 0;
        }
        CHECK(blocked_ok);
        CHECK(lat_ok);
        if (std::string(m) == "always_on") CHECK(std::fabs(s1.summary().m7_active_ms - 1200000.0) < 1e-6);
        if (std::string(m) != "secure") CHECK(s1.summary().security_block == 0);
    }
    // Empty workload.
    SimConfig c = cfg_for("secure", "normal", 1, 60);
    Workload empty;
    empty.scenario = "normal";
    Simulator se(c, empty, pm);
    se.run();
    CHECK(se.summary().wakes == 0);
    CHECK(std::fabs(se.energy_mj() - (pm.power_mw[M4_MONITOR] + pm.power_mw[M7_SLEEP]) * 60.0) < 1e-6);
}

int main() {
    test_rng();
    test_energy_tracker();
    test_watcher();
    test_security_gate();
    test_workload();
    test_simulator();
    std::printf("unit_tests: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
