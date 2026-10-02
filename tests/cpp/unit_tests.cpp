// C++ unit tests for the simulator components (no external framework).
// Build: cmake --build build --target unit_tests && ./build/unit_tests
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "config/sim_config.h"
#include "core/rng.h"
#include "core/simulator.h"
#include "energy/energy_model.h"
#include "security/robust_gate.h"
#include "security/security_gate.h"
#include "security/ugs_gate.h"
#include "watcher/robust_watcher.h"
#include "watcher/ugs_scheduler.h"
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

// ------------------------------------------------------------------ R2

static uint64_t cells_at(int cx, int cy, int w = 1, int h = 1) {
    uint64_t m = 0;
    for (int y = cy; y < cy + h; ++y)
        for (int x = cx; x < cx + w; ++x) m |= 1ULL << (y * 12 + x);
    return m;
}

static void test_robust_watcher() {
    std::printf("test_robust_watcher\n");
    RobustWatcherParams p;
    p.persist_k = 2;
    p.content_cooldown_ms = 1000.0;
    // Background: quiet frames, then a persistent object.
    {
        RobustWatcher w(p);
        double t = 0.0;
        for (int i = 0; i < 40; ++i, t += 100.0) {
            RobustDecision d = w.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0});
            CHECK(!d.trigger);
        }
        // a single-frame flash is not persistent -> no trigger
        RobustDecision d1 = w.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(3, 1)});
        t += 100.0;
        CHECK(!d1.trigger && d1.suppress == RS_PERSISTENCE);
        RobustDecision d2 = w.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0});
        t += 100.0;
        CHECK(!d2.trigger);
        // persistent object: triggers on its 2nd frame, then content cooldown
        int trig = 0;
        for (int i = 0; i < 10; ++i, t += 100.0) trig += w.evaluate(t, {0.8, 0.7, 0.8, 1.0, cells_at(5, 2)}).trigger;
        CHECK(trig == 1);
        // after the cooldown the same object re-triggers (periodic re-detection)
        for (int i = 0; i < 10; ++i, t += 100.0) trig += w.evaluate(t, {0.8, 0.7, 0.8, 1.0, cells_at(5, 2)}).trigger;
        CHECK(trig == 2);
    }
    // Legitimate multi-object burst: distinct objects close in time all trigger
    // with the per-content cooldown, but only one with a global cooldown.
    for (int mode = 0; mode < 2; ++mode) {
        RobustWatcherParams q = p;
        q.content_cooldown = (mode == 0);
        RobustWatcher w(q);
        double t = 0.0;
        for (int i = 0; i < 20; ++i, t += 100.0) w.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0});
        int trig = 0;
        uint64_t objs = 0;
        for (int k = 0; k < 4; ++k) {
            objs |= cells_at(2 * k + 1, k % 4);  // object k appears at frame k
            for (int rep = 0; rep < 2; ++rep, t += 100.0) trig += w.evaluate(t, {0.8, 0.7, 0.8, 1.0, objs}).trigger;
        }
        // with one cell per object the union mask overlaps each new object
        // only partly; separate objects in separate frames:
        RobustWatcher w2(q);
        double t2 = 0.0;
        for (int i = 0; i < 20; ++i, t2 += 100.0) w2.evaluate(t2, {0.02, 0.02, 0.02, 1.0, 0});
        int trig2 = 0;
        for (int i = 0; i < 2; ++i, t2 += 100.0) trig2 += w2.evaluate(t2, {0.8, 0.7, 0.8, 1.0, cells_at(0, 0)}).trigger;
        for (int k = 1; k < 4; ++k, t2 += 100.0)
            trig2 += w2.evaluate(t2, {0.8, 0.7, 0.8, 1.0, cells_at(3 * k, k % 4)}).trigger;
        if (mode == 0) CHECK(trig2 == 4);
        else CHECK(trig2 == 1);
        (void)trig;
    }
    // Noise robustness: a noisy but object-free background raises the robust
    // threshold within [theta_min, theta_max] and does not trigger.
    {
        RobustWatcher w(p);
        Rng r(5);
        double t = 0.0, max_thr = 0.0;
        int trig = 0;
        for (int i = 0; i < 300; ++i, t += 100.0) {
            const double n = 0.15 + 0.05 * r.normal(0.0, 1.0);
            RobustDecision d = w.evaluate(t, {n, n, n, 1.0, 0});
            trig += d.trigger;
            if (d.threshold > max_thr) max_thr = d.threshold;
        }
        CHECK(trig <= 3);
        CHECK(max_thr <= p.theta_max + 1e-12);
    }
}

