// R3 security gate for the utility-gated scheduler (S-UGS).
//
// Header-only, fixed-size state, no heap (Cortex-M4). Observable inputs only:
// the 24x8 block thumbnail T_t of the M4 low-res frame (4x4 block means of the
// 96x32 image), the foreground bit count, the scheduler's novelty flag. No
// labels, no attack labels.
//
// Replay = a STALE observation re-presented, not "an image that resembles an
// old image". With gain normalisation g(T) = T * 128 / median(T) and the
// changed-block count
//   n(A, B) = #{blocks k : |g(A)_k - g(B)_k| > d_abs + d_rel * g(B)_k},
// every frame (requests or not) is classified with a small session state:
//   start   (no session) fg_count_t >= fg_min, n_old <= k_match, n_prev >= k_jump,
//           n_old + margin <= n_prev   -> REPLAY, remember the last live frame R
//   continue (in session) n(T_t, R) > k_match and n_old <= k_match -> REPLAY
//   end      (in session) the frame matches R again (live scene resumed) or is
//           not stale any more (live content)
// with n_old = min over stored LIVE frames h aged [min_age, window] of
// n(T_t, T_h), n_prev = n(T_t, T_{t-1}). A persistent static scene has
// n_prev ~ 0 and never starts a session; a moving live object differs from
// every old frame (n_old > 0). History: live frames with fg >= fg_min.
//
// Wake budget: global token bucket (capacity B, refill r per s); when empty,
// only NOVEL content may use a reserved novelty budget (capacity E, refill
// r_e). Tokens are consumed only by accepted requests.
#pragma once

#include <cstdint>
#include <cstdlib>

namespace sim {

enum UgsGateReason { UG_NONE = 0, UG_RATE_LIMIT = 1, UG_REPLAY = 2 };

inline const char* ugs_gate_reason_name(int r) {
    return r == UG_RATE_LIMIT ? "RATE_LIMIT" : (r == UG_REPLAY ? "REPLAY" : "NONE");
}

struct UgsGateParams {
    bool replay_on = true;
    double min_age_ms = 2000.0;
    double window_ms = 60000.0;
    int fg_min = 12;
    double d_abs = 6.0;
    double d_rel = 0.08;
    int k_match = 2;
    int k_jump = 2;
    int margin = 2;
    int history = 256;
    bool budget_on = true;
    double capacity = 10.0;
    double refill_per_s = 1.0;
    double novelty_capacity = 3.0;
    double novelty_refill_per_s = 0.2;
};

struct UgsGateFrame {
    double t_ms;
    uint8_t thumb[192];
    int fg_count;
    int med = -1;  // cached thumbnail median (computed by the gate)
};

struct UgsGateDecision {
    bool accept = true;
    int reason = UG_NONE;
    int n_old = -1, n_prev = -1;
    double matched_age_ms = -1.0;
    bool used_novelty_budget = false;
};

template <int MAX_HISTORY = 256>
class UgsGate {
public:
    explicit UgsGate(const UgsGateParams& p) : p_(p) {
        cap_ = p_.history < 1 ? 1 : (p_.history > MAX_HISTORY ? MAX_HISTORY : p_.history);
        tok_ = p_.capacity;
        ntok_ = p_.novelty_capacity;
    }

    // Every observed frame, after decide() if the frame was a request.
    void observe(UgsGateFrame f) {
        classify(f);
        commit_frame(f);
    }

    UgsGateDecision decide(UgsGateFrame f, bool novel) {
        UgsGateDecision d;
        refill(f.t_ms);
        const Cls& c = classify(f);
        d.n_old = c.n_old;
        d.n_prev = c.n_prev;
        if (c.replay) {
            d.accept = false;
            d.reason = UG_REPLAY;
            d.matched_age_ms = c.age;
            return d;
        }
        if (p_.budget_on) {
            if (tok_ >= 1.0) {
                tok_ -= 1.0;
            } else if (novel && ntok_ >= 1.0) {
                ntok_ -= 1.0;
                d.used_novelty_budget = true;
            } else {
                d.accept = false;
                d.reason = UG_RATE_LIMIT;
            }
        }
        return d;
    }

