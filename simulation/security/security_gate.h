// M4-side security gate placed between the watcher trigger and the RPC wake
// request. A rejected trigger never reaches the M7.
//
// Header-only, fixed-size ring buffers, no heap: suitable for the Cortex-M4.
// The gate sees only observable data (timestamps, features, the perceptual
// content signature). It never receives ground-truth labels, so attack
// detection performance is a property of the algorithm, not of the labels.
//
// Checks, in order (first failing check gives the block reason):
//   1. CONSISTENCY_FAILURE  c = min(consistency, 1 - |motion - temporal|) < c_min
//   2. DUPLICATE            same content signature seen within the duplicate window
//   3. REPLAY               same signature, or near-identical feature vector
//                           (L_inf < eps), seen within the replay window but
//                           outside the duplicate window
//   4. BURST                more than N_burst trigger candidates in the burst window
//   5. RATE_LIMIT           at least N_rate accepted triggers in the rate window
#pragma once

#include <cmath>
#include <cstdint>

namespace sim {

enum SecurityReason {
    SR_NONE = 0,
    SR_RATE_LIMIT = 1,
    SR_REPLAY = 2,
    SR_DUPLICATE = 3,
    SR_BURST = 4,
    SR_CONSISTENCY_FAILURE = 5,
};

inline const char* security_reason_name(int r) {
    switch (r) {
        case SR_RATE_LIMIT: return "RATE_LIMIT";
        case SR_REPLAY: return "REPLAY";
        case SR_DUPLICATE: return "DUPLICATE";
        case SR_BURST: return "BURST";
        case SR_CONSISTENCY_FAILURE: return "CONSISTENCY_FAILURE";
        default: return "NONE";
    }
}

struct SecurityParams {
    bool rate_limit_on = true;
    int rate_limit = 20;
    double rate_window_ms = 60000.0;
    bool replay_on = true;
    double replay_window_ms = 600000.0;
    double replay_feature_eps = 0.01;
    bool duplicate_on = true;
    double duplicate_window_ms = 2000.0;
    bool burst_on = true;
    int burst_threshold = 10;
    double burst_window_ms = 5000.0;
    bool consistency_on = true;
    double consistency_threshold = 0.5;
    int history_capacity = 512;
};

struct SecurityFrame {
    double t_ms;
    double motion, visual, temporal, consistency;
    uint64_t signature;
};

struct SecurityDecision {
    bool accept = true;
    int reason = SR_NONE;
    double consistency_metric = 0.0;
    int burst_count = 0;
    int rate_count = 0;
    double matched_age_ms = -1.0;  // age of the matching history entry, if any
};

template <int MAX_HISTORY = 2048>
class SecurityGate {
public:
    explicit SecurityGate(const SecurityParams& p) : p_(p) {
        cap_ = p_.history_capacity < 1 ? 1 : (p_.history_capacity > MAX_HISTORY ? MAX_HISTORY : p_.history_capacity);
    }

    // Record every frame the M4 observes (called after decide() for the
    // current frame, so a frame never matches itself).
    void observe(const SecurityFrame& f) {
        hist_[hist_head_] = f;
        hist_head_ = (hist_head_ + 1) % cap_;
        if (hist_size_ < cap_) ++hist_size_;
    }

    // Record a watcher-positive candidate (including cooldown-suppressed ones)
    // for burst anomaly detection.
    void note_candidate(double t_ms) { push_time(cand_, cand_head_, cand_size_, t_ms); }

    SecurityDecision decide(const SecurityFrame& f) {
        SecurityDecision d;
        d.consistency_metric = f.consistency;
        const double coherence = 1.0 - std::fabs(f.motion - f.temporal);
        if (coherence < d.consistency_metric) d.consistency_metric = coherence;
        d.burst_count = count_since(cand_, cand_head_, cand_size_, f.t_ms - p_.burst_window_ms);
        d.rate_count = count_since(acc_, acc_head_, acc_size_, f.t_ms - p_.rate_window_ms);

        if (p_.consistency_on && d.consistency_metric < p_.consistency_threshold) {
            return block(d, SR_CONSISTENCY_FAILURE);
        }
        if (p_.duplicate_on || p_.replay_on) {
            for (int i = 0; i < hist_size_; ++i) {
                const SecurityFrame& h = hist_[(hist_head_ - 1 - i + 2 * cap_) % cap_];
                const double age = f.t_ms - h.t_ms;
                if (age < 0.0) continue;
                const bool same_sig = h.signature == f.signature;
                if (same_sig && p_.duplicate_on && age <= p_.duplicate_window_ms) {
                    d.matched_age_ms = age;
                    return block(d, SR_DUPLICATE);
                }
                if (p_.replay_on && age > p_.duplicate_window_ms && age <= p_.replay_window_ms) {
                    const bool near = linf(h, f) < p_.replay_feature_eps;
                    if (same_sig || near) {
                        d.matched_age_ms = age;
                        return block(d, SR_REPLAY);
                    }
                }
            }
        }
        if (p_.burst_on && d.burst_count > p_.burst_threshold) {
            return block(d, SR_BURST);
        }
        if (p_.rate_limit_on && d.rate_count >= p_.rate_limit) {
            return block(d, SR_RATE_LIMIT);
        }
        push_time(acc_, acc_head_, acc_size_, f.t_ms);
        return d;
    }

private:
    SecurityParams p_;
    int cap_;
    SecurityFrame hist_[MAX_HISTORY];
    int hist_head_ = 0, hist_size_ = 0;
    double cand_[MAX_HISTORY];
    int cand_head_ = 0, cand_size_ = 0;
    double acc_[MAX_HISTORY];
    int acc_head_ = 0, acc_size_ = 0;

    static SecurityDecision block(SecurityDecision d, int reason) {
        d.accept = false;
        d.reason = reason;
        return d;
    }
    static double linf(const SecurityFrame& a, const SecurityFrame& b) {
        double m = std::fabs(a.motion - b.motion);
        const double v = std::fabs(a.visual - b.visual);
        const double t = std::fabs(a.temporal - b.temporal);
        const double c = std::fabs(a.consistency - b.consistency);
        if (v > m) m = v;
        if (t > m) m = t;
        if (c > m) m = c;
        return m;
    }
    void push_time(double* buf, int& head, int& size, double t) {
        buf[head] = t;
        head = (head + 1) % MAX_HISTORY;
        if (size < MAX_HISTORY) ++size;
    }
    static int count_since(const double* buf, int head, int size, double t_from) {
        int n = 0;
        for (int i = 0; i < size; ++i) {
            const double t = buf[(head - 1 - i + 2 * MAX_HISTORY) % MAX_HISTORY];
            if (t <= t_from) break;  // entries are in time order
            ++n;
        }
        return n;
    }
};

}  // namespace sim