static RobustFrame rframe(double t, uint64_t cells, int fg_seed, int fg_bits, uint64_t fp0 = 0x1234) {
    RobustFrame f{};
    f.t_ms = t;
    f.consistency = 1.0;
    f.cells = cells;
    f.fp[0] = fp0;
    f.fp[1] = 0xabcdefULL;
    f.fp[2] = 0;
    f.fp[3] = 0;
    for (int k = 0; k < 12; ++k) f.fg[k] = 0;
    f.fg_count = 0;
    for (int b = 0; b < fg_bits; ++b) {
        const int bit = (fg_seed * 37 + b * 7) % 768;
        if (!(f.fg[bit / 64] >> (bit % 64) & 1ULL)) ++f.fg_count;
        f.fg[bit / 64] |= 1ULL << (bit % 64);
    }
    return f;
}

static void test_robust_gate() {
    std::printf("test_robust_gate\n");
    RobustGateParams p;
    p.replay_min_age_ms = 2000.0;
    p.fg_jaccard_thr = 0.8;
    p.dhash_max = 8;
    // exact replay of a recorded frame is blocked; the live frame is accepted
    {
        RobustGate<512> g(p);
        RobustFrame orig = rframe(1000.0, cells_at(2, 1), 1, 40);
        RobustGateDecision d0 = g.decide(orig, true, 8.0);
        CHECK(d0.accept);
        g.observe(orig);
        RobustFrame rep = orig;
        rep.t_ms = 6000.0;
        RobustGateDecision d1 = g.decide(rep, true, 8.0);
        CHECK(!d1.accept && d1.reason == RR_REPLAY);
        CHECK(std::fabs(d1.matched_age_ms - 5000.0) < 1e-9);
        // too recent to be a replay (continuous live scene)
        RobustGate<512> g2(p);
        g2.observe(orig);
        RobustFrame live = orig;
        live.t_ms = 1500.0;
        CHECK(g2.decide(live, false, 8.0).accept);
    }
    // perturbed replay: a few foreground bits and dHash bits differ -> still blocked;
    // a different foreground (new object) -> accepted
    {
        RobustGate<512> g(p);
        RobustFrame orig = rframe(1000.0, cells_at(2, 1), 1, 60);
        g.observe(orig);
        RobustFrame pert = orig;
        pert.t_ms = 7000.0;
        pert.fg[0] ^= 0x3ULL;  // two bits differ
        pert.fp[0] ^= 0x7ULL;  // three dHash bits differ
        RobustGateDecision d = g.decide(pert, true, 8.0);
        CHECK(!d.accept && d.reason == RR_REPLAY);
        RobustFrame other = rframe(7100.0, cells_at(8, 2), 9, 60);
        CHECK(g.decide(other, true, 8.0).accept);
    }
    // multi-object legitimate burst: distinct contents are all accepted
    {
        RobustGate<512> g(p);
        int acc = 0;
        for (int k = 0; k < 6; ++k) acc += g.decide(rframe(1000.0 + 50.0 * k, cells_at(2 * k, k % 4), 20 + k, 30), true, 8.0).accept;
        CHECK(acc == 6);
    }
    // high-spam degradation: repeated same-content spam is rate-limited per
    // content, while novel legitimate content is still accepted
    {
        RobustGateParams q = p;
        q.replay_on = false;
        RobustGate<512> g(q);
        int spam_acc = 0, legit_acc = 0, legit_n = 0;
        double t = 0.0;
        for (int i = 0; i < 200; ++i, t += 100.0) {
            spam_acc += g.decide(rframe(t, cells_at(6, 3), 3, 30), false, 5.0).accept;
            if (i % 25 == 10) {  // novel objects in the top row, away from the spam region
                ++legit_n;
                legit_acc += g.decide(rframe(t + 1.0, cells_at(i / 25, 0), 50 + i, 30), true, 9.0).accept;
            }
        }
        CHECK(spam_acc <= 3 + 20 * q.content_refill_per_s + 1);  // capacity + refill over 20 s
        CHECK(legit_acc == legit_n);
    }
    // global budget exhausted by many distinct contents: the emergency budget
    // still admits novel high-z content, low-z content is rate-limited
    {
        RobustGateParams q = p;
        q.replay_on = false;
        q.global_capacity = 2.0;
        q.global_refill_per_s = 0.0;
        RobustGate<512> g(q);
        CHECK(g.decide(rframe(0.0, cells_at(0, 0), 1, 30), true, 9.0).accept);
        CHECK(g.decide(rframe(10.0, cells_at(4, 0), 2, 30), true, 9.0).accept);
        RobustGateDecision low = g.decide(rframe(20.0, cells_at(8, 0), 3, 30), true, 1.0);
        CHECK(!low.accept && low.reason == RR_RATE_LIMIT);
        RobustGateDecision hi = g.decide(rframe(30.0, cells_at(8, 3), 4, 30), true, 9.0);
        CHECK(hi.accept && hi.used_emergency);
    }
    // dilation stays inside the 12 x 4 grid
    CHECK(dilate_cells(cells_at(11, 0)) == (cells_at(10, 0, 2, 2)));
    CHECK(dilate_cells(cells_at(0, 3)) == (cells_at(0, 2, 2, 2)));
}

