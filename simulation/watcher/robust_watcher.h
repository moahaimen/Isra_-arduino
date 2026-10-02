// R2 robust M4 watcher (replaces the legacy EWMA-adaptive rule, which is kept
// unchanged in watcher.h as "legacy_adaptive").
//
// Header-only, fixed-size arrays, no heap: suitable for the Cortex-M4. It
// reads only observable features of the current frame (never labels, never
// detector output).
//
// Per frame t:
//   S_t      = w_m m + w_v v + w_t tau + w_c c        (features of the selected front end)
//   med, MAD over the last N_bg background scores (scores recorded while the
//            watcher is idle and S_t < theta_on)
//   sigma    = max(1.4826 MAD, sigma_floor)
//   theta_on = clamp(med + z_on  sigma, theta_min, theta_max)    (bounded threshold)
//   theta_off= clamp(med + z_off sigma, 0,         theta_on)     (hysteresis)
//   z_t      = (S_t - med) / sigma
// State machine (hysteresis + persistence):
//   IDLE   -> ACTIVE when S >= theta_on for persist_k consecutive frames
//   ACTIVE -> IDLE   when S <  theta_off for release_k consecutive frames
// While ACTIVE, a trigger is issued per CONTENT, not globally:
//   the 12x4 motion-cell mask of the frame is matched (overlap >= overlap_thr,
//   1-cell dilation) against a small table of recently triggered regions.
//   * no match           -> novel content: trigger, new region
//   * match, last trigger of that region >= content_cooldown_ms ago -> trigger
//   * otherwise          -> suppressed (same content in cooldown)
//   Frames with an empty cell mask share one "unlocalised" region.
// Different objects appearing close together therefore each trigger at once,
// while repeated observations of the same object are rate-limited.
#pragma once

#include <cstdint>

namespace sim {

enum RobustSuppress { RS_NONE = 0, RS_BELOW_THRESHOLD = 1, RS_PERSISTENCE = 2, RS_CONTENT_COOLDOWN = 3 };

struct RobustWatcherParams {
    double w_motion = 0.30, w_visual = 0.35, w_temporal = 0.20, w_consistency = 0.15;
    int bg_window = 64;           // background score history (<= 128)
    int bg_min = 8;               // history needed before the robust threshold is used
    double z_on = 4.0;
    double z_off = 2.0;
    double theta_min = 0.20;
    double theta_max = 0.55;
    double sigma_floor = 0.02;
    int persist_k = 2;
    int release_k = 3;
    bool robust_threshold = true;    // false: theta_on = theta_max, theta_off = z-free hysteresis ratio
    double fixed_off_ratio = 0.7;
    bool content_cooldown = true;    // false: one global cooldown (legacy behaviour)
    double content_cooldown_ms = 1000.0;
    double overlap_thr = 0.3;
    double region_ttl_ms = 3000.0;
};

struct RobustFeatures {
    double motion, visual, temporal, consistency;
    uint64_t cells;
};

struct RobustDecision {
    double score = 0.0;
    double threshold = 0.0;   // theta_on in force for this frame
    double z = 0.0;
    bool raw_positive = false;  // ACTIVE after this frame's update
    bool trigger = false;
    bool novel = false;         // trigger opened a new content region
    int suppress = RS_NONE;
};

inline int popcount64(uint64_t x) {
    int n = 0;
    while (x) {
        x &= x - 1;
        ++n;
    }
    return n;
}

// 1-cell 8-neighbourhood dilation of a 12 x 4 cell mask.
inline uint64_t dilate_cells(uint64_t m) {
    const uint64_t all = (1ULL << 48) - 1;
    uint64_t left_col = 0, right_col = 0;
    for (int r = 0; r < 4; ++r) {
        left_col |= 1ULL << (r * 12);
        right_col |= 1ULL << (r * 12 + 11);
    }
    uint64_t h = m | ((m & ~right_col) << 1) | ((m & ~left_col) >> 1);
    return (h | (h << 12) | (h >> 12)) & all;
}

class RobustWatcher {
public:
    static const int MAX_BG = 128;
    static const int MAX_REGIONS = 8;

    explicit RobustWatcher(const RobustWatcherParams& p) : p_(p) {
        if (p_.bg_window > MAX_BG) p_.bg_window = MAX_BG;
        if (p_.bg_window < 1) p_.bg_window = 1;
    }