    // Changed-block count after gain normalisation to a median of 128.
    int changed(const UgsGateFrame& a, const UgsGateFrame& b) const {
        const double ga = 128.0 / (a.med + 1e-6), gb = 128.0 / (b.med + 1e-6);
        int n = 0;
        for (int k = 0; k < 192; ++k) {
            const double x = a.thumb[k] * ga, y = b.thumb[k] * gb;
            const double diff = x > y ? x - y : y - x;
            if (diff > p_.d_abs + p_.d_rel * y) ++n;
        }
        return n;
    }

    bool in_session() const { return in_session_; }

private:
    struct Cls {
        double t = -1e300;
        bool replay = false;
        int n_old = -1, n_prev = -1;
        double age = -1.0;
    };
    UgsGateParams p_;
    int cap_;
    UgsGateFrame hist_[MAX_HISTORY];
    int head_ = 0, size_ = 0;
    UgsGateFrame prev_{};
    bool has_prev_ = false;
    UgsGateFrame pre_ref_{};  // last live frame before the current replay session
    bool in_session_ = false;
    Cls cls_;
    double tok_ = 0.0, ntok_ = 0.0, last_ = 0.0;
    bool init_ = false;

    // Replay classification with session state. Computed once per frame
    // (cached by timestamp), whether or not the frame is a request.
    const Cls& classify(UgsGateFrame& f) {
        if (f.med < 0) f.med = static_cast<int>(median192(f.thumb));
        if (cls_.t == f.t_ms) return cls_;
        Cls c;
        c.t = f.t_ms;
        if (p_.replay_on && has_prev_ && f.fg_count >= p_.fg_min) {
            c.n_prev = changed(f, prev_);
            int best = 1 << 30;
            double age_best = -1.0;
            for (int i = 0; i < size_; ++i) {
                const UgsGateFrame& h = hist_[(head_ - 1 - i + 2 * cap_) % cap_];
                const double age = f.t_ms - h.t_ms;
                if (age < p_.min_age_ms || age > p_.window_ms) continue;
                const int n = changed(f, h);
                if (n < best) {
                    best = n;
                    age_best = age;
                }
            }
            c.n_old = best == (1 << 30) ? -1 : best;
            c.age = age_best;
            const bool stale = c.n_old >= 0 && c.n_old <= p_.k_match;
            if (!in_session_) {
                if (stale && c.n_prev >= p_.k_jump && c.n_old + p_.margin <= c.n_prev) {
                    in_session_ = true;
                    pre_ref_ = prev_;
                    c.replay = true;
                }
            } else if (changed(f, pre_ref_) <= p_.k_match || !stale) {
                in_session_ = false;  // live scene resumed or live content
            } else {
                c.replay = true;      // session continues: still stale, still away from the live scene
            }
        } else if (in_session_ && has_prev_ && f.fg_count < p_.fg_min) {
            if (changed(f, pre_ref_) <= p_.k_match) in_session_ = false;
        }
        cls_ = c;
        return cls_;
    }

    void commit_frame(const UgsGateFrame& f) {
        if (cls_.t == f.t_ms && cls_.replay) return;  // replayed frames are not live history
        prev_ = f;
        has_prev_ = true;
        if (f.fg_count < p_.fg_min) return;
        hist_[head_] = f;
        head_ = (head_ + 1) % cap_;
        if (size_ < cap_) ++size_;
    }

    static double median192(const uint8_t* a) {
        int hist[256] = {};
        for (int k = 0; k < 192; ++k) ++hist[a[k]];
        int c = 0;
        for (int v = 0; v < 256; ++v) {
            c += hist[v];
            if (c >= 96) return v;
        }
        return 255;
    }
    void refill(double t) {
        if (!init_) {
            init_ = true;
            last_ = t;
            return;
        }
        const double dt = (t - last_) / 1000.0;
        if (dt <= 0) return;
        last_ = t;
        tok_ += dt * p_.refill_per_s;
        if (tok_ > p_.capacity) tok_ = p_.capacity;
        ntok_ += dt * p_.novelty_refill_per_s;
        if (ntok_ > p_.novelty_capacity) ntok_ = p_.novelty_capacity;
    }
};

}  // namespace sim