// ------------------------------------------------------------------ R3

static void test_ugs_scheduler() {
    std::printf("test_ugs_scheduler\n");
    UgsParams p;
    auto quiet = [](UgsScheduler& s, double& t, int n) {
        for (int i = 0; i < n; ++i, t += 100.0) s.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0, false, 0});
    };
    // a one-frame spike never activates; persistent evidence does
    {
        UgsScheduler s(p);
        double t = 0.0;
        quiet(s, t, 30);
        UgsDecision d = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(2, 1), false, 0});
        t += 100.0;
        CHECK(!d.trigger && !d.active);
        quiet(s, t, 20);
        int trig = 0, first = -1;
        for (int i = 0; i < 5; ++i, t += 100.0) {
            UgsDecision e = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(2, 1), false, 0});
            if (e.trigger && first < 0) first = i;
            if (e.trigger) s.commit(t, e.region_mask);
            trig += e.trigger;
        }
        CHECK(first == 1);  // second frame of strong evidence
        CHECK(trig == 1);   // then waits for the result (in flight)
    }
    // weak but persistent evidence activates after a few frames
    {
        UgsScheduler s(p);
        double t = 0.0;
        Rng r(3);
        for (int i = 0; i < 40; ++i, t += 100.0) {
            const double n = 0.12 + 0.01 * r.normal(0.0, 1.0);
            s.evaluate(t, {n, n, n, 1.0, 0, false, 0});
        }
        int first = -1;
        for (int i = 0; i < 20; ++i, t += 100.0) {
            UgsDecision e = s.evaluate(t, {0.25, 0.25, 0.25, 1.0, cells_at(4, 2), false, 0});
            if (e.trigger) {
                first = i;
                break;
            }
        }
        CHECK(first >= 1 && first <= 6);
    }
    // novelty during a busy period: a second object triggers immediately;
    // closed loop: confirmed region -> slow refresh, barren region -> back-off
    {
        UgsScheduler s(p);
        double t = 0.0;
        quiet(s, t, 30);
        UgsDecision a1 = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(1, 1), false, 0});
        t += 100.0;
        UgsDecision a2 = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(1, 1), false, 0});
        CHECK(!a1.trigger && a2.trigger && a2.novel);
        s.commit(t, a2.region_mask);
        t += 100.0;
        UgsDecision b0 = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(1, 1), false, 1});
        CHECK(!b0.trigger && b0.suppress == US_INFLIGHT);  // same object, result pending
        // a second object appears while A's request is in flight: separate
        // component -> novel -> eligible at once (no global cooldown)
        UgsDecision c = s.evaluate(t + 1.0, {0.9, 0.9, 0.9, 1.0, cells_at(1, 1) | cells_at(9, 2), false, 1});
        CHECK(c.trigger && c.novel && c.region_mask != a2.region_mask && (c.region_mask & a2.region_mask));
        s.commit(t + 1.0, c.region_mask);
        s.feedback(a2.region_mask, cells_at(1, 1), t + 200.0);  // M7 confirmed object A
        s.feedback(c.region_mask, 0, t + 250.0);                 // M7 found nothing for B
        int trigA = 0, trigB = 0;
        for (int i = 0; i < 100; ++i) {  // 10 s with both regions active
            t += 100.0;
            UgsDecision x = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(1, 1), false, 0});
            if (x.trigger) {
                ++trigA;
                s.commit(t, x.region_mask);
                s.feedback(x.region_mask, cells_at(1, 1), t + 1.0);
            }
            UgsDecision y = s.evaluate(t + 2.0, {0.9, 0.9, 0.9, 1.0, cells_at(9, 2), false, 0});
            if (y.trigger) {
                ++trigB;
                s.commit(t + 2.0, y.region_mask);
                s.feedback(y.region_mask, 0, t + 3.0);
            }
        }
        CHECK(trigA >= 8 && trigA <= 11);  // confirmed: refreshed every dt_track (1 s)
        CHECK(trigB >= 3 && trigB <= 6);   // barren: k_retry quick checks, then exponential back-off
    }
}


