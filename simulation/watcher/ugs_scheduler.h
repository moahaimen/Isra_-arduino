// R3 Utility-Gated Scheduler (UGS): closed-loop M4 activation scheduler for
// the M7 detector.
//
// Header-only, fixed-size state, no heap: Cortex-M4 compatible. Inputs are
// observable only: the gain-compensated frame features, the 12x4 motion-cell
// mask, the M4's own request bookkeeping, the M7 power state, and the RESULTS
// of past M7 inferences (cell mask of detected boxes) delivered back over RPC.
// It never sees labels, attack labels, future frames, or the prediction of
// the frame it is deciding about.
//
// Per frame t (score S_t as in the R2 watcher):
//   med_t, sigma_t   median and max(1.4826 MAD, sigma_floor) of recent IDLE scores
//                    (empty-scene prior b_prior / sigma_prior until bg_min samples),
//                    capped at b_cap / sigma_cap
//   e_t   = 0                                   if S_t < s_floor
//         = min(e_max, max(0, (S_t-med_t)/sigma_t - z0))   otherwise       (bounded excess evidence)
//   A_t   = rho * A_{t-1} + e_t                  (leaky evidence accumulator)
//   ACTIVE when A_t >= a_on, IDLE when A_t < a_off (hysteresis). With
//   e_max < a_on a single frame can never activate the watcher; strong evidence
//   activates after 2 frames, weak persistent evidence after a few more.
// While ACTIVE, frame t is mapped to a content region (cell-mask overlap with
// a 1-cell dilation, <= 8 regions). Region state: requests sent n_req, M7
// confirmations n_hit, last request time, in-flight flag. Utility rule:
//   novel region                      -> request now (novelty)
//   request in flight for the region  -> wait for its result
//   confirmed region (last result hit)-> refresh period dt_track
//   unverified, n_req < k_retry       -> retry period dt_retry (the detector may have missed)
//   barren (n_req >= k_retry, no hit) -> dt_barren * 2^(n_req - k_retry), capped (back-off)
// Cost/load: a due non-novel request is deferred while >= max_inflight
// requests are outstanding; when the M7 is already awake (no wake-up cost)
// the period is multiplied by awake_factor (<= 1).
// Feedback: when the result of a request arrives, the region is CONFIRMED if
// the detected-box cell mask overlaps the region's dilated cells.
#pragma once

#include <cstdint>

#include "watcher/robust_watcher.h"

namespace sim {

enum UgsSuppress {
    US_NONE = 0,
    US_BELOW = 1,        // accumulator below the activation threshold
    US_INFLIGHT = 2,     // waiting for the result of this region's request
    US_NOT_DUE = 3,      // region's next request not due yet
    US_LOAD = 4,         // deferred: too many outstanding requests
};

struct UgsParams {
    double w_motion = 0.30, w_visual = 0.35, w_temporal = 0.20, w_consistency = 0.15;
    int bg_window = 64;
    int bg_min = 8;
    double sigma_floor = 0.02;
    double b_prior = 0.15;       // empty-scene score (consistency term only)
    double sigma_prior = 0.05;
    double b_cap = 0.35;
    double sigma_cap = 0.10;
    double s_floor = 0.10;
    double z0 = 1.0;
    double e_max = 4.0;
    double rho = 0.7;
    double a_on = 5.0;
    double a_off = 2.0;
    double dt_retry_ms = 300.0;
    int k_retry = 3;
    double dt_track_ms = 1000.0;
    double dt_barren_ms = 2000.0;
    double barren_cap_ms = 16000.0;
    double overlap_thr = 0.3;
    double region_ttl_ms = 10000.0;
    int max_inflight = 2;
    double awake_factor = 0.5;
    double inflight_timeout_ms = 2000.0;
    // ---- R3.1 mechanisms (all default OFF = exact R3 behaviour) ----
    // noise_norm: drop the absolute evidence floor s_floor and the baseline/scale caps, so that the
    //   evidence is a pure z-score against the scene's own idle statistics (noisy scenes raise sigma).
    int noise_norm = 0;
    // hold_ms: a region confirmed by the M7 keeps the scheduler engaged (even if the evidence
    //   accumulator fell below a_off) for hold_ms after the confirmation.
    double hold_ms = 0.0;
    // value_rule: refresh period of a region = dt_track / max(p_hit, p_min), p_hit the Beta posterior
    //   mean (hits + alpha) / (requests + alpha + beta) of decayed counts (forgetting factor gamma per request).
    int value_rule = 0;
    double vr_alpha = 1.0, vr_beta = 1.0, vr_gamma = 0.9, vr_pmin = 0.1;
};

struct UgsInput {
    double motion, visual, temporal, consistency;
    uint64_t cells;
    bool m7_awake;    // M7 not in stop mode (no wake-up cost)
    int outstanding;  // this M4's requests without a result yet
};

struct UgsDecision {
    double score = 0.0, evidence = 0.0, accum = 0.0, threshold = 0.0, z = 0.0;
    bool active = false;
    bool trigger = false;
    bool novel = false;
    int region = -1;            // first region of the frame (for logs)
    uint8_t region_mask = 0;    // all content regions present in the frame
    int suppress = US_NONE;
};

class UgsScheduler {
public:
    static const int MAX_BG = 128;
    static const int REGIONS = 8;
    static const int MAX_COMP = 8;

