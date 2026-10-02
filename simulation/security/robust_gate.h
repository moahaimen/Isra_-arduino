// R2 diversity-aware security gate (the R1 gate is kept unchanged in
// security_gate.h as "legacy").
//
// Header-only, fixed-size tables, no heap: suitable for the Cortex-M4. It
// sees only observable data of each frame: time, the gain-compensated
// consistency feature, the 12x4 motion-cell mask, the 48x16 foreground mask
// and the 256-bit difference hash, plus the watcher's novelty flag and
// z-score. It never receives labels.
//
// Checks, in order (first failing check gives the block reason):
//   1. CONSISTENCY_FAILURE  r2_consistency < c_min (global flicker that the
//                           gain compensation did not explain)
//   2. REPLAY               the frame re-presents recorded content: for some
//                           history frame h with age in [min_age, window],
//                             Jaccard(FG_t, FG_h) >= j_thr  and
//                             Hamming(dHash_t, dHash_h) <= h_max,
//                           with |FG_t| >= fg_min (a frame without foreground
//                           carries no replayable object). The history holds
//                           every frame the M4 observed (not only triggers).
//   3. CONTENT_RATE         per-content token bucket empty: requests whose
//                           motion-cell mask overlaps a known content slot
//                           share that slot's bucket (capacity b_c, refill r_c/s);
//                           novel content gets a fresh slot.
//   4. RATE_LIMIT           global token bucket (capacity B_g, refill R_g/s)
//                           empty, unless the request is NOVEL content with
//                           z >= z_emergency and the emergency budget (capacity
//                           E, refill R_e/s) has a token.
// Tokens are only consumed by accepted requests, so blocked requests never
// drain the budget of later legitimate ones.
#pragma once

#include <cstdint>

#include "watcher/robust_watcher.h"

namespace sim {

enum RobustReason {
    RR_NONE = 0,
    RR_RATE_LIMIT = 1,
    RR_REPLAY = 2,
    RR_CONTENT_RATE = 3,
    RR_CONSISTENCY_FAILURE = 5,
};

inline const char* robust_reason_name(int r) {
    switch (r) {
        case RR_RATE_LIMIT: return "RATE_LIMIT";
        case RR_REPLAY: return "REPLAY";
        case RR_CONTENT_RATE: return "CONTENT_RATE";
        case RR_CONSISTENCY_FAILURE: return "CONSISTENCY_FAILURE";
        default: return "NONE";
    }
}

struct RobustGateParams {
    bool consistency_on = true;
    double consistency_threshold = 0.3;
    bool replay_on = true;
    double replay_window_ms = 60000.0;
    double replay_min_age_ms = 2000.0;
    double fg_jaccard_thr = 0.80;
    int dhash_max = 32;
    int fg_min = 12;
    int history_capacity = 256;
    bool content_bucket_on = true;
    double content_capacity = 3.0;
    double content_refill_per_s = 0.5;  // < global refill: one content cannot hold the whole budget
    double content_overlap_thr = 0.3;
    double content_ttl_ms = 10000.0;
    bool global_bucket_on = true;
    double global_capacity = 10.0;
    double global_refill_per_s = 1.0;
    bool emergency_on = true;
    double emergency_capacity = 3.0;
    double emergency_refill_per_s = 0.1;
    double z_emergency = 6.0;
};

struct RobustFrame {
    double t_ms;
    double consistency;
    uint64_t cells;
    uint64_t fp[4];
    uint64_t fg[12];
    int fg_count;
};

struct RobustGateDecision {
    bool accept = true;
    int reason = RR_NONE;
    double matched_age_ms = -1.0;
    double best_jaccard = 0.0;
    int best_hamming = -1;
    bool used_emergency = false;
    double global_tokens = 0.0;
};

template <int MAX_HISTORY = 512>
class RobustGate {
public:
    static const int SLOTS = 8;

    explicit RobustGate(const RobustGateParams& p) : p_(p) {
        cap_ = p_.history_capacity < 1 ? 1 : (p_.history_capacity > MAX_HISTORY ? MAX_HISTORY : p_.history_capacity);
        g_tok_ = p_.global_capacity;
        e_tok_ = p_.emergency_capacity;
    }

    // Record every frame the M4 observes. Called after decide() for the
    // current frame, so a frame never matches itself.
    void observe(const RobustFrame& f) {
        if (f.fg_count < p_.fg_min) return;  // nothing replayable in this frame
        hist_[head_] = f;
        head_ = (head_ + 1) % cap_;
        if (size_ < cap_) ++size_;
    }