static void test_ugs_r31() {
    std::printf("test_ugs_r31\n");
    // default flags reproduce R3 exactly: decisions identical with/without explicit zeros
    {
        UgsParams a, b;
        b.noise_norm = 0; b.hold_ms = 0.0; b.value_rule = 0;
        UgsScheduler sa(a), sb(b);
        Rng r(5);
        for (int i = 0; i < 300; ++i) {
            const double x = 0.1 + 0.5 * (r.uniform() < 0.3 ? r.uniform() : 0.1);
            UgsInput in{x, x, x, 1.0, cells_at(i % 10, 1), false, 0};
            UgsDecision da = sa.evaluate(i * 100.0, in), db = sb.evaluate(i * 100.0, in);
            CHECK(da.trigger == db.trigger && da.accum == db.accum);
            if (da.trigger) { sa.commit(i * 100.0, da.region_mask); sb.commit(i * 100.0, db.region_mask); }
        }
    }
    // noise_norm: noisy idle background raises sigma (no cap), so the same excursion yields less evidence
    {
        UgsParams a, b;
        a.a_on = b.a_on = 1e9;  // keep the watcher idle so that the baseline learns the noisy scene
        b.noise_norm = 1;
        UgsScheduler sa(a), sb(b);
        Rng r(7);
        double ea = 0, eb = 0;
        for (int i = 0; i < 80; ++i) {
            const double n = 0.35 + 0.15 * r.normal(0.0, 1.0);
            const double v = n < 0 ? 0 : n;
            sa.evaluate(i * 100.0, {v, v, v, 1.0, 0, false, 0});
            sb.evaluate(i * 100.0, {v, v, v, 1.0, 0, false, 0});
        }
        for (int i = 80; i < 90; ++i) {
            ea += sa.evaluate(i * 100.0, {0.8, 0.8, 0.8, 1.0, cells_at(3, 1), false, 0}).evidence;
            eb += sb.evaluate(i * 100.0, {0.8, 0.8, 0.8, 1.0, cells_at(3, 1), false, 0}).evidence;
        }
        CHECK(eb < ea);
    }
    // hold: after a confirmation the scheduler stays engaged for hold_ms although the evidence vanished
    {
        UgsParams p;
        p.hold_ms = 3000.0;
        UgsScheduler s(p);
        double t = 0.0;
        for (int i = 0; i < 30; ++i, t += 100.0) s.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0, false, 0});
        UgsDecision d;
        for (int i = 0; i < 3; ++i, t += 100.0) {
            d = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(2, 1), false, 0});
            if (d.trigger) { s.commit(t, d.region_mask); break; }
        }
        CHECK(d.trigger);
        s.feedback(d.region_mask, cells_at(2, 1), t + 50.0);
        t += 50.0;
        // quiet frames: accumulator decays below a_off, but the hold keeps the region engaged
        UgsDecision q;
        for (int i = 0; i < 12; ++i, t += 100.0) q = s.evaluate(t, {0.02, 0.02, 0.02, 1.0, cells_at(2, 1), false, 0});
        CHECK(q.active);
        // beyond the hold the scheduler releases
        for (int i = 0; i < 40; ++i, t += 100.0) q = s.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0, false, 0});
        CHECK(!q.active);
    }
    // value rule: a region with a poor hit record is refreshed more slowly than one with a good record
    {
        UgsParams p;
        p.value_rule = 1;
        auto run = [&](bool hit) {
            UgsScheduler s(p);
            double t = 0.0;
            for (int i = 0; i < 30; ++i, t += 100.0) s.evaluate(t, {0.02, 0.02, 0.02, 1.0, 0, false, 0});
            int trig = 0;
            for (int i = 0; i < 400; ++i, t += 100.0) {
                UgsDecision d = s.evaluate(t, {0.9, 0.9, 0.9, 1.0, cells_at(2, 1), false, 0});
                if (d.trigger) {
                    ++trig;
                    s.commit(t, d.region_mask);
                    s.feedback(d.region_mask, hit ? cells_at(2, 1) : 0, t + 1.0);
                }
            }
            return trig;
        };
        CHECK(run(true) > run(false));
    }
}