    RobustDecision evaluate(double t_ms, const RobustFeatures& f) {
        RobustDecision d;
        d.score = p_.w_motion * f.motion + p_.w_visual * f.visual + p_.w_temporal * f.temporal +
                  p_.w_consistency * f.consistency;
        double on = p_.theta_max, off = p_.theta_max * p_.fixed_off_ratio, med = 0.0, sigma = p_.sigma_floor;
        if (p_.robust_threshold && bg_n_ >= p_.bg_min) {
            robust_stats(med, sigma);
            on = clamp(med + p_.z_on * sigma, p_.theta_min, p_.theta_max);
            off = clamp(med + p_.z_off * sigma, 0.0, on);
        } else if (bg_n_ >= p_.bg_min) {
            robust_stats(med, sigma);
        }
        d.threshold = on;
        d.z = (d.score - med) / sigma;
        // hysteresis / persistence state machine
        if (!active_) {
            on_run_ = d.score >= on ? on_run_ + 1 : 0;
            if (on_run_ >= p_.persist_k) {
                active_ = true;
                off_run_ = 0;
            }
        } else {
            off_run_ = d.score < off ? off_run_ + 1 : 0;
            if (off_run_ >= p_.release_k) {
                active_ = false;
                on_run_ = 0;
            }
        }
        if (!active_ && d.score < on) push_bg(d.score);
        d.raw_positive = active_;
        if (!active_) {
            d.suppress = (d.score >= on) ? RS_PERSISTENCE : RS_BELOW_THRESHOLD;
            return d;
        }
        // content-aware cooldown
        if (!p_.content_cooldown) {
            if (has_global_ && t_ms - global_last_ < p_.content_cooldown_ms) {
                d.suppress = RS_CONTENT_COOLDOWN;
                return d;
            }
            has_global_ = true;
            global_last_ = t_ms;
            d.trigger = true;
            return d;
        }
        const int cur_n = popcount64(f.cells);
        int best = -1;
        double best_ov = -1.0;
        for (int i = 0; i < MAX_REGIONS; ++i) {
            Region& r = reg_[i];
            if (!r.used || t_ms - r.last_seen_ms > p_.region_ttl_ms) continue;
            double ov;
            if (cur_n == 0 || r.cells == 0) {
                ov = (cur_n == 0 && r.cells == 0) ? 1.0 : 0.0;
            } else {
                ov = static_cast<double>(popcount64(f.cells & dilate_cells(r.cells))) / cur_n;
            }
            if (ov >= p_.overlap_thr && ov > best_ov) {
                best_ov = ov;
                best = i;
            }
        }
        if (best >= 0) {
            Region& r = reg_[best];
            r.cells = f.cells ? f.cells : r.cells;
            r.last_seen_ms = t_ms;
            if (t_ms - r.last_trigger_ms >= p_.content_cooldown_ms) {
                r.last_trigger_ms = t_ms;
                d.trigger = true;
            } else {
                d.suppress = RS_CONTENT_COOLDOWN;
            }
            return d;
        }
        // novel content: take a free/expired slot, else the least recently seen
        int slot = 0;
        double oldest = 1e300;
        for (int i = 0; i < MAX_REGIONS; ++i) {
            const Region& r = reg_[i];
            const double key = (!r.used || t_ms - r.last_seen_ms > p_.region_ttl_ms) ? -1e300 : r.last_seen_ms;
            if (key < oldest) {
                oldest = key;
                slot = i;
            }
        }
        reg_[slot] = Region{true, f.cells, t_ms, t_ms};
        d.trigger = true;
        d.novel = true;
        return d;
    }

    bool active() const { return active_; }

private:
    struct Region {
        bool used = false;
        uint64_t cells = 0;
        double last_seen_ms = 0.0;
        double last_trigger_ms = 0.0;
    };
    RobustWatcherParams p_;
    double bg_[MAX_BG] = {};
    int bg_head_ = 0, bg_n_ = 0;
    bool active_ = false;
    int on_run_ = 0, off_run_ = 0;
    Region reg_[MAX_REGIONS];
    bool has_global_ = false;
    double global_last_ = 0.0;

    static double clamp(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }

    void push_bg(double s) {
        bg_[bg_head_] = s;
        bg_head_ = (bg_head_ + 1) % p_.bg_window;
        if (bg_n_ < p_.bg_window) ++bg_n_;
    }

    // Median and 1.4826 * MAD of the background history (insertion sort of
    // at most 128 values: bounded M4 cost).
    void robust_stats(double& med, double& sigma) const {
        double a[MAX_BG] = {};
        for (int i = 0; i < bg_n_; ++i) a[i] = bg_[i];
        sort(a, bg_n_);
        med = median_sorted(a, bg_n_);
        for (int i = 0; i < bg_n_; ++i) a[i] = a[i] > med ? a[i] - med : med - a[i];
        sort(a, bg_n_);
        const double mad = median_sorted(a, bg_n_);
        sigma = 1.4826 * mad;
        if (sigma < p_.sigma_floor) sigma = p_.sigma_floor;
    }
    static void sort(double* a, int n) {
        for (int i = 1; i < n; ++i) {
            const double x = a[i];
            int j = i - 1;
            while (j >= 0 && a[j] > x) {
                a[j + 1] = a[j];
                --j;
            }
            a[j + 1] = x;
        }
    }
    static double median_sorted(const double* a, int n) {
        if (n == 0) return 0.0;
        return (n % 2) ? a[n / 2] : 0.5 * (a[n / 2 - 1] + a[n / 2]);
    }
};

}  // namespace sim