    explicit UgsScheduler(const UgsParams& p) : p_(p) {
        if (p_.bg_window > MAX_BG) p_.bg_window = MAX_BG;
        if (p_.bg_window < 1) p_.bg_window = 1;
    }

    UgsDecision evaluate(double t, const UgsInput& in) {
        UgsDecision d;
        d.score = p_.w_motion * in.motion + p_.w_visual * in.visual + p_.w_temporal * in.temporal +
                  p_.w_consistency * in.consistency;
        // baseline/scale: empty-scene prior until bg_min idle samples exist,
        // then median / 1.4826 MAD of idle scores, both capped so that a busy
        // or noisy scene cannot raise them without bound
        if (p_.noise_norm && bg_n_ < p_.bg_min) {  // R3.1: learn the scene's own statistics before judging it
            push_bg(d.score);
            d.suppress = US_BELOW;
            return d;
        }
        double med = p_.b_prior, sigma = p_.sigma_prior;
        const bool warm = bg_n_ >= p_.bg_min;
        if (warm) stats(med, sigma);
        if (!p_.noise_norm) {
            if (med > p_.b_cap) med = p_.b_cap;
            if (sigma > p_.sigma_cap) sigma = p_.sigma_cap;
        }
        d.z = (d.score - med) / sigma;
        double e = 0.0;
        if (p_.noise_norm || d.score >= p_.s_floor) {
            e = d.z - p_.z0;
            if (e < 0.0) e = 0.0;
            if (e > p_.e_max) e = p_.e_max;
        }
        accum_ = p_.rho * accum_ + e;
        d.evidence = e;
        d.accum = accum_;
        d.threshold = p_.a_on;
        if (!active_ && accum_ >= p_.a_on) active_ = true;
        else if (active_ && accum_ < p_.a_off) active_ = false;
        if (!active_) push_bg(d.score);  // idle background sample (robust median tolerates onset frames)
        bool held = false;
        if (!active_ && p_.hold_ms > 0.0) {
            for (int i = 0; i < REGIONS; ++i)
                if (reg_[i].used && reg_[i].confirmed && t - reg_[i].last_confirm < p_.hold_ms) held = true;
        }
        d.active = active_ || held;
        if (!d.active) {
            d.suppress = US_BELOW;
            return d;
        }
        // content regions: one per connected component of the motion-cell mask
        uint64_t comps[MAX_COMP];
        const int nc = components(in.cells, comps);
        bool any_due = false, any_novel = false, any_inflight = false;
        uint8_t mask = 0;
        for (int c = 0; c < nc; ++c) {
            bool novel = false;
            const int ri = match_or_create(t, comps[c], novel);
            Region& r = reg_[ri];
            mask |= static_cast<uint8_t>(1u << ri);
            if (novel) {
                any_novel = true;
                continue;
            }
            if (r.inflight && t - r.last_req < p_.inflight_timeout_ms) {
                any_inflight = true;
                continue;
            }
            r.inflight = false;
            double period;
            if (p_.value_rule) {
                double ph = (r.hits_w + p_.vr_alpha) / (r.req_w + p_.vr_alpha + p_.vr_beta);
                if (ph < p_.vr_pmin) ph = p_.vr_pmin;
                period = p_.dt_track_ms / ph;
                if (period > p_.barren_cap_ms) period = p_.barren_cap_ms;
                if (!r.confirmed && r.n_req < p_.k_retry && period > p_.dt_retry_ms) period = p_.dt_retry_ms;
            } else if (r.confirmed) period = p_.dt_track_ms;
            else if (r.n_req < p_.k_retry) period = p_.dt_retry_ms;
            else {
                period = p_.dt_barren_ms;
                for (int k = p_.k_retry; k < r.n_req && period < p_.barren_cap_ms; ++k) period *= 2.0;
                if (period > p_.barren_cap_ms) period = p_.barren_cap_ms;
            }
            if (in.m7_awake) period *= p_.awake_factor;
            if (t - r.last_req >= period) any_due = true;
        }
        d.region_mask = mask;
        d.region = mask ? __builtin_ctz(mask) : -1;
        d.novel = any_novel;
        if (any_novel) {
            d.trigger = true;
            return d;
        }
        if (!any_due) {
            d.suppress = any_inflight ? US_INFLIGHT : US_NOT_DUE;
            return d;
        }
        if (in.outstanding >= p_.max_inflight) {
            d.suppress = US_LOAD;
            return d;
        }
        d.trigger = true;
        return d;
    }