static UgsGateFrame gframe(double t, int pattern, int fg, double gain = 1.0, int shift_obj = 0) {
    UgsGateFrame f{};
    f.t_ms = t;
    f.fg_count = fg;
    for (int k = 0; k < 192; ++k) f.thumb[k] = static_cast<uint8_t>(std::min(255.0, (60 + (k * 37) % 120) * gain));
    if (pattern > 0) {  // an object of 6 blocks at a pattern-dependent position
        const int x0 = (pattern + shift_obj) % 21;  // a distinct position per pattern
        for (int y = 3; y < 5; ++y)
            for (int x = x0; x < x0 + 3; ++x) f.thumb[y * 24 + x] = static_cast<uint8_t>(250 * std::min(gain, 1.0));
    }
    return f;
}

static void test_ugs_gate() {
    std::printf("test_ugs_gate\n");
    UgsGateParams p;
    p.budget_on = false;
    // a persistent static scene with an object is never a replay
    {
        UgsGate<256> g(p);
        int blocked = 0;
        for (int i = 0; i < 100; ++i) {
            UgsGateFrame f = gframe(i * 100.0, 3, 40);
            blocked += !g.decide(f, false).accept;
            g.observe(f);
        }
        CHECK(blocked == 0);
    }
    // a moving object (new position every frame) is accepted; a replay of an
    // old frame (stale position, discontinuous with the live past) is blocked,
    // also when its brightness changed
    {
        UgsGate<256> g(p);
        int blocked_live = 0;
        double t = 0.0;
        for (int i = 0; i < 60; ++i, t += 100.0) {
            UgsGateFrame f = gframe(t, 1 + i / 3, 40);
            blocked_live += !g.decide(f, true).accept;
            g.observe(f);
        }
        CHECK(blocked_live == 0);
        UgsGateFrame rep = gframe(t, 2, 40, 0.85);  // stale content, brightness x0.85
        UgsGateDecision d = g.decide(rep, true);
        CHECK(!d.accept && d.reason == UG_REPLAY);
        CHECK(d.matched_age_ms >= 2000.0);
    }
    // budget: when the global bucket is empty only novel content uses the reserve
    {
        UgsGateParams q = p;
        q.budget_on = true;
        q.replay_on = false;
        q.capacity = 2.0;
        q.refill_per_s = 0.0;
        q.novelty_capacity = 1.0;
        q.novelty_refill_per_s = 0.0;
        UgsGate<256> g(q);
        CHECK(g.decide(gframe(0, 1, 40), false).accept);
        CHECK(g.decide(gframe(1, 2, 40), false).accept);
        UgsGateDecision r1 = g.decide(gframe(2, 3, 40), false);
        CHECK(!r1.accept && r1.reason == UG_RATE_LIMIT);
        UgsGateDecision r2 = g.decide(gframe(3, 4, 40), true);
        CHECK(r2.accept && r2.used_novelty_budget);
        CHECK(!g.decide(gframe(4, 5, 40), true).accept);
    }
}