    RobustGateDecision decide(const RobustFrame& f, bool novel, double z) {
        RobustGateDecision d;
        refill(f.t_ms);
        d.global_tokens = g_tok_;
        if (p_.consistency_on && f.consistency < p_.consistency_threshold) return block(d, RR_CONSISTENCY_FAILURE);
        if (p_.replay_on && f.fg_count >= p_.fg_min) {
            for (int i = 0; i < size_; ++i) {
                const RobustFrame& h = hist_[(head_ - 1 - i + 2 * cap_) % cap_];
                const double age = f.t_ms - h.t_ms;
                if (age < p_.replay_min_age_ms || age > p_.replay_window_ms) continue;
                const double j = jaccard(f, h);
                if (j > d.best_jaccard) d.best_jaccard = j;
                if (j < p_.fg_jaccard_thr) continue;
                const int hd = hamming(f, h);
                if (d.best_hamming < 0 || hd < d.best_hamming) d.best_hamming = hd;
                if (hd <= p_.dhash_max) {
                    d.matched_age_ms = age;
                    return block(d, RR_REPLAY);
                }
            }
        }
        int slot = -1;
        if (p_.content_bucket_on) {
            slot = find_slot(f);
            if (slot >= 0 && slots_[slot].tokens < 1.0) {
                slots_[slot].last_seen_ms = f.t_ms;
                return block(d, RR_CONTENT_RATE);
            }
        }
        if (p_.global_bucket_on && g_tok_ < 1.0) {
            if (p_.emergency_on && novel && z >= p_.z_emergency && e_tok_ >= 1.0) {
                e_tok_ -= 1.0;
                d.used_emergency = true;
            } else {
                return block(d, RR_RATE_LIMIT);
            }
        } else if (p_.global_bucket_on) {
            g_tok_ -= 1.0;
        }
        if (p_.content_bucket_on) {
            if (slot < 0) slot = new_slot(f);
            slots_[slot].tokens -= 1.0;
            slots_[slot].cells = f.cells ? f.cells : slots_[slot].cells;
            slots_[slot].last_seen_ms = f.t_ms;
        }
        return d;
    }

private:
    struct Slot {
        bool used = false;
        uint64_t cells = 0;
        double tokens = 0.0;
        double last_seen_ms = 0.0;
    };
    RobustGateParams p_;
    int cap_;
    RobustFrame hist_[MAX_HISTORY];
    int head_ = 0, size_ = 0;
    Slot slots_[SLOTS];
    double g_tok_ = 0.0, e_tok_ = 0.0;
    double last_refill_ms_ = 0.0;
    bool refilled_ = false;

    static RobustGateDecision block(RobustGateDecision d, int reason) {
        d.accept = false;
        d.reason = reason;
        return d;
    }
    static double jaccard(const RobustFrame& a, const RobustFrame& b) {
        int in = 0, un = 0;
        for (int k = 0; k < 12; ++k) {
            in += popcount64(a.fg[k] & b.fg[k]);
            un += popcount64(a.fg[k] | b.fg[k]);
        }
        return un ? static_cast<double>(in) / un : 0.0;
    }
    static int hamming(const RobustFrame& a, const RobustFrame& b) {
        int n = 0;
        for (int k = 0; k < 4; ++k) n += popcount64(a.fp[k] ^ b.fp[k]);
        return n;
    }
    void refill(double t) {
        if (!refilled_) {
            refilled_ = true;
            last_refill_ms_ = t;
            return;
        }
        const double dt = (t - last_refill_ms_) / 1000.0;
        if (dt <= 0.0) return;
        last_refill_ms_ = t;
        g_tok_ = min(p_.global_capacity, g_tok_ + dt * p_.global_refill_per_s);
        e_tok_ = min(p_.emergency_capacity, e_tok_ + dt * p_.emergency_refill_per_s);
        for (Slot& s : slots_)
            if (s.used) s.tokens = min(p_.content_capacity, s.tokens + dt * p_.content_refill_per_s);
    }
    int find_slot(const RobustFrame& f) const {
        const int n = popcount64(f.cells);
        int best = -1;
        double best_ov = -1.0;
        for (int i = 0; i < SLOTS; ++i) {
            const Slot& s = slots_[i];
            if (!s.used || f.t_ms - s.last_seen_ms > p_.content_ttl_ms) continue;
            double ov;
            if (n == 0 || s.cells == 0) {
                ov = (n == 0 && s.cells == 0) ? 1.0 : 0.0;
            } else {
                ov = static_cast<double>(popcount64(f.cells & dilate_cells(s.cells))) / n;
            }
            if (ov >= p_.content_overlap_thr && ov > best_ov) {
                best_ov = ov;
                best = i;
            }
        }
        return best;
    }
    int new_slot(const RobustFrame& f) {
        int slot = 0;
        double oldest = 1e300;
        for (int i = 0; i < SLOTS; ++i) {
            const Slot& s = slots_[i];
            const double key = (!s.used || f.t_ms - s.last_seen_ms > p_.content_ttl_ms) ? -1e300 : s.last_seen_ms;
            if (key < oldest) {
                oldest = key;
                slot = i;
            }
        }
        slots_[slot] = Slot{true, f.cells, p_.content_capacity, f.t_ms};
        return slot;
    }
    static double min(double a, double b) { return a < b ? a : b; }
};

}  // namespace sim