    // The request for this frame was actually sent (after the security gate):
    // every region of the frame is checked by the one M7 inference.
    void commit(double t, uint8_t region_mask) {
        for (int i = 0; i < REGIONS; ++i) {
            if (!(region_mask >> i & 1u)) continue;
            Region& r = reg_[i];
            r.inflight = true;
            r.last_req = t;
            ++r.n_req;
            r.req_w = p_.vr_gamma * r.req_w + 1.0;
            r.hits_w *= p_.vr_gamma;
        }
    }

    // Result of that inference arrived at the M4 (detected-box cell mask).
    void feedback(uint8_t region_mask, uint64_t detected_cells, double t) {
        for (int i = 0; i < REGIONS; ++i) {
            if (!(region_mask >> i & 1u)) continue;
            Region& r = reg_[i];
            r.inflight = false;
            const bool hit = detected_cells != 0 &&
                             ((r.cells == 0) || (detected_cells & dilate_cells(r.cells)) != 0);
            r.confirmed = hit;
            if (hit) {
                ++r.n_hit;
                r.hits_w += 1.0;
                r.last_confirm = t;
            }
        }
    }

    bool active() const { return active_; }

private:
    struct Region {
        bool used = false;
        uint64_t cells = 0;
        double last_seen = 0.0, last_req = -1e300;
        int n_req = 0, n_hit = 0;
        double req_w = 0.0, hits_w = 0.0, last_confirm = -1e300;
        bool confirmed = false, inflight = false;
    };
    UgsParams p_;
    double bg_[MAX_BG] = {};
    int bg_head_ = 0, bg_n_ = 0;
    double accum_ = 0.0;
    bool active_ = false;
    Region reg_[REGIONS];

    // Connected components (8-connectivity) of a 12x4 cell mask; an empty mask
    // is one "unlocalised" component. At most MAX_COMP components (the
    // smallest ones are merged into the last).
    static int components(uint64_t m, uint64_t* out) {
        if (m == 0) {
            out[0] = 0;
            return 1;
        }
        int n = 0;
        uint64_t rest = m;
        while (rest) {
            uint64_t comp = rest & (~rest + 1);  // lowest set bit
            for (;;) {
                const uint64_t grown = dilate_cells(comp) & m;
                if (grown == comp) break;
                comp = grown;
            }
            rest &= ~comp;
            if (n < MAX_COMP) out[n++] = comp;
            else out[MAX_COMP - 1] |= comp;
        }
        return n;
    }

    int match_or_create(double t, uint64_t cells, bool& novel) {
        const int n = popcount64(cells);
        int best = -1;
        double best_ov = -1.0;
        for (int i = 0; i < REGIONS; ++i) {
            const Region& r = reg_[i];
            if (!r.used || t - r.last_seen > p_.region_ttl_ms) continue;
            double ov;
            if (n == 0 || r.cells == 0) ov = (n == 0 && r.cells == 0) ? 1.0 : 0.0;
            else ov = static_cast<double>(popcount64(cells & dilate_cells(r.cells))) / n;
            if (p_.overlap_thr <= 0.0) ov = 1.0;  // ablation: no novelty (one shared region)
            if (ov >= p_.overlap_thr && ov > best_ov) {
                best_ov = ov;
                best = i;
            }
        }
        novel = best < 0;
        if (novel) best = new_region(t, cells);
        Region& r = reg_[best];
        r.cells = cells ? cells : r.cells;
        r.last_seen = t;
        return best;
    }

    int new_region(double t, uint64_t cells) {
        int slot = 0;
        double oldest = 1e300;
        for (int i = 0; i < REGIONS; ++i) {
            const Region& r = reg_[i];
            const double key = (!r.used || t - r.last_seen > p_.region_ttl_ms) ? -1e300 : r.last_seen;
            if (key < oldest) {
                oldest = key;
                slot = i;
            }
        }
        reg_[slot] = Region();
        reg_[slot].used = true;
        reg_[slot].cells = cells;
        reg_[slot].last_seen = t;
        return slot;
    }
    void push_bg(double s) {
        bg_[bg_head_] = s;
        bg_head_ = (bg_head_ + 1) % p_.bg_window;
        if (bg_n_ < p_.bg_window) ++bg_n_;
    }
    void stats(double& med, double& sigma) const {
        double a[MAX_BG] = {};
        for (int i = 0; i < bg_n_; ++i) a[i] = bg_[i];
        isort(a, bg_n_);
        med = (bg_n_ % 2) ? a[bg_n_ / 2] : 0.5 * (a[bg_n_ / 2 - 1] + a[bg_n_ / 2]);
        for (int i = 0; i < bg_n_; ++i) a[i] = a[i] > med ? a[i] - med : med - a[i];
        isort(a, bg_n_);
        const double mad = (bg_n_ % 2) ? a[bg_n_ / 2] : 0.5 * (a[bg_n_ / 2 - 1] + a[bg_n_ / 2]);
        sigma = 1.4826 * mad;
        if (sigma < p_.sigma_floor) sigma = p_.sigma_floor;
    }
    static void isort(double* a, int n) {
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
};

}  // namespace sim