static UgsGateFrame shifted(const UgsGateFrame& f, int dx, int dy) {
    UgsGateFrame o = f;
    o.med = -1;
    for (int y = 0; y < 8; ++y)
        for (int x = 0; x < 24; ++x) {
            const int sx = std::min(23, std::max(0, x - dx)), sy = std::min(7, std::max(0, y - dy));
            o.thumb[y * 24 + x] = f.thumb[sy * 24 + sx];
        }
    return o;
}

static void test_ugs_gate_r31() {
    std::printf("test_ugs_gate_r31\n");
    UgsGateParams p;
    p.budget_on = false;
    auto run = [&](UgsGateParams q, int dx, int dy) {
        UgsGate<256> g(q);
        double t = 0.0;
        for (int i = 0; i < 60; ++i, t += 100.0) {
            UgsGateFrame f = gframe(t, 1 + i / 3, 40);
            g.decide(f, true);
            g.observe(f);
        }
        return g.decide(shifted(gframe(t, 2, 40), dx, dy), true);
    };
    UgsGateParams q = p;
    q.shift_tol = 1;
    q.shift_try = 192;
    CHECK(run(p, 0, 0).reason == UG_REPLAY);   // exact stale frame: blocked either way
    CHECK(run(q, 0, 0).reason == UG_REPLAY);
    CHECK(run(p, 1, 0).accept);                // one-block displaced replay slips through R3
    CHECK(!run(q, 1, 0).accept && run(q, 1, 1).reason == UG_REPLAY);  // tolerated with shift_tol
    // shift tolerance does not turn a live, different scene into a replay
    {
        UgsGate<256> g(q);
        double t = 0.0;
        int blocked = 0;
        for (int i = 0; i < 90; ++i, t += 100.0) {  // object advancing one block per 0.5 s
            UgsGateFrame f = gframe(t, 1 + i / 5, 40);
            blocked += !g.decide(f, true).accept;
            g.observe(f);
        }
        CHECK(blocked == 0);
    }
    // per-content bucket: one region cannot drain the global budget; another region still passes
    {
        UgsGateParams b = p;
        b.budget_on = true;
        b.replay_on = false;
        b.capacity = 10.0;
        b.refill_per_s = 0.0;
        b.novelty_capacity = 0.0;
        b.content_on = 1;
        b.content_capacity = 3.0;
        b.content_refill_per_s = 0.0;
        UgsGate<256> g(b);
        int acc0 = 0, acc1 = 0;
        for (int i = 0; i < 8; ++i) acc0 += g.decide(gframe(i, 1, 40), false, 0).accept;
        for (int i = 0; i < 3; ++i) acc1 += g.decide(gframe(10 + i, 2, 40), false, 1).accept;
        CHECK(acc0 == 3);  // spam on region 0 stops at the content capacity
        CHECK(acc1 == 3);  // region 1 unaffected (global budget has 4 tokens left)
        UgsGateParams off = b;
        off.content_on = 0;
        UgsGate<256> h(off);
        int a = 0;
        for (int i = 0; i < 12; ++i) a += h.decide(gframe(i, 1, 40), false, 0).accept;
        CHECK(a == 10);    // without the content bucket one region takes the whole global budget
    }
}

int main() {
    test_rng();
    test_energy_tracker();
    test_watcher();
    test_security_gate();
    test_workload();
    test_simulator();
    test_robust_watcher();
    test_robust_gate();
    test_ugs_scheduler();
    test_ugs_r31();
    test_ugs_gate_r31();
    test_ugs_gate();
    std::printf("unit_tests: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
